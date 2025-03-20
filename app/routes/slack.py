import os
import time
import tempfile
from fastapi import APIRouter, Request

from app.config import logger, ALLOWED_CHANNEL
from app.utils.helpers import is_duplicate_message
from app.utils.rate_limiter import user_rate_limiter
from app.services.slack_service import (
    get_thread_history, process_current_message, 
    is_image_generation_request,
    upload_file_to_slack
)
from app.services.ai_service import get_openai_response, generate_image
from app.services.file_service import download_image

# Create router for Slack endpoints
router = APIRouter()

@router.post("/slack/events")
async def slack_events(request: Request):
    """Handle Slack events."""
    try:
        # Get request body as JSON
        data = await request.json()
        
        # Handle URL verification
        if data.get("type") == "url_verification":
            logger.info("Handling URL verification challenge")
            return {"challenge": data.get("challenge")}
        
        # Get clients from app state
        slack_client = request.app.state.slack_client
        openai_client = request.app.state.openai_client
        bot_user_id = request.app.state.bot_user_id
        
        # Process event
        event = data.get("event", {})
        event_type = event.get("type")
        
        # Log the event for debugging
        logger.info(f"Received event type: {event_type}, event_ts: {event.get('ts')}, user: {event.get('user')}")
        
        # Only process message and app_mention events
        if event_type not in ["message", "app_mention"]:
            return {"status": "ignored_event_type"}
        
        # Check if the event is from the allowed channel
        channel = event.get("channel")
        if ALLOWED_CHANNEL and channel != ALLOWED_CHANNEL:
            logger.info(f"Ignoring message from unauthorized channel: {channel}")
            return {"status": "ignored_channel"}
        
        # Check for DM channels (which start with 'D')
        if event.get("channel_type") == "im":
            logger.info("Ignoring direct message")
            return {"status": "ignored_dm"}
            
        # More aggressive filtering for bot messages
        if event.get("bot_id") or event.get("user") == bot_user_id or event.get("subtype") == "bot_message":
            logger.info("Ignoring bot message")
            return {"status": "ignored_bot_message"}
        
        # Check for message_changed events which can cause loops
        if event.get("subtype") == "message_changed":
            logger.info("Ignoring message_changed event")
            return {"status": "ignored_message_changed"}
        
        # Check for duplicate messages
        if is_duplicate_message(event):
            logger.info("Ignoring duplicate message")
            return {"status": "ignored_duplicate"}
        
        # Get user_id and team_id for rate limiting
        user_id = event.get("user")
        team_id = data.get("team_id")
        
        # Check rate limiting
        is_limited, reason = user_rate_limiter.is_rate_limited(user_id, team_id)
        if is_limited:
            logger.warning(f"Rate limited user {user_id}: {reason}", {
                "user_id": user_id,
                "team_id": team_id,
                "reason": reason
            })
            
            # Get the remaining seconds until the rate limit resets
            remaining = user_rate_limiter.get_remaining_requests(user_id, team_id)
            reset_seconds = remaining.get("user_window_reset_seconds", 60)
            
            # Notify the user they are being rate limited
            slack_client.chat_postEphemeral(
                channel=channel,
                user=user_id,
                text=f"⚠️ You've reached the rate limit for bot interactions. Please try again in about {int(reset_seconds)} seconds."
            )
            return {"status": "rate_limited", "reason": reason}
        
        # Get channel, thread, and message text
        thread_ts = event.get("thread_ts", event.get("ts"))
        message_text = event.get("text", "").lower()
        
        # Ensure we have actual text to process
        if not message_text.strip():
            logger.info("Ignoring empty message")
            return {"status": "ignored_empty_message"}
            
        logger.info(f"Processing message in thread: {thread_ts}")
        
        # Check for image generation request
        is_image_request, image_prompt = is_image_generation_request(message_text)
        
        if is_image_request and image_prompt:
            logger.info(f"Generating image with prompt: {image_prompt}")
            
            # Send a processing message and capture its timestamp
            processing_msg = slack_client.chat_postMessage(
                channel=channel,
                thread_ts=thread_ts,
                text="Generating image, please wait..."
            )
            processing_msg_ts = processing_msg['ts']
            
            # Generate the image
            image_url = generate_image(openai_client, image_prompt)
            
            if image_url:
                logger.info(f"Image URL received, downloading...")
                
                # Download the image
                image_data = download_image(image_url)
                
                if image_data:
                    logger.info(f"Uploading image to Slack, size: {len(image_data)} bytes")
                    
                    try:
                        # Use tempfile for secure temp file creation
                        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
                            temp_file_path = temp_file.name
                            temp_file.write(image_data)
                            
                        # Upload to Slack
                        upload_success = upload_file_to_slack(
                            slack_client=slack_client,
                            file_path=temp_file_path,
                            filename=f"image_{int(time.time())}.png",
                            title="Generated Image", 
                            initial_comment="Here's your generated image:",
                            channel=channel,
                            thread_ts=thread_ts
                        )
                        
                        # Clean up temp file
                        os.remove(temp_file_path)
                        
                        # Delete the "please wait" message to reduce clutter
                        if upload_success:
                            try:
                                slack_client.chat_delete(
                                    channel=channel,
                                    ts=processing_msg_ts
                                )
                            except Exception as delete_error:
                                logger.warning(f"Could not delete processing message: {delete_error}")
                                
                    except Exception as upload_error:
                        logger.error(f"Error uploading to Slack: {upload_error}")
                        # Fallback to sharing URL if upload fails
                        slack_client.chat_update(
                            channel=channel,
                            ts=processing_msg_ts,
                            text=f"<{image_url}|Here's your generated image> (direct link)"
                        )
                else:
                    # Update the processing message with the direct link
                    slack_client.chat_update(
                        channel=channel,
                        ts=processing_msg_ts,
                        text=f"<{image_url}|Here's your generated image> (direct link)"
                    )
            else:
                # Update the processing message
                slack_client.chat_update(
                    channel=channel,
                    ts=processing_msg_ts,
                    text="Sorry, I couldn't generate the image. Please try a different prompt."
                )
            
            return {"status": "ok_image_generation"}
        
        # Process the current message for normal conversation
        current_message = process_current_message(slack_client, openai_client, event)
        
        # Get thread history if this is in a thread
        conversation = []
        if thread_ts and thread_ts != event.get("ts"):
            # Only get history if this is a reply in a thread, not the start of a thread
            thread_history = get_thread_history(slack_client, openai_client, channel, thread_ts, bot_user_id)
            if thread_history:
                conversation.extend(thread_history)
                logger.info(f"Retrieved {len(conversation)} messages from thread history")
        
        # Add the current message to the conversation
        conversation.append(current_message)
        
        # Get response from OpenAI with conversation history
        ai_response = get_openai_response(openai_client, conversation)
        
        # Post response to Slack
        slack_client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=ai_response
        )
        
        return {"status": "ok"}
        
    except Exception as e:
        logger.error(f"Error: {e}")
        return {"status": "error", "message": str(e)}
