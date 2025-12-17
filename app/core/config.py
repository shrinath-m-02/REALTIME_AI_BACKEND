import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root - try multiple locations
env_locations = [
    Path(__file__).resolve().parent.parent.parent / ".env",  # app/core/config.py -> .env
    Path.cwd() / ".env",  # Current working directory
    Path("c:/workspace/realtime_ai_backend/.env"),  # Absolute path
]

for env_path in env_locations:
    if env_path.exists():
        print(f"Loading .env from: {env_path}")
        load_dotenv(dotenv_path=env_path, override=False)
        break

# Fix any BOM-encoded keys by reassigning from os.environ with BOM stripped
if not os.getenv("OPENAI_API_KEY"):
    # Check for BOM-prefixed key
    for key, value in os.environ.items():
        if 'OPENAI_API_KEY' in key:
            clean_key = key.lstrip('\ufeff')
            if clean_key == 'OPENAI_API_KEY':
                os.environ['OPENAI_API_KEY'] = value
                break

class Settings:
    """Application configuration loaded from environment variables"""
    
    # Debug mode
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"
    
    # OpenAI / LLM Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.7"))
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1500"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    SUPABASE_POOL_SIZE = int(os.getenv("SUPABASE_POOL_SIZE", "10"))
    
    # Session Configuration
    SESSION_TIMEOUT_SECONDS = int(os.getenv("SESSION_TIMEOUT_SECONDS", "3600"))
    
    # Server Configuration
    SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "8001"))
    
    def validate(self):
        """Validate critical configuration"""
        if not self.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is required")
        return True

settings = Settings()
