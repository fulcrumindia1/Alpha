"""
services/logger.py — Structured Observability & Security-Safe Logging for FULCRUM-INDIA
======================================================================================
Provides structured JSON logging for Cluster A operations:
- Automatic redaction of sensitive credentials (passwords, API keys, JWT tokens)
- Standard fields: timestamp, module, operation, actor_id, actor_role, status, message, error_class
- Safe for production multi-tenant environments
"""

import json
import logging
import re
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any

# Regex patterns for sensitive data redaction
_REDACT_PATTERNS = [
    (re.compile(r'("(?:password|new_password|temp_password|confirm_password)":\s*")[^"]+(")', re.IGNORECASE), r'\1***REDACTED***\2'),
    (re.compile(r'(password[=:]\s*)[^\s&,;]+', re.IGNORECASE), r'\1***REDACTED***'),
    (re.compile(r'(Bearer\s+)[A-Za-z0-9\-._~+/]+=*', re.IGNORECASE), r'\1***REDACTED_TOKEN***'),
    (re.compile(r'(eyJ[A-Za-z0-9-_=]+\.eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_.+/=]*)', re.IGNORECASE), r'***REDACTED_JWT***'),
    (re.compile(r'(SUPABASE_SECRET_KEY|SUPABASE_SERVICE_ROLE_KEY)[=:]\s*[^\s,;]+', re.IGNORECASE), r'\1=***REDACTED_KEY***'),
]

def sanitize_message(msg: str) -> str:
    """Removes passwords, secret keys, and JWT tokens from log strings."""
    if not msg:
        return ""
    sanitized = str(msg)
    for pattern, replacement in _REDACT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    return sanitized

class StructuredLogger:
    def __init__(self, name: str = "fulcrum"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(logging.Formatter('%(message)s'))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log(
        self,
        level: str,
        module: str,
        operation: str,
        message: str,
        actor_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        status: str = "OK",
        error: Optional[Exception] = None,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Emits a structured JSON log entry to stdout."""
        clean_msg = sanitize_message(message)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.upper(),
            "module": module,
            "operation": operation,
            "status": status,
            "actor_id": actor_id or "anonymous",
            "actor_role": actor_role or "system",
            "message": clean_msg
        }

        if error:
            entry["error_class"] = error.__class__.__name__
            entry["error_detail"] = sanitize_message(str(error))

        if extra:
            sanitized_extra = {}
            for k, v in extra.items():
                if any(sec in k.lower() for sec in ["pass", "token", "secret", "key"]):
                    sanitized_extra[k] = "***REDACTED***"
                else:
                    sanitized_extra[k] = sanitize_message(str(v)) if isinstance(v, str) else v
            entry["extra"] = sanitized_extra

        log_json = json.dumps(entry)
        if level.upper() in ("ERROR", "CRITICAL"):
            self.logger.error(log_json)
        elif level.upper() == "WARN" or level.upper() == "WARNING":
            self.logger.warning(log_json)
        else:
            self.logger.info(log_json)

    def info(self, module: str, operation: str, message: str, **kwargs):
        self.log("INFO", module, operation, message, **kwargs)

    def warning(self, module: str, operation: str, message: str, **kwargs):
        self.log("WARN", module, operation, message, status="WARNING", **kwargs)

    def error(self, module: str, operation: str, message: str, error: Optional[Exception] = None, **kwargs):
        self.log("ERROR", module, operation, message, status="ERROR", error=error, **kwargs)

# Global logger instance
app_logger = StructuredLogger()
