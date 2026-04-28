import json
import uuid
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
            last_message = state["messages"][-1].content if state["messages"] else ""

            prompt = f"""Classify this as 'query' or 'action'.

Message: "{last_message}"
Answer ONLY 'query' or 'action'."""

            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.lower().strip()

            if "action" in content:
                agent = "action"
            else:
                agent = "query"

            return {**state, "current_agent": agent}

        async def query_agent_node(state: AgentState) -> AgentState:
            system_prompt = f"""You are Query Agent. Only read operations."""

            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await query_llm.ainvoke(messages)
            return {**state, "messages": [response]}

        async def action_agent_node(state: AgentState) -> AgentState:
            system_prompt = f"""You are Action Agent. Only write operations."""

            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await action_llm.ainvoke(messages)
            return {**state, "messages": [response]}

        async def tool_executor_node(state: AgentState) -> AgentState:
            last = state["messages"][-1]

            if not hasattr(last, "tool_calls") or not last.tool_calls:
                return state

            tool_node = ToolNode(self.all_tools)
            result = await tool_node.ainvoke(state)

            # SAFE handling
            if isinstance(result, dict):
                data = result
            else:
                data = getattr(result, "__dict__", {})

            new_messages = data.get("messages", [])

            for msg in new_messages:
                if hasattr(msg, "content"):
                    try:
                        parsed = json.loads(msg.content)
                        if parsed.get("requires_confirmation"):
                            return {
                                **state,
                                "messages": new_messages,
                                "pending_action": parsed,
                                "requires_confirmation": True,
                            }
                    except:
                        continue

            return {
                **state,
                "messages": new_messages,
                "requires_confirmation": False,
            }

        def should_use_tools(state: AgentState):
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "end"

        def after_tools(state: AgentState):
            if state.get("requires_confirmation"):
                return "end"
            return should_use_tools(state)

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

        long_term = await self.memory_store.get_long_term_summary()
        session_context = await self.memory_store.get_session_context(session_id)
        history = await self.memory_store.get_session_history(session_id)

        await self.memory_store.save_message(session_id, "user", user_message)

        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))

        messages.append(HumanMessage(content=user_message))

        # HANDLE CONFIRMATION
        if confirmation is True and pending_action:
            result = await self._execute_action(pending_action)
            await self.memory_store.save_message(session_id, "assistant", result)
            return {"response": result, "requires_confirmation": False, "pending_action": None}

        if confirmation is False and pending_action:
            msg = "❌ Action cancelled."
            await self.memory_store.save_message(session_id, "assistant", msg)
            return {"response": msg, "requires_confirmation": False, "pending_action": None}

        initial_state: AgentState = {
            "messages": messages,
            "user_id": user_id,
            "session_id": session_id,
            "current_agent": "query",
            "pending_action": None,
            "requires_confirmation": False,
            "long_term_context": long_term,
            "session_context": session_context,
        }

        result = await self.graph.ainvoke(initial_state, config={"recursion_limit": 25})

        # SAFE normalize
        if isinstance(result, dict):
            data = result
        else:
            data = getattr(result, "__dict__", {})

        response_messages = data.get("messages", [])
        pending = data.get("pending_action")
        requires_conf = data.get("requires_confirmation", False)

        last_msg = ""
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and msg.content:
                last_msg = msg.content
                break

        if requires_conf and pending:
            last_msg = f"""⚠️ Confirmation Required

{pending.get('summary')}

Reply YES to confirm or NO to cancel."""

        await self.memory_store.save_message(
            session_id,
            "assistant",
            last_msg,
            metadata={"pending_action": pending} if pending else {},
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
                return f"Task created: {res.get('id')}"
            elif action == "update_task":
                await self.zoho_client.update_task(**details)
                return "Task updated"
            elif action == "delete_task":
                await self.zoho_client.delete_task(details["project_id"], details["task_id"])
                return "Task deleted"
            return "Unknown action"
        except Exception as e:
            return f"Error: {str(e)}"