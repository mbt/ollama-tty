"""
Configuration System for Autonomous Development Team.

Loads and manages project configuration from JSON files.
"""

import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path


class ProjectConfig:
    """
    Project configuration manager.

    Loads configuration from JSON file and provides
    convenient property access to settings.
    """

    def __init__(self, config_path: str = "config/project_config.json"):
        """
        Initialize project configuration.

        Args:
            config_path: Path to configuration JSON file

        Raises:
            FileNotFoundError: If config file doesn't exist
            json.JSONDecodeError: If config file is invalid JSON
        """
        self.config_path = config_path

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r') as f:
            self.config = json.load(f)

    @property
    def project_name(self) -> str:
        """Get project name."""
        return self.config.get("project", {}).get("name", "Unnamed Project")

    @property
    def project_id(self) -> Optional[str]:
        """Get project ID."""
        return self.config.get("project", {}).get("id")

    @property
    def max_workers(self) -> int:
        """Get maximum number of workers."""
        return self.config.get("project", {}).get("max_workers", 8)

    @property
    def min_workers(self) -> int:
        """Get minimum number of workers."""
        return self.config.get("project", {}).get("min_workers", 2)

    @property
    def auto_scale(self) -> bool:
        """Check if auto-scaling is enabled."""
        return self.config.get("project", {}).get("auto_scale", False)

    @property
    def worker_profiles(self) -> List[Dict[str, Any]]:
        """Get worker profiles configuration."""
        return self.config.get("workers", {}).get("profiles", [])

    @property
    def mcp_server_host(self) -> str:
        """Get MCP server host."""
        return self.config.get("mcp_server", {}).get("host", "localhost")

    @property
    def mcp_server_port(self) -> int:
        """Get MCP server port."""
        return self.config.get("mcp_server", {}).get("port", 8080)

    @property
    def mcp_enable_cors(self) -> bool:
        """Check if CORS is enabled for MCP server."""
        return self.config.get("mcp_server", {}).get("enable_cors", False)

    @property
    def mcp_max_connections(self) -> int:
        """Get maximum MCP connections."""
        return self.config.get("mcp_server", {}).get("max_connections", 100)

    @property
    def mcp_request_timeout(self) -> float:
        """Get MCP request timeout in seconds."""
        return self.config.get("mcp_server", {}).get("request_timeout", 30.0)

    @property
    def log_level(self) -> str:
        """Get logging level."""
        return self.config.get("logging", {}).get("level", "INFO")

    @property
    def enable_network_logging(self) -> bool:
        """Check if network I/O logging is enabled."""
        return self.config.get("logging", {}).get("include_network_io", True)

    @property
    def log_file(self) -> str:
        """Get log file path."""
        return self.config.get("logging", {}).get("log_file", "logs/project_activity.log")

    @property
    def log_rotation(self) -> str:
        """Get log rotation strategy."""
        return self.config.get("logging", {}).get("rotation", "daily")

    @property
    def log_max_file_size_mb(self) -> int:
        """Get maximum log file size in MB."""
        return self.config.get("logging", {}).get("max_file_size_mb", 100)

    @property
    def log_retention_days(self) -> int:
        """Get log retention period in days."""
        return self.config.get("logging", {}).get("retention_days", 30)

    @property
    def display_refresh_rate_hz(self) -> float:
        """Get display refresh rate in Hz."""
        return self.config.get("display", {}).get("refresh_rate_hz", 1.0)

    @property
    def display_show_network_io_realtime(self) -> bool:
        """Check if real-time network I/O should be displayed."""
        return self.config.get("display", {}).get("show_network_io_realtime", False)

    @property
    def display_color_scheme(self) -> str:
        """Get display color scheme."""
        return self.config.get("display", {}).get("color_scheme", "dark")

    @property
    def display_worker_panel_height(self) -> int:
        """Get worker panel height."""
        return self.config.get("display", {}).get("worker_panel_height", 5)

    def get_worker_profile_by_type(self, worker_type: str) -> Optional[Dict[str, Any]]:
        """
        Get worker profile by type.

        Args:
            worker_type: Worker type (developer, tester, devops, architect)

        Returns:
            Worker profile dictionary or None if not found
        """
        for profile in self.worker_profiles:
            if profile.get("type") == worker_type:
                return profile
        return None

    def to_dict(self) -> dict:
        """
        Convert configuration to dictionary.

        Returns:
            Configuration dictionary
        """
        return self.config

    def __repr__(self) -> str:
        """String representation of configuration."""
        return f"ProjectConfig(project='{self.project_name}', workers={self.min_workers}-{self.max_workers})"
