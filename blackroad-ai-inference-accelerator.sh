#!/bin/bash
# BlackRoad AI Inference Accelerator
# Main CLI entry point

set -e

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors (BlackRoad brand)
HOT_PINK='\033[38;2;255;29;108m'
AMBER='\033[38;2;245;166;35m'
BLUE='\033[38;2;41;121;255m'
VIOLET='\033[38;2;156;39;176m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

print_banner() {
    echo -e "${HOT_PINK}"
    echo "  ____  _            _    ____                 _ "
    echo " | __ )| | __ _  ___| | _|  _ \ ___   __ _  __| |"
    echo " |  _ \| |/ _\` |/ __| |/ / |_) / _ \ / _\` |/ _\` |"
    echo " | |_) | | (_| | (__|   <|  _ < (_) | (_| | (_| |"
    echo " |____/|_|\__,_|\___|_|\_\_| \_\___/ \__,_|\__,_|"
    echo -e "${NC}"
    echo -e "${AMBER}AI Inference Accelerator v${VERSION}${NC}"
    echo ""
}

print_help() {
    print_banner
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  init            Initialize the accelerator environment"
    echo "  serve           Start inference server"
    echo "  optimize        Optimize a model for inference"
    echo "  validate        Validate all endpoints"
    echo "  sync            Synchronize state across platforms"
    echo "  health          Check system health"
    echo "  kanban          Manage kanban board"
    echo "  hash            Compute SHA-256/Infinity hash"
    echo "  help            Show this help message"
    echo ""
    echo "Options:"
    echo "  --port PORT     Server port (default: 8080)"
    echo "  --model MODEL   Model to use"
    echo "  --all           Apply to all endpoints/platforms"
    echo "  --force         Force operation"
    echo "  --json          Output as JSON"
    echo "  -v, --verbose   Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 serve --port 8080"
    echo "  $0 validate --all"
    echo "  $0 sync --source salesforce --targets cloudflare,github"
    echo "  $0 hash --file config/endpoints.yaml"
    echo ""
}

cmd_init() {
    print_banner
    echo -e "${BLUE}Initializing BlackRoad AI Inference Accelerator...${NC}"

    # Check Python
    if command -v python3 &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} Python 3 found"
    else
        echo -e "${RED}[FAIL]${NC} Python 3 not found"
        exit 1
    fi

    # Check pip
    if command -v pip3 &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} pip3 found"
    else
        echo -e "${RED}[FAIL]${NC} pip3 not found"
        exit 1
    fi

    # Install dependencies
    echo -e "${AMBER}Installing dependencies...${NC}"
    pip3 install -r "${SCRIPT_DIR}/requirements.txt" --quiet

    # Create state directory
    mkdir -p "${SCRIPT_DIR}/.blackroad/state"

    # Check for .env
    if [ ! -f "${SCRIPT_DIR}/.env" ]; then
        echo -e "${AMBER}[WARN]${NC} No .env file found. Copy .env.example and configure."
    fi

    echo -e "${GREEN}Initialization complete!${NC}"
}

cmd_serve() {
    local port=8080

    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                port="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    print_banner
    echo -e "${BLUE}Starting inference server on port ${port}...${NC}"
    echo -e "${AMBER}Server functionality coming soon.${NC}"
    echo ""
    echo "For now, use:"
    echo "  python3 -m src.endpoints.client"
}

cmd_validate() {
    print_banner
    echo -e "${BLUE}Validating endpoints...${NC}"
    python3 "${SCRIPT_DIR}/scripts/validate_endpoints.py" "$@"
}

cmd_sync() {
    print_banner
    echo -e "${BLUE}Synchronizing state...${NC}"
    python3 "${SCRIPT_DIR}/scripts/sync_state.py" "$@"
}

cmd_health() {
    print_banner
    echo -e "${BLUE}Checking system health...${NC}"
    echo ""

    # Check endpoints
    echo "Endpoint Health:"
    python3 "${SCRIPT_DIR}/scripts/validate_endpoints.py" --all --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for name, ep in data.get('endpoints', {}).items():
        status = 'OK' if ep.get('healthy') else 'FAIL'
        print(f'  [{status}] {name}')
except:
    print('  Unable to check endpoints')
"

    # Check state sync
    echo ""
    echo "Platform Health:"
    python3 "${SCRIPT_DIR}/scripts/sync_state.py" --health --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for platform, healthy in data.get('platforms', {}).items():
        status = 'OK' if healthy else 'FAIL'
        print(f'  [{status}] {platform}')
except:
    print('  Unable to check platforms')
"
}

cmd_kanban() {
    print_banner
    echo -e "${BLUE}Kanban Board Manager${NC}"

    case "${1:-list}" in
        list)
            echo "Kanban commands:"
            echo "  init-task   - Initialize a new task"
            echo "  summary     - Show board summary"
            ;;
        init-task)
            shift
            python3 "${SCRIPT_DIR}/scripts/init_task.py" "$@"
            ;;
        summary)
            python3 -c "
from src.kanban.board import KanbanBoard
board = KanbanBoard()
summary = board.get_board_summary()
print(f'Board: {summary.get(\"board_name\", \"Main\")}')
print(f'Total Cards: {summary.get(\"total_cards\", 0)}')
for col in summary.get('columns', []):
    print(f'  {col[\"name\"]}: {col[\"card_count\"]} cards')
"
            ;;
        *)
            echo "Unknown kanban command: $1"
            ;;
    esac
}

cmd_hash() {
    local file=""
    local data=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --file|-f)
                file="$2"
                shift 2
                ;;
            --data|-d)
                data="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ -n "$file" ]; then
        python3 -c "
from src.hashing.sha_infinity import sha256_hash_file, SHAInfinity
import json

# SHA-256
sha = sha256_hash_file('$file')
print(f'SHA-256: {sha}')

# SHA-Infinity
hasher = SHAInfinity()
with open('$file', 'r') as f:
    content = f.read()
hasher.add_node(content)
infinity = hasher.compute_infinity_hash()
print(f'SHA-INF: {infinity}')
"
    elif [ -n "$data" ]; then
        python3 -c "
from src.hashing.sha_infinity import sha256_hash, SHAInfinity

# SHA-256
sha = sha256_hash('$data')
print(f'SHA-256: {sha}')

# SHA-Infinity
hasher = SHAInfinity()
hasher.add_node('$data')
infinity = hasher.compute_infinity_hash()
print(f'SHA-INF: {infinity}')
"
    else
        echo "Usage: $0 hash --file <path> or --data <string>"
    fi
}

# Main command router
case "${1:-help}" in
    init)
        shift
        cmd_init "$@"
        ;;
    serve)
        shift
        cmd_serve "$@"
        ;;
    optimize)
        print_banner
        echo -e "${AMBER}Model optimization coming soon.${NC}"
        ;;
    validate)
        shift
        cmd_validate "$@"
        ;;
    sync)
        shift
        cmd_sync "$@"
        ;;
    health)
        shift
        cmd_health "$@"
        ;;
    kanban)
        shift
        cmd_kanban "$@"
        ;;
    hash)
        shift
        cmd_hash "$@"
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo "Unknown command: $1"
        print_help
        exit 1
        ;;
esac
