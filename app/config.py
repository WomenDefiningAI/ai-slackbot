import os
import logging
from app.utils.pii_logger import get_logger

# Set up logging
logging.basicConfig(level=logging.INFO)
# Create PII-redacted logger
logger = get_logger("slackbot")

# Environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Optional environment variables with defaults
MAX_THREAD_HISTORY = int(os.environ.get("MAX_THREAD_HISTORY", "10"))
ALLOWED_CHANNEL = os.environ.get("ALLOWED_CHANNEL")

# Rate limiting configuration
RATE_LIMIT_ENABLED = os.environ.get("RATE_LIMIT_ENABLED", "true").lower() in ("true", "1", "yes")
USER_RATE_LIMIT_WINDOW = int(os.environ.get("USER_RATE_LIMIT_WINDOW", "60"))  # seconds
USER_RATE_LIMIT_MAX = int(os.environ.get("USER_RATE_LIMIT_MAX", "10"))  # requests per window
TEAM_RATE_LIMIT_WINDOW = int(os.environ.get("TEAM_RATE_LIMIT_WINDOW", "60"))  # seconds
TEAM_RATE_LIMIT_MAX = int(os.environ.get("TEAM_RATE_LIMIT_MAX", "100"))  # requests per window

# Log configuration
logger.info(f"Bot configured to work only in channel: {ALLOWED_CHANNEL}")
if RATE_LIMIT_ENABLED:
    logger.info(f"Rate limiting enabled: {USER_RATE_LIMIT_MAX} requests per {USER_RATE_LIMIT_WINDOW}s per user, " +
                f"{TEAM_RATE_LIMIT_MAX} requests per {TEAM_RATE_LIMIT_WINDOW}s per team")
else:
    logger.info("Rate limiting disabled")

# Constants for the application
DEFAULT_MODEL = "gpt-4o"  # This model supports web search capability
IMAGE_MODEL = "dall-e-3"
TTS_MODEL = "tts-1"
WHISPER_MODEL = "whisper-1"
TTS_VOICE = "alloy"  # Options: alloy, echo, fable, onyx, nova, shimmer
IMAGE_SIZE = "1024x1024"
IMAGE_QUALITY = "standard"
MAX_CACHE_SIZE = 100
CACHE_EXPIRY_SECONDS = 60
