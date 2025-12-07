"""
MCP Server Implementation.

Provides a simple HTTP-based server for handling MCP tool calls.
In production, this would use the official MCP SDK with proper protocol support.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from aiohttp import web
import argparse
from pathlib import Path

from .context_store import ContextStore
from .tools import register_tools
from logging.json_logger import JSONLogger


class MCPServer:
    """
    MCP Server for autonomous development team.

    Handles:
    - Tool registration and execution
    - Context management
    - Request/response logging
    - CORS support (optional)
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        context_store_path: str = "context/project_store.json",
        log_file: str = "logs/project_activity.log",
        enable_cors: bool = False
    ):
        """
        Initialize MCP server.

        Args:
            host: Server host
            port: Server port
            context_store_path: Path to context storage
            log_file: Path to log file
            enable_cors: Enable CORS support
        """
        self.host = host
        self.port = port
        self.enable_cors = enable_cors

        # Initialize context store
        self.context_store = ContextStore(context_store_path)

        # Register tools
        self.tools = register_tools(self.context_store)

        # Initialize logger
        self.logger = JSONLogger("mcp_server", "server-001", log_file)

        # Create web application
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_post("/v1/mcp/tools/{tool_name}", self.handle_tool_call)
        self.app.router.add_get("/v1/mcp/status", self.handle_status)
        self.app.router.add_get("/v1/mcp/tools", self.handle_list_tools)
        self.app.router.add_get("/health", self.handle_health)

    async def handle_tool_call(self, request: web.Request) -> web.Response:
        """
        Handle MCP tool call.

        POST /v1/mcp/tools/{tool_name}
        Body: {"params": {...}}
        """
        tool_name = request.match_info["tool_name"]
        start_time = asyncio.get_event_loop().time()

        try:
            # Parse request body
            body = await request.json()
            params = body.get("params", {})

            # Log incoming request
            await self.logger.log_network_io(
                direction="request",
                protocol="http",
                endpoint=f"/v1/mcp/tools/{tool_name}",
                body={"params": params},
                headers=dict(request.headers)
            )

            # Check if tool exists
            if tool_name not in self.tools:
                return web.json_response(
                    {"error": f"Tool '{tool_name}' not found"},
                    status=404
                )

            # Execute tool
            tool = self.tools[tool_name]
            result = await tool["handler"](params)

            # Calculate latency
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000

            # Log response
            await self.logger.log_network_io(
                direction="response",
                protocol="http",
                endpoint=f"/v1/mcp/tools/{tool_name}",
                body=result,
                status_code=200,
                latency_ms=latency_ms
            )

            return web.json_response(result, status=200)

        except json.JSONDecodeError:
            return web.json_response(
                {"error": "Invalid JSON in request body"},
                status=400
            )
        except Exception as e:
            # Log error
            await self.logger.log(
                "system_error",
                {
                    "tool": tool_name,
                    "error": str(e),
                    "type": type(e).__name__
                },
                level="ERROR"
            )

            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def handle_status(self, request: web.Request) -> web.Response:
        """
        Get project status.

        GET /v1/mcp/status
        """
        try:
            status = await self.context_store.get_project_status()
            return web.json_response(status)
        except Exception as e:
            return web.json_response(
                {"error": str(e)},
                status=500
            )

    async def handle_list_tools(self, request: web.Request) -> web.Response:
        """
        List available tools.

        GET /v1/mcp/tools
        """
        tools_list = {
            name: {
                "name": tool["name"],
                "description": tool["description"]
            }
            for name, tool in self.tools.items()
        }

        return web.json_response({
            "tools": tools_list,
            "count": len(tools_list)
        })

    async def handle_health(self, request: web.Request) -> web.Response:
        """
        Health check endpoint.

        GET /health
        """
        return web.json_response({
            "status": "healthy",
            "server": "mcp-autonomous-dev-team",
            "version": "1.0.0"
        })

    async def start(self):
        """Start the MCP server."""
        await self.logger.log(
            "server_started",
            {
                "host": self.host,
                "port": self.port,
                "tools_count": len(self.tools)
            }
        )

        runner = web.AppRunner(self.app)
        await runner.setup()

        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        print(f"MCP Server running on http://{self.host}:{self.port}")
        print(f"Available tools: {len(self.tools)}")
        print(f"Health check: http://{self.host}:{self.port}/health")

    async def stop(self):
        """Stop the MCP server."""
        await self.logger.log(
            "server_stopped",
            {"message": "Server shutting down"}
        )


async def main():
    """Main entry point for MCP server."""
    parser = argparse.ArgumentParser(description="MCP Server for Autonomous Dev Team")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--context-store", default="context/project_store.json",
                       help="Path to context store")
    parser.add_argument("--log-file", default="logs/project_activity.log",
                       help="Path to log file")
    parser.add_argument("--log-level", default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    parser.add_argument("--enable-cors", action="store_true",
                       help="Enable CORS support")

    args = parser.parse_args()

    # Create server
    server = MCPServer(
        host=args.host,
        port=args.port,
        context_store_path=args.context_store,
        log_file=args.log_file,
        enable_cors=args.enable_cors
    )

    # Start server
    await server.start()

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        await server.stop()


if __name__ == "__main__":
    asyncio.run(main())
