"""
Project Lead Module for Autonomous Development Team.

The Project Lead is responsible for:
- Analyzing requirements
- Creating project plans
- Decomposing work into tasks
- Managing worker assignments
- Monitoring progress
- Handling escalations
"""

import asyncio
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

from workers.worker import MCPClient
from json_logging.json_logger import JSONLogger


class ProjectLead:
    """
    Project Lead orchestrates the entire autonomous development team.

    Responsibilities:
    - Requirement analysis and planning
    - Task decomposition and assignment
    - Worker pool management
    - Progress monitoring
    - Escalation handling
    - Project completion
    """

    def __init__(
        self,
        project_name: str,
        requirements: str,
        mcp_host: str = "localhost",
        mcp_port: int = 8080,
        log_file: str = "logs/project_activity.log"
    ):
        """
        Initialize Project Lead.

        Args:
            project_name: Name of the project
            requirements: Natural language requirements
            mcp_host: MCP server host
            mcp_port: MCP server port
            log_file: Path to log file
        """
        self.project_name = project_name
        self.requirements = requirements
        self.project_id = f"proj-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8]}"

        # Initialize MCP client
        self.mcp_client = MCPClient(mcp_host, mcp_port)

        # Initialize logger
        self.logger = JSONLogger("project_lead", "lead-001", log_file)

        # Project state
        self.plan = None
        self.workers = []
        self.is_running = False
        self.tasks_created = []

    async def initialize_project(self):
        """
        Phase 1: Project Initialization and Planning.

        Steps:
        1. Log project start
        2. Analyze requirements using MCP
        3. Create project plan
        4. Decompose into tasks
        5. Determine worker count
        """
        await self.logger.log(
            "project_started",
            {
                "project_id": self.project_id,
                "project_name": self.project_name,
                "raw_requirements": self.requirements
            }
        )

        # Analyze requirements using MCP tool
        await self.logger.log(
            "task_started",
            {
                "task": "analyze_requirements",
                "status": "in_progress"
            }
        )

        try:
            result = await self.mcp_client.call_tool(
                "analyze_requirements",
                {"text": self.requirements}
            )

            self.plan = result.get("plan", {})

            await self.logger.log(
                "task_completed",
                {
                    "task": "analyze_requirements",
                    "plan_phases": len(self.plan.get("phases", [])),
                    "plan": self.plan
                }
            )

        except Exception as e:
            await self.logger.log(
                "system_error",
                {
                    "task": "analyze_requirements",
                    "error": str(e)
                },
                level="ERROR"
            )
            raise

        # Create tasks from plan
        tasks = await self.create_tasks_from_plan()

        await self.logger.log(
            "initialization_complete",
            {
                "total_tasks": len(tasks),
                "project_id": self.project_id
            }
        )

        return tasks

    async def create_tasks_from_plan(self) -> List[dict]:
        """
        Decompose project plan into atomic tasks.

        This is a simplified implementation. In production, this would use
        an AI model to intelligently break down the plan.

        Returns:
            List of created tasks
        """
        tasks = []

        # Example task decomposition based on plan
        example_tasks = [
            {
                "description": "Set up project structure and dependencies",
                "dependencies": [],
                "required_capabilities": ["python", "docker"],
                "estimated_hours": 2
            },
            {
                "description": "Design and implement database schema",
                "dependencies": [],
                "required_capabilities": ["postgresql", "python"],
                "estimated_hours": 4
            },
            {
                "description": "Implement authentication system",
                "dependencies": [],
                "required_capabilities": ["python", "fastapi", "api_development"],
                "estimated_hours": 6
            },
            {
                "description": "Create API endpoints",
                "dependencies": [],
                "required_capabilities": ["python", "fastapi", "api_development"],
                "estimated_hours": 8
            },
            {
                "description": "Write unit tests",
                "dependencies": [],
                "required_capabilities": ["pytest", "unittest"],
                "estimated_hours": 4
            },
            {
                "description": "Write integration tests",
                "dependencies": [],
                "required_capabilities": ["pytest", "integration_testing"],
                "estimated_hours": 4
            },
            {
                "description": "Set up Docker containerization",
                "dependencies": [],
                "required_capabilities": ["docker", "deployment"],
                "estimated_hours": 3
            },
            {
                "description": "Create CI/CD pipeline",
                "dependencies": [],
                "required_capabilities": ["github_actions", "docker"],
                "estimated_hours": 4
            }
        ]

        for task_data in example_tasks:
            try:
                result = await self.mcp_client.call_tool(
                    "create_task",
                    task_data
                )

                if result.get("success"):
                    task = result.get("task")
                    tasks.append(task)
                    self.tasks_created.append(task["id"])

                    await self.logger.log(
                        "task_created",
                        {
                            "task_id": task["id"],
                            "description": task["description"]
                        }
                    )

            except Exception as e:
                await self.logger.log(
                    "system_error",
                    {
                        "action": "create_task",
                        "task_data": task_data,
                        "error": str(e)
                    },
                    level="ERROR"
                )

        return tasks

    def calculate_optimal_workers(self, tasks: List[dict]) -> int:
        """
        Determine optimal number of workers based on tasks.

        Simple heuristic:
        - 1-5 tasks: 2 workers
        - 6-10 tasks: 3-4 workers
        - 11-20 tasks: 4-6 workers
        - 21+ tasks: 6-8 workers

        Args:
            tasks: List of tasks

        Returns:
            Optimal worker count (2-8)
        """
        task_count = len(tasks)

        if task_count <= 5:
            return 2
        elif task_count <= 10:
            return 4
        elif task_count <= 20:
            return 6
        else:
            return 8

    async def monitor_progress(self):
        """
        Continuously monitor project progress.

        Checks status every 10 seconds and logs updates.
        """
        while self.is_running:
            try:
                result = await self.mcp_client.call_tool(
                    "get_project_status",
                    {}
                )

                status = result.get("status", {})

                await self.logger.log(
                    "task_progress",
                    {
                        "overall_progress": status.get("overall_progress", 0),
                        "completed_tasks": status.get("metrics", {}).get("completed_tasks", 0),
                        "total_tasks": status.get("metrics", {}).get("total_tasks", 0),
                        "active_workers": status.get("active_workers", 0)
                    }
                )

                # Check if all tasks are complete
                metrics = status.get("metrics", {})
                if (metrics.get("completed_tasks", 0) + metrics.get("failed_tasks", 0)) >= metrics.get("total_tasks", 0):
                    if metrics.get("total_tasks", 0) > 0:
                        await self.logger.log(
                            "project_completed",
                            {
                                "project_id": self.project_id,
                                "total_tasks": metrics["total_tasks"],
                                "completed_tasks": metrics["completed_tasks"],
                                "failed_tasks": metrics["failed_tasks"]
                            }
                        )
                        self.is_running = False
                        break

            except Exception as e:
                await self.logger.log(
                    "system_error",
                    {
                        "action": "monitor_progress",
                        "error": str(e)
                    },
                    level="ERROR"
                )

            await asyncio.sleep(10)

    async def run_project(self, workers: List[Any]):
        """
        Run the project with given workers.

        Args:
            workers: List of Worker instances
        """
        self.workers = workers
        self.is_running = True

        async with self.mcp_client:
            # Initialize project
            await self.initialize_project()

            # Start monitoring
            await self.logger.log(
                "task_started",
                {
                    "task": "monitor_progress",
                    "worker_count": len(workers)
                }
            )

            # Monitor until completion
            await self.monitor_progress()

            await self.logger.log(
                "task_completed",
                {
                    "task": "project_execution",
                    "status": "completed"
                }
            )

    async def handle_clarification(self, clarification_request: dict) -> str:
        """
        Handle clarification request from worker.

        In production, this would use an AI model to answer questions
        or escalate to human oversight.

        Args:
            clarification_request: Clarification request details

        Returns:
            Clarification response
        """
        await self.logger.log(
            "clarification_request",
            clarification_request
        )

        # Simplified response
        return "Please proceed with standard best practices for this task."

    async def handle_escalation(self, escalation: dict):
        """
        Handle task escalation.

        Args:
            escalation: Escalation details
        """
        await self.logger.log(
            "escalation",
            escalation,
            level="WARNING"
        )

        # In production, this would:
        # 1. Analyze the issue
        # 2. Attempt automatic resolution
        # 3. Reassign task if needed
        # 4. Escalate to human if critical

    def get_project_summary(self) -> dict:
        """
        Get project summary.

        Returns:
            Project summary dictionary
        """
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "requirements": self.requirements,
            "plan": self.plan,
            "tasks_created": len(self.tasks_created),
            "workers": len(self.workers),
            "status": "running" if self.is_running else "completed"
        }
