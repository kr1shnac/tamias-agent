#!/usr/bin/env bash
# Run agent.py against the local mock model (demo/mock_provider.py), so the
# agent's own loop can be shown when the real provider is unavailable.
#
#   ./demo/mock_act.sh --company-id todoinc \
#       --policy policies/todoinc-todo.toml --task "create todo in desktop"
#
# With no --task on an interactive terminal this launches the TUI.
#
# Say in a demo that the model is a mock. It is not a live run.
set -euo pipefail

cd "$(dirname "$0")/.."

PORT="${MOCK_PORT:-8099}"
PY=".venv/bin/python"

"$PY" demo/mock_provider.py --port "$PORT" &
MOCK_PID=$!
trap 'kill "$MOCK_PID" 2>/dev/null || true' EXIT

# wait for the port (no curl dependency)
for _ in $(seq 1 50); do
    if (exec 3<>"/dev/tcp/127.0.0.1/$PORT") 2>/dev/null; then
        exec 3>&- 2>/dev/null || true
        break
    fi
    sleep 0.1
done

TAMIAS_BASE_URL="http://127.0.0.1:$PORT/v1" TAMIAS_API_KEY=mock \
    "$PY" agent.py "$@"
