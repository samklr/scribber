#!/bin/bash
# =============================================================================
# status.sh - Service Status Script
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if sudo is needed for docker
if [ "$EUID" -ne 0 ] && ! groups | grep -q "\bdocker\b"; then
    DOCKER="sudo docker"
else
    DOCKER="docker"
fi

# Load environment
if [ -f "$INFRA_DIR/.env" ]; then
    set -a
    source "$INFRA_DIR/.env"
    set +a
fi

echo ""
echo "============================================================================="
echo "  Project Template - Service Status"
echo "============================================================================="
echo ""

cd "$INFRA_DIR"

# Show container status
echo -e "${BLUE}Container Status:${NC}"
echo ""
$DOCKER compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

echo ""

# Health checks
echo -e "${BLUE}Health Checks:${NC}"
echo ""

check_health() {
    local name=$1
    local url=$2

    if curl -sf "$url" &>/dev/null; then
        echo -e "   ${GREEN}OK${NC} $name"
    else
        echo -e "   ${RED}FAIL${NC} $name"
    fi
}

check_health "Backend API" "http://localhost:8000/health/live"
check_health "Frontend" "http://localhost/"

if [ "$DATABASE_MODE" = "local" ]; then
    echo -n "   "
    if $DOCKER exec app-postgres pg_isready -U "${POSTGRES_USER:-appuser}" >/dev/null 2>&1; then
        echo -e "${GREEN}OK${NC} PostgreSQL"
    else
        echo -e "${RED}FAIL${NC} PostgreSQL"
    fi
fi

echo ""

# Resource usage
echo -e "${BLUE}Resource Usage:${NC}"
echo ""
$DOCKER stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" 2>/dev/null | head -10

echo ""
