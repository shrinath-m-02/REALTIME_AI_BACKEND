import json
import logging
from typing import Dict, Callable, Any
from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Manages active WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a WebSocket connection and store it"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"✓ WebSocket connected: {session_id}")
    
    async def disconnect(self, session_id: str):
        """Remove a disconnected session"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"✗ WebSocket disconnected: {session_id}")
    
    async def send_json(self, session_id: str, data: dict):
        """Send JSON message to a specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending JSON to {session_id}: {e}")
                await self.disconnect(session_id)
    
    async def send_text(self, session_id: str, text: str):
        """Send text message to a specific session"""
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(text)
            except Exception as e:
                logger.error(f"Error sending text to {session_id}: {e}")
                await self.disconnect(session_id)
    
    async def broadcast(self, data: dict):
        """Send message to all connected sessions"""
        disconnected = []
        for session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting to {session_id}: {e}")
                disconnected.append(session_id)
        
        for session_id in disconnected:
            await self.disconnect(session_id)
    
    async def handle_message(
        self, 
        session_id: str, 
        message: str, 
        handler: Callable[[str, str], Any]
    ):
        """Handle incoming message by calling the provided handler"""
        try:
            await handler(session_id, message)
        except Exception as e:
            logger.error(f"Error handling message from {session_id}: {e}")
            await self.send_json(session_id, {
                "type": "error",
                "content": f"Error processing message: {str(e)}"
            })
    
    def get_connected_count(self) -> int:
        """Get count of active connections"""
        return len(self.active_connections)


manager = WebSocketManager()
