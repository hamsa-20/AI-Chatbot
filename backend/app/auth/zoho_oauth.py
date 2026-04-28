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

        # ✅ Use portal_id from .env (no API call)
        portal_id = settings.zoho_portal_id

        user_id = str(portal_id)
        email = ""
        display_name = "Zoho User"

        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.access_token = access_token
            if refresh_token:
                user.refresh_token = refresh_token
            user.token_expires_at = token_expires_at
            user.zoho_api_domain = api_domain
            user.updated_at = datetime.utcnow()
        else:
            user = User(
                id=user_id,
                email=email,
                display_name=display_name,
                access_token=access_token,
                refresh_token=refresh_token,
                token_expires_at=token_expires_at,
                zoho_api_domain=api_domain,
            )
            db.add(user)

        await db.commit()
        await db.refresh(user)

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