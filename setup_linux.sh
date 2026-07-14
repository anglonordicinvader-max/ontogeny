#!/bin/bash
# Ontogeny — Linux Setup Script
# Run: chmod +x setup_linux.sh && ./setup_linux.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║      ONTOGENY — Linux Installer       ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Detect distro
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
    echo -e "${YELLOW}[1/7] Detected: $PRETTY_NAME${NC}"
else
    DISTRO="unknown"
    echo -e "${YELLOW}[1/7] Unknown distro${NC}"
fi

# Check Python
echo -e "${YELLOW}[2/7] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing Python3..."
    case $DISTRO in
        ubuntu|debian) sudo apt update && sudo apt install -y python3 python3-pip python3-venv ;;
        fedora) sudo dnf install -y python3 python3-pip ;;
        arch) sudo pacman -S --noconfirm python python-pip ;;
        centos|rhel) sudo yum install -y python3 python3-pip ;;
        *) echo -e "${RED}Install Python 3.11+ manually${NC}" ;;
    esac
fi
PY_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PY_VERSION${NC}"

# Check/install Ollama
echo -e "${YELLOW}[3/7] Checking Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
echo -e "${GREEN}✓ Ollama ready${NC}"

# Pull model
echo -e "${YELLOW}[4/7] Pulling llama3.2 model...${NC}"
ollama pull llama3.2 2>/dev/null || echo -e "${YELLOW}⚠ Start Ollama first: ollama serve${NC}"

# Check Docker
echo -e "${YELLOW}[5/7] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    case $DISTRO in
        ubuntu|debian)
            sudo apt update
            sudo apt install -y docker.io
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            echo -e "${YELLOW}⚠ Log out and back in for docker group to take effect${NC}"
            ;;
        fedora)
            sudo dnf install -y docker
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            ;;
        arch)
            sudo pacman -S --noconfirm docker
            sudo systemctl enable docker
            sudo systemctl start docker
            sudo usermod -aG docker $USER
            ;;
        *)
            echo -e "${YELLOW}Install Docker manually: https://docs.docker.com/engine/install/${NC}"
            ;;
    esac
fi
echo -e "${GREEN}✓ Docker ready${NC}"

# Setup project
echo -e "${YELLOW}[6/7] Setting up Ontogeny...${NC}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi

source .venv/bin/activate
pip install -r requirements.txt 2>/dev/null || pip install -e . 2>/dev/null || {
    echo -e "${YELLOW}Installing from setup.py...${NC}"
    pip install -e .
}

# Create .env if missing
if [ ! -f ".env" ]; then
    cat > .env << 'EOF'
# Proxy Configuration
PROXY_ENABLED=true
PROXY_REQUIRED=true
PROXY_AUTO_REFRESH=true
PROXY_MIN_PROXIES=5
PROXY_REFRESH_INTERVAL=300
PROXY_FETCH_FREE_PROXIES=true
PROXY_ROTATE_EVERY=10
PROXY_MAX_FAILURES=3
PROXY_HEALTH_CHECK_INTERVAL=300

# Crawler Settings
CRAWLER_REQUESTS_PER_SECOND=5.0
CRAWLER_BURST_SIZE=25
CRAWLER_MIN_DELAY=1.0
CRAWLER_MAX_DELAY=3.0

# API Keys (optional)
GITHUB_TOKEN=
HUGGINGFACE_TOKEN=

# LLM Settings (Ollama)
LLM_API_KEY=ollama
LLM_MODEL=llama3.2
LLM_API_BASE=http://localhost:11434/v1

# Storage
STORAGE_DATABASE_URL=sqlite+aiosqlite:///./crawler.db
STORAGE_STATE_PATH=./data/agent_state.json
EOF
    echo -e "${GREEN}✓ Created .env${NC}"
fi

# Create data directory
mkdir -p data

echo -e "${YELLOW}[7/7] Starting Ollama in background...${NC}"
pgrep -x "ollama" > /dev/null || ollama serve &>/dev/null &
sleep 2

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Ontogeny installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Start Ollama:  ${CYAN}ollama serve${NC}"
echo -e "  Run agent:     ${CYAN}source .venv/bin/activate && python -m crawler_agent.main${NC}"
echo -e "  Autonomous:    ${CYAN}source .venv/bin/activate && python -m crawler_agent.main --autonomous${NC}"
echo ""
