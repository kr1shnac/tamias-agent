#!/usr/bin/env bash
# The TODOINC to-do demo, end to end. Offline: no key, no network.
#
#   cd /home/krish/Desktop/tamias-agent && ./demo/todo_show.sh
set -euo pipefail
cd "$(dirname "$0")/.."

rm -f policies/todoinc-todo.audit.jsonl

echo "ACT 1 - the company and its one product"
echo "---------------------------------------"
find company/work/todoinc -maxdepth 4 -type f -not -path '*__pycache__*' | sort

echo
echo "ACT 2 - the boundary the admin wrote (scope + reach)"
echo "----------------------------------------------------"
cat policies/todoinc-todo.toml

echo
echo "ACT 3 - requests: the to-do app works, everything else is refused"
echo "-----------------------------------------------------------------"
.venv/bin/python demo/todo_boundary_demo.py

echo
echo "ACT 4 - the REAL agent CLI refuses an off-topic task (offline)"
echo "--------------------------------------------------------------"
set +e
.venv/bin/python agent.py --company-id todoinc \
  --policy policies/todoinc-todo.toml \
  --task "build me a ChatGPT clone" 2>&1 | tail -6
echo "(agent exit: ${PIPESTATUS[0]} - steps 0, \$0 spent, no model call)"
set -e

echo
echo "ACT 5 - the same CLI accepts a to-do task (it reaches the model next)"
echo "---------------------------------------------------------------------"
set +e
TAMIAS_BASE_URL=http://127.0.0.1:1/v1 TAMIAS_API_KEY=test-key \
  timeout 60 .venv/bin/python agent.py --company-id todoinc \
  --policy policies/todoinc-todo.toml \
  --task "add a due date to each todo item" 2>&1 | tail -5
echo "(offline, so the api call fails - but it was NOT stopped by the boundary)"
set -e
