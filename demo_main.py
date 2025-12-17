from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="Realtime AI Backend - Demo", version="1.0.0")

@app.get("/")
async def root():
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Realtime AI Backend</title>
    <style>
        body { font-family: Arial; max-width: 800px; margin: 50px auto; padding: 20px; }
        .status { padding: 20px; background: #e8f5e9; border-radius: 8px; margin: 20px 0; }
        h1 { color: #667eea; }
        .code { background: #f5f5f5; padding: 15px; border-radius: 5px; font-family: monospace; overflow-x: auto; }
        a { color: #667eea; text-decoration: none; }
        a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1> Realtime AI Backend is Running!</h1>
    <div class="status">
        <h2>Demo Project Status: Active</h2>
        <p><strong>Server:</strong> http://localhost:8000</p>
        <p><strong>API Docs:</strong> <a href="/docs" target="_blank">/docs</a></p>
        <p><strong>Project Files:</strong> C:\workspace\realtime_ai_backend\</p>
    </div>
    <h2>Project Structure</h2>
    <div class="code">
app/
  core/ (Configuration, WebSocket, LLM)
  db/ (Supabase, Models)
  services/ (Session, Summary, Tools)
  migrations/ (Database schema)
static/ (Web UI)
main.py (FastAPI server)
requirements.txt (Dependencies)
    </div>
    <h2>To Enable Full AI Chat</h2>
    <ol>
        <li>Get Supabase credentials (free at supabase.com)</li>
        <li>Get OpenAI API key from platform.openai.com</li>
        <li>Edit .env file with credentials</li>
        <li>Run: pip install -r requirements.txt</li>
        <li>Run: python main.py</li>
    </ol>
</body>
</html>"""
    return HTMLResponse(content=html)

@app.get("/health")
async def health():
    return {"status": "Realtime AI Backend is Running!", "version": "1.0.0"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
