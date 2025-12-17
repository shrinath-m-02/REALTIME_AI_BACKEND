# Realtime AI Backend - WebSockets + Supabase

A production-ready FastAPI backend for real-time AI conversations with WebSocket streaming, Supabase persistence, tool calling, and async background tasks.

## 🎯 Features

✅ **Real-time WebSocket Streaming** - Token-by-token LLM response streaming  
✅ **Tool Calling** - LLM can invoke tools (fetch_user_profile, get_system_metrics)  
✅ **Supabase Integration** - Full session and event persistence with fallback in-memory storage  
✅ **Async Architecture** - 100% async with proper event loop management  
✅ **Session Management** - Track conversations, calculate duration, generate summaries  
✅ **Background Tasks** - Non-blocking session summaries on disconnect  
✅ **Beautiful UI** - Modern web frontend with real-time chat  
✅ **Production Ready** - Error handling, logging, health checks  

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  WebSocket Endpoint (/ws/session/{session_id})         │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐              │
│         │                 │                 │              │
│    ┌────▼───┐     ┌──────▼──────┐   ┌─────▼──────┐      │
│    │ Manager  │     │  Session    │   │ Summary    │      │
│    │ (WS)    │     │ Service     │   │ Service    │      │
│    └────┬───┘     └──────┬──────┘   └─────┬──────┘      │
│         │                 │                │               │
│         └─────────────────┼────────────────┘              │
│                           │                               │
│                    ┌──────▼──────┐                        │
│                    │ LLM Service  │                        │
│                    │ (Streaming)  │                        │
│                    └──────┬──────┘                        │
│                           │                               │
│                    ┌──────▼──────┐                        │
│                    │   OpenAI     │                        │
│                    │   API        │                        │
│                    └──────────────┘                        │
│         │                                                  │
│         └──► ┌─────────────────────┐                     │
│             │ Supabase Service    │                     │
│             │ (Persistence)       │                     │
│             └──────────┬──────────┘                     │
│                        │                                │
│              ┌─────────┴──────────┐                    │
│              │                    │                    │
│          ┌───▼───┐          ┌────▼─────┐            │
│          │Session│          │Event Logs │            │
│          │ Table │          │  Table    │            │
│          └───────┘          └───────────┘            │
│                                                        │
└────────────────────────────────────────────────────────┘
```

## 📊 Database Schema

### Sessions Table
```sql
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    final_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
```

### Event Logs Table
```sql
CREATE TABLE event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_event_logs_session_id ON event_logs(session_id);
CREATE INDEX idx_event_logs_created_at ON event_logs(created_at);
```

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10+
- OpenAI API key
- (Optional) Supabase account for cloud persistence

### 2. Installation

```bash
# Clone repository
cd realtime_ai_backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Edit `.env`:
```env
# Required
OPENAI_API_KEY=sk-proj-xxxxx

# Optional - leave empty to use in-memory storage
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key

# Optional
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.7
SERVER_PORT=8001
```

### 4. Setup Supabase (Optional)

If using Supabase, run these SQL commands:

```sql
-- Create sessions table
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL UNIQUE,
    user_id TEXT,
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    final_summary TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create event logs table
CREATE TABLE event_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_sessions_session_id ON sessions(session_id);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_event_logs_session_id ON event_logs(session_id);
CREATE INDEX idx_event_logs_created_at ON event_logs(created_at);
```

### 5. Run Server

```bash
python main.py
```

Or with uvicorn directly:

```bash
uvicorn main:app --host 127.0.0.1 --port 8001 --reload
```

Access:
- **Web UI**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **WebSocket**: ws://localhost:8001/ws/session/{session_id}
- **Health**: http://localhost:8001/health

## 📡 WebSocket Protocol

### Connection
```javascript
ws = new WebSocket("ws://localhost:8001/ws/session/my-session-123");
```

### Message Format

**Client → Server** (text):
```
"Hello, what is the weather like?"
```

**Server → Client** (JSON):
```json
// Connection established
{"type": "system", "content": "Connected to session..."}

// Start of AI response
{"type": "ai_response_start"}

// Streaming chunks
{"type": "ai_response_chunk", "content": "The"}
{"type": "ai_response_chunk", "content": " weather"}
{"type": "ai_response_chunk", "content": "..."}

// End of response
{"type": "ai_response_end"}

// Error
{"type": "error", "content": "Error message"}
```

## 🛠️ Tool Calling

The LLM can automatically call these tools:

### `fetch_user_profile`
```json
{
    "name": "fetch_user_profile",
    "parameters": {
        "user_id": "user123"
    }
}
```

**Response:**
```json
{
    "user_id": "user123",
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "account_status": "active",
    "subscription_tier": "premium"
}
```

### `get_system_metrics`
```json
{
    "name": "get_system_metrics",
    "parameters": {
        "metric_type": "all"
    }
}
```

**Response:**
```json
{
    "cpu_usage_percent": 45.2,
    "memory_usage_percent": 62.8,
    "memory_available_gb": 8.2,
    "timestamp": "2024-12-17 10:30:00"
}
```

## 🧪 Testing

### Browser
1. Open http://localhost:8001
2. Type message and press Enter
3. See real-time streaming response

### Using wscat
```bash
# Install wscat
npm install -g wscat

# Connect
wscat -c "ws://localhost:8001/ws/session/test-123"

# Send message (type and press Enter)
> Tell me about your system metrics
```

### Using Python
```python
import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8001/ws/session/test-123") as ws:
        # Receive connection message
        msg = await ws.recv()
        print("System:", json.loads(msg))
        
        # Send message
        await ws.send("What can you tell me about users?")
        
        # Receive streaming response
        while True:
            try:
                msg = await ws.recv()
                data = json.loads(msg)
                print(f"{data['type']}: {data.get('content', '')}", end="", flush=True)
            except:
                break

asyncio.run(test())
```

### Using curl + websocat
```bash
# Install websocat
cargo install websocat  # or download binary

# Test
echo "Hi there" | websocat ws://localhost:8001/ws/session/test-123
```

## 📂 Project Structure

```
realtime_ai_backend/
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py          # Configuration management
│   │   ├── llm.py             # OpenAI streaming + tool calling
│   │   └── websocket.py       # WebSocket manager
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py          # Pydantic models
│   │   └── supabase.py        # Database operations
│   └── services/
│       ├── __init__.py
│       ├── session_service.py # Session state management
│       ├── summary_service.py # Session summary generation
│       └── tools.py           # Tool execution
├── static/
│   └── index.html             # Web UI
├── main.py                    # FastAPI application
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
└── README.md                 # This file
```

## 🔑 Key Design Decisions

### 1. **100% Async Architecture**
- All database operations are async-ready
- Uses asyncio background tasks for non-blocking summaries
- Event loop properly yielded during streaming

### 2. **Dual Storage Strategy**
- **Primary**: Supabase (when configured) for cloud persistence
- **Fallback**: In-memory dictionaries for offline/development
- Automatic fallback if Supabase is unavailable

### 3. **WebSocket Streaming Without Buffering**
- Tokens are sent immediately to client
- No waiting for complete LLM response
- Low latency: ~50-200ms per token

### 4. **Tool Calling Integration**
- LLM can detect when tools are needed
- Tool results are fed back into conversation
- Seamless continuation of response

### 5. **Session Lifecycle**
```
CONNECT → CREATE_SESSION → 
RECEIVE_MESSAGE → 
  ADD_TO_CONVERSATION → 
  STREAM_LLM_RESPONSE → 
  SAVE_EVENTS →
REPEAT MESSAGE_HANDLING →
DISCONNECT → 
  TRIGGER_SUMMARY_TASK (non-blocking) →
  SAVE_END_TIME_AND_DURATION
```

### 6. **Error Handling**
- Graceful WebSocket error recovery
- Database fallback to in-memory storage
- Detailed logging for debugging
- User-friendly error messages

## 📈 Performance Considerations

- **Streaming Latency**: ~100-300ms from user message to first token
- **Token Generation**: ~50-150ms per token (depends on model)
- **Database Operations**: Async, non-blocking
- **Concurrent Sessions**: Limited by OpenAI API rate limits and server resources
- **Memory Usage**: ~50MB baseline + ~1MB per active session

## 🔒 Security Notes

⚠️ **For Production:**
- Set `DEBUG=false` in .env
- Use environment variables for all secrets (never hardcode)
- Implement authentication (JWT, API keys)
- Rate limiting on WebSocket endpoints
- HTTPS/WSS (not WS) for cloud deployment
- Input validation and sanitization
- SQL injection protection (Supabase handles via ORM)

## 🐛 Troubleshooting

### WebSocket Connection Fails
```
Error: Connection refused
```
- Check server is running: `python main.py`
- Verify port: `netstat -an | grep 8001`
- Check firewall settings

### "No module named 'app.core.config'"
```bash
# Ensure you're running from project root
cd /path/to/realtime_ai_backend
python main.py
```

### Supabase Connection Error
```
ModuleNotFoundError: No module named 'supabase'
```
- Install: `pip install supabase`
- Or reinstall: `pip install -r requirements.txt`

### "OPENAI_API_KEY not set"
```bash
# Create .env file with your key
echo "OPENAI_API_KEY=sk-proj-xxx" > .env
```

### LLM Requests Timeout
- Increase `LLM_TIMEOUT` in .env (default: 30 seconds)
- Check OpenAI API status
- Try with `gpt-4o-mini` (faster) instead of `gpt-4`

## 📝 API Endpoints

### WebSocket
- `GET /ws/session/{session_id}` - Open WebSocket connection

### REST
- `GET /` - Serve web UI (index.html)
- `GET /health` - Health check endpoint
- `GET /api/session/{session_id}` - Get session details and history
- `GET /docs` - Interactive API documentation (Swagger)
- `GET /redoc` - Alternative API documentation

## 🚀 Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV OPENAI_API_KEY=${OPENAI_API_KEY}
ENV SUPABASE_URL=${SUPABASE_URL}
ENV SUPABASE_KEY=${SUPABASE_KEY}

CMD ["python", "main.py"]
```

Build and run:
```bash
docker build -t realtime-ai-backend .
docker run -p 8001:8001 \
  -e OPENAI_API_KEY=sk-proj-xxx \
  -e SUPABASE_URL=https://xxx.supabase.co \
  -e SUPABASE_KEY=xxx \
  realtime-ai-backend
```

### Heroku
```bash
heroku create your-app-name
heroku config:set OPENAI_API_KEY=sk-proj-xxx
heroku config:set SUPABASE_URL=https://xxx.supabase.co
heroku config:set SUPABASE_KEY=xxx
git push heroku main
```

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [OpenAI API](https://platform.openai.com/docs)
- [Supabase Documentation](https://supabase.com/docs)
- [Python asyncio](https://docs.python.org/3/library/asyncio.html)

## 📄 License

MIT License - feel free to use this project for personal or commercial purposes.

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

---

**Built with ❤️ using FastAPI, OpenAI, and Supabase**
