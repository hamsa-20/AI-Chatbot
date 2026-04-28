import uuid
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
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
            mem = UserMemory(
                id=str(uuid.uuid4()),
                user_id=self.user_id,
                memory_type=memory_type,
                key=key,
                value=value,
            )
            self.db.add(mem)
        await self.db.commit()

    async def get_long_term(self, memory_type: str = None) -> list[dict]:
        query = select(UserMemory).where(UserMemory.user_id == self.user_id)
        if memory_type:
            query = query.where(UserMemory.memory_type == memory_type)
        result = await self.db.execute(query)
        memories = result.scalars().all()
        return [
            {"type": m.memory_type, "key": m.key, "value": m.value}
            for m in memories
        ]

    async def get_long_term_summary(self) -> str:
        memories = await self.get_long_term()
        if not memories:
            return "No previous context."
        lines = []
        for m in memories:
            lines.append(f"- [{m['type']}] {m['key']}: {m['value']}")
        return "\n".join(lines)

    # ─── Short-term (session) memory via ChatHistory ─────────────────────────
    async def save_message(self, session_id: str, role: str, content: str, metadata: dict = None):
        msg = ChatHistory(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            session_id=session_id,
            role=role,
            content=content,
            metadata=metadata if isinstance(metadata, dict) else {},
        )
        self.db.add(msg)
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
        messages = result.scalars().all()

        return [
            {
                "role": m.role,
                "content": m.content,
                "metadata": m.metadata if isinstance(m.metadata, dict) else {},
            }
            for m in reversed(messages)
        ]

    async def get_session_context(self, session_id: str) -> dict:
        """Extract structured context from session history."""
        history = await self.get_session_history(session_id)

        context = {
            "current_project_id": None,
            "current_project_name": None,
            "recent_task_ids": [],
        }

        for msg in history:
            # 🔥 SAFE METADATA HANDLING (FIX)
            meta = msg.get("metadata") if isinstance(msg, dict) else {}

            if not isinstance(meta, dict):
                try:
                    meta = meta.__dict__
                except:
                    meta = {}

            if meta.get("project_id"):
                context["current_project_id"] = meta["project_id"]
                context["current_project_name"] = meta.get("project_name")

            if meta.get("task_id"):
                if meta["task_id"] not in context["recent_task_ids"]:
                    context["recent_task_ids"].append(meta["task_id"])

        return context