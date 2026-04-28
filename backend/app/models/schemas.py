from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime


class ChatRequest(BaseModel):
    message: str
    session_id: str
    confirmation: Optional[bool] = None  # For HIL confirmation


class ChatResponse(BaseModel):
    response: str
    requires_confirmation: bool = False
    pending_action: Optional[dict] = None
    session_id: str


class TokenData(BaseModel):
    user_id: str


class UserInfo(BaseModel):
    id: str
    email: str
    display_name: str


class TaskCreate(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = "Normal"


class TaskUpdate(BaseModel):
    task_id: str
    project_id: str
    status: Optional[str] = None
    assignee_id: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None