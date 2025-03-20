import os
import time
import tempfile
from typing import List, Dict, Any, Optional
import requests

from app.config import (
    logger, DEFAULT_MODEL, IMAGE_MODEL, 
    IMAGE_SIZE, IMAGE_QUALITY, TTS_MODEL, TTS_VOICE, WHISPER_MODEL
)
from app.clients.slack_client import WebClient


def get_openai_response(openai_client, messages: List[Dict[str, Any]]) -> str:
    """Get a response from OpenAI with conversation history."""
    try:
        # Prepend system message
        full_messages = [{
            "role": "system", 
            "content": "You are a helpful assistant. If there are images in the conversation, describe what you see in them and answer any questions about them. If there is CSV, PDF, or tabular data, analyze it appropriately. Always provide concise, clear responses. For any creative requests like haikus, provide ONLY ONE response."
        }]
        
        # Add the other messages
        for msg in messages:
            full_messages.append(msg)
        
        # Log the messages being sent
        logger.info(f"Sending {len(full_messages)} messages to OpenAI")
        
        # Use specified model
        completion = openai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=full_messages
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"OpenAI API error: {e}")
        return f"Sorry, I encountered an error: {str(e)}"


def generate_image(openai_client, prompt: str) -> Optional[str]:
    """Generate an image using DALL-E 3."""
    try:
        logger.info(f"Calling DALL-E API with prompt: {prompt}")
        response = openai_client.images.generate(
            model=IMAGE_MODEL,
            prompt=prompt,
            size=IMAGE_SIZE,
            quality=IMAGE_QUALITY,
            n=1,
        )
        image_url = response.data[0].url
        logger.info(f"Image generated successfully, URL: {image_url[:50]}...")
        return image_url
    except Exception as e:
        logger.error(f"Error generating image: {e}")
        return None


def convert_text_to_speech(openai_client, text: str) -> Optional[str]:
    """Convert text to speech using OpenAI TTS."""
    try:
        response = openai_client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=text
        )
        
        # Use tempfile for secure temp file creation
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file_path = temp_file.name
            response.stream_to_file(temp_file_path)
        
        return temp_file_path
    except Exception as e:
        logger.error(f"Error converting text to speech: {e}")
        return None


def transcribe_audio(openai_client, audio_url: str, client: WebClient) -> str:
    """Transcribe an audio file using OpenAI's Whisper model."""
    try:
        # Download the file from Slack
        response = client.files_info(file=audio_url.split('-')[0])
        download_url = response["file"]["url_private_download"]
        
        headers = {"Authorization": f"Bearer {client.token}"}
        # Add timeout to prevent hanging
        file_response = requests.get(download_url, headers=headers, timeout=30)
        
        # Use tempfile for secure temp file creation
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file_path = temp_file.name
            temp_file.write(file_response.content)
        
        # Transcribe the audio
        with open(temp_file_path, "rb") as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1"
            )
        
        # Remove temporary file
        os.remove(temp_file_path)
        
        return transcription.text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return f"Audio transcription failed: {str(e)}"
