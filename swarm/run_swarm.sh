#!/bin/bash
# GSTD Swarm Client — запуск участника роя на Linux
# Использование:
#   export GSTD_API_KEY="your_key"
#   export GSTD_WALLET="EQ..."
#   ./run_swarm.sh
#
# Или: ./run_swarm.sh --api-key KEY --wallet EQ...

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Проверка Python
if ! command -v python3 &>/dev/null; then
    echo "Python 3 required. Install: apt install python3 python3-pip"
    exit 1
fi

# Создание venv если нет
VENV="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV" ]; then
    echo "[*] Creating virtual environment..."
    python3 -m venv "$VENV"
fi
source "$VENV/bin/activate"

# Установка зависимостей
pip install -q requests websocket-client 2>/dev/null || true

# Запуск
exec python3 swarm_client.py "$@"
