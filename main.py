#!/usr/bin/env python3
"""
Main Entry Point for MCP-Enabled Autonomous Development Team.

This script orchestrates the entire autonomous development process:
1. Starts MCP server
2. Initializes project lead
3. Creates worker pool
4. Starts terminal UI display
5. Executes project
6. Handles cleanup
"""

import asyncio
import argparse
import os
import sys
from pathlib import Path
from typing import List

from config.settings import ProjectConfig
from project_lead.lead import ProjectLead
from workers.worker import Worker, WorkerType
from display.terminal_ui import TerminalStatusDisplay
from mcp_server.server import MCPServer
from logging.json_logger import JSONLogger


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MCP-Enabled Autonomous Software Development Team",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default config and requirements file
  python main.py --requirements examples/simple_api.txt

  # Run with custom worker count
  python main.py --requirements examples/simple_api.txt --workers 4

  # Run with custom project name
  python main.py --name "My Project" --requirements examples/simple_api.txt

  # Run with custom config
  python main.py --config config/custom_config.json --requirements examples/simple_api.txt
        """
    )

    parser.add_argument(
        "--name",
        type=str,
        help="Project name (default: from requirements or config)"
    )

    parser.add_argument(
        "--requirements",
        type=str,
        required=True,
        help="Path to requirements file (natural language)"
    )

    parser.add_argument(
        "--workers",
        type=int,
        help="Number of workers (overrides config, 2-8)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="config/project_config.json",
        help="Path to configuration file (default: config/project_config.json)"
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (overrides config)"
    )

    parser.add_argument(
        "--no-display",
        action="store_true",
        help="Disable terminal UI display"
    )

    parser.add_argument(
        "--mcp-host",
        type=str,
        help="MCP server host (overrides config)"
    )

    parser.add_argument(
        "--mcp-port",
        type=int,
        help="MCP server port (overrides config)"
    )

    return parser.parse_args()


def load_requirements(requirements_file: str) -> str:
    """
    Load requirements from file.

    Args:
        requirements_file: Path to requirements file

    Returns:
        Requirements text

    Raises:
        FileNotFoundError: If requirements file doesn't exist
    """
    if not os.path.exists(requirements_file):
        raise FileNotFoundError(f"Requirements file not found: {requirements_file}")

    with open(requirements_file, 'r') as f:
        return f.read()


async def initialize_workers(
    worker_count: int,
    config: ProjectConfig,
    mcp_host: str,
    mcp_port: int,
    log_file: str
) -> List[Worker]:
    """
    Initialize worker pool based on configuration.

    Args:
        worker_count: Number of workers to create
        config: Project configuration
        mcp_host: MCP server host
        mcp_port: MCP server port
        log_file: Path to log file

    Returns:
        List of Worker instances
    """
    workers = []

    # Get worker profiles from config
    profiles = config.worker_profiles

    # Calculate worker distribution based on profiles
    total_profile_count = sum(p.get("count", 0) for p in profiles)

    if total_profile_count == 0:
        # Fallback: create all developers
        for i in range(worker_count):
            worker = Worker(
                worker_id=f"worker-{i+1:03d}",
                worker_type=WorkerType.DEVELOPER,
                mcp_host=mcp_host,
                mcp_port=mcp_port,
                log_file=log_file
            )
            workers.append(worker)
    else:
        # Distribute workers according to profile ratios
        worker_id = 1

        for profile in profiles:
            profile_type = profile.get("type", "developer")
            profile_count = profile.get("count", 0)

            # Calculate actual count based on worker_count
            actual_count = int((profile_count / total_profile_count) * worker_count)

            # Ensure at least 1 of each type if specified in config
            if profile_count > 0 and actual_count == 0:
                actual_count = 1

            # Map profile type to WorkerType enum
            try:
                worker_type = WorkerType(profile_type)
            except ValueError:
                worker_type = WorkerType.DEVELOPER

            for _ in range(actual_count):
                worker = Worker(
                    worker_id=f"worker-{worker_id:03d}",
                    worker_type=worker_type,
                    mcp_host=mcp_host,
                    mcp_port=mcp_port,
                    log_file=log_file
                )
                workers.append(worker)
                worker_id += 1

    return workers[:worker_count]  # Ensure we don't exceed requested count


async def cleanup(mcp_server_task, worker_tasks, display_task):
    """
    Cleanup resources on shutdown.

    Args:
        mcp_server_task: MCP server task
        worker_tasks: List of worker tasks
        display_task: Display task
    """
    print("\n\nShutting down...")

    # Cancel all tasks
    if mcp_server_task and not mcp_server_task.done():
        mcp_server_task.cancel()

    for task in worker_tasks:
        if not task.done():
            task.cancel()

    if display_task and not display_task.done():
        display_task.cancel()

    # Wait for cancellation
    await asyncio.sleep(1)

    print("Cleanup complete")


async def main():
    """Main execution function."""
    # Parse arguments
    args = parse_args()

    try:
        # Load configuration
        config = ProjectConfig(args.config)
        print(f"Loaded configuration: {config}")

        # Override config with command line arguments
        mcp_host = args.mcp_host or config.mcp_server_host
        mcp_port = args.mcp_port or config.mcp_server_port
        log_file = args.log_file or config.log_file

        # Ensure log directory exists
        os.makedirs("logs", exist_ok=True)

        # Load requirements
        requirements = load_requirements(args.requirements)
        print(f"\nLoaded requirements from: {args.requirements}")
        print(f"Requirements length: {len(requirements)} characters\n")

        # Determine project name
        project_name = args.name or config.project_name

        # Determine worker count
        if args.workers:
            worker_count = max(config.min_workers, min(args.workers, config.max_workers))
        else:
            worker_count = config.min_workers

        print(f"Project: {project_name}")
        print(f"Workers: {worker_count}")
        print(f"MCP Server: {mcp_host}:{mcp_port}")
        print(f"Log file: {log_file}\n")

        # Initialize logger
        logger = JSONLogger("system", "main", log_file)

        await logger.log(
            "system_started",
            {
                "project_name": project_name,
                "worker_count": worker_count,
                "requirements_length": len(requirements)
            }
        )

        # Start MCP server
        print("Starting MCP server...")
        mcp_server = MCPServer(
            host=mcp_host,
            port=mcp_port,
            log_file=log_file
        )

        mcp_server_task = asyncio.create_task(mcp_server.start())
        await asyncio.sleep(2)  # Wait for server to start

        # Initialize project lead
        print("Initializing project lead...")
        lead = ProjectLead(
            project_name=project_name,
            requirements=requirements,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            log_file=log_file
        )

        # Initialize workers
        print(f"Initializing {worker_count} workers...")
        workers = await initialize_workers(
            worker_count=worker_count,
            config=config,
            mcp_host=mcp_host,
            mcp_port=mcp_port,
            log_file=log_file
        )

        print(f"Created {len(workers)} workers:")
        for worker in workers:
            print(f"  - {worker.worker_id} ({worker.worker_type.value})")

        # Start worker tasks
        print("\nStarting worker tasks...")
        worker_tasks = [
            asyncio.create_task(worker.work_loop())
            for worker in workers
        ]

        # Start display (if not disabled)
        display_task = None
        if not args.no_display:
            print("Starting terminal UI display...")
            display = TerminalStatusDisplay(
                project_lead=lead,
                workers=workers,
                mcp_host=mcp_host,
                mcp_port=mcp_port,
                refresh_rate=config.display_refresh_rate_hz
            )
            display_task = asyncio.create_task(display.run())

        # Run project
        print("\n" + "="*80)
        print("PROJECT EXECUTION STARTED")
        print("="*80 + "\n")

        try:
            await lead.run_project(workers)
        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal...")
        finally:
            # Stop workers
            for worker in workers:
                await worker.stop()

            # Cleanup
            await cleanup(mcp_server_task, worker_tasks, display_task)

            await logger.log(
                "system_stopped",
                {
                    "project_name": project_name,
                    "status": "completed" if not lead.is_running else "interrupted"
                }
            )

            print("\n" + "="*80)
            print("PROJECT EXECUTION COMPLETED")
            print("="*80 + "\n")

            # Print summary
            summary = lead.get_project_summary()
            print("Project Summary:")
            print(f"  Project ID: {summary['project_id']}")
            print(f"  Tasks Created: {summary['tasks_created']}")
            print(f"  Workers Used: {summary['workers']}")
            print(f"  Status: {summary['status']}")
            print(f"\nLogs saved to: {log_file}\n")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
