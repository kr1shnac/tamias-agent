#!/usr/bin/env bash
# One-command demo of the Tamias agent boundary with model/reasoning showcase. Offline: no key, no network.
#
#   cd /home/krish/Desktop/tamias-agent && ./demo/show.sh
set -euo pipefail
cd "$(dirname "$0")/.."

rm -f policies/acme-codefix.audit.jsonl policies/todoinc-todo.audit.jsonl

echo "====================================================================="
echo "  TAMIAS ENHANCED BOUNDARY DEMO – Showcasing the agentic part inside Tamias"
echo "====================================================================="
echo

echo "ACT 1 – The company boundary the admin wrote"
echo "--------------------------------------------"
cat policies/acme-codefix.toml

echo
echo "ACT 2 – The areas the agent can reach"
echo "-------------------------------------"
find company/work/acme -maxdepth 4 -type f | sort

echo
echo "ACT 3 – Model switching and reasoning level display"
echo "----------------------------------------------------"
.venv/bin/python -c "
import os, sys
sys.path.insert(0, '/home/krish/Desktop/tamias-agent')
import agent
model = getattr(agent, 'MODEL', 'nvidia/nemotron-3.5-lightning:free')
effort = os.environ.get('AGENT_EFFORT_POLICY', 'auto')
print(f'Current model: {model}')
print(f'Current effort: {effort}')
print(f'Model chip: ● ⟨ {model} · {effort} ⟩')
# Check model allowlist
allowed = agent.allowed_models()
print(f'Any model permitted' if not allowed else f'Policy allowlist: {allowed}')
"

echo
echo "ACT 4 – Task inside the boundary + reasoning level switch"
echo "-----------------------------------------------------------"
.venv/bin/python demo/task_scope_demo.py

echo
echo "ACT 5 – Full gate check every probe"
echo "-------------------------------------"
.venv/bin/python demo/check_boundary.py

echo
echo "ACT 6 – Model/Reasoning switching + project restrictions accuracy"
echo "------------------------------------------------------------------"
.venv/bin/python demo/enhanced_boundary_demo.py

echo
echo "ACT 7 – How the company runs the real agent against this boundary"
echo "-----------------------------------------------------------------"
cat <<'CMD'
.venv/bin/python agent.py \
  --company-id acme \
  --policy policies/acme-codefix.toml \
  --task-id PROJ-1457 --assignee codefix-bot \
  --task "add a discount() helper to src/cart.py and run its tests"
CMD