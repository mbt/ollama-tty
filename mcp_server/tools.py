"""
MCP Tool Registry and Handlers.

Defines all tools available to the autonomous development team:
- analyze_requirements: Break down requirements into project plan
- create_task: Create a new task
- assign_task: Assign task to worker
- fetch_task: Worker fetches next available task
- update_task_status: Update task progress
- complete_task: Mark task as completed
- fail_task: Mark task as failed
- log_event: Universal logging endpoint
- request_clarification: Worker asks project question
- get_project_status: Get full project overview
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid


# Tool input schemas (simplified for demonstration)
class ToolSchema:
    """Base class for tool schemas."""
    pass


class RequirementsSchema(ToolSchema):
    """Schema for analyze_requirements tool."""
    properties = {
        "text": {"type": "string", "description": "Natural language requirements"}
    }
    required = ["text"]


class TaskCreateSchema(ToolSchema):
    """Schema for create_task tool."""
    properties = {
        "description": {"type": "string"},
        "dependencies": {"type": "array", "items": {"type": "string"}},
        "required_capabilities": {"type": "array", "items": {"type": "string"}},
        "estimated_hours": {"type": "number"}
    }
    required = ["description"]


class TaskAssignSchema(ToolSchema):
    """Schema for assign_task tool."""
    properties = {
        "task_id": {"type": "string"},
        "worker_id": {"type": "string"}
    }
    required = ["task_id", "worker_id"]


class TaskFetchSchema(ToolSchema):
    """Schema for fetch_task tool."""
    properties = {
        "worker_id": {"type": "string"},
        "capabilities": {"type": "array", "items": {"type": "string"}}
    }
    required = ["worker_id", "capabilities"]


class TaskStatusSchema(ToolSchema):
    """Schema for update_task_status tool."""
    properties = {
        "task_id": {"type": "string"},
        "status": {"type": "string"},
        "progress": {"type": "integer", "minimum": 0, "maximum": 100}
    }
    required = ["task_id", "status"]


class LogEventSchema(ToolSchema):
    """Schema for log_event tool."""
    properties = {
        "event_type": {"type": "string"},
        "data": {"type": "object"}
    }
    required = ["event_type", "data"]


class ClarificationSchema(ToolSchema):
    """Schema for request_clarification tool."""
    properties = {
        "worker_id": {"type": "string"},
        "task_id": {"type": "string"},
        "question": {"type": "string"}
    }
    required = ["worker_id", "task_id", "question"]


class StatusQuerySchema(ToolSchema):
    """Schema for get_project_status tool."""
    properties = {}
    required = []


# Tool handler functions
async def analyze_requirements(context_store, params: dict) -> dict:
    """
    Analyze requirements and create project plan.

    This is a simplified implementation. In production, this would use
    an AI model to break down requirements into tasks.
    """
    requirements = params.get("text", "")

    # Simple task decomposition (in production, use AI)
    plan = {
        "project_description": requirements,
        "architecture": "To be determined by project lead",
        "tech_stack": [],
        "phases": [
            {"name": "Planning", "status": "in_progress"},
            {"name": "Development", "status": "pending"},
            {"name": "Testing", "status": "pending"},
            {"name": "Deployment", "status": "pending"}
        ],
        "estimated_tasks": 0
    }

    await context_store.set_plan(plan)

    return {
        "success": True,
        "plan": plan
    }


async def create_task(context_store, params: dict) -> dict:
    """Create a new task in the project."""
    task_id = f"task-{str(uuid.uuid4())[:8]}"

    task_data = {
        "description": params.get("description"),
        "dependencies": params.get("dependencies", []),
        "required_capabilities": params.get("required_capabilities", []),
        "estimated_hours": params.get("estimated_hours", 0)
    }

    task = await context_store.create_task(task_id, task_data)

    return {
        "success": True,
        "task": task
    }


async def assign_task(context_store, params: dict) -> dict:
    """Assign a task to a specific worker."""
    task_id = params.get("task_id")
    worker_id = params.get("worker_id")

    success = await context_store.assign_task(task_id, worker_id)

    return {
        "success": success,
        "task_id": task_id,
        "worker_id": worker_id
    }


async def fetch_available_task(context_store, params: dict) -> dict:
    """Worker fetches next available task."""
    worker_id = params.get("worker_id")
    capabilities = params.get("capabilities", [])

    # Get available tasks matching worker capabilities
    available_tasks = await context_store.get_available_tasks(capabilities)

    if not available_tasks:
        return {
            "success": True,
            "task": None,
            "message": "No available tasks"
        }

    # Assign first available task to this worker
    task = available_tasks[0]
    await context_store.assign_task(task["id"], worker_id)

    return {
        "success": True,
        "task": task
    }


async def update_task_status(context_store, params: dict) -> dict:
    """Update task progress."""
    task_id = params.get("task_id")
    status = params.get("status")
    progress = params.get("progress")

    success = await context_store.update_task_status(
        task_id,
        status,
        progress=progress
    )

    return {
        "success": success,
        "task_id": task_id,
        "status": status,
        "progress": progress
    }


async def complete_task(context_store, params: dict) -> dict:
    """Mark task as completed."""
    task_id = params.get("task_id")
    result = params.get("result", {})

    success = await context_store.update_task_status(
        task_id,
        "completed",
        progress=100,
        result=result
    )

    return {
        "success": success,
        "task_id": task_id,
        "status": "completed"
    }


async def fail_task(context_store, params: dict) -> dict:
    """Mark task as failed."""
    task_id = params.get("task_id")
    error = params.get("error", "Unknown error")

    success = await context_store.update_task_status(
        task_id,
        "failed",
        result={"error": error}
    )

    return {
        "success": success,
        "task_id": task_id,
        "status": "failed",
        "error": error
    }


async def log_event(context_store, params: dict) -> dict:
    """Universal logging endpoint."""
    event_type = params.get("event_type")
    data = params.get("data", {})

    await context_store.add_conversation_entry({
        "event_type": event_type,
        "data": data
    })

    return {
        "success": True
    }


async def request_clarification(context_store, params: dict) -> dict:
    """Worker requests clarification from project lead."""
    worker_id = params.get("worker_id")
    task_id = params.get("task_id")
    question = params.get("question")

    clarification_id = f"clarify-{str(uuid.uuid4())[:8]}"

    await context_store.add_conversation_entry({
        "type": "clarification_request",
        "id": clarification_id,
        "worker_id": worker_id,
        "task_id": task_id,
        "question": question,
        "status": "pending"
    })

    return {
        "success": True,
        "clarification_id": clarification_id,
        "message": "Clarification request submitted to project lead"
    }


async def get_project_status(context_store, params: dict) -> dict:
    """Get full project overview."""
    status = await context_store.get_project_status()

    return {
        "success": True,
        "status": status
    }


# Tool registry
TOOLS = {
    "analyze_requirements": {
        "handler": analyze_requirements,
        "description": "Break down requirements into project plan",
        "input_schema": RequirementsSchema
    },
    "create_task": {
        "handler": create_task,
        "description": "Create a new task in the project",
        "input_schema": TaskCreateSchema
    },
    "assign_task": {
        "handler": assign_task,
        "description": "Assign task to specific worker",
        "input_schema": TaskAssignSchema
    },
    "fetch_task": {
        "handler": fetch_available_task,
        "description": "Worker fetches next available task",
        "input_schema": TaskFetchSchema
    },
    "update_task_status": {
        "handler": update_task_status,
        "description": "Update task progress (0-100%)",
        "input_schema": TaskStatusSchema
    },
    "complete_task": {
        "handler": complete_task,
        "description": "Mark task as completed with result",
        "input_schema": TaskCreateSchema
    },
    "fail_task": {
        "handler": fail_task,
        "description": "Mark task as failed with error",
        "input_schema": TaskCreateSchema
    },
    "log_event": {
        "handler": log_event,
        "description": "Universal logging endpoint",
        "input_schema": LogEventSchema
    },
    "request_clarification": {
        "handler": request_clarification,
        "description": "Worker asks project question",
        "input_schema": ClarificationSchema
    },
    "get_project_status": {
        "handler": get_project_status,
        "description": "Get full project overview",
        "input_schema": StatusQuerySchema
    }
}


def register_tools(context_store) -> Dict[str, Any]:
    """
    Register all tools with the context store.

    Args:
        context_store: ContextStore instance

    Returns:
        Dictionary of tool definitions
    """
    registered_tools = {}

    for tool_name, tool_def in TOOLS.items():
        # Create a bound handler that includes context_store
        async def bound_handler(params, handler=tool_def["handler"], store=context_store):
            return await handler(store, params)

        registered_tools[tool_name] = {
            "name": tool_name,
            "description": tool_def["description"],
            "handler": bound_handler,
            "input_schema": tool_def["input_schema"]
        }

    return registered_tools
