#!/usr/bin/env bash
# Live demo: the to-do boundary + a visibly rotating model roster, free only.
#
#   ./demo/live_show.sh                       # TUI (default on a terminal)
#   ./demo/live_show.sh --plain               # text REPL
#   ./demo/live_show.sh --task "list the todo app files"
#   ./demo/live_show.sh --allow-paid          # also offer paid models
#   ./demo/live_show.sh --wide                # rotate all 16 free models
#
# What it pins, and why:
#   --policy policies/todoinc-todo.toml  the to-do fence, applied before any
#                                        model call; an off-topic request is
#                                        refused without spending a token
#   AGENT_MODEL_ROTATE=turn              a different model each turn, announced
#                                        with a switch card when it changes
#   AGENT_MODEL_POOL=<free models>       every pick bills $0.00
#
# By default the pool is the two models the live gate rehearses (lightning ->
# ultra): the switch is real, and a demo cannot be derailed by an untested free
# model. --wide rotates all 16 free models; the picker always offers all of them.
set -euo pipefail

cd "$(dirname "$0")/.."

PY=.venv/bin/python
POLICY=policies/todoinc-todo.toml

WIDE=0
if [[ "${1:-}" == "--wide" ]]; then
  WIDE=1
  shift
fi

if [[ ! -x "$PY" ]]; then
  echo "no virtualenv at .venv - create it first (see README)" >&2
  exit 2
fi

if [[ ! -f models/catalog.json ]]; then
  echo "models/catalog.json is missing; regenerate it with:" >&2
  echo "  .venv/bin/python demo/fetch_models.py" >&2
  exit 2
fi

# free rotation is the default; a caller can pin their own pool or mode
export AGENT_MODEL_ROTATE="${AGENT_MODEL_ROTATE:-turn}"

if [[ -z "${AGENT_MODEL_POOL:-}" ]]; then
  POOL_LIMIT=2
  [[ "$WIDE" -eq 1 ]] && POOL_LIMIT=16

  AGENT_MODEL_POOL="$("$PY" - "$POOL_LIMIT" <<'PY'
import sys
import model_catalog

print(",".join(model_catalog.pool("free", limit=int(sys.argv[1]))))
PY
)"
  export AGENT_MODEL_POOL
fi

POOL_COUNT="$(awk -F, '{print NF}' <<<"$AGENT_MODEL_POOL")"

cat <<EOF
┌─ TAMIAS live demo ─────────────────────────────────────────────────────────┐
  policy      : $POLICY  (todo-app · todoinc)
  project     : company/work/todoinc/apps/todo
  rotation    : $AGENT_MODEL_ROTATE  ($POOL_COUNT free models, \$0.00 each)
  paid models : $(if [[ "${AGENT_ALLOW_PAID:-0}" =~ ^(1|true|yes|on)$ ]]; then echo enabled; else echo "off (--allow-paid to enable)"; fi)

  allowed : "build a todo app with add() and complete()"
            "make the to-do list sort by due date"
  blocked : "write a chatbot"        (off-topic)
            "read company/work/todoinc/hr/salaries.csv"  (off-project)

  switch manually : press m (next model) · /model <text> to search all 16 free
  the switch card : appears automatically when the model changes between turns
  wide rotation   : ./demo/live_show.sh --wide   (all 16 free models)
  quit            : ctrl+q in the TUI, /quit in the text REPL
└────────────────────────────────────────────────────────────────────────────┘
EOF

exec "$PY" agent.py --policy "$POLICY" "$@"
