import json
import re
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage
import operator

from app.config import get_settings
from app.agents.tools import create_zoho_tools
from app.zoho.client import ZohoClient
from app.memory.memory_store import MemoryStore

settings = get_settings()


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    user_id: str
    session_id: str
    current_agent: str
    pending_action: Optional[dict]
    requires_confirmation: bool
    long_term_context: str
    session_context: dict
    current_user_message: str   # ← router reads THIS, not messages[-1]


class ZohoChatGraph:
    def __init__(self, zoho_client: ZohoClient, memory_store: MemoryStore):
        self.zoho_client = zoho_client
        self.memory_store = memory_store
        self.llm = ChatGroq(
            api_key=settings.groq_api_key,
            model="llama-3.3-70b-versatile",
            temperature=0,
        )
        self.query_tools, self.action_tools = create_zoho_tools(zoho_client)
        self.all_tools = self.query_tools + self.action_tools
        self.graph = self._build_graph()

    def _build_graph(self):
        query_llm = self.llm.bind_tools(self.query_tools)
        action_llm = self.llm.bind_tools(self.action_tools)

        async def router_node(state: AgentState) -> AgentState:
            # Always use current_user_message so router never reads stale history
            user_msg = state.get("current_user_message", "")

            prompt = (
                "Classify this user request as exactly 'query' or 'action'.\n\n"
                "query = read-only: list projects, list tasks, get details, members, reports.\n"
                "action = write: create task, update task, delete task, assign task.\n\n"
                f"User: \"{user_msg}\"\n\n"
                "Reply with ONE word only: query or action"
            )
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            agent = "action" if "action" in response.content.lower().strip() else "query"
            return {**state, "current_agent": agent}

        async def query_agent_node(state: AgentState) -> AgentState:
            system = SystemMessage(content=(
                "You are a Zoho Projects AI assistant (read-only mode).\n"
                "Answer using the available tools. Be concise.\n\n"
                f"Long-term context:\n{state.get('long_term_context', 'None')}\n\n"
                f"Session context:\n"
                f"- Project ID: {state.get('session_context', {}).get('current_project_id', 'None')}\n"
                f"- Project name: {state.get('session_context', {}).get('current_project_name', 'None')}"
            ))
            response = await query_llm.ainvoke([system] + state["messages"])
            return {**state, "messages": [response]}

        async def action_agent_node(state: AgentState) -> AgentState:
            system = SystemMessage(content=(
                "You are a Zoho Projects AI assistant (write mode).\n"
                "Handle create / update / delete operations using the available tools.\n\n"
                f"Long-term context:\n{state.get('long_term_context', 'None')}\n\n"
                f"Session context:\n"
                f"- Project ID: {state.get('session_context', {}).get('current_project_id', 'None')}\n"
                f"- Project name: {state.get('session_context', {}).get('current_project_name', 'None')}\n\n"
                "When a tool returns requires_confirmation=true, tell the user exactly what will happen "
                "and ask them to reply YES or NO."
            ))
            response = await action_llm.ainvoke([system] + state["messages"])
            return {**state, "messages": [response]}

        async def tool_executor_node(state: AgentState) -> AgentState:
            last = state["messages"][-1]
            if not hasattr(last, "tool_calls") or not last.tool_calls:
                return state

            tool_node = ToolNode(self.all_tools)
            result = await tool_node.ainvoke(state)
            new_messages = result.get("messages", []) if isinstance(result, dict) else []

            for msg in new_messages:
                content = getattr(msg, "content", None)
                if not content:
                    continue
                try:
                    parsed = json.loads(content)
                    if isinstance(parsed, dict) and parsed.get("requires_confirmation"):
                        return {
                            **state,
                            "messages": new_messages,
                            "pending_action": parsed,
                            "requires_confirmation": True,
                        }
                except (json.JSONDecodeError, TypeError):
                    continue

            return {**state, "messages": new_messages, "requires_confirmation": False}

        def should_use_tools(state: AgentState) -> str:
            last = state["messages"][-1]
            return "tools" if hasattr(last, "tool_calls") and last.tool_calls else "end"

        def after_tools(state: AgentState) -> str:
            return "end" if state.get("requires_confirmation") else should_use_tools(state)

        graph = StateGraph(AgentState)
        graph.add_node("router", router_node)
        graph.add_node("query_agent", query_agent_node)
        graph.add_node("action_agent", action_agent_node)
        graph.add_node("tool_executor", tool_executor_node)

        graph.set_entry_point("router")

        graph.add_conditional_edges(
            "router",
            lambda s: s["current_agent"],
            {"query": "query_agent", "action": "action_agent"},
        )
        graph.add_conditional_edges("query_agent", should_use_tools, {"tools": "tool_executor", "end": END})
        graph.add_conditional_edges("action_agent", should_use_tools, {"tools": "tool_executor", "end": END})
        graph.add_conditional_edges("tool_executor", after_tools, {"tools": "tool_executor", "end": END})

        return graph.compile()

    async def chat(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        confirmation: Optional[bool] = None,
        pending_action: Optional[dict] = None,
    ) -> dict:
        # Step 1: Recover pending_action from history FIRST before anything else
        if pending_action is None:
            raw_history = await self.memory_store.get_session_history(session_id)
            for msg in reversed(raw_history):
                meta = msg.get("metadata", {})
                if isinstance(meta, dict) and meta.get("pending_action"):
                    pending_action = meta["pending_action"]
                    break

        # Step 2: THEN normalise yes/no (now pending_action is already set)
        normalized = user_message.strip().lower()
        if normalized in {"yes", "yes, confirm", "confirm", "y"}:
            confirmation = True
        elif normalized in {"no", "cancel", "n"}:
            confirmation = False

        # Step 3: Confirmed — execute directly
        if confirmation is True and pending_action:
            result_msg = await self._execute_action(pending_action)
            await self.memory_store.save_message(session_id, "user", user_message)
            await self.memory_store.save_message(session_id, "assistant", result_msg)
            return {"response": result_msg, "requires_confirmation": False, "pending_action": None}

        # Step 4: Cancelled
        if confirmation is False:
            cancel_msg = "❌ Action cancelled. No changes were made."
            await self.memory_store.save_message(session_id, "user", user_message)
            await self.memory_store.save_message(session_id, "assistant", cancel_msg)
            return {"response": cancel_msg, "requires_confirmation": False, "pending_action": None}

        # Context-aware message rewriting
        session_context = await self.memory_store.get_session_context(session_id)

        if "first" in user_message.lower() and session_context.get("current_project_id"):
            user_message = f"show tasks for project {session_context['current_project_id']}"

        if "delete" in user_message.lower():
            match = re.search(r"#?(\d+)", user_message)
            if match and session_context.get("current_project_id"):
                user_message = (
                    f"delete task {match.group(1)} "
                    f"in project {session_context['current_project_id']}"
                )

        if "most tasks" in user_message.lower() and session_context.get("current_project_id"):
            user_message = f"get task utilisation for project {session_context['current_project_id']}"

        # Fetch history BEFORE saving the new message (avoids duplication)
        history = await self.memory_store.get_session_history(session_id)
        await self.memory_store.save_message(session_id, "user", user_message)

        # Build LangChain message list from PREVIOUS history only
        lc_messages: list[BaseMessage] = []
        for msg in history:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        # Append the new user message ONCE at the end
        lc_messages.append(HumanMessage(content=user_message))

        long_term = await self.memory_store.get_long_term_summary()

        initial_state: AgentState = {
            "messages": lc_messages,
            "user_id": user_id,
            "session_id": session_id,
            "current_agent": "query",
            "pending_action": None,
            "requires_confirmation": False,
            "long_term_context": long_term,
            "session_context": session_context,
            "current_user_message": user_message,  # router reads this
        }

        result = await self.graph.ainvoke(initial_state, config={"recursion_limit": 25})

        result_dict = result if isinstance(result, dict) else {}
        pending = result_dict.get("pending_action")
        requires_conf = result_dict.get("requires_confirmation", False)

        last_msg = ""
        for msg in reversed(result_dict.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content:
                last_msg = msg.content
                break

        if requires_conf and pending:
            last_msg = (
                f"⚠️ **Confirmation Required**\n\n"
                f"I'm about to: **{pending.get('summary', 'perform an action')}**\n\n"
                f"Reply **YES** to confirm or **NO** to cancel."
            )

        save_meta: dict = {}
        if pending:
            save_meta["pending_action"] = pending
            details = pending.get("details", {})
            if details.get("project_id"):
                save_meta["project_id"] = details["project_id"]
            if details.get("task_id"):
                save_meta["task_id"] = details["task_id"]

        await self.memory_store.save_message(
            session_id, "assistant", last_msg, metadata=save_meta
        )

        if session_context.get("current_project_id"):
            await self.memory_store.save_long_term(
                "context", "last_project_id", session_context["current_project_id"]
            )

        return {
            "response": last_msg,
            "requires_confirmation": requires_conf,
            "pending_action": pending,
        }

    async def _execute_action(self, pending_action: dict) -> str:
        action = pending_action.get("action")
        details = pending_action.get("details", {})
        try:
            if action == "create_task":
                res = await self.zoho_client.create_task(**details)
                return f"✅ Task **'{res.get('name', details.get('name'))}'** created! ID: `{res.get('id')}`"
            elif action == "update_task":
                await self.zoho_client.update_task(**details)
                return f"✅ Task `{details.get('task_id')}` updated successfully!"
            elif action == "delete_task":
                await self.zoho_client.delete_task(details["project_id"], details["task_id"])
                return f"✅ Task `{details.get('task_id')}` has been permanently deleted."
            return f"❌ Unknown action type: `{action}`"
        except Exception as e:
            return f"❌ Action failed: {str(e)}"