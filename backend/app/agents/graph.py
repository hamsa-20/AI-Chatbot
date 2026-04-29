import json
import re
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage, BaseMessage, ToolMessage
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
    current_user_message: str


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
            user_msg = state.get("current_user_message", "")
            prompt = (
                "Classify this user request as exactly 'query' or 'action'.\n\n"
                "query = read-only: list projects, list tasks, get details, members, reports, who has most tasks.\n"
                "action = write: create task, update task, delete task, assign task.\n\n"
                f"User: \"{user_msg}\"\n\n"
                "Reply with ONE word only: query or action"
            )
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            agent = "action" if "action" in response.content.lower().strip() else "query"
            return {**state, "current_agent": agent}

        async def query_agent_node(state: AgentState) -> AgentState:
            ctx = state.get("session_context", {})
            system = SystemMessage(content=(
                "You are a Zoho Projects AI assistant (read-only mode).\n"
                "Use the available tools to answer questions. Be concise and friendly.\n\n"
                f"Long-term context:\n{state.get('long_term_context', 'None')}\n\n"
                "Current session context:\n"
                f"- Current Project ID: {ctx.get('current_project_id', 'None')}\n"
                f"- Current Project Name: {ctx.get('current_project_name', 'None')}\n"
                f"- Recent Task IDs: {ctx.get('recent_task_ids', [])}\n\n"
                "IMPORTANT RULES:\n"
                "- If asked about 'the first one' or 'first project', use the current_project_id from context.\n"
                "- For 'who has the most tasks this month' or task utilisation questions, "
                "  call get_task_utilisation with the current project ID from context.\n"
                "- Always prefer context over asking the user to repeat information.\n"
                "- After receiving tool results, ALWAYS provide a clear, human-readable summary. Never leave the response empty."
            ))
            response = await query_llm.ainvoke([system] + state["messages"])
            return {**state, "messages": [response]}

        async def action_agent_node(state: AgentState) -> AgentState:
            ctx = state.get("session_context", {})
            system = SystemMessage(content=(
                "You are a Zoho Projects AI assistant (write mode).\n"
                "Handle create / update / delete operations using the available tools.\n\n"
                f"Long-term context:\n{state.get('long_term_context', 'None')}\n\n"
                "Current session context:\n"
                f"- Current Project ID: {ctx.get('current_project_id', 'None')}\n"
                f"- Current Project Name: {ctx.get('current_project_name', 'None')}\n"
                f"- Recent Task IDs: {ctx.get('recent_task_ids', [])}\n\n"
                "IMPORTANT RULES:\n"
                "- ALWAYS use the current_project_id from context when the user says 'this project' or doesn't specify.\n"
                "- When deleting, use task IDs from recent_task_ids if the user says '#5' or 'task 5'.\n"
                "- After calling a tool that requires confirmation, tell the user EXACTLY what will happen "
                "  and ask them to reply YES or NO.\n"
                "- After receiving tool results, ALWAYS provide a clear, human-readable summary. Never leave the response empty."
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

        # ✅ PART 1: REPLACED after_tools function
        def after_tools(state: AgentState) -> str:
            if state.get("requires_confirmation"):
                return "end"
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            if isinstance(last, ToolMessage):
                return state.get("current_agent", "query")  # returns "query" or "action"
            return "end"

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
        graph.add_conditional_edges(
            "query_agent",
            should_use_tools,
            {"tools": "tool_executor", "end": END}
        )
        graph.add_conditional_edges(
            "action_agent",
            should_use_tools,
            {"tools": "tool_executor", "end": END}
        )
        
        # ✅ PART 2: REPLACED conditional edges for tool_executor
        graph.add_conditional_edges(
            "tool_executor",
            after_tools,
            {
                "tools": "tool_executor",
                "query": "query_agent",    # ✅ matches "query" returned by after_tools
                "action": "action_agent",  # ✅ matches "action" returned by after_tools
                "end": END,
            }
        )

        return graph.compile()

    async def chat(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        confirmation: Optional[bool] = None,
        pending_action: Optional[dict] = None,
    ) -> dict:

        # ── Step 1: Recover pending_action from history if not passed in ──
        if pending_action is None:
            raw_history = await self.memory_store.get_session_history(session_id)
            for msg in reversed(raw_history):
                meta = msg.get("metadata", {})
                if isinstance(meta, dict) and meta.get("pending_action"):
                    pending_action = meta["pending_action"]
                    break

        # ── Step 2: Normalise yes/no ──
        normalized = user_message.strip().lower()
        if normalized in {"yes", "yes, confirm", "confirm", "y"}:
            confirmation = True
        elif normalized in {"no", "cancel", "n"}:
            confirmation = False

        # ── Step 3: Confirmed → execute directly ──
        if confirmation is True and pending_action:
            result_msg = await self._execute_action(pending_action)
            await self.memory_store.save_message(session_id, "user", user_message)
            await self.memory_store.save_message(session_id, "assistant", result_msg)
            return {"response": result_msg, "requires_confirmation": False, "pending_action": None}

        # ── Step 4: Cancelled ──
        if confirmation is False:
            cancel_msg = "❌ Action cancelled. No changes were made."
            await self.memory_store.save_message(session_id, "user", user_message)
            await self.memory_store.save_message(session_id, "assistant", cancel_msg)
            return {"response": cancel_msg, "requires_confirmation": False, "pending_action": None}

        # ── Step 5: Load session context ──
        session_context = await self.memory_store.get_session_context(session_id)

        # ── Step 6: Smart message rewriting based on context ──
        original_message = user_message

        if re.search(r"\bfirst\b", user_message.lower()):
            if not session_context.get("current_project_id"):
                try:
                    projects = await self.zoho_client.list_projects()
                    if projects:
                        first = projects[0]
                        session_context["current_project_id"] = str(first.get("id"))
                        session_context["current_project_name"] = first.get("name")
                        await self.memory_store.save_long_term("context", "last_project_id", str(first.get("id")))
                        await self.memory_store.save_long_term("context", "last_project_name", first.get("name", ""))
                except Exception:
                    pass

            pid = session_context.get("current_project_id")
            if pid:
                user_message = f"show tasks for project {pid}"

        elif re.search(r"\bdelete\b", user_message.lower()):
            match = re.search(r"#?(\d+)", user_message)
            pid = session_context.get("current_project_id")
            if match and pid:
                user_message = f"delete task {match.group(1)} in project {pid}"

        elif re.search(r"(most tasks|task utilis|utilization|utilisation)", user_message.lower()):
            pid = session_context.get("current_project_id")
            if pid:
                user_message = f"get task utilisation for project {pid}"
            else:
                try:
                    projects = await self.zoho_client.list_projects()
                    if projects:
                        first = projects[0]
                        pid = str(first.get("id"))
                        session_context["current_project_id"] = pid
                        session_context["current_project_name"] = first.get("name")
                        user_message = f"get task utilisation for project {pid}"
                except Exception:
                    pass

        # ── Step 7: Load history, save new user message ──
        history = await self.memory_store.get_session_history(session_id)
        await self.memory_store.save_message(session_id, "user", original_message)

        lc_messages: list[BaseMessage] = []
        for msg in history:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

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
            "current_user_message": user_message,
        }

        result = await self.graph.ainvoke(initial_state, config={"recursion_limit": 25})

        result_dict = result if isinstance(result, dict) else {}
        pending = result_dict.get("pending_action")
        requires_conf = result_dict.get("requires_confirmation", False)

        # ✅ FIXED: Also check ToolMessages as fallback if AIMessage is empty
        last_msg = ""
        for msg in reversed(result_dict.get("messages", [])):
            if isinstance(msg, AIMessage) and msg.content and not getattr(msg, "tool_calls", None):
                last_msg = msg.content
                break

        # Fallback: collect tool result content if LLM gave no final response
        if not last_msg:
            tool_contents = []
            for msg in result_dict.get("messages", []):
                if isinstance(msg, ToolMessage) and msg.content:
                    try:
                        parsed = json.loads(msg.content)
                        if isinstance(parsed, list):
                            tool_contents.append(json.dumps(parsed, indent=2))
                        elif isinstance(parsed, dict) and not parsed.get("requires_confirmation"):
                            tool_contents.append(json.dumps(parsed, indent=2))
                    except (json.JSONDecodeError, TypeError):
                        tool_contents.append(str(msg.content))
            if tool_contents:
                last_msg = "Here are the results:\n\n" + "\n\n".join(tool_contents)

        if not last_msg:
            last_msg = "I processed your request but couldn't generate a response. Please try again."

        if requires_conf and pending:
            last_msg = (
                f"⚠️ **Confirmation Required**\n\n"
                f"I'm about to: **{pending.get('summary', 'perform an action')}**\n\n"
                f"Reply **YES** to confirm or **NO** to cancel."
            )

        # ── Step 8: Extract and save project/task context ──
        save_meta: dict = {}
        if pending:
            save_meta["pending_action"] = pending
            details = pending.get("details", {})
            if details.get("project_id"):
                save_meta["project_id"] = details["project_id"]
            if details.get("task_id"):
                save_meta["task_id"] = details["task_id"]

        for msg in result_dict.get("messages", []):
            content = getattr(msg, "content", "")
            if not content or not isinstance(content, str):
                continue
            project_id_matches = re.findall(r"\[(\d{6,})\]", content)
            if project_id_matches and not save_meta.get("project_id"):
                save_meta["project_id"] = project_id_matches[0]
            name_match = re.search(r"\d+\.\s+\[\d+\]\s+(.+?)\s+—", content)
            if name_match and not save_meta.get("project_name"):
                save_meta["project_name"] = name_match.group(1).strip()

        await self.memory_store.save_message(session_id, "assistant", last_msg, metadata=save_meta)

        # ── Step 9: Persist project to long-term memory ──
        project_id_to_save = save_meta.get("project_id") or session_context.get("current_project_id")
        project_name_to_save = save_meta.get("project_name") or session_context.get("current_project_name")
        if project_id_to_save:
            await self.memory_store.save_long_term("context", "last_project_id", project_id_to_save)
        if project_name_to_save:
            await self.memory_store.save_long_term("context", "last_project_name", project_name_to_save)

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
                return f"✅ Task **'{res.get('name', details.get('name'))}'** created successfully! ID: `{res.get('id')}`"
            elif action == "update_task":
                await self.zoho_client.update_task(**details)
                return f"✅ Task `{details.get('task_id')}` updated successfully!"
            elif action == "delete_task":
                await self.zoho_client.delete_task(details["project_id"], details["task_id"])
                return f"✅ Task `{details.get('task_id')}` has been permanently deleted."
            return f"❌ Unknown action type: `{action}`"
        except Exception as e:
            return f"❌ Action failed: {str(e)}"