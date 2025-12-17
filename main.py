import logging
import uuid
import asyncio
import os
import sys
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Ensure we're in the right directory and load .env
project_root = Path(__file__).parent
os.chdir(project_root)
sys.path.insert(0, str(project_root))

from app.core.config import settings
from app.core.websocket import manager
from app.core.llm import llm_service
from app.db.supabase import supabase_service
from app.services.session_service import session_service
from app.services.summary_service import summary_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown"""
    logger.info("=" * 70)
    logger.info("Starting Realtime AI Backend")
    logger.info("=" * 70)
    
    # Validate configuration
    try:
        settings.validate()
        logger.info("✓ Configuration validated")
    except ValueError as e:
        logger.error(f"✗ Configuration error: {e}")
    
    # Check database health
    health = await supabase_service.health_check()
    if health:
        logger.info("✓ Supabase connection healthy")
    else:
        logger.warning("⚠ Supabase connection unavailable (using in-memory storage)")
    
    # Log status
    logger.info(f"  LLM Model: {settings.LLM_MODEL}")
    logger.info(f"  Server: {settings.SERVER_HOST}:{settings.SERVER_PORT}")
    logger.info("=" * 70)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Realtime AI Backend")
    logger.info(f"Active sessions: {session_service.get_session_count()}")


app = FastAPI(
    title="Realtime AI Backend",
    description="WebSocket-based AI backend with Supabase persistence",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
    logger.info("✓ Static files mounted")
except Exception as e:
    logger.warning(f"⚠ Could not mount static files: {e}")


@app.get("/")
async def root():
    """Serve the frontend"""
    try:
        return FileResponse("static/index.html", media_type="text/html")
    except FileNotFoundError:
        return {
            "message": "Realtime AI Backend is running",
            "version": "1.0.0",
            "docs": "/docs",
            "websocket": "/ws/session/{session_id}"
        }


@app.get("/health")
async def health():
    """Health check endpoint"""
    db_health = await supabase_service.health_check()
    return {
        "status": "healthy" if db_health else "degraded",
        "database": "connected" if db_health else "in-memory",
        "sessions": session_service.get_session_count()
    }


@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time chat with streaming responses"""
    
    # Generate session ID if not provided
    if not session_id or session_id == "new":
        session_id = str(uuid.uuid4())
    
    # Connect and create session
    await manager.connect(websocket, session_id)
    await session_service.create_session(session_id)
    
    try:
        # Send welcome message
        await manager.send_json(session_id, {
            "type": "system",
            "content": f"Connected to session {session_id}",
            "session_id": session_id
        })
        
        # Message loop
        while True:
            message = await websocket.receive_text()
            await manager.handle_message(session_id, message, handle_user_message)
    
    except WebSocketDisconnect:
        logger.info(f"✗ WebSocket disconnected: {session_id}")
        await manager.disconnect(session_id)
        
        # Generate summary as background task (non-blocking)
        conversation = session_service.get_conversation(session_id)
        await summary_service.generate_summary_async(session_id, conversation)
    
    except Exception as e:
        logger.error(f"✗ WebSocket error: {e}")
        await manager.disconnect(session_id)


async def handle_user_message(session_id: str, user_message: str):
    """Handle incoming user message and stream LLM response"""
    try:
        # Add user message to conversation
        await session_service.add_message(session_id, "user", user_message)
        logger.info(f"→ User message ({session_id}): {user_message[:50]}...")
        
        # Get current conversation
        conversation = session_service.get_conversation(session_id)
        
        # Stream LLM response
        full_response = ""
        await manager.send_json(session_id, {
            "type": "ai_response_start"
        })
        
        async for token in llm_service.stream_response(conversation):
            full_response += token
            await manager.send_json(session_id, {
                "type": "ai_response_chunk",
                "content": token
            })
            # Yield to event loop for better responsiveness
            await asyncio.sleep(0)
        
        # Send completion marker
        await manager.send_json(session_id, {
            "type": "ai_response_end"
        })
        
        # Save AI response to conversation and database
        await session_service.add_message(session_id, "assistant", full_response)
        logger.info(f"← AI response ({session_id}): {full_response[:50]}...")
    
    except Exception as e:
        logger.error(f"✗ Error handling user message: {e}")
        await manager.send_json(session_id, {
            "type": "error",
            "content": f"Error: {str(e)}"
        })


@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    """Get session details and conversation history"""
    try:
        session = await supabase_service.get_session(session_id)
        history = await supabase_service.get_session_history(session_id)
        conversation = session_service.get_conversation(session_id)
        
        return {
            "session": session,
            "history": history,
            "conversation": conversation,
            "message_count": len(conversation)
        }
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return {"error": str(e)}, 500


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "=" * 70)
    print(" REALTIME AI BACKEND - STARTING SERVER")
    print("=" * 70)
    print(f" Host: {settings.SERVER_HOST}")
    print(f" Port: {settings.SERVER_PORT}")
    print(f" Debug: {settings.DEBUG}")
    print()
    print(" Web UI: http://localhost:8001")
    print(" API Docs: http://localhost:8001/docs")
    print(" Health: http://localhost:8001/health")
    print("=" * 70 + "\n")
    
    uvicorn.run(
        "main:app",
        host=settings.SERVER_HOST,
        port=settings.SERVER_PORT,
        reload=settings.DEBUG
    )
