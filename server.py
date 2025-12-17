import os
import logging
import uuid
import json
import asyncio
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))

openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
sessions: Dict[str, List[dict]] = {}

class Manager:
    def __init__(self):
        self.active = {}
    
    async def connect(self, ws: WebSocket, sid: str):
        await ws.accept()
        self.active[sid] = ws
        logger.info(f"Connected: {sid}")
    
    async def disconnect(self, sid: str):
        if sid in self.active:
            del self.active[sid]
    
    async def send_json(self, sid: str, data: dict):
        if sid in self.active:
            try:
                await self.active[sid].send_json(data)
            except:
                pass

manager = Manager()
app = FastAPI()

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Chat</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 10px;
        }
        .container {
            width: 100%;
            max-width: 700px;
            height: 85vh;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .header h1 { font-size: 24px; margin-bottom: 5px; }
        .chat-box {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .message { display: flex; animation: slideIn 0.3s ease; }
        .message.user { justify-content: flex-end; }
        .bubble {
            max-width: 75%;
            padding: 12px 16px;
            border-radius: 15px;
            line-height: 1.4;
            font-size: 14px;
        }
        .message.user .bubble {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        .message.ai .bubble { background: #e9ecef; color: #333; }
        .loading { display: flex; gap: 4px; align-items: center; }
        .dot {
            width: 6px;
            height: 6px;
            background: #667eea;
            border-radius: 50%;
            animation: bounce 1.4s infinite;
        }
        .dot:nth-child(2) { animation-delay: 0.2s; }
        .dot:nth-child(3) { animation-delay: 0.4s; }
        @keyframes bounce { 0%, 60%, 100% { opacity: 0.3; } 30% { opacity: 1; } }
        @keyframes slideIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; } }
        .input-area {
            padding: 16px 20px;
            border-top: 1px solid #ddd;
            display: flex;
            gap: 10px;
        }
        #msg { flex: 1; padding: 12px 15px; border: 1px solid #ddd; border-radius: 25px; }
        #msg:focus { outline: none; border-color: #667eea; }
        #send {
            padding: 12px 25px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-weight: 600;
        }
        #send:disabled { opacity: 0.6; cursor: not-allowed; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>Chat</h1></div>
        <div id="box" class="chat-box"></div>
        <div class="input-area">
            <input type="text" id="msg" placeholder="Type message..." autofocus>
            <button id="send">Send</button>
        </div>
    </div>
    <script>
        let ws;
        const box = document.getElementById('box');
        const msg = document.getElementById('msg');
        const send = document.getElementById('send');
        let waiting = false;

        function connect() {
            const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const host = window.location.host;
            ws = new WebSocket(proto + '//' + host + '/ws/new');
            
            ws.onopen = () => console.log('Connected');
            ws.onmessage = (e) => {
                const data = JSON.parse(e.data);
                if (data.type === 'start') addLoading();
                else if (data.type === 'chunk') appendAI(data.text);
                else if (data.type === 'end') {
                    waiting = false;
                    send.disabled = false;
                }
            };
            ws.onerror = (e) => console.error('Error', e);
            ws.onclose = () => setTimeout(connect, 3000);
        }

        function sendMsg() {
            const text = msg.value.trim();
            if (!text || waiting) return;
            
            const div = document.createElement('div');
            div.className = 'message user';
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = text;
            div.appendChild(bubble);
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
            
            msg.value = '';
            waiting = true;
            send.disabled = true;
            ws.send(JSON.stringify({content: text}));
        }

        function addLoading() {
            const div = document.createElement('div');
            div.className = 'message ai';
            const bubble = document.createElement('div');
            bubble.className = 'bubble loading';
            bubble.id = 'ai';
            bubble.innerHTML = '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';
            div.appendChild(bubble);
            box.appendChild(div);
            box.scrollTop = box.scrollHeight;
        }

        function appendAI(text) {
            const ai = document.getElementById('ai');
            if (!ai) return;
            if (ai.classList.contains('loading')) {
                ai.classList.remove('loading');
                ai.innerHTML = '';
            }
            ai.textContent += text;
            box.scrollTop = box.scrollHeight;
        }

        msg.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendMsg();
            }
        });
        send.addEventListener('click', sendMsg);
        connect();
    </script>
</body>
</html>"""

async def stream(conv):
    try:
        resp = await openai_client.chat.completions.create(
            model=LLM_MODEL,
            messages=[{"role": "system", "content": "You are helpful."}] + conv,
            temperature=LLM_TEMPERATURE,
            stream=True,
            max_tokens=2000
        )
        async for chunk in resp:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except Exception as e:
        logger.error(str(e))
        yield f"Error: {str(e)}"

@app.get("/")
def home():
    return HTMLResponse(HTML)

@app.websocket("/ws/new")
async def ws(websocket: WebSocket):
    sid = str(uuid.uuid4())
    await manager.connect(websocket, sid)
    sessions[sid] = []
    
    try:
        while True:
            data = await websocket.receive_text()
            msg_data = json.loads(data)
            text = msg_data.get("content", "")
            
            if not text:
                continue
            
            sessions[sid].append({"role": "user", "content": text})
            await manager.send_json(sid, {"type": "start"})
            
            full = ""
            async for token in stream(sessions[sid]):
                full += token
                await manager.send_json(sid, {"type": "chunk", "text": token})
                await asyncio.sleep(0)
            
            if full and not full.startswith("Error"):
                sessions[sid].append({"role": "assistant", "content": full})
            
            await manager.send_json(sid, {"type": "end"})
            
    except WebSocketDisconnect:
        await manager.disconnect(sid)
    except Exception as e:
        logger.error(str(e))
        await manager.disconnect(sid)

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    print("CHAT SERVER")
    print("="*60)
    print("Server: http://localhost:8000")
    print("="*60 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
