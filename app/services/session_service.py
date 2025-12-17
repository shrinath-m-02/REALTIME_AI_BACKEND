import logging
from typing import List, Dict, Any, Optional
from app.db.supabase import supabase_service

logger = logging.getLogger(__name__)


class SessionService:
    """Service for managing session state and conversation history"""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
    
    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ):
        """Initialize a new session"""
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        # Create session in database
        await supabase_service.create_session(session_id, user_id)
        logger.info(f"✓ Session created: {session_id}")
    
    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str
    ):
        """Add a message to the conversation and persist to database"""
        
        # Initialize if needed
        if session_id not in self.conversations:
            self.conversations[session_id] = []
        
        # Add to in-memory conversation
        self.conversations[session_id].append({
            "role": role,
            "content": content
        })
        
        # Persist to database
        event_type = "user_message" if role == "user" else "ai_response"
        await supabase_service.log_event(
            session_id=session_id,
            event_type=event_type,
            content=content
        )
        
        logger.debug(f"Message added to {session_id}: {role}")
    
    def get_conversation(self, session_id: str) -> List[Dict[str, str]]:
        """Get the current conversation for a session"""
        return self.conversations.get(session_id, [])
    
    async def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get the full conversation history from database"""
        history = await supabase_service.get_session_history(session_id)
        
        # Convert to message format
        messages = []
        for event in history:
            if event["event_type"] in ["user_message", "ai_response"]:
                role = "user" if event["event_type"] == "user_message" else "assistant"
                messages.append({
                    "role": role,
                    "content": event["content"],
                    "timestamp": event.get("created_at")
                })
        
        return messages
    
    async def close_session(self, session_id: str) -> str:
        """Close a session and return summary text for persistence"""
        conversation = self.get_conversation(session_id)
        
        # Clean up in-memory storage
        if session_id in self.conversations:
            del self.conversations[session_id]
        
        logger.info(f"✓ Session closed: {session_id}")
        return f"Session {session_id} closed with {len(conversation)} messages"
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.conversations)


session_service = SessionService()
