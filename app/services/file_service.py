import base64
import csv
import io
import requests
from typing import Dict, Any, Optional

from app.config import logger, SLACK_BOT_TOKEN


def get_file_info(slack_client, file_id: str) -> Optional[Dict[str, Any]]:
    """Get information about a file from Slack."""
    try:
        response = slack_client.files_info(file=file_id)
        return response["file"]
    except Exception as e:
        logger.error(f"Error getting file info: {e}")
        return None


def download_file(file_url: str) -> Optional[bytes]:
    """Download a file from Slack."""
    try:
        response = requests.get(
            file_url,
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            timeout=30,  # Add timeout to prevent hanging
        )
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Error downloading file: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return None


def extract_text_from_pdf(openai_client, pdf_data: bytes) -> str:
    """Extract text from a PDF file using OpenAI's vision capabilities."""
    try:
        # Convert PDF to base64
        base64_pdf = base64.b64encode(pdf_data).decode("utf-8")

        # Use OpenAI to extract text
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Extract and summarize the text content from this PDF document.",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:application/pdf;base64,{base64_pdf}"
                        },
                    },
                ],
            }
        ]

        # Call OpenAI with the PDF
        response = openai_client.chat.completions.create(
            model="gpt-4o", messages=messages
        )

        # Return the extracted text
        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {e}")
        return f"This appears to be a PDF document, but I couldn't extract its contents: {str(e)}"


def parse_csv_content(file_data: bytes) -> str:
    """Parse CSV data and return it as a string table."""
    try:
        content = file_data.decode("utf-8")
        # Parse CSV into a readable format
        csv_reader = csv.reader(io.StringIO(content))
        rows = list(csv_reader)

        if not rows:
            return "CSV file appears to be empty."

        # Format as a simple table for text
        table_text = "Here's the CSV data:\n\n"
        for row in rows:
            table_text += " | ".join(row) + "\n"

        return table_text
    except Exception as e:
        logger.error(f"Error parsing CSV: {e}")
        return f"Could not parse CSV file: {str(e)}"


def process_file_attachment(
    slack_client, openai_client, file: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Process a file attachment based on its type."""
    file_info = get_file_info(slack_client, file["id"])

    if not file_info or "url_private" not in file_info:
        return None

    file_data = download_file(file_info["url_private"])
    if not file_data:
        return None

    mimetype = file_info.get("mimetype", "")
    filename = file_info.get("name", "").lower()

    # Handle different file types
    if mimetype.startswith("image/"):
        # Process image file
        base64_image = base64.b64encode(file_data).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:{mimetype};base64,{base64_image}"},
        }
    elif mimetype == "application/pdf" or filename.endswith(".pdf"):
        # Process PDF file
        pdf_text = extract_text_from_pdf(openai_client, file_data)
        return {"type": "text", "text": pdf_text}
    elif mimetype in ["text/csv", "application/csv"] or filename.endswith(".csv"):
        # Process CSV file
        csv_text = parse_csv_content(file_data)
        return {"type": "text", "text": csv_text}
    elif mimetype.startswith("text/"):
        # Process other text files
        try:
            text_content = file_data.decode("utf-8")
            return {"type": "text", "text": f"File content:\n\n{text_content}"}
        except UnicodeDecodeError:
            return {
                "type": "text",
                "text": f"Attached a {mimetype} file but couldn't extract text content.",
            }
    else:
        # Other file types - just acknowledge
        return {
            "type": "text",
            "text": f"Attached a {mimetype} file named '{file_info.get('name', 'unknown')}'.",
        }


def download_image(url: str) -> Optional[bytes]:
    """Download image from URL."""
    try:
        logger.info(f"Downloading image from URL: {url[:50]}...")
        response = requests.get(url, timeout=30)  # Add timeout to prevent hanging
        if response.status_code == 200:
            logger.info(
                f"Image downloaded successfully, size: {len(response.content)} bytes"
            )
            return response.content
        else:
            logger.error(f"Error downloading image: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None
