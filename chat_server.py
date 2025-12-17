import os
import uuid
import json
import asyncio
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv("C:\\workspace\\realtime_ai_backend\\.env")

app = FastAPI()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
sessions = {}
MODEL = os.getenv("LLM_MODEL", "gpt-4")

HTML = """<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width"><title>Chat</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:system-ui;background:linear-gradient(135deg,#667eea,#764ba2);min-height:100vh;display:flex;align-items:center;justify-content:center}.container{width:100%;max-width:700px;height:85vh;background:white;border-radius:15px;box-shadow:0 20px 60px rgba(0,0,0,.3);display:flex;flex-direction:column}.header{background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;text-align:center}.header h1{font-size:24px;margin:0}.chat-box{flex:1;overflow-y:auto;padding:20px;background:#f8f9fa;display:flex;flex-direction:column;gap:12px}.message{display:flex}.message.user{justify-content:flex-end}.message.ai{justify-content:flex-start}.bubble{max-width:75%;padding:12px 16px;border-radius:15px;word-wrap:break-word;font-size:14px}.message.user .bubble{background:linear-gradient(135deg,#667eea,#764ba2);color:white}.message.ai .bubble{background:#e9ecef;color:#333}.input-area{padding:16px 20px;border-top:1px solid #ddd;display:flex;gap:10px}#messageInput{flex:1;padding:12px 15px;border:1px solid #ddd;border-radius:25px;font-size:14px;font-family:inherit}#messageInput:focus{outline:0;border-color:#667eea}#sendBtn{padding:12px 25px;background:linear-gradient(135deg,#667eea,#764ba2);color:white;border:0;border-radius:25px;cursor:pointer;font-weight:600;font-size:14px}#sendBtn:disabled{opacity:.6}</style></head><body><div class="container"><div class="header"><h1>AI Chat</h1></div><div id="chatBox" class="chat-box"></div><div class="input-area"><input type="text" id="messageInput" placeholder="Type message..." autocomplete="off"><button id="sendBtn">Send</button></div></div><script>let ws,waiting=false;const chat=document.getElementById('chatBox'),input=document.getElementById('messageInput'),btn=document.getElementById('sendBtn');function connect(){const proto=location.protocol==='https:'?'wss:':'ws:',url=proto+'//'+location.host+'/ws/new';ws=new WebSocket(url);ws.onopen=()=>{console.log('Connected');msg('Ready!',false)};ws.onmessage=e=>{const d=JSON.parse(e.data);if(d.type==='start'){const div=document.createElement('div');div.className='message ai';const b=document.createElement('div');b.className='bubble';b.id='aiMsg';b.textContent='';div.appendChild(b);chat.appendChild(div)}else if(d.type==='chunk'){const ai=document.getElementById('aiMsg');if(ai)ai.textContent+=d.text}else if(d.type==='end'){waiting=false;btn.disabled=false}};ws.onerror=()=>msg('Error',false);ws.onclose=()=>setTimeout(connect,3000)}function msg(text,isUser){const div=document.createElement('div');div.className='message '+(isUser?'user':'ai');const b=document.createElement('div');b.className='bubble';b.textContent=text;div.appendChild(b);chat.appendChild(div);chat.scrollTop=chat.scrollHeight}function send(){const text=input.value.trim();if(!text||waiting)return;msg(text,true);input.value='';waiting=true;btn.disabled=true;ws.send(JSON.stringify({text}))}input.addEventListener('keypress',e=>{e.key==='Enter'&&send()});btn.onclick=send;connect()</script></body></html>"""

@app.get("/")
async def root():
    return HTMLResponse(HTML)

@app.websocket("/ws/new")
async def ws_endpoint(websocket: WebSocket):
    sid = str(uuid.uuid4())
    await websocket.accept()
    sessions[sid] = []
    
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data).get("text", "").strip()
            
            if not msg:
                continue
            
            sessions[sid].append({"role": "user", "content": msg})
            await websocket.send_json({"type": "start"})
            
            response = await client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "system", "content": "You are helpful."}] + sessions[sid],
                stream=True,
                max_tokens=2000
            )
            
            full = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    token = chunk.choices[0].delta.content
                    full += token
                    await websocket.send_json({"type": "chunk", "text": token})
                    await asyncio.sleep(0)
            
            sessions[sid].append({"role": "assistant", "content": full})
            await websocket.send_json({"type": "end"})
            
    except Exception as e:
        print(f"Error: {e}")
        if sid in sessions:
            del sessions[sid]

if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*50)
    print("AI Chat Server - http://localhost:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
