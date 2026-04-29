import uuid
import json
import re
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.db_models import UserMemory, ChatHistory


class MemoryStore:
    def __init__(self, db: AsyncSession, user_id: str):
        self.db = db
        self.user_id = user_id

    # ─── Long-term memory ────────────────────────────────────────────────────

    async def save_long_term(self, memory_type: str, key: str, value: str):
        result = await self.db.execute(
            select(UserMemory).where(
                UserMemory.user_id == self.user_id,
                UserMemory.memory_type == memory_type,
                UserMemory.key == key,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            existing.value = value
            existing.updated_at = datetime.utcnow()
        else:
            self.db.add(UserMemory(
                id=str(uuid.uuid4()),
                user_id=self.user_id,
                memory_type=memory_type,
                key=key,
                value=value,
            ))
        await self.db.commit()

    async def get_long_term(self, memory_type: str = None) -> list[dict]:
        query = select(UserMemory).where(UserMemory.user_id == self.user_id)
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)
        result = await self.db.execute(query)
        return [
            {"type": m.memory_type, "key": m.key, "value": m.value}
            for m in result.scalars().all()
        ]

    async def get_long_term_summary(self) -> str:
        memories = await self.get_long_term()
        if not memories:
            return "No previous context."
        return "\n".join(f"- [{m['type']}] {m['key']}: {m['value']}" for m in memories)

    # ─── Short-term (session) memory ─────────────────────────────────────────

    async def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: dict = None,
    ):
        safe_meta = metadata if isinstance(metadata, dict) else {}

        self.db.add(ChatHistory(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata=safe_meta,
        ))
        await self.db.commit()

    async def get_session_history(self, session_id: str, limit: int = 20) -> list[dict]:
        result = await self.db.execute(
            select(ChatHistory)
            .where(
                ChatHistory.user_id == self.user_id,
                ChatHistory.session_id == session_id,
            )
            .order_by(ChatHistory.created_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()

        history = []
        for m in reversed(rows):
            raw_meta = getattr(m, "metadata", None)
            safe_meta = raw_meta if isinstance(raw_meta, dict) else {}

            history.append({
                "role": m.role,
                "content": m.content,
                "metadata": safe_meta,
            })

        return history

    async def get_session_context(self, session_id: str) -> dict:
        """
        Build session context by scanning chat history for project/task references.
        Also scans message content for embedded project info from list_projects tool output.
        """
        history = await self.get_session_history(session_id)

        context = {
            "current_project_id": None,
            "current_project_name": None,
            "recent_task_ids": [],
            "projects_list": [],  # full list from last list_projects call
        }

        for msg in history:
            meta = msg.get("metadata", {})
            content = msg.get("content", "")

            # ── Extract from metadata (set by graph.py) ──
            if isinstance(meta, dict):
                if meta.get("project_id"):
                    context["current_project_id"] = meta["project_id"]
                if meta.get("project_name"):
                    context["current_project_name"] = meta["project_name"]
                if meta.get("task_id"):
                    tid = meta["task_id"]
                    if tid not in context["recent_task_ids"]:
                        context["recent_task_ids"].append(tid)

            # ── Extract from tool output embedded in assistant messages ──
            if msg.get("role") == "assistant" and content:
                # Parse structured projects JSON embedded by list_projects tool
                json_match = re.search(r"__projects_json__:(\[.+?\])", content)
                if json_match:
                    try:
                        projects = json.loads(json_match.group(1))
                        context["projects_list"] = projects
                        # Auto-set first project as current if none set yet
                        if projects and not context["current_project_id"]:
                            context["current_project_id"] = projects[0]["id"]
                            context["current_project_name"] = projects[0]["name"]
                    except (json.JSONDecodeError, KeyError):
                        pass

                # Extract project IDs from bracketed numbers in content e.g. [12345678]
                if not context["current_project_id"]:
                    pid_matches = re.findall(r"\[(\d{6,})\]", content)
                    if pid_matches:
                        context["current_project_id"] = pid_matches[0]

                # Extract project name from numbered list format
                if not context["current_project_name"] and context["current_project_id"]:
                    name_match = re.search(
                        rf"\[{re.escape(context['current_project_id'])}\]\s+(.+?)\s+—",
                        content
                    )
                    if name_match:
                        context["current_project_name"] = name_match.group(1).strip()

                # Extract task IDs from task list output e.g. [987654321]
                task_matches = re.findall(r"\[(\d{8,})\]", content)
                for tid in task_matches:
                    if tid != context.get("current_project_id") and tid not in context["recent_task_ids"]:
                        context["recent_task_ids"].append(tid)

        # ── Fall back to long-term memory if session has no project ──
        if not context["current_project_id"]:
            lt_memories = await self.get_long_term("context")
            for m in lt_memories:
                if m["key"] == "last_project_id":
                    context["current_project_id"] = m["value"]
                if m["key"] == "last_project_name":
                    context["current_project_name"] = m["value"]

        return context