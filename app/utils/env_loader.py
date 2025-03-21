import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_env_file(env_file=".env"):
    """
    Load environment variables from .env file for local development.
    This is only used for development, not production.
    """
    try:
        env_path = Path(env_file)
        if env_path.exists():
            logger.info(f"Loading environment variables from {env_file}")
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if not line or line.startswith("#"):
                        continue

                    # Parse key-value pairs
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip()

                        # Don't override existing environment variables
                        if key not in os.environ:
                            os.environ[key] = value
                            logger.debug(f"Set environment variable: {key}")

            return True
        else:
            logger.warning(
                f"Environment file {env_file} not found. Using existing environment variables."
            )
            return False
    except Exception as e:
        logger.error(f"Error loading environment file: {e}")
        return False
