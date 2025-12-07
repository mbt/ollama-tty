#!/bin/bash
#
# Startup Script for MCP-Enabled Autonomous Development Team
#
# Usage:
#   ./run_autonomous_team.sh <project_name> <requirements_file> [worker_count]
#
# Examples:
#   ./run_autonomous_team.sh "Simple API" examples/simple_api.txt 3
#   ./run_autonomous_team.sh "Enterprise Portal" examples/enterprise.txt 8
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check arguments
if [ $# -lt 2 ]; then
    print_error "Usage: $0 <project_name> <requirements_file> [worker_count]"
    echo ""
    echo "Examples:"
    echo "  $0 \"Simple API\" examples/simple_api.txt 3"
    echo "  $0 \"Enterprise Portal\" examples/enterprise.txt 8"
    exit 1
fi

PROJECT_NAME=$1
REQUIREMENTS_FILE=$2
WORKER_COUNT=${3:-4}  # Default to 4 workers

# Validate requirements file
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    print_error "Requirements file not found: $REQUIREMENTS_FILE"
    exit 1
fi

# Validate worker count
if [ "$WORKER_COUNT" -lt 2 ] || [ "$WORKER_COUNT" -gt 8 ]; then
    print_warning "Worker count must be between 2 and 8. Using default: 4"
    WORKER_COUNT=4
fi

# Create timestamped log file
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="logs/project_${TIMESTAMP}.log"

print_info "Starting MCP-Enabled Autonomous Development Team"
echo ""
echo "Configuration:"
echo "  Project Name: $PROJECT_NAME"
echo "  Requirements: $REQUIREMENTS_FILE"
echo "  Workers: $WORKER_COUNT"
echo "  Log File: $LOG_FILE"
echo ""

# Create necessary directories
print_info "Creating directories..."
mkdir -p logs context

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi

print_success "Python 3 found: $(python3 --version)"

# Check if dependencies are installed
print_info "Checking dependencies..."
if ! python3 -c "import aiohttp" 2>/dev/null; then
    print_warning "Dependencies not installed. Installing now..."
    pip3 install -r requirements.txt
fi

print_success "Dependencies verified"

# Cleanup function for graceful shutdown
cleanup() {
    print_info "Shutting down..."

    # Kill MCP server if running
    if [ ! -z "$MCP_PID" ]; then
        print_info "Stopping MCP server (PID: $MCP_PID)..."
        kill $MCP_PID 2>/dev/null || true
    fi

    # Kill any remaining Python processes
    pkill -f "mcp_server.server" 2>/dev/null || true

    print_success "Cleanup complete"
    exit 0
}

# Register cleanup function
trap cleanup EXIT INT TERM

# Start MCP server in background
print_info "Starting MCP server..."
python3 -m mcp_server.server \
    --host localhost \
    --port 8080 \
    --log-file "$LOG_FILE" \
    --log-level DEBUG &

MCP_PID=$!

# Wait for MCP server to start
sleep 2

# Check if MCP server is running
if ! ps -p $MCP_PID > /dev/null; then
    print_error "MCP server failed to start"
    exit 1
fi

print_success "MCP server started (PID: $MCP_PID)"

# Run main application
print_info "Starting autonomous development team..."
echo ""
echo "========================================================================"
echo "                     PROJECT EXECUTION STARTING                         "
echo "========================================================================"
echo ""

python3 main.py \
    --name "$PROJECT_NAME" \
    --requirements "$REQUIREMENTS_FILE" \
    --workers "$WORKER_COUNT" \
    --log-file "$LOG_FILE"

EXIT_CODE=$?

echo ""
echo "========================================================================"
echo "                     PROJECT EXECUTION COMPLETED                        "
echo "========================================================================"
echo ""

if [ $EXIT_CODE -eq 0 ]; then
    print_success "Project completed successfully!"
else
    print_error "Project failed with exit code: $EXIT_CODE"
fi

print_info "Logs saved to: $LOG_FILE"

# View logs
read -p "Would you like to view the logs? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    less "$LOG_FILE"
fi

exit $EXIT_CODE
