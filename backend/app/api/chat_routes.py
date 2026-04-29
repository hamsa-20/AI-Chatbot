from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.db_models import User
from app.models.schemas import ChatRequest, ChatResponse
from app.zoho.client import ZohoClient
from app.memory.memory_store import MemoryStore
from app.agents.graph import ZohoChatGraph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    try:
        zoho_client = ZohoClient(user=user, db=db)
        memory_store = MemoryStore(db=db, user_id=user.id)
        graph = ZohoChatGraph(
            zoho_client=zoho_client,
            memory_store=memory_store
        )

        result = await graph.chat(
            user_message=request.message,
            session_id=request.session_id,
            user_id=user.id,
            confirmation=request.confirmation,
            pending_action=getattr(request, "pending_action", None),
        )

        # 🔍 Log raw result to see what graph returns
        logger.warning(f"[GRAPH RAW RESULT] type={type(result)} value={result}")

        # Normalize result safely (dict OR object)
        if isinstance(result, dict):
            data = result
        else:
            data = vars(result) if hasattr(result, '__dict__') else {}

        logger.warning(f"[GRAPH DATA] {data}")

        # Try multiple possible keys for the response text
        response_text = (
            data.get("response")
            or data.get("message")
            or data.get("content")
            or data.get("output")
            or data.get("answer")
            or ""
        )

        if not response_text:
            logger.error(f"[EMPTY RESPONSE] graph returned no text. data keys: {list(data.keys())}")
            response_text = "I received your message but couldn't generate a response. Please try again."

        return ChatResponse(
            response=response_text,
            requires_confirmation=data.get("requires_confirmation", False),
            pending_action=data.get("pending_action"),
            session_id=request.session_id,
        )

    except Exception as e:
        logger.exception(f"[CHAT ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    memory = MemoryStore(db=db, user_id=user.id)
    history = await memory.get_session_history(session_id)
    return {"history": history}