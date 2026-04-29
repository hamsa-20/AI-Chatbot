import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import User
from app.auth.zoho_oauth import zoho_oauth


class ZohoClient:
    def __init__(self, user: User, db: AsyncSession):
        self.user = user
        self.db = db
        self.base_url = "https://projectsapi.zoho.in/restapi"
        self._portal_id: str = None

    async def _get_headers(self) -> dict:
        token = await zoho_oauth.ensure_valid_token(self.db, self.user)
        return {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json",
        }

    async def _get(self, path: str, params: dict = None) -> dict:
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{self.base_url}{path}",
                headers=headers,
                params=params or {},
            )
            response.raise_for_status()
            return response.json()

    async def _post(self, path: str, data: dict = None) -> dict:
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}{path}",
                headers=headers,
                json=data or {},
            )
            response.raise_for_status()
            return response.json()

    async def _patch(self, path: str, data: dict = None) -> dict:
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.patch(
                f"{self.base_url}{path}",
                headers=headers,
                json=data or {},
            )
            response.raise_for_status()
            return response.json()

    async def _delete(self, path: str) -> dict:
        headers = await self._get_headers()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.delete(
                f"{self.base_url}{path}",
                headers=headers,
            )
            response.raise_for_status()
            return response.json()

    async def get_portal_id(self) -> str:
        if self._portal_id:
            return self._portal_id

        data = await self._get("/portals/")
        portals = data.get("portals", [])

        if not portals:
            raise ValueError("No Zoho Projects portal found for this account")

        self._portal_id = portals[0]["id"]
        return self._portal_id

    # ─── Tool 1: list_projects ───────────────────────────────────────────────
    async def list_projects(self) -> str:
        portal_id = await self.get_portal_id()
        data = await self._get(f"/portal/{portal_id}/projects/")

        projects = data.get("projects", [])

        if not projects:
            return "No projects found."

        result = []
        for i, p in enumerate(projects, 1):
            result.append(f"{i}. {p.get('name')} (ID: {p.get('id')})")

        return "\n".join(result)

    # ─── Tool 2: list_tasks ──────────────────────────────────────────────────
    async def list_tasks(
        self,
        project_id: str,
        status: str = None,
        assignee: str = None,
    ) -> list[dict]:
        portal_id = await self.get_portal_id()
        params = {}
        if status:
            params["status"] = status
        if assignee:
            params["owner"] = assignee
        data = await self._get(
            f"/portal/{portal_id}/projects/{project_id}/tasks/",
            params=params,
        )
        return data.get("tasks", [])

    # ─── Tool 3: get_task_details ────────────────────────────────────────────
    async def get_task_details(self, project_id: str, task_id: str) -> dict:
        portal_id = await self.get_portal_id()
        data = await self._get(
            f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"
        )
        tasks = data.get("tasks", [])
        return tasks[0] if tasks else {}

    # ─── Tool 4: create_task ─────────────────────────────────────────────────
    async def create_task(
        self,
        project_id: str,
        name: str,
        description: str = None,
        assignee_id: str = None,
        due_date: str = None,
        priority: str = "Normal",
    ) -> dict:
        portal_id = await self.get_portal_id()
        payload = {"name": name, "priority": priority}
        if description:
            payload["description"] = description
        if assignee_id:
            payload["person_responsible"] = assignee_id
        if due_date:
            payload["end_date"] = due_date
        data = await self._post(
            f"/portal/{portal_id}/projects/{project_id}/tasks/",
            data=payload,
        )
        tasks = data.get("tasks", [{}])
        return tasks[0] if tasks else {}

    # ─── Tool 5: update_task ─────────────────────────────────────────────────
    async def update_task(
        self,
        project_id: str,
        task_id: str,
        status: str = None,
        assignee_id: str = None,
        due_date: str = None,
        priority: str = None,
    ) -> dict:
        portal_id = await self.get_portal_id()
        payload = {}
        if status:
            payload["status"] = status
        if assignee_id:
            payload["person_responsible"] = assignee_id
        if due_date:
            payload["end_date"] = due_date
        if priority:
            payload["priority"] = priority
        data = await self._patch(
            f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/",
            data=payload,
        )
        tasks = data.get("tasks", [{}])
        return tasks[0] if tasks else {}

    # ─── Tool 6: delete_task ─────────────────────────────────────────────────
    async def delete_task(self, project_id: str, task_id: str) -> dict:
        portal_id = await self.get_portal_id()
        return await self._delete(
            f"/portal/{portal_id}/projects/{project_id}/tasks/{task_id}/"
        )

    # ─── Tool 7: list_project_members ────────────────────────────────────────
    async def list_project_members(self, project_id: str) -> list[dict]:
        portal_id = await self.get_portal_id()
        data = await self._get(
            f"/portal/{portal_id}/projects/{project_id}/users/"
        )
        return data.get("users", [])

    # ─── Tool 8: get_task_utilisation ────────────────────────────────────────
    async def get_task_utilisation(self, project_id: str) -> list[dict]:
        tasks = await self.list_tasks(project_id)
        members = await self.list_project_members(project_id)

        member_map = {m.get("id"): m.get("name", "Unknown") for m in members}
        utilisation: dict[str, dict] = {}

        for task in tasks:
            assignee_id = task.get("details", {}).get("owners", [{}])[0].get("id") if task.get("details", {}).get("owners") else None
            assignee_name = member_map.get(assignee_id, "Unassigned") if assignee_id else "Unassigned"

            if assignee_name not in utilisation:
                utilisation[assignee_name] = {
                    "name": assignee_name,
                    "total_tasks": 0,
                    "open": 0,
                    "completed": 0,
                    "overdue": 0,
                }

            utilisation[assignee_name]["total_tasks"] += 1
            status = task.get("status", {}).get("name", "").lower()
            if "complete" in status or "done" in status or "closed" in status:
                utilisation[assignee_name]["completed"] += 1
            else:
                utilisation[assignee_name]["open"] += 1

            if task.get("overdue") == "true":
                utilisation[assignee_name]["overdue"] += 1

        return sorted(
            utilisation.values(), key=lambda x: x["total_tasks"], reverse=True
        )