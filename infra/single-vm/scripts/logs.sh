#!/bin/bash
# =============================================================================
# logs.sh - Log Viewer Script
# =============================================================================
# Usage:
#   ./logs.sh              # All services
#   ./logs.sh backend      # Specific service
#   ./logs.sh -f           # Follow mode
#   ./logs.sh backend -f   # Follow specific service
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if sudo is needed for docker
if [ "$EUID" -ne 0 ] && ! groups | grep -q "\bdocker\b"; then
    DOCKER="sudo docker"
else
    DOCKER="docker"
fi

cd "$INFRA_DIR"

# Parse arguments
SERVICE=""
FOLLOW=""
TAIL="100"

while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--follow)
            FOLLOW="-f"
            shift
            ;;
        -n|--tail)
            TAIL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [SERVICE] [OPTIONS]"
            echo ""
            echo "Services: backend, frontend, caddy, postgres"
            echo ""
            echo "Options:"
            echo "  -f, --follow    Follow log output"
            echo "  -n, --tail N    Show last N lines (default: 100)"
            echo "  -h, --help      Show this help"
            exit 0
            ;;
        *)
            SERVICE="$1"
            shift
            ;;
    esac
done

# Build command
CMD="$DOCKER compose logs --tail=$TAIL"

if [ -n "$FOLLOW" ]; then
    CMD="$CMD $FOLLOW"
fi

if [ -n "$SERVICE" ]; then
    CMD="$CMD $SERVICE"
fi

# Run
exec $CMD
