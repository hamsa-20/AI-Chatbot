from langchain.tools import tool
from typing import Optional
import json


def create_zoho_tools(zoho_client):
    """Factory that creates tools bound to a specific ZohoClient instance."""

    @tool("list_projects")
    async def list_projects() -> str:
        """List all Zoho Projects for the authenticated user."""
        try:
            projects = await zoho_client.list_projects()
            if not projects:
                return "No projects found."
            result = []
            for i, p in enumerate(projects, 1):
                result.append(
                    f"{i}. [{p.get('id')}] {p.get('name')} — Status: {p.get('status', 'active')}"
                )
            return "\n".join(result)
        except Exception as e:
            return f"Error fetching projects: {str(e)}"

    @tool("list_tasks")
    async def list_tasks(
        project_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> str:
        """List tasks for a project."""
        try:
            if not project_id or project_id == "None":
                return "❌ Please provide a valid project ID."

            tasks = await zoho_client.list_tasks(project_id, status, assignee)
            if not tasks:
                return f"No tasks found for project {project_id}."

            result = []
            for t in tasks:
                owner = "Unassigned"
                owners = t.get("details", {}).get("owners", [])
                if owners:
                    owner = owners[0].get("name", "Unassigned")

                result.append(
                    f"- [{t.get('id')}] {t.get('name')} | "
                    f"Status: {t.get('status', {}).get('name', 'N/A')} | "
                    f"Assignee: {owner} | "
                    f"Due: {t.get('end_date', 'N/A')}"
                )

            return "\n".join(result)

        except Exception as e:
            return f"Error fetching tasks: {str(e)}"

    @tool("get_task_details")
    async def get_task_details(project_id: str, task_id: str) -> str:
        """Get task details."""
        try:
            if not project_id:
                return "❌ Project ID is required."

            task = await zoho_client.get_task_details(project_id, task_id)
            if not task:
                return f"Task {task_id} not found."

            owners = task.get("details", {}).get("owners", [])
            owner = owners[0].get("name", "Unassigned") if owners else "Unassigned"

            return (
                f"Task: {task.get('name')}\n"
                f"ID: {task.get('id')}\n"
                f"Status: {task.get('status', {}).get('name', 'N/A')}\n"
                f"Priority: {task.get('priority', 'N/A')}\n"
                f"Assignee: {owner}\n"
                f"Due Date: {task.get('end_date', 'N/A')}\n"
                f"Description: {task.get('description', 'N/A')}\n"
                f"Percent Complete: {task.get('percent_complete', '0')}%"
            )

        except Exception as e:
            return f"Error fetching task details: {str(e)}"

    @tool("list_project_members")
    async def list_project_members(project_id: str) -> str:
        """List project members."""
        try:
            if not project_id:
                return "❌ Project ID required."

            members = await zoho_client.list_project_members(project_id)
            if not members:
                return "No members found."

            result = []
            for m in members:
                result.append(
                    f"- [{m.get('id')}] {m.get('name')} ({m.get('email', '')}) — Role: {m.get('role', 'N/A')}"
                )

            return "\n".join(result)

        except Exception as e:
            return f"Error fetching members: {str(e)}"

    @tool("get_task_utilisation")
    async def get_task_utilisation(project_id: str) -> str:
        """Task utilisation."""
        try:
            if not project_id:
                return "❌ Project ID required."

            utilisation = await zoho_client.get_task_utilisation(project_id)
            if not utilisation:
                return "No utilisation data available."

            result = ["Task Utilisation by Member:"]
            for u in utilisation:
                result.append(
                    f"- {u['name']}: {u['total_tasks']} total "
                    f"({u['open']} open, {u['completed']} completed, {u['overdue']} overdue)"
                )

            return "\n".join(result)

        except Exception as e:
            return f"Error calculating utilisation: {str(e)}"

    # ─── ACTION TOOLS ─────────────────────────────────────────────

    @tool("create_task")
    async def create_task(
        project_id: str,
        name: str,
        description: Optional[str] = None,
        assignee_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: str = "Normal",
    ) -> str:
        """Create a new task (requires confirmation)."""

        if not project_id or project_id == "None":
            return "❌ Please specify a valid project. Try: 'list projects'"

        return json.dumps({
            "action": "create_task",
            "requires_confirmation": True,
            "details": {
                "project_id": project_id,
                "name": name,
                "description": description,
                "assignee_id": assignee_id,
                "due_date": due_date,
                "priority": priority,
            },
            "summary": f"Create task '{name}' in project {project_id}" +
                       (f" assigned to {assignee_id}" if assignee_id else "") +
                       (f" due {due_date}" if due_date else ""),
        })

    @tool("update_task")
    async def update_task(
        project_id: str,
        task_id: str,
        status: Optional[str] = None,
        assignee_id: Optional[str] = None,
        due_date: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> str:
        """Update a task."""

        if not project_id:
            return "❌ Project ID required."

        changes = []
        if status:
            changes.append(f"status → {status}")
        if assignee_id:
            changes.append(f"assignee → {assignee_id}")
        if due_date:
            changes.append(f"due date → {due_date}")
        if priority:
            changes.append(f"priority → {priority}")

        return json.dumps({
            "action": "update_task",
            "requires_confirmation": True,
            "details": {
                "project_id": project_id,
                "task_id": task_id,
                "status": status,
                "assignee_id": assignee_id,
                "due_date": due_date,
                "priority": priority,
            },
            "summary": f"Update task {task_id}: " + ", ".join(changes),
        })

    @tool("delete_task")
    async def delete_task(project_id: str, task_id: str) -> str:
        """Delete a task."""

        if not project_id:
            return "❌ Project ID required."

        return json.dumps({
            "action": "delete_task",
            "requires_confirmation": True,
            "details": {
                "project_id": project_id,
                "task_id": task_id,
            },
            "summary": f"Delete task {task_id} from project {project_id}",
        })

    query_tools = [
        list_projects,
        list_tasks,
        get_task_details,
        list_project_members,
        get_task_utilisation,
    ]

    action_tools = [
        create_task,
        update_task,
        delete_task,
    ]

    return query_tools, action_tools