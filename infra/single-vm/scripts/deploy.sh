#!/bin/bash
# =============================================================================
# deploy.sh - Single VM Deployment Script
# =============================================================================
# Automated deployment for Docker-based infrastructure
#
# Usage:
#   ./deploy.sh              # Standard deployment
#   ./deploy.sh --build      # Force rebuild images
#   ./deploy.sh --no-pull    # Skip pulling base images
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_ROOT="$(cd "$INFRA_DIR/../.." && pwd)"

# =============================================================================
# Helper Functions
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Detect if we need sudo for docker
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

# =============================================================================
# Configuration
# =============================================================================

BUILD=false
PULL=true

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --build)
            BUILD=true
            shift
            ;;
        --no-pull)
            PULL=false
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --build       Force rebuild of Docker images"
            echo "  --no-pull     Don't pull latest base images"
            echo "  -h, --help    Show this help message"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# Prerequisites Check
# =============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command_exists docker; then
        log_error "Docker is not installed. Install Docker first."
        exit 1
    fi
    log_success "Docker found: $(docker --version)"

    # Check Docker Compose
    if ! docker compose version >/dev/null 2>&1; then
        log_error "Docker Compose is not installed or not available as plugin."
        exit 1
    fi
    log_success "Docker Compose found: $(docker compose version --short)"

    # Check if Docker daemon is running
    if ! $DOCKER_CMD info >/dev/null 2>&1; then
        log_error "Docker daemon is not running. Start it with: sudo systemctl start docker"
        exit 1
    fi
    log_success "Docker daemon is running"
}

# =============================================================================
# Environment Configuration
# =============================================================================

setup_environment() {
    log_info "Setting up environment configuration..."

    cd "$INFRA_DIR"

    # Create .env if it doesn't exist
    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            log_warning "Created .env from .env.example"
            log_warning "Please edit .env with your configuration before continuing."
            log_info "Required configurations:"
            echo "  - SECRET_KEY: Generate with 'openssl rand -base64 64'"
            echo "  - POSTGRES_PASSWORD: Set a secure password"
            echo "  - DOMAIN_NAME: Set your domain for SSL"
            read -p "Press Enter to edit .env now, or Ctrl+C to exit..."
            ${EDITOR:-nano} .env
        else
            log_error ".env.example not found. Cannot create configuration."
            exit 1
        fi
    fi

    # Load environment
    set -a
    source .env
    set +a

    # Validate required variables
    if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "CHANGE_ME_GENERATE_WITH_OPENSSL" ]; then
        log_error "SECRET_KEY is not set or uses default value."
        log_info "Generate one with: openssl rand -base64 64"
        exit 1
    fi

    if [ "$DATABASE_MODE" = "local" ]; then
        if [ -z "$POSTGRES_PASSWORD" ] || [ "$POSTGRES_PASSWORD" = "CHANGE_ME_SECURE_PASSWORD" ]; then
            log_error "POSTGRES_PASSWORD is not set or uses default value."
            exit 1
        fi
    fi

    log_success "Environment configuration validated"
}

# =============================================================================
# Pull Base Images
# =============================================================================

pull_images() {
    if [ "$PULL" = true ]; then
        log_info "Pulling latest base images..."

        $DOCKER_CMD pull postgres:16-alpine
        $DOCKER_CMD pull caddy:2-alpine
        $DOCKER_CMD pull python:3.12-slim
        $DOCKER_CMD pull node:20-alpine

        log_success "Base images updated"
    else
        log_warning "Skipping image pull (--no-pull flag set)"
    fi
}

# =============================================================================
# Build and Deploy
# =============================================================================

build_images() {
    log_info "Building Docker images..."
    cd "$INFRA_DIR"

    BUILD_ARGS=""
    if [ "$BUILD" = true ]; then
        BUILD_ARGS="--no-cache"
        log_info "Full rebuild requested..."
    fi

    $COMPOSE_CMD build $BUILD_ARGS

    log_success "Docker images built successfully"
}

start_services() {
    log_info "Starting services..."
    cd "$INFRA_DIR"

    # Determine profile based on DATABASE_MODE
    if [ "$DATABASE_MODE" = "local" ]; then
        log_info "Starting with local PostgreSQL database..."
        $COMPOSE_CMD --profile local-db up -d
    else
        log_info "Starting with remote database..."
        $COMPOSE_CMD up -d
    fi

    log_success "Services started"
}

# =============================================================================
# Health Checks
# =============================================================================

wait_for_services() {
    log_info "Waiting for services to be healthy..."

    # Wait for PostgreSQL (if local)
    if [ "$DATABASE_MODE" = "local" ]; then
        log_info "Waiting for PostgreSQL..."
        local retries=30
        while [ $retries -gt 0 ]; do
            if $DOCKER_CMD exec app-postgres pg_isready -U "${POSTGRES_USER:-appuser}" >/dev/null 2>&1; then
                log_success "PostgreSQL is ready"
                break
            fi
            retries=$((retries - 1))
            sleep 2
        done
        if [ $retries -eq 0 ]; then
            log_error "PostgreSQL failed to start"
            exit 1
        fi
    fi

    # Wait for Backend
    log_info "Waiting for Backend..."
    local retries=60
    while [ $retries -gt 0 ]; do
        if curl -sf http://localhost:8000/health/live >/dev/null 2>&1 || \
           $DOCKER_CMD exec app-backend curl -sf http://localhost:8000/health/live >/dev/null 2>&1; then
            log_success "Backend is ready"
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done
    if [ $retries -eq 0 ]; then
        log_warning "Backend health check timed out - checking logs..."
        $COMPOSE_CMD logs --tail=50 backend
    fi

    # Wait for Caddy
    log_info "Waiting for Caddy..."
    local retries=30
    while [ $retries -gt 0 ]; do
        if curl -sf http://localhost/ >/dev/null 2>&1; then
            log_success "Caddy is ready"
            break
        fi
        retries=$((retries - 1))
        sleep 2
    done
    if [ $retries -eq 0 ]; then
        log_warning "Caddy health check timed out - checking logs..."
        $COMPOSE_CMD logs --tail=20 caddy
    fi
}

# =============================================================================
# Deployment Summary
# =============================================================================

print_summary() {
    echo ""
    echo "============================================================================="
    echo -e "${GREEN}DEPLOYMENT COMPLETE${NC}"
    echo "============================================================================="
    echo ""
    echo "Access Points:"
    if [ "$DOMAIN_NAME" = "localhost" ]; then
        echo "  - Application: http://localhost"
        echo "  - API: http://localhost/api/v1"
        echo "  - API Docs: http://localhost/docs"
    else
        echo "  - Application: https://$DOMAIN_NAME"
        echo "  - API: https://$DOMAIN_NAME/api/v1"
        echo "  - API Docs: https://$DOMAIN_NAME/docs"
    fi
    echo ""
    echo "Database:"
    if [ "$DATABASE_MODE" = "local" ]; then
        echo "  - Mode: Local PostgreSQL (Docker)"
        echo "  - Host: postgres:5432 (internal)"
    else
        echo "  - Mode: Remote database"
    fi
    echo ""
    echo "Useful Commands:"
    echo "  ./scripts/manage.sh status    - View service status"
    echo "  ./scripts/manage.sh logs      - View all logs"
    echo "  ./scripts/manage.sh health    - Check service health"
    echo "  ./scripts/manage.sh backup    - Backup database"
    echo ""
    echo "============================================================================="
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo "============================================================================="
    echo "Project Template - Deployment Script"
    echo "============================================================================="
    echo ""

    check_prerequisites
    setup_environment
    pull_images
    build_images
    start_services
    wait_for_services
    print_summary
}

main "$@"
