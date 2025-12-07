# MCP-Enabled Autonomous Software Development Team

An autonomous software development team powered by the Model Context Protocol (MCP) and AI agents. This system coordinates multiple AI workers to collaboratively plan, develop, test, and deploy software projects from natural language requirements.

## Overview

This project implements a multi-agent system where:
- A **Project Lead** analyzes requirements and orchestrates development
- Multiple **Workers** (2-8) execute tasks in parallel based on their capabilities
- An **MCP Server** manages context and coordinates communication
- A **Terminal UI** provides real-time visibility into progress
- **JSON Logging** captures all activity for analysis and debugging

## Architecture

```
┌─────────────────┐
│  Project Lead   │──────┐
└─────────────────┘      │
                         ▼
         ┌───────────────────────┐
         │     MCP Server        │
         │  (Context & Tools)    │
         └───────────────────────┘
                ▲       ▲       ▲
                │       │       │
    ┌───────────┼───────┼───────┼──────────┐
    │           │       │       │          │
┌───▼───┐  ┌───▼───┐  ┌▼────┐  ┌▼────┐  ┌▼────┐
│Worker │  │Worker │  │Worker│ │Worker│ │ ... │
│  001  │  │  002  │  │  003 │ │  004 │ │     │
└───────┘  └───────┘  └──────┘ └──────┘ └─────┘
```

## Features

### Core Capabilities
- **Natural Language Requirements**: Describe projects in plain English
- **Automatic Task Decomposition**: AI breaks down projects into atomic tasks
- **Parallel Execution**: 2-8 workers execute tasks concurrently
- **Dynamic Worker Types**:
  - Developers (Python, JavaScript, APIs, databases)
  - Testers (unit tests, integration tests, QA)
  - DevOps (Docker, CI/CD, deployment)
  - Architects (system design, code review)
- **Real-Time Monitoring**: Live terminal UI shows progress
- **Comprehensive Logging**: NDJSON logs for all activity

### MCP Integration
- Tool-based architecture using Model Context Protocol
- Centralized context storage for project state
- Network I/O logging for debugging
- Asynchronous communication between agents

## Installation

### Prerequisites
- Python 3.11 or higher
- pip (Python package manager)

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ollama-tty
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify installation:
```bash
python3 main.py --help
```

## Quick Start

### Using the Startup Script (Recommended)

```bash
./run_autonomous_team.sh "My Project" examples/simple_api.txt 4
```

This will:
1. Start the MCP server
2. Initialize 4 workers
3. Parse requirements from `examples/simple_api.txt`
4. Execute the project
5. Display live progress in terminal

### Using Python Directly

```bash
python3 main.py \
  --name "E-commerce API" \
  --requirements examples/ecommerce.txt \
  --workers 6
```

### Command Line Options

```
python3 main.py [OPTIONS]

Required:
  --requirements PATH    Path to requirements file (natural language)

Optional:
  --name TEXT           Project name
  --workers N           Number of workers (2-8, default: from config)
  --config PATH         Configuration file (default: config/project_config.json)
  --log-file PATH       Log file path (default: logs/project_activity.log)
  --no-display          Disable terminal UI
  --mcp-host HOST       MCP server host (default: localhost)
  --mcp-port PORT       MCP server port (default: 8080)
```

## Configuration

Edit `config/project_config.json` to customize:

```json
{
  "project": {
    "min_workers": 2,
    "max_workers": 8,
    "auto_scale": true
  },
  "workers": {
    "profiles": [
      {
        "type": "developer",
        "count": 3,
        "capabilities": ["python", "fastapi", "postgresql"],
        "model": "claude-3-5-sonnet-20241022"
      }
    ]
  },
  "logging": {
    "level": "DEBUG",
    "include_network_io": true
  }
}
```

## Requirements File Format

Requirements files should be natural language descriptions of your project:

```
examples/simple_api.txt:

Build a RESTful API for a task management system with the following features:

1. User authentication with JWT tokens
2. CRUD operations for tasks
3. Task assignment to users
4. Due date tracking
5. PostgreSQL database
6. Docker containerization
7. Comprehensive unit and integration tests
8. API documentation with OpenAPI/Swagger

Technical Requirements:
- Python 3.11+
- FastAPI framework
- SQLAlchemy ORM
- Pytest for testing
- Docker and docker-compose
- CI/CD with GitHub Actions
```

## Project Structure

```
ollama-tty/
├── config/                  # Configuration files
│   ├── __init__.py
│   ├── settings.py         # Configuration loader
│   └── project_config.json # Project settings
├── context/                # Project state storage
├── display/                # Terminal UI
│   ├── __init__.py
│   └── terminal_ui.py     # Rich-based display
├── examples/              # Example requirements
│   ├── simple_api.txt
│   └── enterprise.txt
├── logging/               # Logging system
│   ├── __init__.py
│   └── json_logger.py    # NDJSON logger
├── logs/                  # Log files
├── mcp_server/           # MCP server implementation
│   ├── __init__.py
│   ├── context_store.py  # State management
│   ├── server.py         # HTTP server
│   └── tools.py          # MCP tools registry
├── project_lead/         # Project lead agent
│   ├── __init__.py
│   └── lead.py           # Lead orchestrator
├── workers/              # Worker agents
│   ├── __init__.py
│   └── worker.py         # Worker implementation
├── main.py               # Main entry point
├── run_autonomous_team.sh # Startup script
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

## Usage Examples

### Example 1: Simple API (3 workers)
```bash
./run_autonomous_team.sh "Task API" examples/simple_api.txt 3
```

### Example 2: Enterprise Portal (8 workers)
```bash
./run_autonomous_team.sh "Enterprise Portal" examples/enterprise.txt 8
```

### Example 3: Custom Configuration
```bash
python3 main.py \
  --name "Custom Project" \
  --requirements my_requirements.txt \
  --workers 6 \
  --config config/custom_config.json
```

### Example 4: Without Terminal UI
```bash
python3 main.py \
  --requirements examples/simple_api.txt \
  --workers 4 \
  --no-display
```

## Monitoring and Logs

### Terminal UI

The terminal UI displays:
- Project name, elapsed time, overall progress
- Individual worker status and current tasks
- Recent activity log
- Task statistics (completed, active, failed, queued)

### Log Files

Logs are saved in NDJSON format to `logs/project_activity.log`:

```json
{"timestamp":"2025-12-07T14:30:00.123456Z","node_type":"worker","node_id":"worker-001","event_type":"task_completed","level":"INFO","data":{"task_id":"task-005"}}
```

Analyze logs with:
```bash
# View all events
cat logs/project_activity.log | jq '.'

# Filter by event type
cat logs/project_activity.log | jq 'select(.event_type=="task_completed")'

# Filter by worker
cat logs/project_activity.log | jq 'select(.node_id=="worker-001")'

# Count events by type
cat logs/project_activity.log | jq -r '.event_type' | sort | uniq -c
```

## Troubleshooting

### MCP Server Won't Start
```bash
# Check if port 8080 is available
lsof -i :8080

# Kill conflicting process
kill $(lsof -t -i :8080)
```

### Workers Not Fetching Tasks
- Check MCP server is running: `curl http://localhost:8080/health`
- Verify log file for errors: `tail -f logs/project_activity.log`
- Ensure workers have matching capabilities for available tasks

### Dependencies Missing
```bash
pip install -r requirements.txt
```

## Development

### Running Tests (Future)
```bash
pytest tests/
```

### Code Formatting
```bash
black .
```

### Type Checking
```bash
mypy .
```

## Architecture Details

### Worker Types

| Type | Capabilities | Concurrent Tasks | Model |
|------|--------------|------------------|-------|
| Developer | Python, JS, API dev, databases | 2 | Claude-3.5 Sonnet |
| Tester | Pytest, integration tests, QA | 3 | Claude-3.5 Haiku |
| DevOps | Docker, CI/CD, deployment | 2 | Claude-3.5 Haiku |
| Architect | System design, code review | 1 | Claude-3.5 Opus |

### MCP Tools

- `analyze_requirements`: Break down requirements into project plan
- `create_task`: Create a new task in the project
- `assign_task`: Assign task to specific worker
- `fetch_task`: Worker fetches next available task
- `update_task_status`: Update task progress (0-100%)
- `complete_task`: Mark task as completed with result
- `fail_task`: Mark task as failed with error
- `log_event`: Universal logging endpoint
- `request_clarification`: Worker asks project question
- `get_project_status`: Get full project overview

### Execution Flow

1. **Initialization (0-5 min)**
   - Start MCP server
   - Initialize project lead
   - Create worker pool
   - Start terminal UI

2. **Planning (5-15 min)**
   - Analyze requirements
   - Generate architecture plan
   - Decompose into tasks
   - Assign initial tasks

3. **Execution (15 min - N hours)**
   - Workers fetch and execute tasks
   - Real-time progress updates
   - Dynamic task assignment
   - Error handling and escalation

4. **Completion**
   - Final integration
   - Generate documentation
   - Project summary report

## Future Enhancements

- [ ] Multi-project orchestration
- [ ] Human-in-the-loop clarifications
- [ ] Code review agent
- [ ] Learning from past projects
- [ ] Integration with Jira, GitHub, Slack
- [ ] Web-based UI
- [ ] Distributed worker nodes
- [ ] Plugin system for custom worker types

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - See LICENSE file for details

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

## Acknowledgments

Built with:
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Anthropic Claude](https://www.anthropic.com/claude)
- [Rich](https://github.com/Textualize/rich) - Terminal UI
- [aiohttp](https://docs.aiohttp.org/) - Async HTTP

---

**Note**: This is a demonstration/research project. In production environments, ensure proper security, error handling, and monitoring practices are in place.
