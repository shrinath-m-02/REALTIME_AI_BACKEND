import os
import sys
os.chdir("C:\\workspace\\realtime_ai_backend")
sys.path.insert(0, "C:\\workspace\\realtime_ai_backend")

import logging
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.core.config import settings
from app.core.websocket import manager
from app.core.llm import llm_service
from app.db.supabase import supabase_service
from app.services.session_service import session_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Realtime AI Backend")
    health = await supabase_service.health_check()
    if health:
        logger.info(" Supabase connection healthy")
    else:
        logger.warning(" Supabase connection failed - check credentials")
    yield
    logger.info("Shutting down Realtime AI Backend")

app = FastAPI(title="Realtime AI Backend", description="WebSocket-based AI backend", version="1.0.0", lifespan=lifespan)

try:
    app.mount("/static", StaticFiles(directory="static"), name="static")
except Exception as e:
    logger.warning(f"Could not mount static files: {e}")

@app.get("/")
async def root():
    try:
        return FileResponse("static/index.html", media_type="text/html")
    except FileNotFoundError:
        return {"message": "Realtime AI Backend is running", "version": "1.0.0", "docs": "/docs"}

@app.get("/health")
async def health():
    db_health = await supabase_service.health_check()
    return {"status": "healthy" if db_health else "degraded", "database": "connected" if db_health else "disconnected"}

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    if not session_id or session_id == "new":
        session_id = str(uuid.uuid4())
    await manager.connect(websocket, session_id)
    try:
        await manager.send_json(session_id, {"type": "system", "content": f"Connected to session {session_id}. Send your message to start.", "session_id": session_id})
        while True:
            message = await websocket.receive_text()
            await manager.handle_message(session_id, message, handle_user_message)
    except WebSocketDisconnect:
        await manager.disconnect(session_id)
        logger.info(f"WebSocket connection closed: {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(session_id)

async def handle_user_message(session_id: str, user_message: str):
    try:
        await session_service.add_message(session_id, "user", user_message)
        conversation = session_service.get_conversation(session_id)
        full_response = ""
        await manager.send_json(session_id, {"type": "ai_response_start", "content": ""})
        async for token in llm_service.stream_response(conversation):
            full_response += token
            await manager.send_json(session_id, {"type": "ai_response_chunk", "content": token})
            if len(full_response) % 5 == 0:
                import asyncio
                await asyncio.sleep(0)
        await manager.send_json(session_id, {"type": "ai_response_end", "content": ""})
        await session_service.add_message(session_id, "assistant", full_response)
        await supabase_service.log_event(session_id=session_id, event_type="ai_response", content=full_response)
        logger.info(f"Response streamed for {session_id}")
    except Exception as e:
        logger.error(f"Error handling user message: {e}")
        await manager.send_json(session_id, {"type": "error", "content": f"Error processing message: {str(e)}"})

@app.get("/api/session/{session_id}")
async def get_session(session_id: str):
    try:
        session = await supabase_service.get_session(session_id)
        history = await supabase_service.get_session_history(session_id)
        return {"session": session, "history": history, "conversation": session_service.get_conversation(session_id)}
    except Exception as e:
        logger.error(f"Error retrieving session: {e}")
        return {"error": str(e)}, 500

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*70)
    print(" REALTIME AI BACKEND - PRODUCTION MODE")
    print("="*70)
    print(" Supabase URL configured")
    print(" OpenAI API key configured")
    print(" WebSocket streaming enabled")
    print(" Database persistence active")
    print()
    print(" Server: http://localhost:8000")
    print(" API Docs: http://localhost:8000/docs")
    print(" Chat UI: http://localhost:8000/")
    print(" Health: http://localhost:8000/health")
    print("="*70 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
