import logging
import re
import os
from typing import Dict, Any

class PIIRedactedLogger:
    def __init__(self, logger_name: str, log_level=logging.INFO):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        
        # Clear existing handlers if any
        if self.logger.handlers:
            self.logger.handlers.clear()
        
        # Add handlers (file and console)
        log_dir = os.environ.get("LOG_DIR", "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(f"{log_dir}/bot_activity.log")
        console_handler = logging.StreamHandler()
        
        # Create formatter with timestamps
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Patterns to redact
        self.pii_patterns = {
            'email': r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+',
            'ip': r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b',
            'phone': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
            'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
            'credit_card': r'\b(?:\d{4}[-\s]?){3}\d{4}\b',
            'api_key': r'\b(?:sk|pk)[-_][a-zA-Z0-9]{20,}\b',  # Common API key patterns
            'slack_token': r'\bxox[a-zA-Z]-[a-zA-Z0-9-]+\b',  # Slack token pattern
        }
    
    def _redact_pii(self, message: str) -> str:
        if not isinstance(message, str):
            return str(message)
        
        redacted = message
        for pii_type, pattern in self.pii_patterns.items():
            redacted = re.sub(pattern, f"[REDACTED-{pii_type.upper()}]", redacted)
        return redacted
    
    def _redact_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact PII from dictionary values recursively"""
        redacted = {}
        for key, value in data.items():
            if isinstance(value, str):
                redacted[key] = self._redact_pii(value)
            elif isinstance(value, dict):
                redacted[key] = self._redact_dict(value)
            elif isinstance(value, list):
                redacted[key] = [
                    self._redact_dict(item) if isinstance(item, dict) 
                    else self._redact_pii(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                redacted[key] = value
        return redacted
    
    def log_event(self, level: int, message: str, metadata: Dict[str, Any] = None):
        redacted_message = self._redact_pii(message)
        
        if metadata:
            # Redact PII from metadata values
            redacted_metadata = self._redact_dict(metadata)
            self.logger.log(level, f"{redacted_message} - {redacted_metadata}")
        else:
            self.logger.log(level, redacted_message)
    
    def info(self, message: str, metadata: Dict[str, Any] = None):
        self.log_event(logging.INFO, message, metadata)
    
    def warning(self, message: str, metadata: Dict[str, Any] = None):
        self.log_event(logging.WARNING, message, metadata)
    
    def error(self, message: str, metadata: Dict[str, Any] = None):
        self.log_event(logging.ERROR, message, metadata)
    
    def critical(self, message: str, metadata: Dict[str, Any] = None):
        self.log_event(logging.CRITICAL, message, metadata)
    
    def debug(self, message: str, metadata: Dict[str, Any] = None):
        self.log_event(logging.DEBUG, message, metadata)

# Create a singleton instance
def get_logger(name: str = "slackbot", log_level: int = logging.INFO) -> PIIRedactedLogger:
    return PIIRedactedLogger(name, log_level) 