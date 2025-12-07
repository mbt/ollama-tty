"""
JSON Logger for MCP-enabled autonomous development team.

Provides structured logging with NDJSON format for all node types:
- Project Lead
- Workers
- MCP Server
- Display

Includes network I/O logging and sensitive data sanitization.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional, Dict
from pathlib import Path


class JSONLogger:
    """
    Structured logger that writes NDJSON (Newline Delimited JSON) format.

    Each log entry contains:
    - timestamp: ISO8601 with microseconds
    - node_type: project_lead, worker, mcp_server, or display
    - node_id: Unique identifier for the node
    - event_type: Type of event being logged
    - level: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - correlation_id: UUID for tracking request flow
    - data: Event-specific payload
    - network_io: Optional network I/O details
    """

    VALID_NODE_TYPES = {"project_lead", "worker", "mcp_server", "display"}
    VALID_EVENT_TYPES = {
        "project_started",
        "task_created",
        "task_assigned",
        "task_started",
        "task_progress",
        "task_completed",
        "task_failed",
        "network_io",
        "clarification_request",
        "escalation",
        "system_error",
        "worker_started",
        "worker_stopped",
        "server_started",
        "server_stopped"
    }
    VALID_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    def __init__(self, node_type: str, node_id: str, log_file: str = "logs/project_activity.log"):
        """
        Initialize the JSON logger.

        Args:
            node_type: Type of node (project_lead, worker, mcp_server, display)
            node_id: Unique identifier for this node instance
            log_file: Path to the log file (default: logs/project_activity.log)

        Raises:
            ValueError: If node_type is invalid
        """
        if node_type not in self.VALID_NODE_TYPES:
            raise ValueError(f"Invalid node_type: {node_type}. Must be one of {self.VALID_NODE_TYPES}")

        self.node_type = node_type
        self.node_id = node_id
        self.log_file = log_file

        # Ensure log directory exists
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)

    def _create_log_entry(
        self,
        event_type: str,
        data: dict,
        network_io: Optional[dict] = None,
        level: str = "INFO",
        correlation_id: Optional[str] = None
    ) -> dict:
        """
        Create a structured log entry.

        Args:
            event_type: Type of event
            data: Event-specific data
            network_io: Optional network I/O details
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            correlation_id: Optional correlation ID for tracking requests

        Returns:
            Dictionary representing the log entry
        """
        if level not in self.VALID_LEVELS:
            level = "INFO"

        if correlation_id is None:
            correlation_id = str(uuid.uuid4())

        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "node_type": self.node_type,
            "node_id": self.node_id,
            "event_type": event_type,
            "level": level,
            "correlation_id": correlation_id,
            "data": self._sanitize_data(data)
        }

        if network_io:
            entry["network_io"] = network_io

        return entry

    async def log(
        self,
        event_type: str,
        data: dict,
        network_io: Optional[dict] = None,
        level: str = "INFO",
        correlation_id: Optional[str] = None
    ):
        """
        Log an event asynchronously.

        Args:
            event_type: Type of event
            data: Event-specific data
            network_io: Optional network I/O details
            level: Log level
            correlation_id: Optional correlation ID
        """
        entry = self._create_log_entry(event_type, data, network_io, level, correlation_id)

        # Write as NDJSON (newline-delimited JSON)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry, separators=(',', ':')) + "\n")
            f.flush()  # Ensure immediate write

    def log_sync(
        self,
        event_type: str,
        data: dict,
        network_io: Optional[dict] = None,
        level: str = "INFO",
        correlation_id: Optional[str] = None
    ):
        """
        Log an event synchronously (for non-async contexts).

        Args:
            event_type: Type of event
            data: Event-specific data
            network_io: Optional network I/O details
            level: Log level
            correlation_id: Optional correlation ID
        """
        entry = self._create_log_entry(event_type, data, network_io, level, correlation_id)

        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry, separators=(',', ':')) + "\n")
            f.flush()

    async def log_network_io(
        self,
        direction: str,
        protocol: str,
        endpoint: str,
        body: Any,
        status_code: Optional[int] = None,
        latency_ms: Optional[float] = None,
        headers: Optional[dict] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Log network I/O activity.

        Args:
            direction: "request" or "response"
            protocol: Protocol used (e.g., "mcp", "http", "postgresql")
            endpoint: Endpoint or URL
            body: Request/response body
            status_code: HTTP status code or equivalent
            latency_ms: Latency in milliseconds
            headers: Optional headers
            correlation_id: Optional correlation ID
        """
        network_io = {
            "direction": direction,
            "protocol": protocol,
            "endpoint": endpoint,
            "body": self._sanitize_data(body) if isinstance(body, dict) else body,
            "status_code": status_code,
            "latency_ms": latency_ms
        }

        if headers:
            network_io["headers"] = self._sanitize_data(headers)

        await self.log(
            "network_io",
            {},
            network_io=network_io,
            level="DEBUG",
            correlation_id=correlation_id
        )

    def _sanitize_data(self, data: Any) -> Any:
        """
        Sanitize sensitive data before logging.

        Redacts fields like passwords, API keys, tokens, etc.

        Args:
            data: Data to sanitize

        Returns:
            Sanitized data
        """
        sensitive_keys = {
            "password",
            "api_key",
            "secret",
            "token",
            "authorization",
            "auth",
            "credential",
            "access_token",
            "refresh_token",
            "private_key",
            "jwt"
        }

        def _sanitize(obj):
            if isinstance(obj, dict):
                return {
                    k: "***REDACTED***" if any(sens in k.lower() for sens in sensitive_keys)
                    else _sanitize(v)
                    for k, v in obj.items()
                }
            elif isinstance(obj, list):
                return [_sanitize(item) for item in obj]
            return obj

        return _sanitize(data)


def sanitize_log_data(data: dict) -> dict:
    """
    Standalone function to sanitize sensitive data.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data
    """
    logger = JSONLogger("system", "sanitizer")
    return logger._sanitize_data(data)
