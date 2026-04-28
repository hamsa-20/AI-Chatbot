import uuid
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.auth.zoho_oauth import zoho_oauth
from app.auth.middleware import create_session_token
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory state store (use Redis in production)
_oauth_states: set[str] = set()


@router.get("/login")
async def login():
    """Initiate OAuth flow — redirect user to Zoho login."""
    state = str(uuid.uuid4())
    _oauth_states.add(state)
    auth_url = zoho_oauth.get_authorization_url(state)
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(
    code: str,
    state: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Handle Zoho OAuth callback."""
    if state not in _oauth_states:
        raise HTTPException(status_code=400, detail="Invalid OAuth state")
    _oauth_states.remove(state)

    try:
        token_data = await zoho_oauth.exchange_code_for_tokens(code)
        user = await zoho_oauth.save_user_tokens(db, token_data)

        session_token = create_session_token(user.id)
        
        redirect = RedirectResponse(url=f"{settings.frontend_url}/chat")
        redirect.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            samesite="lax",
            max_age=86400 * 7,  # 7 days
        )
        return redirect

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OAuth failed: {str(e)}")


@router.get("/me")
async def get_me(request: Request, db: AsyncSession = Depends(get_db)):
    """Return current user info."""
    from app.auth.middleware import get_current_user
    user = await get_current_user(
        session_token=request.cookies.get("session_token"), db=db
    )
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
    }


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("session_token")
    return {"message": "Logged out"}