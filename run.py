#!/usr/bin/env python3
"""
Simple script to run the application locally for development.
This will load environment variables from .env file and start the server.
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the project root to the path to allow importing the app
sys.path.insert(0, str(Path(__file__).resolve().parent))


def main():
    # Try to load environment variables from .env file
    try:
        from app.utils.env_loader import load_env_file

        load_env_file()
    except ImportError:
        print(
            "Warning: Could not import env_loader. Make sure the application is properly installed."
        )

    # Start the server
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting server on http://localhost:{port}")
    print("Press Ctrl+C to stop the server")

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Enable auto-reload for development
        log_level="info",
    )


if __name__ == "__main__":
    main()
