#!/bin/bash
# Ontogeny — macOS Launcher
# Run: ./run_macos.sh

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# Activate venv
if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo -e "${YELLOW}No .venv found. Run setup_macos.sh first.${NC}"
    exit 1
fi

# Start Ollama if not running
if ! pgrep -x "ollama" > /dev/null; then
    echo -e "${YELLOW}Starting Ollama...${NC}"
    ollama serve &>/dev/null &
    sleep 3
fi

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║         ONTOGENY v1.0                 ║"
echo "  ║    Proto-AGI Cognitive Agent          ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"
echo -e "  ${GREEN}1${NC} - Interactive mode"
echo -e "  ${GREEN}2${NC} - Autonomous mode (infinite)"
echo -e "  ${GREEN}3${NC} - Demo mode"
echo -e "  ${RED}q${NC} - Quit"
echo ""
read -p "mode> " choice

case $choice in
    1) python -m crawler_agent.main --interactive ;;
    2) python -m crawler_agent.main --autonomous ;;
    3) python -m crawler_agent.main --demo ;;
    q) exit 0 ;;
    *) python -m crawler_agent.main ;;
esac
