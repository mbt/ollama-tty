"""
Terminal Status Display for Autonomous Development Team.

Provides a live, interactive terminal UI showing:
- Project overview and progress
- Individual worker status
- Recent activity log
- Overall metrics
"""

import asyncio
import time
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich.text import Text

from workers.worker import MCPClient, Worker
from project_lead.lead import ProjectLead


class TerminalStatusDisplay:
    """
    Live terminal status display for autonomous development team.

    Shows:
    - Project header with name, elapsed time, overall progress
    - Worker panels (2-8 workers)
    - Recent activity log
    - Footer with task statistics
    """

    def __init__(
        self,
        project_lead: ProjectLead,
        workers: List[Worker],
        mcp_host: str = "localhost",
        mcp_port: int = 8080,
        refresh_rate: float = 1.0
    ):
        """
        Initialize terminal status display.

        Args:
            project_lead: ProjectLead instance
            workers: List of Worker instances
            mcp_host: MCP server host
            mcp_port: MCP server port
            refresh_rate: Refresh rate in seconds
        """
        self.console = Console()
        self.project_lead = project_lead
        self.workers = workers
        self.refresh_rate = refresh_rate

        # Initialize MCP client for status queries
        self.mcp_client = MCPClient(mcp_host, mcp_port)

        # Activity log
        self.activity_log = []
        self.max_activity_entries = 10

        # Project start time
        self.start_time = datetime.now()

        # Layout
        self.layout = self._create_layout()

    def _create_layout(self) -> Layout:
        """
        Create terminal layout.

        Returns:
            Layout instance
        """
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="workers"),
            Layout(name="activity", size=12),
            Layout(name="footer", size=3)
        )

        # Split workers section based on worker count
        worker_count = len(self.workers)

        if worker_count <= 2:
            # Single row for 1-2 workers
            workers_layout = Layout()
            workers_layout.split_row(
                *[Layout(name=f"worker_{i}") for i in range(worker_count)]
            )
        elif worker_count <= 4:
            # Single row for 3-4 workers
            workers_layout = Layout()
            workers_layout.split_row(
                *[Layout(name=f"worker_{i}") for i in range(worker_count)]
            )
        else:
            # Two rows for 5-8 workers
            workers_layout = Layout()
            top_count = (worker_count + 1) // 2
            bottom_count = worker_count - top_count

            top_row = Layout()
            top_row.split_row(
                *[Layout(name=f"worker_{i}") for i in range(top_count)]
            )

            bottom_row = Layout()
            bottom_row.split_row(
                *[Layout(name=f"worker_{i}") for i in range(top_count, worker_count)]
            )

            workers_layout.split_column(top_row, bottom_row)

        layout["workers"].update(workers_layout)

        return layout

    def _render_header(self, status: dict) -> Panel:
        """
        Render header panel with project info and overall progress.

        Args:
            status: Project status dictionary

        Returns:
            Panel instance
        """
        elapsed = datetime.now() - self.start_time
        elapsed_str = str(elapsed).split('.')[0]  # Remove microseconds

        overall_progress = status.get("overall_progress", 0)
        progress_bar = self._render_progress_bar(overall_progress)

        header_text = (
            f"Project: {self.project_lead.project_name}    "
            f"Elapsed: {elapsed_str}    "
            f"Overall: {progress_bar} {overall_progress:.1f}%"
        )

        return Panel(
            header_text,
            style="bold white on blue",
            border_style="blue"
        )

    def _render_progress_bar(self, progress: float, width: int = 5) -> str:
        """
        Render a simple progress bar.

        Args:
            progress: Progress percentage (0-100)
            width: Width in characters

        Returns:
            Progress bar string
        """
        filled = int((progress / 100) * width)
        bar = "▓" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def _render_worker_panel(self, worker: Worker, status: dict) -> Panel:
        """
        Render individual worker panel.

        Args:
            worker: Worker instance
            status: Project status dictionary

        Returns:
            Panel instance
        """
        # Get worker info from status
        workers_info = status.get("workers", {})
        worker_info = workers_info.get(worker.worker_id, {})

        # Determine current task
        current_task = "IDLE"
        progress = 0

        if worker.current_task:
            task_id = worker.current_task.get("id", "unknown")
            current_task = task_id
            progress = worker.current_task.get("progress", 0)

        progress_bar = self._render_progress_bar(progress)

        # Determine border color based on status
        border_style = "green" if worker.is_active else "red"

        panel_text = (
            f"Worker {worker.worker_id} ({worker.worker_type.value})\n"
            f"Task: {current_task}\n"
            f"Progress: {progress_bar} {progress}%\n"
            f"Status: {worker.status}"
        )

        return Panel(
            panel_text,
            border_style=border_style,
            title=f"[bold]{worker.worker_type.value.upper()}[/bold]"
        )

    def _render_activity(self) -> Panel:
        """
        Render recent activity log.

        Returns:
            Panel instance
        """
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Time", style="dim", width=8)
        table.add_column("Source", style="cyan", width=12)
        table.add_column("Event", width=60)

        # Show most recent entries (reversed)
        for entry in reversed(self.activity_log[-self.max_activity_entries:]):
            table.add_row(
                entry["time"],
                entry["source"],
                entry["event"]
            )

        return Panel(
            table,
            title="[bold]Recent Activity[/bold]",
            border_style="yellow"
        )

    def _render_footer(self, status: dict) -> Panel:
        """
        Render footer with task statistics.

        Args:
            status: Project status dictionary

        Returns:
            Panel instance
        """
        tasks_by_status = status.get("tasks_by_status", {})

        completed = tasks_by_status.get("completed", 0)
        in_progress = tasks_by_status.get("in_progress", 0)
        failed = tasks_by_status.get("failed", 0)
        pending = tasks_by_status.get("pending", 0)

        footer_text = (
            f"Completed: {completed} | "
            f"Active: {in_progress} | "
            f"Failed: {failed} | "
            f"Queue: {pending}"
        )

        return Panel(
            footer_text,
            style="bold white on black",
            border_style="white"
        )

    def add_activity(self, source: str, event: str):
        """
        Add entry to activity log.

        Args:
            source: Source of the event (worker ID, "lead", etc.)
            event: Event description
        """
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")

        self.activity_log.append({
            "time": time_str,
            "source": source,
            "event": event
        })

        # Keep only recent entries
        if len(self.activity_log) > 100:
            self.activity_log = self.activity_log[-100:]

    async def update_display(self):
        """Update the display with current status."""
        try:
            # Fetch current project status
            result = await self.mcp_client.call_tool(
                "get_project_status",
                {}
            )

            status = result.get("status", {})

            # Update header
            self.layout["header"].update(self._render_header(status))

            # Update worker panels
            for i, worker in enumerate(self.workers):
                worker_panel = self._render_worker_panel(worker, status)
                self.layout[f"worker_{i}"].update(worker_panel)

            # Update activity log
            self.layout["activity"].update(self._render_activity())

            # Update footer
            self.layout["footer"].update(self._render_footer(status))

        except Exception as e:
            # Handle errors gracefully
            error_text = f"Error updating display: {str(e)}"
            self.add_activity("display", error_text)

    async def run(self):
        """
        Run the terminal display.

        Continuously updates the display until project completes.
        """
        async with self.mcp_client:
            with Live(self.layout, console=self.console, refresh_per_second=1/self.refresh_rate):
                while self.project_lead.is_running:
                    await self.update_display()
                    await asyncio.sleep(self.refresh_rate)

                # Final update after completion
                await self.update_display()
                self.add_activity("lead", "Project completed!")

    def run_sync(self):
        """
        Run the display synchronously (for background threads).

        This is a simplified version that can run in a separate process.
        """
        # Simplified synchronous version
        print(f"Terminal UI running for project: {self.project_lead.project_name}")
        print(f"Workers: {len(self.workers)}")
        print(f"Refresh rate: {self.refresh_rate}s")
        print("\nPress Ctrl+C to stop display\n")


async def main():
    """Main entry point for standalone terminal UI."""
    import argparse

    parser = argparse.ArgumentParser(description="Terminal Status Display")
    parser.add_argument("--mcp-host", default="localhost", help="MCP server host")
    parser.add_argument("--mcp-port", type=int, default=8080, help="MCP server port")
    parser.add_argument("--refresh-rate", type=float, default=1.0, help="Refresh rate in seconds")

    args = parser.parse_args()

    # This would need to be connected to actual project lead and workers
    print(f"Connecting to MCP server at {args.mcp_host}:{args.mcp_port}")
    print("Display starting...")

    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\nDisplay stopped")


if __name__ == "__main__":
    asyncio.run(main())
