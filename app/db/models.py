from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class SessionModel(BaseModel):
    """Database model for a session"""
    id: Optional[str] = None
    session_id: str
    user_id: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    final_summary: Optional[str] = None
    
    class Config:
        from_attributes = True


class EventLogModel(BaseModel):
    """Database model for event logs"""
    id: Optional[str] = None
    session_id: str
    event_type: str  # user_message, ai_response, tool_call, system
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageModel(BaseModel):
    """Model for a message in conversation"""
    role: str  # user, assistant, system
    content: str
