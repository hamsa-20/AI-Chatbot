from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    zoho_client_id: str
    zoho_portal_id: str
    zoho_client_secret: str
    zoho_redirect_uri: str = "http://localhost:8000/auth/callback"
    zoho_auth_url: str = "https://accounts.zoho.in/oauth/v2/auth"
    zoho_token_url: str = "https://accounts.zoho.in/oauth/v2/token"
    zoho_scopes: str = "ZohoProjects.portals.READ,ZohoProjects.projects.ALL,ZohoProjects.tasks.ALL,AaaServer.profile.READ"

    groq_api_key: str
    secret_key: str
    database_url: str = "sqlite+aiosqlite:///./zoho_chatbot.db"
    frontend_url: str = "http://localhost:3000"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()