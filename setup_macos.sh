#!/bin/bash
# Ontogeny — macOS Setup Script
# Run: chmod +x setup_macos.sh && ./setup_macos.sh

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║       ONTOGENY — macOS Installer      ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# Check macOS version
echo -e "${YELLOW}[1/7] Checking macOS version...${NC}"
SW_VERS=$(sw_vers -productVersion)
MAJOR=$(echo "$SW_VERS" | cut -d. -f1)
if [ "$MAJOR" -lt 11 ]; then
    echo -e "${RED}⚠ macOS $SW_VERS detected. Ollama + Docker require macOS 11+${NC}"
    echo -e "${YELLOW}Proceeding anyway — some features may be limited${NC}"
fi
echo -e "${GREEN}✓ macOS $SW_VERS${NC}"

# Check/install Homebrew
echo -e "${YELLOW}[2/7] Checking Homebrew...${NC}"
if ! command -v brew &> /dev/null; then
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
    eval "$(/opt/homebrew/bin/brew shellenv)"
fi
echo -e "${GREEN}✓ Homebrew ready${NC}"

# Check/install Python
echo -e "${YELLOW}[3/7] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo "Installing Python..."
    brew install python@3.11
fi
PY_VERSION=$(python3 --version)
echo -e "${GREEN}✓ $PY_VERSION${NC}"

# Install Ollama
echo -e "${YELLOW}[4/7] Checking Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    echo "Installing Ollama..."
    brew install ollama
fi
echo -e "${GREEN}✓ Ollama ready${NC}"

# Pull llama3.2
echo -e "${YELLOW}[5/7] Pulling llama3.2 model...${NC}"
ollama pull llama3.2 2>/dev/null || echo -e "${YELLOW}⚠ Ollama not running — start it and run: ollama pull llama3.2${NC}"

# Check Docker
echo -e "${YELLOW}[6/7] Checking Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}⚠ Docker not found. Install from: https://docker.com/products/docker-desktop${NC}"
    echo -e "${YELLOW}  Code execution sandbox will be unavailable without Docker${NC}"
else
    echo -e "${GREEN}✓ Docker ready${NC}"
fi

# Setup project
echo -e "${YELLOW}[7/7] Setting up Ontogeny...${NC}"
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

# Copy .env if missing
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

echo ""
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo -e "${GREEN}  Ontogeny installed successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════${NC}"
echo ""
echo -e "  Start Ollama:  ${CYAN}ollama serve${NC}"
echo -e "  Run agent:     ${CYAN}source .venv/bin/activate && python -m crawler_agent.main${NC}"
echo -e "  Autonomous:    ${CYAN}source .venv/bin/activate && python -m crawler_agent.main --autonomous${NC}"
echo ""
