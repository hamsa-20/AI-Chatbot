import httpx
from datetime import datetime, timedelta
from urllib.parse import urlencode
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.db_models import User

settings = get_settings()


class ZohoOAuth:
    def __init__(self):
        self.client_id = settings.zoho_client_id
        self.client_secret = settings.zoho_client_secret
        self.redirect_uri = settings.zoho_redirect_uri
        self.auth_url = settings.zoho_auth_url
        self.token_url = settings.zoho_token_url
        self.scopes = settings.zoho_scopes

    def get_authorization_url(self, state: str) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "scope": self.scopes,
            "redirect_uri": self.redirect_uri,
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }
        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                },
            )
            response.raise_for_status()
            data = response.json()
            print("TOKEN RESPONSE:", data)
            return data

    async def refresh_access_token(self, refresh_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            return response.json()

    async def save_user_tokens(self, db: AsyncSession, token_data: dict) -> User:
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        api_domain = token_data.get("api_domain")

        print("API DOMAIN:", api_domain)

        # Use portal_id from .env as the stable user identifier
        portal_id = settings.zoho_portal_id
        user_id = str(portal_id)
        display_name = "Zoho User"

        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        # --- FIX: Try lookup by ID first, then fall back to any existing user row ---
        # This handles the case where a row exists with a conflicting empty email
        user = None

        # 1. Try to find by primary key (user_id / portal_id)
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        # 2. If not found by ID, check if a row exists with email="" to avoid
        #    the UNIQUE constraint error on re-login after a DB reset
        if user is None:
            result = await db.execute(select(User).where(User.email == ""))
            user = result.scalar_one_or_none()

        if user:
            # Update existing user — never change the email if it's already set
            user.id = user_id  # Correct the ID if it was fetched via email fallback
            user.access_token = access_token
            if refresh_token:
                user.refresh_token = refresh_token
            user.token_expires_at = token_expires_at
            user.zoho_api_domain = api_domain
            user.display_name = display_name
            user.updated_at = datetime.utcnow()
        else:
            # Create new user — use None for email to avoid UNIQUE constraint
            # issues with empty strings across multiple potential rows
            user = User(
                id=user_id,
                email=None,          # None (NULL) avoids UNIQUE constraint collisions
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                zoho_api_domain=api_domain,
            )
            db.add(user)

        try:
            await db.commit()
            await db.refresh(user)
        except Exception as e:
            await db.rollback()
            print(f"DB commit failed: {e}")
            raise

        return user

    async def ensure_valid_token(self, db: AsyncSession, user: User) -> str:
        if datetime.utcnow() >= user.token_expires_at - timedelta(minutes=5):
            token_data = await self.refresh_access_token(user.refresh_token)
            user.access_token = token_data["access_token"]
            user.token_expires_at = datetime.utcnow() + timedelta(
                seconds=token_data.get("expires_in", 3600)
            )
            await db.commit()

        return user.access_token


zoho_oauth = ZohoOAuth()