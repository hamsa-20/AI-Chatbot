import uuid
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
        """
        Save a chat message.
        Uses 'msg_metadata' as the dict key internally to avoid any clash
        with SQLAlchemy's own 'metadata' attribute on the model class.
        """
        safe_meta = metadata if isinstance(metadata, dict) else {}

        self.db.add(ChatHistory(
            id=str(uuid.uuid4()),
            user_id=self.user_id,
            session_id=session_id,
            role=role,
            content=content,
            # Use the actual column name on your model.
            # If your column is called `metadata`, keep it.
            # If SQLAlchemy complains, rename the column to `msg_metadata`.
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
            # Safely read metadata regardless of whether it came back as
            # a dict, a SQLAlchemy object, or None.
            raw_meta = getattr(m, "metadata", None)
            if isinstance(raw_meta, dict):
                safe_meta = raw_meta
            else:
                safe_meta = {}

            history.append({
                "role": m.role,
                "content": m.content,
                "metadata": safe_meta,
            })

        return history

    async def get_session_context(self, session_id: str) -> dict:
        history = await self.get_session_history(session_id)

        context = {
            "current_project_id": None,
            "current_project_name": None,
            "recent_task_ids": [],
        }

        for msg in history:
            meta = msg.get("metadata", {})
            if not isinstance(meta, dict):
                continue

            if meta.get("project_id"):
                context["current_project_id"] = meta["project_id"]
                context["current_project_name"] = meta.get("project_name")

            if meta.get("task_id"):
                tid = meta["task_id"]
                if tid not in context["recent_task_ids"]:
                    context["recent_task_ids"].append(tid)

        return context