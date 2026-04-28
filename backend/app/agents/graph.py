import json
import uuid
from typing import TypedDict, Annotated, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.messages import BaseMessage
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
            """Decide which agent should handle this message."""
            last_message = state["messages"][-1].content if state["messages"] else ""
            
            router_prompt = f"""You are a router. Classify this user message as either 'query' or 'action'.

Query = read-only operations: listing projects, listing tasks, getting task details, listing members, utilisation reports.
Action = write operations: creating tasks, updating tasks, deleting tasks, assigning tasks.

User message: "{last_message}"

Respond with ONLY one word: 'query' or 'action'"""

            response = await self.llm.ainvoke([HumanMessage(content=router_prompt)])
            agent_type = "query" if "query" in response.content.lower() else "action"
            return {**state, "current_agent": agent_type}

        async def query_agent_node(state: AgentState) -> AgentState:
            """Query agent handles all read operations."""
            system_prompt = f"""You are a helpful Zoho Projects assistant (Query Agent).
You ONLY handle read operations: listing projects, tasks, members, and utilisation.

Long-term user context:
{state.get('long_term_context', 'None')}

Session context:
- Current project ID: {state.get('session_context', {}).get('current_project_id', 'None')}
- Current project name: {state.get('session_context', {}).get('current_project_name', 'None')}

Use the available tools to answer the user's question. Be concise and helpful."""

            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await query_llm.ainvoke(messages)
            return {**state, "messages": [response]}

        async def action_agent_node(state: AgentState) -> AgentState:
            """Action agent handles all write operations with HIL."""
            system_prompt = f"""You are a helpful Zoho Projects assistant (Action Agent).
You ONLY handle write operations: creating, updating, and deleting tasks.

Long-term user context:
{state.get('long_term_context', 'None')}

Session context:
- Current project ID: {state.get('session_context', {}).get('current_project_id', 'None')}
- Current project name: {state.get('session_context', {}).get('current_project_name', 'None')}

IMPORTANT: When you call a write tool, it will return a JSON object with 'requires_confirmation: true'.
Format your response to tell the user EXACTLY what will happen and ask them to confirm with 'yes' or 'no'."""

            messages = [SystemMessage(content=system_prompt)] + state["messages"]
            response = await action_llm.ainvoke(messages)
            return {**state, "messages": [response]}

        async def tool_executor_node(state: AgentState) -> AgentState:
            """Execute tool calls and check for HIL requirement."""
            last_message = state["messages"][-1]
            
            if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
                return state

            tool_node = ToolNode(self.all_tools)
            result = await tool_node.ainvoke(state)
            
            # Check if any tool result requires confirmation
            new_messages = result.get("messages", [])
            for msg in new_messages:
                if hasattr(msg, "content"):
                    try:
                        data = json.loads(msg.content)
                        if data.get("requires_confirmation"):
                            return {
                                **state,
                                "messages": new_messages,
                                "pending_action": data,
                                "requires_confirmation": True,
                            }
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        pass

            return {**state, "messages": new_messages, "requires_confirmation": False}

        async def execute_confirmed_action(state: AgentState) -> AgentState:
            """Execute the confirmed action against Zoho API."""
            pending = state.get("pending_action")
            if not pending:
                return {**state, "messages": [AIMessage(content="No pending action found.")]}

            action = pending.get("action")
            details = pending.get("details", {})

            try:
                if action == "create_task":
                    result = await self.zoho_client.create_task(**details)
                    msg = f"✅ Task '{result.get('name', details.get('name'))}' created successfully! Task ID: {result.get('id')}"
                elif action == "update_task":
                    result = await self.zoho_client.update_task(**details)
                    msg = f"✅ Task {details.get('task_id')} updated successfully!"
                elif action == "delete_task":
                    await self.zoho_client.delete_task(
                        details["project_id"], details["task_id"]
                    )
                    msg = f"✅ Task {details.get('task_id')} deleted successfully."
                else:
                    msg = "Unknown action."
            except Exception as e:
                msg = f"❌ Action failed: {str(e)}"

            return {
                **state,
                "messages": [AIMessage(content=msg)],
                "pending_action": None,
                "requires_confirmation": False,
            }

        def should_use_tools(state: AgentState) -> str:
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "end"

        def after_tools(state: AgentState) -> str:
            if state.get("requires_confirmation"):
                return "end"  # Return to user for confirmation
            last = state["messages"][-1]
            if hasattr(last, "tool_calls") and last.tool_calls:
                return "tools"
            return "end"

        # Build the graph
        graph = StateGraph(AgentState)

        graph.add_node("router", router_node)
        graph.add_node("query_agent", query_agent_node)
        graph.add_node("action_agent", action_agent_node)
        graph.add_node("tool_executor", tool_executor_node)
        graph.add_node("execute_confirmed", execute_confirmed_action)

        graph.set_entry_point("router")

        graph.add_conditional_edges(
            "router",
            lambda s: s["current_agent"],
            {"query": "query_agent", "action": "action_agent"},
        )

        graph.add_conditional_edges(
            "query_agent", should_use_tools, {"tools": "tool_executor", "end": END}
        )

        graph.add_conditional_edges(
            "action_agent", should_use_tools, {"tools": "tool_executor", "end": END}
        )

        graph.add_conditional_edges(
            "tool_executor", after_tools, {"tools": "tool_executor", "end": END}
        )

        graph.add_edge("execute_confirmed", END)

        return graph.compile()

    async def chat(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        confirmation: Optional[bool] = None,
        pending_action: Optional[dict] = None,
    ) -> dict:
        # Load memory
        long_term = await self.memory_store.get_long_term_summary()
        session_context = await self.memory_store.get_session_context(session_id)
        history = await self.memory_store.get_session_history(session_id)

        # Save user message
        await self.memory_store.save_message(session_id, "user", user_message)

        # Build message history
        messages = []
        for msg in history:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        messages.append(HumanMessage(content=user_message))

        # Handle confirmed action
        if confirmation is True and pending_action:
            initial_state: AgentState = {
                "messages": messages,
                "user_id": user_id,
                "session_id": session_id,
                "current_agent": "action",
                "pending_action": pending_action,
                "requires_confirmation": False,
                "long_term_context": long_term,
                "session_context": session_context,
            }
            result = await self.graph.ainvoke(
                initial_state,
                config={"recursion_limit": 10},
                # Jump straight to execute
            )
            # Manually execute since graph routing is complex for this path
            exec_result = await self._execute_action(pending_action)
            await self.memory_store.save_message(session_id, "assistant", exec_result)
            return {
                "response": exec_result,
                "requires_confirmation": False,
                "pending_action": None,
            }

        if confirmation is False and pending_action:
            cancel_msg = "❌ Action cancelled. No changes were made."
            await self.memory_store.save_message(session_id, "assistant", cancel_msg)
            return {
                "response": cancel_msg,
                "requires_confirmation": False,
                "pending_action": None,
            }

        # Normal flow
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

        result = await self.graph.ainvoke(
            initial_state,
            config={"recursion_limit": 25},
        )

        # Extract response
        response_messages = result.get("messages", [])
        last_ai_msg = ""
        for msg in reversed(response_messages):
            if isinstance(msg, AIMessage) and msg.content:
                last_ai_msg = msg.content
                break

        pending = result.get("pending_action")
        requires_conf = result.get("requires_confirmation", False)

        if requires_conf and pending:
            last_ai_msg = (
                f"⚠️ **Confirmation Required**\n\n"
                f"I'm about to: **{pending.get('summary')}**\n\n"
                f"Do you want to proceed? Reply with **yes** to confirm or **no** to cancel."
            )

        # Update session context in memory
        if session_context.get("current_project_id"):
            await self.memory_store.save_long_term(
                "context", "last_project_id", session_context["current_project_id"]
            )

        await self.memory_store.save_message(
            session_id, "assistant", last_ai_msg,
            metadata={"pending_action": pending} if pending else {}
        )

        return {
            "response": last_ai_msg,
            "requires_confirmation": requires_conf,
            "pending_action": pending,
        }

    async def _execute_action(self, pending_action: dict) -> str:
        action = pending_action.get("action")
        details = pending_action.get("details", {})
        try:
            if action == "create_task":
                result = await self.zoho_client.create_task(**details)
                return f"✅ Task '{result.get('name', details.get('name'))}' created! ID: {result.get('id')}"
            elif action == "update_task":
                await self.zoho_client.update_task(**details)
                return f"✅ Task {details.get('task_id')} updated successfully!"
            elif action == "delete_task":
                await self.zoho_client.delete_task(details["project_id"], details["task_id"])
                return f"✅ Task {details.get('task_id')} permanently deleted."
            return "Unknown action."
        except Exception as e:
            return f"❌ Action failed: {str(e)}"