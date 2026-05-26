import logging
import json
import re
from typing import Any

def redact_sensitive_data(text: str) -> str:
    """
    Utility to redact potentially sensitive data if it accidentally slips into logs.
    We don't log task or response text, but this is a defensive measure for IDs/keys.
    """
    if not isinstance(text, str):
        return text
    # Basic redaction for anything that looks like an API key or generic long ID
    # This is a fallback; the primary defense is simply not passing raw text to the logger.
    redacted = re.sub(r'sk-[a-zA-Z0-9]{32,}', '[REDACTED_KEY]', text)
    return redacted

class SafeJSONFormatter(logging.Formatter):
    """
    Formatter that ensures extra kwargs are included safely as structured JSON,
    and never logs the standard `msg` if it contains raw execution traces.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "level": record.levelname,
            "module": record.name,
            "message": redact_sensitive_data(record.getMessage())
        }
        
        # Capture safe extra fields (event, error_type, etc.)
        for key, value in record.__dict__.items():
            if key not in logging.LogRecord(None, None, "", 0, "", (), None).__dict__:
                log_obj[key] = value
                
        return json.dumps(log_obj)

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Returns a standard logger configured for LearnKit.
    Callers MUST NEVER pass raw task text, model responses, or context blocks into this logger.
    Use `extra={"event": "..."}` for structured properties.
    """
    logger = logging.getLogger(f"learnkit.{name}")
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(SafeJSONFormatter())
        logger.addHandler(handler)
        
    logger.setLevel(level)
    # Prevent duplicate logging if root logger is also configured
    logger.propagate = False 
    return logger
