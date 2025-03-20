import os
from fastapi import FastAPI
from slack_sdk import WebClient
from openai import OpenAI

# Try to load environment variables from .env file (for local development only)
try:
    from app.utils.env_loader import load_env_file
    load_env_file()
except ImportError:
    pass  # Skip if not in development mode

from app.config import SLACK_BOT_TOKEN, OPENAI_API_KEY, logger
from app.routes import health, slack
from app.services.slack_service import get_bot_user_id

# Initialize FastAPI app
app = FastAPI(title="WDAI Slack AI Bot")

# Include routers
app.include_router(health.router)
app.include_router(slack.router)

@app.on_event("startup")
async def startup_event():
    """Initialize clients and configurations on startup."""
    # Initialize Slack client
    app.state.slack_client = WebClient(token=SLACK_BOT_TOKEN)
    
    # Initialize OpenAI client with default configuration
    # This client will be used for all OpenAI API calls including web search
    app.state.openai_client = OpenAI(api_key=OPENAI_API_KEY)
    
    # Get bot user ID
    app.state.bot_user_id = get_bot_user_id(app.state.slack_client)
    
    logger.info(f"Bot started with user ID: {app.state.bot_user_id}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    
    # Bind to localhost by default, but allow external access if explicitly enabled
    host = "0.0.0.0" if os.environ.get("ALLOW_EXTERNAL_ACCESS", "").lower() in ("true", "1", "yes") else "127.0.0.1"
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run("app.main:app", host=host, port=port)
