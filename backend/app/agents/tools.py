from langchain.tools import tool
from typing import Optional
import json


def create_zoho_tools(zoho_client):
    """Factory that creates tools bound to a specific ZohoClient instance."""

    # ─── QUERY TOOLS ──────────────────────────────────────────────

    @tool("list_projects")
    async def list_projects() -> str:
        """List all Zoho Projects for the authenticated user. Returns project IDs and names."""
        try:
            projects = await zoho_client.list_projects()
            if not projects:
                return "No projects found."
            result = []
            for i, p in enumerate(projects, 1):
                result.append(
                    f"{i}. [{p.get('id')}] {p.get('name')} — Status: {p.get('status', 'active')}"
                )
            # Also return structured data for context extraction
            structured = json.dumps([
                {"id": str(p.get("id")), "name": p.get("name")} for p in projects
            ])
            return "\n".join(result) + f"\n\n__projects_json__:{structured}"
        except Exception as e:
            return f"Error fetching projects: {str(e)}"

    @tool("list_tasks")
    async def list_tasks(
        project_id: str,
        status: Optional[str] = None,
        assignee: Optional[str] = None,
    ) -> str:
        """List tasks for a given project_id. Returns task IDs, names, status, assignee, due date."""
        try:
            if not project_id or project_id in ("None", "none", ""):
                return "❌ Please provide a valid project ID. Try asking 'What projects do I have?' first."

            tasks = await zoho_client.list_tasks(project_id, status, assignee)
            if not tasks:
                return f"No tasks found for project {project_id}."

            result = []
            for i, t in enumerate(tasks, 1):
                owner = "Unassigned"
                owners = t.get("details", {}).get("owners", [])
                if owners:
                    owner = owners[0].get("name", "Unassigned")

                result.append(
                    f"{i}. [{t.get('id')}] {t.get('name')} | "
                    f"Status: {t.get('status', {}).get('name', 'N/A')} | "
                    f"Assignee: {owner} | "
                    f"Due: {t.get('end_date', 'N/A')}"
                )

            return "\n".join(result)

        except Exception as e:
            return f"Error fetching tasks: {str(e)}"

    @tool("get_task_details")
    async def get_task_details(project_id: str, task_id: str) -> str:
        """Get detailed information about a specific task by project_id and task_id."""
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
        """List all members of a project by project_id."""
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
        """
        Get task utilisation per member for a project — shows who has the most tasks.
        Use this for questions like 'who has the most tasks this month?'
        """
        try:
            if not project_id or project_id in ("None", "none", ""):
                return "❌ Project ID required. Please specify a project or list your projects first."

            utilisation = await zoho_client.get_task_utilisation(project_id)
            if not utilisation:
                return "No utilisation data available for this project."

            # Sort by total tasks descending so "most tasks" is obvious
            sorted_util = sorted(utilisation, key=lambda u: u.get("total_tasks", 0), reverse=True)

            result = [f"📊 Task Utilisation for project {project_id}:\n"]
            for i, u in enumerate(sorted_util, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                result.append(
                    f"{medal} {u['name']}: {u['total_tasks']} total tasks "
                    f"({u['open']} open, {u['completed']} completed, {u['overdue']} overdue)"
                )

            top = sorted_util[0] if sorted_util else None
            if top:
                result.append(f"\n👑 **{top['name']}** has the most tasks this month with {top['total_tasks']} tasks.")

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
        """
        Create a new task in a project. Requires confirmation before executing.
        Always use this for 'create a task called X' requests.
        """
        if not project_id or project_id in ("None", "none", ""):
            return "❌ Please specify a valid project. Try: 'What projects do I have?'"

        summary = f"Create task '{name}' in project {project_id}"
        if assignee_id:
            summary += f" assigned to user {assignee_id}"
        if due_date:
            summary += f" due {due_date}"
        if priority and priority != "Normal":
            summary += f" with {priority} priority"

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
            "summary": summary,
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
        """
        Update an existing task's status, assignee, due date, or priority. Requires confirmation.
        """
        if not project_id or project_id in ("None", "none", ""):
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
            "summary": f"Update task {task_id}: " + (", ".join(changes) if changes else "no changes specified"),
        })

    @tool("delete_task")
    async def delete_task(project_id: str, task_id: str) -> str:
        """
        Delete a task permanently. Requires confirmation before executing.
        Use this when the user says 'delete task #X' or 'delete task X'.
        """
        if not project_id or project_id in ("None", "none", ""):
            return "❌ Project ID required."

        if not task_id or task_id in ("None", "none", ""):
            return "❌ Task ID required. Please list tasks first to get the task ID."

        return json.dumps({
            "action": "delete_task",
            "requires_confirmation": True,
            "details": {
                "project_id": project_id,
                "task_id": task_id,
            },
            "summary": f"Permanently delete task {task_id} from project {project_id}",
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