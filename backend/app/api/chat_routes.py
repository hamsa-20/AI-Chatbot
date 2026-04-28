from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.middleware import get_current_user
from app.models.db_models import User
from app.models.schemas import ChatRequest, ChatResponse
from app.zoho.client import ZohoClient
from app.memory.memory_store import MemoryStore
from app.agents.graph import ZohoChatGraph

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Main chat endpoint."""
    try:
        zoho_client = ZohoClient(user=user, db=db)
        memory_store = MemoryStore(db=db, user_id=user.id)
        graph = ZohoChatGraph(zoho_client=zoho_client, memory_store=memory_store)

        result = await graph.chat(
            user_message=request.message,
            session_id=request.session_id,
            user_id=user.id,
            confirmation=request.confirmation,
            pending_action=getattr(request, "pending_action", None),
        )

        return ChatResponse(
            response=result["response"],
            requires_confirmation=result.get("requires_confirmation", False),
            pending_action=result.get("pending_action"),
            session_id=request.session_id,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{session_id}")
async def get_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get chat history for a session."""
    memory = MemoryStore(db=db, user_id=user.id)
    history = await memory.get_session_history(session_id)
    return {"history": history}