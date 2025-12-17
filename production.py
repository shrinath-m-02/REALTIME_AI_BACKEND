import os
import logging
import uuid
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv("C:\\workspace\\realtime_ai_backend\\.env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"Client connected: {session_id}")

    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]

    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_json(data)
            except Exception as e:
                logger.error(f"Error sending: {e}")

sessions: Dict[str, List[dict]] = {}

async def stream_response(conversation: List[dict]):
    try:
        response = await openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "You are a helpful AI assistant."}] + conversation,
            temperature=LLM_TEMPERATURE,
            stream=True,
            max_tokens=2000
        )
        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(f"Error: {e}")
        yield f"Error: {str(e)}"

manager = WebSocketManager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Backend starting")
    yield

app = FastAPI(lifespan=lifespan)

CHAT_HTML = """<!DOCTYPE html>
<html>
<head>
<title>AI Chat</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 10px; }
.container { width: 100%; max-width: 700px; height: 85vh; background: white; border-radius: 15px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); display: flex; flex-direction: column; }
.header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; text-align: center; }
.chat-box { flex: 1; overflow-y: auto; padding: 20px; background: #f8f9fa; display: flex; flex-direction: column; gap: 12px; }
.message { display: flex; }
.message.user { justify-content: flex-end; }
.bubble { max-width: 75%; padding: 12px 16px; border-radius: 15px; word-wrap: break-word; }
.message.user .bubble { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.message.ai .bubble { background: #e9ecef; color: #333; }
.loading { display: flex; gap: 4px; }
.dot { width: 6px; height: 6px; background: #667eea; border-radius: 50%; animation: bounce 1.4s infinite; }
@keyframes bounce { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 1; } }
.input-area { padding: 16px 20px; border-top: 1px solid #ddd; display: flex; gap: 10px; }
#messageInput { flex: 1; padding: 12px 15px; border: 1px solid #ddd; border-radius: 25px; font-size: 14px; }
#messageInput:focus { outline: none; border-color: #667eea; }
#sendBtn { padding: 12px 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; border-radius: 25px; cursor: pointer; font-weight: 600; }
#sendBtn:disabled { opacity: 0.6; cursor: not-allowed; }
</style>
</head>
<body>
<div class="container">
<div class="header"><h1>Chat</h1></div>
<div id="chatBox" class="chat-box"></div>
<div class="input-area">
<input type="text" id="messageInput" placeholder="Type message..." autofocus>
<button id="sendBtn">Send</button>
</div>
</div>
<script>
let ws = null;
const chatBox = document.getElementById("chatBox");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
let isWaiting = false;

function connectWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = protocol + "//" + host + "/ws/session/new";
    console.log("Connecting to:", url);
    ws = new WebSocket(url);
    
    ws.onopen = () => console.log("Connected");
    ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "ai_response_start") addLoading();
        else if (msg.type === "ai_response_chunk") appendAI(msg.content);
        else if (msg.type === "ai_response_end") { isWaiting = false; sendBtn.disabled = false; }
    };
    ws.onerror = (e) => console.error("Error:", e);
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
}

function sendMessage() {
    const text = messageInput.value.trim();
    if (!text || isWaiting || !ws || ws.readyState !== 1) return;
    addMessage(text, "user");
    messageInput.value = "";
    isWaiting = true;
    sendBtn.disabled = true;
    ws.send(JSON.stringify({ content: text }));
}

function addMessage(text, type) {
    const div = document.createElement("div");
    div.className = "message " + (type === "user" ? "user" : "ai");
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.textContent = text;
    if (type !== "user") bubble.id = "last";
    div.appendChild(bubble);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function addLoading() {
    const div = document.createElement("div");
    div.className = "message ai";
    const bubble = document.createElement("div");
    bubble.className = "bubble loading";
    bubble.id = "last";
    bubble.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
    div.appendChild(bubble);
    chatBox.appendChild(div);
    chatBox.scrollTop = chatBox.scrollHeight;
}

function appendAI(text) {
    const last = document.getElementById("last");
    if (last && last.classList.contains("loading")) {
        last.classList.remove("loading");
        last.innerHTML = "";
    }
    if (last) {
        last.textContent += text;
        chatBox.scrollTop = chatBox.scrollHeight;
    }
}

messageInput.addEventListener("keypress", (e) => e.key === "Enter" && (e.preventDefault(), sendMessage()));
sendBtn.addEventListener("click", sendMessage);
connectWebSocket();
</script>
</body>
</html>"""

@app.get("/")
def root():
    return HTMLResponse(CHAT_HTML)

@app.websocket("/ws/session/{sid}")
async def ws_endpoint(websocket: WebSocket, sid: str):
    if sid == "new":
        sid = str(uuid.uuid4())
    
    await manager.connect(websocket, sid)
    if sid not in sessions:
        sessions[sid] = []
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            text = msg.get("content", "")
            if not text:
                continue
            
            logger.info(f"Message: {text[:50]}")
            sessions[sid].append({"role": "user", "content": text})
            
            await manager.send_json(sid, {"type": "ai_response_start"})
            full = ""
            async for token in stream_response(sessions[sid]):
                full += token
                await manager.send_json(sid, {"type": "ai_response_chunk", "content": token})
                await asyncio.sleep(0)
            
            if full:
                sessions[sid].append({"role": "assistant", "content": full})
            await manager.send_json(sid, {"type": "ai_response_end"})
            
    except WebSocketDisconnect:
        await manager.disconnect(sid)
    except Exception as e:
        logger.error(f"Error: {e}")
        await manager.disconnect(sid)

if __name__ == "__main__":
    import uvicorn
    print("\nServer: http://localhost:8000\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
