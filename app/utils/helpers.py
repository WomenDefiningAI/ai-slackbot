import hashlib
import time
from typing import Dict, Any

from app.config import logger, MAX_CACHE_SIZE, CACHE_EXPIRY_SECONDS

# Simple in-memory cache to prevent duplicate processing
# Format: {message_hash: timestamp}
processed_messages: Dict[str, str] = {}


def create_message_hash(event: Dict[str, Any]) -> str:
    """
    Create a unique hash for a message to prevent duplicate processing.
    Note: This is NOT used for security purposes, only for duplicate detection.
    """
    text = event.get("text", "")
    files = "-".join([f["id"] for f in event.get("files", [])])
    timestamp = event.get("ts", "")

    # Create a unique signature
    message_signature = f"{text}|{files}|{timestamp}"
    # Use SHA-256 which is more secure than MD5
    return hashlib.sha256(message_signature.encode("utf-8")).hexdigest()


def is_duplicate_message(event: Dict[str, Any]) -> bool:
    """Check if a message has already been processed."""
    message_hash = create_message_hash(event)

    # Check if this exact message was processed recently
    if message_hash in processed_messages:
        logger.info(f"Duplicate message detected: {event.get('text', '')[:30]}...")
        return True

    # Check the timestamp to prevent processing very old messages that might suddenly appear
    event_ts = float(event.get("ts", 0))
    current_time = time.time()
    if current_time - event_ts > CACHE_EXPIRY_SECONDS:
        logger.info(f"Ignoring old message from {current_time - event_ts} seconds ago")
        return True

    # Store this message hash
    processed_messages[message_hash] = event.get("ts", "")

    # Cleanup old entries (keep only the last MAX_CACHE_SIZE)
    if len(processed_messages) > MAX_CACHE_SIZE:
        # Remove the oldest entries
        sorted_keys = sorted(processed_messages.items(), key=lambda x: x[1])
        for key, _ in sorted_keys[: len(processed_messages) - MAX_CACHE_SIZE]:
            processed_messages.pop(key, None)

    return False
