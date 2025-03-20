import logging
import re
import os
import time
from typing import Dict, Any, Optional
from threading import Lock

class RateLimiter:
    """Token bucket rate limiter for controlling log message frequency"""
    
    def __init__(self, tokens_per_second: float = 5.0, max_tokens: int = 100):
        """
        Initialize a token bucket rate limiter
        
        Args:
            tokens_per_second: Rate at which tokens are added to the bucket
            max_tokens: Maximum number of tokens the bucket can hold
        """
        self.tokens_per_second = tokens_per_second
        self.max_tokens = max_tokens
        self.tokens = max_tokens
        self.last_refill_time = time.time()
        self.lock = Lock()
        self.dropped_count = 0
    
    def _refill(self):
        """Refill tokens based on time elapsed since last refill"""
        now = time.time()
        elapsed = now - self.last_refill_time
        new_tokens = elapsed * self.tokens_per_second
        
        if new_tokens > 0:
            self.tokens = min(self.max_tokens, self.tokens + new_tokens)
            self.last_refill_time = now
    
    def allow_message(self) -> bool:
        """
        Check if a new message is allowed based on current token count
        
        Returns:
            True if the message is allowed, False otherwise
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            else:
                self.dropped_count += 1
                return False
    
    def get_dropped_count(self) -> int:
        """Get the count of messages dropped due to rate limiting"""
        with self.lock:
            return self.dropped_count
    
    def reset_dropped_count(self):
        """Reset the dropped message counter"""
        with self.lock:
            self.dropped_count = 0


class PIIRedactedLogger:
    def __init__(self, logger_name: str, log_level=logging.INFO, 
                 rate_limit_enabled: bool = True,
                 rate_limit_per_second: float = 5.0,
                 rate_limit_burst: int = 100):
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
        
        # Setup rate limiting
        self.rate_limit_enabled = rate_limit_enabled
        if rate_limit_enabled:
            self.rate_limiter = RateLimiter(
                tokens_per_second=rate_limit_per_second,
                max_tokens=rate_limit_burst
            )
            # Create a daily throttled log message counter
            self.last_throttle_report = time.time()
            self.throttle_report_interval = 3600  # Report dropped logs every hour
        
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
    
    def _check_rate_limit(self, level: int) -> bool:
        """
        Check if the message should be rate limited
        
        Args:
            level: The logging level of the message
            
        Returns:
            True if the message should be logged, False if it should be dropped
        """
        # If rate limiting is disabled or this is a high-level message, always allow
        if not self.rate_limit_enabled or level >= logging.ERROR:
            return True
            
        # For less critical messages, apply rate limiting
        allowed = self.rate_limiter.allow_message()
        
        # Periodically report on dropped messages
        now = time.time()
        if (now - self.last_throttle_report) > self.throttle_report_interval:
            dropped_count = self.rate_limiter.get_dropped_count()
            if dropped_count > 0:
                self.logger.warning(f"Rate limiting dropped {dropped_count} log messages in the last hour")
                self.rate_limiter.reset_dropped_count()
            self.last_throttle_report = now
            
        return allowed
    
    def log_event(self, level: int, message: str, metadata: Dict[str, Any] = None):
        # Check if this message should be rate limited
        if not self._check_rate_limit(level):
            return
            
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

# Create a singleton instance with configurable rate limits
def get_logger(name: str = "slackbot", log_level: int = logging.INFO,
               rate_limit_enabled: bool = True,
               rate_limit_per_second: float = 5.0,
               rate_limit_burst: int = 100) -> PIIRedactedLogger:
    """
    Get a PIIRedactedLogger instance with configurable rate limiting
    
    Args:
        name: Logger name
        log_level: Minimum logging level
        rate_limit_enabled: Whether to enable rate limiting
        rate_limit_per_second: Maximum logs per second (sustained rate)
        rate_limit_burst: Maximum burst of logs allowed
        
    Returns:
        A configured PIIRedactedLogger instance
    """
    return PIIRedactedLogger(
        name, 
        log_level,
        rate_limit_enabled,
        rate_limit_per_second,
        rate_limit_burst
    ) 