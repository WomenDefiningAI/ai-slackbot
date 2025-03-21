from typing import List, Dict, Any, Optional, Tuple

from app.config import logger, MAX_THREAD_HISTORY
from app.services.file_service import process_file_attachment


def get_bot_user_id(slack_client) -> Optional[str]:
    """Get the bot's user ID from Slack."""
    try:
        bot_info = slack_client.auth_test()
        bot_user_id = bot_info["user_id"]
        logger.info(f"Bot user ID: {bot_user_id}")
        return bot_user_id
    except Exception as e:
        logger.error(f"Could not get bot user ID: {e}")
        return None


def get_thread_history(
    slack_client, openai_client, channel_id: str, thread_ts: str, bot_user_id: str
) -> List[Dict[str, Any]]:
    """Get conversation history from a thread."""
    try:
        # Fetch the conversation history
        result = slack_client.conversations_replies(
            channel=channel_id, ts=thread_ts, limit=MAX_THREAD_HISTORY
        )

        messages = result.get("messages", [])

        # Deduplicate messages to avoid repetition
        message_contents = set()

        # Process each message and its attachments
        conversation = []
        for msg in messages:
            # Skip bot's own messages - we'll add them differently
            if msg.get("user") == bot_user_id:
                # Don't deduplicate assistant messages
                conversation.append(
                    {"role": "assistant", "content": msg.get("text", "")}
                )
                continue

            # Create a unique hash for this message
            msg_text = msg.get("text", "")
            if not msg_text:
                continue

            # Skip duplicate messages
            if msg_text in message_contents:
                logger.info(f"Skipping duplicate message: {msg_text[:30]}...")
                continue

            message_contents.add(msg_text)

            content_items = []

            # Add text content if present
            content_items.append({"type": "text", "text": msg_text})

            # Check for files/attachments
            if "files" in msg:
                for file in msg["files"]:
                    file_content = process_file_attachment(
                        slack_client, openai_client, file
                    )
                    if file_content:
                        content_items.append(file_content)

            # If we have content items, add the message
            if content_items:
                conversation.append({"role": "user", "content": content_items})

        return conversation

    except Exception as e:
        logger.error(f"Error fetching thread history: {e}")
        return []


def process_current_message(
    slack_client, openai_client, event: Dict[str, Any]
) -> Dict[str, Any]:
    """Process the current message including any attachments."""
    content_items = []

    # Add text content
    text = event.get("text", "")
    if text:
        content_items.append({"type": "text", "text": text})

    # Check for files/attachments
    if "files" in event:
        for file in event["files"]:
            file_content = process_file_attachment(slack_client, openai_client, file)
            if file_content:
                content_items.append(file_content)

    if content_items:
        return {"role": "user", "content": content_items}
    return {"role": "user", "content": "Hello"}  # Fallback if no content


def is_image_generation_request(message_text: str) -> Tuple[bool, Optional[str]]:
    """Determine if a message is requesting image generation and extract the prompt."""
    message_text = message_text.lower()

    # Verbs and nouns that might indicate an image generation request
    image_generation_verbs = [
        "generate",
        "create",
        "make",
        "draw",
        "design",
        "produce",
        "render",
        "show",
        "visualize",
        "depict",
        "illustrate",
        "craft",
    ]
    image_nouns = [
        "image",
        "picture",
        "photo",
        "meme",
        "drawing",
        "art",
        "illustration",
        "visual",
        "graphic",
        "diagram",
        "scene",
        "portrait",
        "cartoon",
    ]

    # Check if any verb + noun combination exists in the message
    if any(verb in message_text for verb in image_generation_verbs) and any(
        noun in message_text for noun in image_nouns
    ):
        # Find which verb was used
        used_verb = next(
            (verb for verb in image_generation_verbs if verb in message_text), None
        )

        if used_verb:
            # Extract the prompt - everything after the verb
            prompt_parts = message_text.split(used_verb, 1)
            if len(prompt_parts) > 1:
                prompt = prompt_parts[1].strip()

                # If prompt starts with "a" or "an" or similar preposition, trim it
                words_to_trim = ["a ", "an ", "the ", "of ", "about ", "showing "]
                for word in words_to_trim:
                    if prompt.startswith(word):
                        prompt = prompt[len(word) :].strip()
                        break

                return True, prompt

    return False, None


def upload_file_to_slack(
    slack_client,
    file_path: str,
    filename: str,
    title: str,
    initial_comment: str,
    channel: str,
    thread_ts: str,
) -> bool:
    """Upload a file to Slack."""
    try:
        result = slack_client.files_upload_v2(
            file=file_path,
            filename=filename,
            title=title,
            initial_comment=initial_comment,
            channel=channel,
            thread_ts=thread_ts,
        )
        logger.info(f"File uploaded successfully to Slack: {result.get('file_id')}")
        return True
    except Exception as e:
        logger.error(f"Error uploading file to Slack: {e}")
        return False
