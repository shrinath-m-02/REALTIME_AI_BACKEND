import logging
import asyncio
from typing import List, Dict, Any
from app.db.supabase import supabase_service
from app.core.llm import llm_service
from datetime import datetime

logger = logging.getLogger(__name__)


class SummaryService:
    """Service for generating session summaries after disconnection"""
    
    async def generate_and_save_summary(
        self,
        session_id: str,
        conversation: List[Dict[str, str]]
    ):
        """Generate a summary for the session and save to database"""
        
        if not conversation or len(conversation) == 0:
            logger.info(f"No conversation history for {session_id}, skipping summary")
            return
        
        try:
            summary = await self._generate_summary(conversation)
            
            # Calculate duration (in seconds)
            session = await supabase_service.get_session(session_id)
            if session and session.get("start_time"):
                start_time = datetime.fromisoformat(session["start_time"])
                duration = int((datetime.utcnow() - start_time).total_seconds())
            else:
                duration = None
            
            # Update session with summary
            await supabase_service.update_session(
                session_id=session_id,
                end_time=datetime.utcnow().isoformat(),
                duration_seconds=duration,
                final_summary=summary
            )
            
            logger.info(f"✓ Summary generated for {session_id}")
        
        except Exception as e:
            logger.error(f"Error generating summary for {session_id}: {e}")
    
    async def generate_summary_async(
        self,
        session_id: str,
        conversation: List[Dict[str, str]]
    ):
        """Generate and save summary as a background task (non-blocking)"""
        
        # Run as a background task without blocking the disconnect
        asyncio.create_task(
            self.generate_and_save_summary(session_id, conversation)
        )
    
    async def _generate_summary(self, conversation: List[Dict[str, str]]) -> str:
        """Generate a concise summary of the conversation"""
        
        if len(conversation) == 0:
            return "Empty session - no conversation occurred."
        
        # Build a context for summary generation
        conversation_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content'][:200]}"
            for msg in conversation[-10:]  # Use last 10 messages
        ])
        
        prompt = f"""Provide a brief (2-3 sentences) summary of this conversation:

{conversation_text}

Summary:"""
        
        try:
            summary = ""
            async for token in llm_service.stream_response(
                [{"role": "user", "content": prompt}],
                use_tools=False
            ):
                summary += token
            
            return summary.strip()
        
        except Exception as e:
            logger.error(f"Error in _generate_summary: {e}")
            return f"Summary generation failed: {str(e)}"


summary_service = SummaryService()
