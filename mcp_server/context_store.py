"""
Context Store for MCP Server.

Manages project state, tasks, workers, and conversation history.
Uses JSON file storage with in-memory caching for performance.
"""

import json
import os
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class WorkerStatus(Enum):
    """Worker status enumeration."""
    IDLE = "idle"
    ACTIVE = "active"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class ContextStore:
    """
    Manages all project context and state.

    Stores:
    - Project metadata and plan
    - Task definitions and status
    - Worker information and assignments
    - Conversation history
    - Metrics and statistics
    """

    def __init__(self, storage_path: str = "context/project_store.json"):
        """
        Initialize the context store.

        Args:
            storage_path: Path to the JSON storage file
        """
        self.storage_path = storage_path
        self.lock = asyncio.Lock()
        self.context = {
            "project_id": None,
            "project_name": None,
            "state": "initializing",
            "plan": {},
            "tasks": {},
            "workers": {},
            "conversation_history": [],
            "metrics": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "start_time": None,
                "end_time": None
            }
        }

        # Ensure storage directory exists
        storage_dir = os.path.dirname(storage_path)
        if storage_dir:
            Path(storage_dir).mkdir(parents=True, exist_ok=True)

        # Load existing context if available
        if os.path.exists(storage_path):
            self._load()

    def _load(self):
        """Load context from disk."""
        try:
            with open(self.storage_path, 'r') as f:
                self.context = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Could not load context from {self.storage_path}: {e}")

    async def _save(self):
        """Save context to disk."""
        async with self.lock:
            with open(self.storage_path, 'w') as f:
                json.dump(self.context, f, indent=2)

    async def initialize_project(self, project_id: str, project_name: str, requirements: str):
        """Initialize a new project."""
        async with self.lock:
            self.context.update({
                "project_id": project_id,
                "project_name": project_name,
                "state": "active",
                "requirements": requirements,
                "metrics": {
                    **self.context["metrics"],
                    "start_time": datetime.utcnow().isoformat() + "Z"
                }
            })
        await self._save()

    async def set_plan(self, plan: dict):
        """Set the project plan."""
        async with self.lock:
            self.context["plan"] = plan
        await self._save()

    async def create_task(self, task_id: str, task_data: dict) -> dict:
        """
        Create a new task.

        Args:
            task_id: Unique task identifier
            task_data: Task details (description, dependencies, etc.)

        Returns:
            Created task dictionary
        """
        task = {
            "id": task_id,
            "status": TaskStatus.PENDING.value,
            "assigned_to": None,
            "progress": 0,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
            **task_data
        }

        async with self.lock:
            self.context["tasks"][task_id] = task
            self.context["metrics"]["total_tasks"] += 1
        await self._save()

        return task

    async def assign_task(self, task_id: str, worker_id: str) -> bool:
        """Assign a task to a worker."""
        async with self.lock:
            if task_id not in self.context["tasks"]:
                return False

            self.context["tasks"][task_id].update({
                "status": TaskStatus.ASSIGNED.value,
                "assigned_to": worker_id,
                "updated_at": datetime.utcnow().isoformat() + "Z"
            })

            if worker_id in self.context["workers"]:
                if "current_tasks" not in self.context["workers"][worker_id]:
                    self.context["workers"][worker_id]["current_tasks"] = []
                self.context["workers"][worker_id]["current_tasks"].append(task_id)

        await self._save()
        return True

    async def update_task_status(
        self,
        task_id: str,
        status: str,
        progress: Optional[int] = None,
        result: Optional[dict] = None
    ) -> bool:
        """Update task status and progress."""
        async with self.lock:
            if task_id not in self.context["tasks"]:
                return False

            task = self.context["tasks"][task_id]
            task["status"] = status
            task["updated_at"] = datetime.utcnow().isoformat() + "Z"

            if progress is not None:
                task["progress"] = progress

            if result is not None:
                task["result"] = result

            # Update metrics
            if status == TaskStatus.COMPLETED.value:
                self.context["metrics"]["completed_tasks"] += 1
            elif status == TaskStatus.FAILED.value:
                self.context["metrics"]["failed_tasks"] += 1

        await self._save()
        return True

    async def register_worker(self, worker_id: str, worker_data: dict) -> dict:
        """Register a new worker."""
        worker = {
            "id": worker_id,
            "status": WorkerStatus.IDLE.value,
            "current_tasks": [],
            "completed_tasks": 0,
            "failed_tasks": 0,
            "registered_at": datetime.utcnow().isoformat() + "Z",
            **worker_data
        }

        async with self.lock:
            self.context["workers"][worker_id] = worker
        await self._save()

        return worker

    async def update_worker_status(self, worker_id: str, status: str, current_task: Optional[str] = None):
        """Update worker status."""
        async with self.lock:
            if worker_id not in self.context["workers"]:
                return False

            worker = self.context["workers"][worker_id]
            worker["status"] = status

            if current_task:
                worker["current_task"] = current_task

        await self._save()
        return True

    async def get_available_tasks(self, worker_capabilities: List[str]) -> List[dict]:
        """
        Get tasks available for assignment based on worker capabilities.

        Args:
            worker_capabilities: List of worker capabilities

        Returns:
            List of available tasks
        """
        available = []

        async with self.lock:
            for task_id, task in self.context["tasks"].items():
                if task["status"] == TaskStatus.PENDING.value:
                    # Check if dependencies are met
                    dependencies = task.get("dependencies", [])
                    dependencies_met = all(
                        self.context["tasks"].get(dep, {}).get("status") == TaskStatus.COMPLETED.value
                        for dep in dependencies
                    )

                    if dependencies_met:
                        # Check capability match if required
                        required_capabilities = task.get("required_capabilities", [])
                        if not required_capabilities or any(
                            cap in worker_capabilities for cap in required_capabilities
                        ):
                            available.append(task)

        return available

    async def get_project_status(self) -> dict:
        """Get full project status."""
        async with self.lock:
            tasks_by_status = {}
            for task in self.context["tasks"].values():
                status = task["status"]
                tasks_by_status[status] = tasks_by_status.get(status, 0) + 1

            workers_by_status = {}
            for worker in self.context["workers"].values():
                status = worker["status"]
                workers_by_status[status] = workers_by_status.get(status, 0) + 1

            overall_progress = 0
            if self.context["metrics"]["total_tasks"] > 0:
                overall_progress = (
                    self.context["metrics"]["completed_tasks"] /
                    self.context["metrics"]["total_tasks"] * 100
                )

            return {
                "project_id": self.context["project_id"],
                "project_name": self.context["project_name"],
                "state": self.context["state"],
                "overall_progress": round(overall_progress, 2),
                "metrics": self.context["metrics"],
                "tasks_by_status": tasks_by_status,
                "workers_by_status": workers_by_status,
                "active_workers": len([
                    w for w in self.context["workers"].values()
                    if w["status"] in [WorkerStatus.ACTIVE.value, WorkerStatus.BUSY.value]
                ])
            }

    async def add_conversation_entry(self, entry: dict):
        """Add an entry to conversation history."""
        async with self.lock:
            self.context["conversation_history"].append({
                **entry,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            })
        await self._save()

    async def get_task(self, task_id: str) -> Optional[dict]:
        """Get a specific task by ID."""
        async with self.lock:
            return self.context["tasks"].get(task_id)

    async def get_worker(self, worker_id: str) -> Optional[dict]:
        """Get a specific worker by ID."""
        async with self.lock:
            return self.context["workers"].get(worker_id)

    async def complete_project(self):
        """Mark project as completed."""
        async with self.lock:
            self.context["state"] = "completed"
            self.context["metrics"]["end_time"] = datetime.utcnow().isoformat() + "Z"
        await self._save()
