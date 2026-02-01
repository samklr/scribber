#!/bin/bash
# =============================================================================
# install-docker.sh - Docker Installation Script
# =============================================================================
# Installs Docker and Docker Compose on Ubuntu/Debian
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo ./install-docker.sh)"
    exit 1
fi

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    log_error "Cannot detect OS"
    exit 1
fi

log_info "Detected OS: $OS"

# Install Docker based on OS
case $OS in
    ubuntu|debian)
        log_info "Installing Docker for $OS..."

        # Remove old versions
        apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

        # Install prerequisites
        apt-get update
        apt-get install -y \
            ca-certificates \
            curl \
            gnupg \
            lsb-release

        # Add Docker's official GPG key
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/$OS/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg

        # Set up repository
        echo \
            "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/$OS \
            $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

        # Install Docker
        apt-get update
        apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        ;;
    centos|rhel|fedora)
        log_info "Installing Docker for $OS..."

        # Remove old versions
        yum remove -y docker docker-client docker-client-latest docker-common docker-latest docker-latest-logrotate docker-logrotate docker-engine 2>/dev/null || true

        # Install prerequisites
        yum install -y yum-utils

        # Add Docker repository
        yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

        # Install Docker
        yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

        ;;
    *)
        log_error "Unsupported OS: $OS"
        log_info "Please install Docker manually: https://docs.docker.com/engine/install/"
        exit 1
        ;;
esac

# Start and enable Docker
log_info "Starting Docker service..."
systemctl start docker
systemctl enable docker

# Add current user to docker group
SUDO_USER_NAME="${SUDO_USER:-$USER}"
if [ "$SUDO_USER_NAME" != "root" ]; then
    log_info "Adding $SUDO_USER_NAME to docker group..."
    usermod -aG docker "$SUDO_USER_NAME"
    log_info "Log out and back in for group changes to take effect"
fi

# Verify installation
log_info "Verifying installation..."
docker --version
docker compose version

log_success "Docker installed successfully!"
echo ""
echo "Next steps:"
echo "  1. Log out and back in (for docker group to take effect)"
echo "  2. Run: docker run hello-world"
echo "  3. Configure your .env file"
echo "  4. Run: ./deploy.sh"
