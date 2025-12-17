import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from app.core.config import settings

logger = logging.getLogger(__name__)


class SupabaseService:
    """Service for Supabase database operations"""
    
    def __init__(self):
        self.url = settings.SUPABASE_URL
        self.key = settings.SUPABASE_KEY
        self.client = None
        self.init_client()
    
    def init_client(self):
        """Initialize Supabase client if credentials are available"""
        if self.url and self.key:
            try:
                from supabase import create_client
                self.client = create_client(self.url, self.key)
                logger.info("✓ Supabase client initialized")
            except Exception as e:
                logger.warning(f"Could not initialize Supabase: {e}")
                self.client = None
        else:
            logger.warning("Supabase credentials not configured - using in-memory storage")
    
    async def health_check(self) -> bool:
        """Check if Supabase connection is healthy"""
        if not self.client:
            return False
        
        try:
            result = self.client.table("sessions").select("*").limit(1).execute()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
    
    async def create_session(
        self,
        session_id: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new session in the database"""
        if not self.client:
            return self._create_session_memory(session_id, user_id)
        
        try:
            data = {
                "session_id": session_id,
                "user_id": user_id or "anonymous",
                "start_time": datetime.utcnow().isoformat(),
                "end_time": None,
                "duration_seconds": None,
                "final_summary": None
            }
            result = self.client.table("sessions").insert(data).execute()
            logger.info(f"✓ Session created: {session_id}")
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            return self._create_session_memory(session_id, user_id)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by session_id"""
        if not self.client:
            return self._get_session_memory(session_id)
        
        try:
            result = self.client.table("sessions").select("*").eq(
                "session_id", session_id
            ).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting session: {e}")
            return self._get_session_memory(session_id)
    
    async def update_session(
        self,
        session_id: str,
        end_time: Optional[str] = None,
        duration_seconds: Optional[int] = None,
        final_summary: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update session with end time and summary"""
        if not self.client:
            return self._update_session_memory(
                session_id, end_time, duration_seconds, final_summary
            )
        
        try:
            data = {}
            if end_time:
                data["end_time"] = end_time
            if duration_seconds is not None:
                data["duration_seconds"] = duration_seconds
            if final_summary:
                data["final_summary"] = final_summary
            
            result = self.client.table("sessions").update(data).eq(
                "session_id", session_id
            ).execute()
            logger.info(f"✓ Session updated: {session_id}")
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f"Error updating session: {e}")
            return self._update_session_memory(
                session_id, end_time, duration_seconds, final_summary
            )
    
    async def log_event(
        self,
        session_id: str,
        event_type: str,
        content: str
    ) -> Dict[str, Any]:
        """Log an event to the event_logs table"""
        if not self.client:
            return self._log_event_memory(session_id, event_type, content)
        
        try:
            data = {
                "session_id": session_id,
                "event_type": event_type,
                "content": content,
                "created_at": datetime.utcnow().isoformat()
            }
            result = self.client.table("event_logs").insert(data).execute()
            return result.data[0] if result.data else data
        except Exception as e:
            logger.error(f"Error logging event: {e}")
            return self._log_event_memory(session_id, event_type, content)
    
    async def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all events for a session"""
        if not self.client:
            return self._get_session_history_memory(session_id)
        
        try:
            result = self.client.table("event_logs").select("*").eq(
                "session_id", session_id
            ).order("created_at", desc=False).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting session history: {e}")
            return self._get_session_history_memory(session_id)
    
    # In-memory fallbacks for when Supabase is not configured
    _memory_sessions: Dict[str, Dict] = {}
    _memory_events: Dict[str, List[Dict]] = {}
    
    def _create_session_memory(self, session_id: str, user_id: Optional[str] = None) -> Dict:
        self._memory_sessions[session_id] = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "user_id": user_id or "anonymous",
            "start_time": datetime.utcnow().isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "final_summary": None
        }
        self._memory_events[session_id] = []
        return self._memory_sessions[session_id]
    
    def _get_session_memory(self, session_id: str) -> Optional[Dict]:
        return self._memory_sessions.get(session_id)
    
    def _update_session_memory(
        self, session_id: str, end_time, duration_seconds, final_summary
    ) -> Dict:
        if session_id in self._memory_sessions:
            if end_time:
                self._memory_sessions[session_id]["end_time"] = end_time
            if duration_seconds is not None:
                self._memory_sessions[session_id]["duration_seconds"] = duration_seconds
            if final_summary:
                self._memory_sessions[session_id]["final_summary"] = final_summary
        return self._memory_sessions.get(session_id, {})
    
    def _log_event_memory(self, session_id: str, event_type: str, content: str) -> Dict:
        event = {
            "id": str(uuid.uuid4()),
            "session_id": session_id,
            "event_type": event_type,
            "content": content,
            "created_at": datetime.utcnow().isoformat()
        }
        if session_id not in self._memory_events:
            self._memory_events[session_id] = []
        self._memory_events[session_id].append(event)
        return event
    
    def _get_session_history_memory(self, session_id: str) -> List[Dict]:
        return self._memory_events.get(session_id, [])


supabase_service = SupabaseService()
