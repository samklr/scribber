#!/bin/bash
# =============================================================================
# manage.sh - Service Management Script
# =============================================================================
# Usage: ./manage.sh <command>
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Detect sudo need
needs_sudo() {
    if [ "$(id -u)" -eq 0 ]; then
        echo ""
    elif groups | grep -q docker; then
        echo ""
    else
        echo "sudo"
    fi
}

DOCKER_CMD="$(needs_sudo) docker"
COMPOSE_CMD="$(needs_sudo) docker compose"

# Load environment
if [ -f "$INFRA_DIR/.env" ]; then
    set -a
    source "$INFRA_DIR/.env"
    set +a
fi

# =============================================================================
# Commands
# =============================================================================

cmd_status() {
    echo -e "${BLUE}=== Service Status ===${NC}"
    cd "$INFRA_DIR"
    $COMPOSE_CMD ps
}

cmd_logs() {
    local service="${1:-}"
    cd "$INFRA_DIR"
    if [ -n "$service" ]; then
        $COMPOSE_CMD logs -f "$service"
    else
        $COMPOSE_CMD logs -f
    fi
}

cmd_logs_backend() {
    cmd_logs backend
}

cmd_logs_frontend() {
    cmd_logs frontend
}

cmd_logs_caddy() {
    cmd_logs caddy
}

cmd_logs_db() {
    if [ "$DATABASE_MODE" = "local" ]; then
        cmd_logs postgres
    else
        echo -e "${YELLOW}Database is in remote mode. Check your database provider's logs.${NC}"
    fi
}

cmd_start() {
    echo -e "${BLUE}Starting services...${NC}"
    cd "$INFRA_DIR"
    if [ "$DATABASE_MODE" = "local" ]; then
        $COMPOSE_CMD --profile local-db up -d
    else
        $COMPOSE_CMD up -d
    fi
    echo -e "${GREEN}Services started${NC}"
}

cmd_stop() {
    echo -e "${BLUE}Stopping services...${NC}"
    cd "$INFRA_DIR"
    $COMPOSE_CMD --profile local-db down
    echo -e "${GREEN}Services stopped${NC}"
}

cmd_restart() {
    echo -e "${BLUE}Restarting all services...${NC}"
    cmd_stop
    cmd_start
}

cmd_restart_backend() {
    echo -e "${BLUE}Restarting backend...${NC}"
    cd "$INFRA_DIR"
    $COMPOSE_CMD restart backend
    echo -e "${GREEN}Backend restarted${NC}"
}

cmd_restart_frontend() {
    echo -e "${BLUE}Restarting frontend...${NC}"
    cd "$INFRA_DIR"
    $COMPOSE_CMD restart frontend
    echo -e "${GREEN}Frontend restarted${NC}"
}

cmd_update() {
    echo -e "${BLUE}Updating application...${NC}"
    cd "$INFRA_DIR/../.."

    # Pull latest code
    echo "Pulling latest code..."
    git pull

    # Rebuild and restart
    cd "$INFRA_DIR"
    echo "Rebuilding images..."
    $COMPOSE_CMD build --no-cache

    echo "Restarting services..."
    cmd_restart

    echo -e "${GREEN}Update complete${NC}"
}

cmd_backup() {
    if [ "$DATABASE_MODE" != "local" ]; then
        echo -e "${YELLOW}Database is in remote mode. Use your database provider's backup tools.${NC}"
        return 1
    fi

    echo -e "${BLUE}Creating database backup...${NC}"
    cd "$INFRA_DIR"

    # Create backup directory
    mkdir -p backups

    # Generate backup filename with timestamp
    BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).sql.gz"

    # Create backup
    $DOCKER_CMD exec app-postgres pg_dump -U "${POSTGRES_USER:-appuser}" "${POSTGRES_DB:-app_db}" | gzip > "$BACKUP_FILE"

    echo -e "${GREEN}Backup created: $BACKUP_FILE${NC}"

    # Show backup size
    ls -lh "$BACKUP_FILE"

    # List recent backups
    echo ""
    echo "Recent backups:"
    ls -lt backups/*.sql.gz 2>/dev/null | head -5
}

cmd_restore() {
    if [ "$DATABASE_MODE" != "local" ]; then
        echo -e "${YELLOW}Database is in remote mode. Use your database provider's restore tools.${NC}"
        return 1
    fi

    echo -e "${BLUE}Available backups:${NC}"
    ls -lt "$INFRA_DIR/backups"/*.sql.gz 2>/dev/null || {
        echo -e "${RED}No backups found in backups/ directory${NC}"
        return 1
    }

    echo ""
    read -p "Enter backup filename to restore: " BACKUP_FILE

    if [ ! -f "$INFRA_DIR/backups/$BACKUP_FILE" ]; then
        echo -e "${RED}Backup file not found: $BACKUP_FILE${NC}"
        return 1
    fi

    echo -e "${YELLOW}WARNING: This will replace all data in the database!${NC}"
    read -p "Are you sure? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Restore cancelled."
        return 0
    fi

    echo "Restoring database..."
    cd "$INFRA_DIR"
    gunzip -c "backups/$BACKUP_FILE" | $DOCKER_CMD exec -i app-postgres psql -U "${POSTGRES_USER:-appuser}" "${POSTGRES_DB:-app_db}"

    echo -e "${GREEN}Database restored from $BACKUP_FILE${NC}"
}

cmd_shell_db() {
    if [ "$DATABASE_MODE" != "local" ]; then
        echo -e "${YELLOW}Database is in remote mode. Use your database provider's tools.${NC}"
        return 1
    fi

    echo -e "${BLUE}Connecting to PostgreSQL...${NC}"
    $DOCKER_CMD exec -it app-postgres psql -U "${POSTGRES_USER:-appuser}" "${POSTGRES_DB:-app_db}"
}

cmd_shell_backend() {
    echo -e "${BLUE}Connecting to backend container...${NC}"
    $DOCKER_CMD exec -it app-backend /bin/bash
}

cmd_stats() {
    echo -e "${BLUE}=== Container Resource Usage ===${NC}"
    $DOCKER_CMD stats --no-stream app-backend app-frontend app-caddy app-postgres 2>/dev/null || \
    $DOCKER_CMD stats --no-stream
}

cmd_health() {
    echo -e "${BLUE}=== Health Checks ===${NC}"
    echo ""

    # PostgreSQL
    if [ "$DATABASE_MODE" = "local" ]; then
        echo -n "PostgreSQL: "
        if $DOCKER_CMD exec app-postgres pg_isready -U "${POSTGRES_USER:-appuser}" >/dev/null 2>&1; then
            echo -e "${GREEN}HEALTHY${NC}"
        else
            echo -e "${RED}UNHEALTHY${NC}"
        fi
    else
        echo "PostgreSQL: REMOTE (not checked)"
    fi

    # Backend
    echo -n "Backend:    "
    if curl -sf http://localhost:8000/health/live >/dev/null 2>&1 || \
       $DOCKER_CMD exec app-backend curl -sf http://localhost:8000/health/live >/dev/null 2>&1; then
        echo -e "${GREEN}HEALTHY${NC}"
    else
        echo -e "${RED}UNHEALTHY${NC}"
    fi

    # Frontend
    echo -n "Frontend:   "
    if $DOCKER_CMD exec app-frontend wget -q --spider http://localhost/ 2>/dev/null; then
        echo -e "${GREEN}HEALTHY${NC}"
    else
        echo -e "${RED}UNHEALTHY${NC}"
    fi

    # Caddy
    echo -n "Caddy:      "
    if curl -sf http://localhost/ >/dev/null 2>&1; then
        echo -e "${GREEN}HEALTHY${NC}"
    else
        echo -e "${RED}UNHEALTHY${NC}"
    fi

    echo ""
}

cmd_clean() {
    echo -e "${YELLOW}WARNING: This will remove all containers, images, and volumes!${NC}"
    read -p "Are you sure? (yes/no): " CONFIRM

    if [ "$CONFIRM" != "yes" ]; then
        echo "Clean cancelled."
        return 0
    fi

    echo -e "${BLUE}Cleaning up...${NC}"
    cd "$INFRA_DIR"

    # Stop and remove containers
    $COMPOSE_CMD --profile local-db down -v --rmi local

    echo -e "${GREEN}Cleanup complete${NC}"
}

cmd_help() {
    echo -e "${CYAN}=============================================================================${NC}"
    echo -e "${CYAN}Project Template - Service Management${NC}"
    echo -e "${CYAN}=============================================================================${NC}"
    echo ""
    echo "Usage: ./manage.sh <command>"
    echo ""
    echo -e "${BLUE}Service Control:${NC}"
    echo "  status            Show service status"
    echo "  start             Start all services"
    echo "  stop              Stop all services"
    echo "  restart           Restart all services"
    echo "  restart-backend   Restart backend only"
    echo "  restart-frontend  Restart frontend only"
    echo "  update            Pull code, rebuild, and restart"
    echo ""
    echo -e "${BLUE}Logs:${NC}"
    echo "  logs              Follow all logs"
    echo "  logs-backend      Follow backend logs"
    echo "  logs-frontend     Follow frontend logs"
    echo "  logs-caddy        Follow Caddy logs"
    echo "  logs-db           Follow database logs (local mode only)"
    echo ""
    echo -e "${BLUE}Database (local mode only):${NC}"
    echo "  backup            Create database backup"
    echo "  restore           Restore from backup"
    echo "  shell-db          Open PostgreSQL shell"
    echo ""
    echo -e "${BLUE}Debugging:${NC}"
    echo "  shell-backend     Open shell in backend container"
    echo "  stats             Show resource usage"
    echo "  health            Check service health"
    echo ""
    echo -e "${BLUE}Maintenance:${NC}"
    echo "  clean             Remove all containers and volumes"
    echo ""
    echo -e "${YELLOW}Current DATABASE_MODE: ${DATABASE_MODE:-local}${NC}"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

case "${1:-help}" in
    status)           cmd_status ;;
    logs)             cmd_logs "${2:-}" ;;
    logs-backend)     cmd_logs_backend ;;
    logs-frontend)    cmd_logs_frontend ;;
    logs-caddy)       cmd_logs_caddy ;;
    logs-db)          cmd_logs_db ;;
    start)            cmd_start ;;
    stop)             cmd_stop ;;
    restart)          cmd_restart ;;
    restart-backend)  cmd_restart_backend ;;
    restart-frontend) cmd_restart_frontend ;;
    update)           cmd_update ;;
    backup)           cmd_backup ;;
    restore)          cmd_restore ;;
    shell-db)         cmd_shell_db ;;
    shell-backend)    cmd_shell_backend ;;
    stats)            cmd_stats ;;
    health)           cmd_health ;;
    clean)            cmd_clean ;;
    help|--help|-h)   cmd_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
