"""
Worker Module for Autonomous Development Team.

Workers execute tasks assigned by the project lead.
Different worker types have different capabilities and models.
"""

import asyncio
import traceback
from enum import Enum
from typing import List, Optional, Dict, Any
import aiohttp

from logging.json_logger import JSONLogger


class WorkerType(Enum):
    """Types of workers with different capabilities."""
    DEVELOPER = "developer"
    TESTER = "tester"
    DEVOPS = "devops"
    ARCHITECT = "architect"


class WorkerCapabilities:
    """Define capabilities for each worker type."""

    PROFILES = {
        WorkerType.DEVELOPER: {
            "capabilities": ["python", "javascript", "fastapi", "postgresql", "docker", "api_development"],
            "max_concurrent_tasks": 2,
            "model": "claude-3-5-sonnet-20241022",
            "timeout_seconds": 3600
        },
        WorkerType.TESTER: {
            "capabilities": ["pytest", "unittest", "integration_testing", "selenium", "test_design"],
            "max_concurrent_tasks": 3,
            "model": "claude-3-5-haiku-20241022",
            "timeout_seconds": 1800
        },
        WorkerType.DEVOPS: {
            "capabilities": ["docker", "kubernetes", "github_actions", "terraform", "aws", "deployment"],
            "max_concurrent_tasks": 2,
            "model": "claude-3-5-haiku-20241022",
            "timeout_seconds": 2400
        },
        WorkerType.ARCHITECT: {
            "capabilities": ["system_design", "code_review", "integration", "architecture"],
            "max_concurrent_tasks": 1,
            "model": "claude-3-5-opus-20241022",
            "timeout_seconds": 3600
        }
    }


class MCPClient:
    """Simple MCP client for communicating with MCP server."""

    def __init__(self, mcp_host: str = "localhost", mcp_port: int = 8080):
        """
        Initialize MCP client.

        Args:
            mcp_host: MCP server host
            mcp_port: MCP server port
        """
        self.base_url = f"http://{mcp_host}:{mcp_port}/v1/mcp"
        self.session = None

    async def __aenter__(self):
        """Create session on context enter."""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close session on context exit."""
        if self.session:
            await self.session.close()

    async def call_tool(self, tool_name: str, params: dict) -> dict:
        """
        Call an MCP tool.

        Args:
            tool_name: Name of the tool
            params: Tool parameters

        Returns:
            Tool result

        Raises:
            Exception: If tool call fails
        """
        if not self.session:
            self.session = aiohttp.ClientSession()

        url = f"{self.base_url}/tools/{tool_name}"

        try:
            async with self.session.post(url, json={"params": params}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"MCP tool call failed: {error_text}")
        except aiohttp.ClientError as e:
            raise Exception(f"Network error calling MCP tool: {str(e)}")


class Worker:
    """
    Worker that executes tasks from the project queue.

    Workers:
    - Fetch available tasks based on their capabilities
    - Execute tasks with progress reporting
    - Handle errors and escalate to project lead
    - Log all activity
    """

    def __init__(
        self,
        worker_id: str,
        worker_type: WorkerType,
        mcp_host: str = "localhost",
        mcp_port: int = 8080,
        log_file: str = "logs/project_activity.log"
    ):
        """
        Initialize worker.

        Args:
            worker_id: Unique worker identifier
            worker_type: Type of worker (determines capabilities)
            mcp_host: MCP server host
            mcp_port: MCP server port
            log_file: Path to log file
        """
        self.worker_id = worker_id
        self.worker_type = worker_type

        # Get capabilities from profile
        profile = WorkerCapabilities.PROFILES[worker_type]
        self.capabilities = profile["capabilities"]
        self.max_concurrent_tasks = profile["max_concurrent_tasks"]
        self.model = profile["model"]
        self.timeout_seconds = profile["timeout_seconds"]

        # Initialize MCP client
        self.mcp_client = MCPClient(mcp_host, mcp_port)

        # Initialize logger
        self.logger = JSONLogger("worker", worker_id, log_file)

        # Worker state
        self.current_task = None
        self.is_active = True
        self.tasks_completed = 0
        self.tasks_failed = 0

    async def start(self):
        """Start the worker."""
        await self.logger.log(
            "worker_started",
            {
                "worker_type": self.worker_type.value,
                "capabilities": self.capabilities,
                "model": self.model
            }
        )

        # Register with MCP server
        await self.mcp_client.call_tool(
            "log_event",
            {
                "event_type": "worker_registered",
                "data": {
                    "worker_id": self.worker_id,
                    "worker_type": self.worker_type.value,
                    "capabilities": self.capabilities
                }
            }
        )

    async def work_loop(self):
        """
        Continuous task execution loop.

        Worker continuously:
        1. Fetches next available task
        2. Executes task with progress updates
        3. Reports completion or failure
        4. Repeats until stopped
        """
        async with self.mcp_client:
            await self.start()

            while self.is_active:
                try:
                    # Fetch next available task
                    task = await self.fetch_eligible_task()

                    if not task:
                        # No tasks available, wait before checking again
                        await asyncio.sleep(2)
                        continue

                    # Execute task
                    await self.execute_task_with_logging(task)

                except Exception as e:
                    await self.logger.log(
                        "system_error",
                        {
                            "error": str(e),
                            "stack_trace": traceback.format_exc()
                        },
                        level="ERROR"
                    )
                    await asyncio.sleep(5)  # Wait before retrying

    async def fetch_eligible_task(self) -> Optional[dict]:
        """
        Fetch next task eligible for this worker.

        Returns:
            Task dictionary or None if no tasks available
        """
        try:
            result = await self.mcp_client.call_tool(
                "fetch_task",
                {
                    "worker_id": self.worker_id,
                    "capabilities": self.capabilities
                }
            )

            task = result.get("task")

            if task:
                await self.logger.log(
                    "task_assigned",
                    {
                        "task_id": task["id"],
                        "description": task.get("description", ""),
                        "estimated_hours": task.get("estimated_hours", 0)
                    }
                )

            return task

        except Exception as e:
            await self.logger.log(
                "system_error",
                {
                    "action": "fetch_task",
                    "error": str(e)
                },
                level="ERROR"
            )
            return None

    async def execute_task_with_logging(self, task: dict):
        """
        Execute task with comprehensive logging.

        Args:
            task: Task dictionary
        """
        task_id = task["id"]
        self.current_task = task

        await self.logger.log(
            "task_started",
            {
                "task_id": task_id,
                "description": task.get("description", "")
            }
        )

        try:
            # Update task status to in_progress
            await self.mcp_client.call_tool(
                "update_task_status",
                {
                    "task_id": task_id,
                    "status": "in_progress",
                    "progress": 0
                }
            )

            # Execute task iteratively with progress updates
            result = await self.execute_task_iterative(task)

            # Mark task as completed
            await self.mcp_client.call_tool(
                "complete_task",
                {
                    "task_id": task_id,
                    "result": result
                }
            )

            self.tasks_completed += 1

            await self.logger.log(
                "task_completed",
                {
                    "task_id": task_id,
                    "result_summary": self.summarize_result(result)
                }
            )

        except Exception as e:
            # Mark task as failed
            await self.mcp_client.call_tool(
                "fail_task",
                {
                    "task_id": task_id,
                    "error": str(e)
                }
            )

            self.tasks_failed += 1

            await self.logger.log(
                "task_failed",
                {
                    "task_id": task_id,
                    "error": str(e),
                    "stack_trace": traceback.format_exc()
                },
                level="ERROR"
            )

        finally:
            self.current_task = None

    async def execute_task_iterative(self, task: dict) -> dict:
        """
        Execute task with iterative progress updates.

        This is a simplified implementation. In production, this would:
        1. Use AI model to understand task
        2. Break down into steps
        3. Execute steps with code generation
        4. Report progress
        5. Handle errors and retries

        Args:
            task: Task dictionary

        Returns:
            Result dictionary
        """
        task_id = task["id"]
        description = task.get("description", "")

        # Simulate task execution with progress updates
        steps = 5
        for step in range(1, steps + 1):
            progress = int((step / steps) * 100)

            await self.logger.log(
                "task_progress",
                {
                    "task_id": task_id,
                    "progress": progress,
                    "step": step,
                    "total_steps": steps
                }
            )

            await self.mcp_client.call_tool(
                "update_task_status",
                {
                    "task_id": task_id,
                    "status": "in_progress",
                    "progress": progress
                }
            )

            # Simulate work
            await asyncio.sleep(2)

        # Return result
        return {
            "status": "completed",
            "description": description,
            "steps_executed": steps,
            "artifacts": [],
            "notes": "Task executed successfully (simulated)"
        }

    def summarize_result(self, result: dict) -> str:
        """
        Create a brief summary of task result.

        Args:
            result: Result dictionary

        Returns:
            Summary string
        """
        return result.get("notes", "Task completed")

    async def stop(self):
        """Stop the worker."""
        self.is_active = False

        await self.logger.log(
            "worker_stopped",
            {
                "tasks_completed": self.tasks_completed,
                "tasks_failed": self.tasks_failed
            }
        )

    def progress_bar(self) -> str:
        """
        Generate progress bar for current task.

        Returns:
            Progress bar string
        """
        if not self.current_task:
            return "[░░░░░] 0%"

        progress = self.current_task.get("progress", 0)
        filled = int(progress / 20)  # 5 segments for 100%
        bar = "▓" * filled + "░" * (5 - filled)

        return f"[{bar}] {progress}%"

    @property
    def status(self) -> str:
        """Get worker status string."""
        if not self.is_active:
            return "STOPPED"
        elif self.current_task:
            return "BUSY"
        else:
            return "IDLE"
