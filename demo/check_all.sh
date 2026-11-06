#!/usr/bin/env bash
# check_all.sh - the full verification sweep for the Tamias agent.
#
# One command that runs every check we actually trust, in increasing order of
# cost, and prints PASS/FAIL per check plus a summary. Exit 0 only if nothing
# failed. Nothing here reads or prints .env: the key is only ever resolved to a
# yes/no.
#
#   ./demo/check_all.sh              # everything offline (default)
#   ./demo/check_all.sh --fast       # skip the slow demos and mock runs
#   ./demo/check_all.sh --live       # also rehearse the live model twice
#   ./demo/check_all.sh --fast --live
#
# What each tier proves:
#   static   internal consistency - registry, prompt budget, imports
#   gate     policy engine blocks correctly at every layer
#   demos    the end-to-end offline acts still produce their expected verdicts
#   mock     the real agent loop runs against a local fake model (NOT live)
#   live     real model -> tool -> boundary; needs key + network, may 429
#
# For a live presentation:
#   ./demo/showcase.py       offline 18/18 boundary table + roster (10s)
#   ./demo/live_show.sh      the interactive TUI with visible model switching
set -uo pipefail

cd "$(dirname "$0")/.."

PY=".venv/bin/python"
FAST=0
LIVE=0

for arg in "$@"; do
    case "$arg" in
        --fast) FAST=1 ;;
        --live) LIVE=1 ;;
        -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown option: $arg (try --help)" >&2; exit 2 ;;
    esac
done

if [ -t 1 ]; then
    B=$'\033[1m'; G=$'\033[32m'; R=$'\033[31m'; Y=$'\033[33m'; D=$'\033[2m'; N=$'\033[0m'
else
    B=""; G=""; R=""; Y=""; D=""; N=""
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0; FAIL=0; SKIP=0
live_pass=0   # section 6 owns this; initialised so the summary is safe with --no-live
FAILED=()
T0=$SECONDS

say()  { printf '%s\n' "$*"; }
head1() { say ""; say "${B}== $* ==${N}"; }

pass() { PASS=$((PASS+1)); printf '  %sPASS%s  %s\n' "$G" "$N" "$1"; }
fail() {
    FAIL=$((FAIL+1)); FAILED+=("$1")
    printf '  %sFAIL%s  %s\n' "$R" "$N" "$1"
    [ -n "${2:-}" ] && printf '        why: %s\n' "$2"
    if [ -n "${3:-}" ] && [ -f "${3}" ]; then
        tail -n 14 "${3}" | sed 's/^/        /'
    fi
}
skip() { SKIP=$((SKIP+1)); printf '  %sSKIP%s  %s\n' "$Y" "$N" "$1"; }

# Rich wraps its panels at the terminal width, so a sentence we want to match
# can be split across lines with box-drawing borders wedged into the middle.
# Flatten first: drop the borders, collapse every whitespace run to one space.
flatten() {
    tr -d '│╭╮╰╯─━┃┏┓┗┛' < "$1" | tr '\n\r\t' '   ' | tr -s ' '
}

# run_check <label> <zero|nonzero|any> <required-substring-or-empty> <cmd...>
run_check() {
    local label="$1" expect="$2" pattern="$3"
    shift 3
    local out="$TMP/out"
    "$@" >"$out" 2>&1
    local rc=$?
    local why=""

    case "$expect" in
        zero)    [ $rc -eq 0 ] || why="exit $rc, expected 0" ;;
        nonzero) [ $rc -ne 0 ] || why="exit 0, expected a refusal" ;;
    esac
    if [ -z "$why" ] && [ -n "$pattern" ] \
       && ! flatten "$out" | grep -qF -- "$pattern"; then
        why="missing expected text: $pattern"
    fi

    if [ -z "$why" ]; then pass "$label"; else fail "$label" "$why" "$out"; fi
    return 0
}

# ------------------------------------------------------------------ header
say "${B}TAMIAS agent - full verification sweep${N}"
say "${D}$(date '+%Y-%m-%d %H:%M:%S')  $(pwd)${N}"

# ------------------------------------------------------- 0. environment
head1 "0. environment"

if [ ! -x "$PY" ]; then
    say "  ${R}no venv at $PY${N} - create it and install requirements.txt first"
    exit 2
fi
say "  interpreter : $("$PY" -V 2>&1)"
say "  tools       : $("$PY" -c 'import agent; print(len(agent.TOOLS))' 2>/dev/null || echo '?')"
say "  policies    : $(ls policies/*.toml 2>/dev/null | tr '\n' ' ')"

key_state="$("$PY" - <<'PYEOF' 2>/dev/null || echo error
try:
    import agent
    print("yes" if agent.resolve_api_key() else "no")
except Exception:
    print("error")
PYEOF
)"
case "$key_state" in
    yes) say "  api key     : ${G}resolved${N} ${D}(value never printed)${N}" ;;
    no)  say "  api key     : ${Y}not set${N} ${D}(offline checks only)${N}" ;;
    *)   say "  api key     : ${Y}unresolved${N}" ;;
esac

run_check "dependencies import (textual, rich, openai, dotenv)" zero "" \
    "$PY" -c 'import textual, rich, openai, dotenv'

run_check "TUI modules import (events, credits, model_picker, app)" zero "" \
    "$PY" -c 'import tui.events, tui.credits, tui.model_picker, tui.app'

# --------------------------------------------------------- 1. static checks
head1 "1. static - registry and prompt budget"

tools_out="$("$PY" - <<'PYEOF' 2>&1
import agent
names = [t["function"]["name"] for t in agent.TOOLS]
expected = [
    "run_shell", "write_file", "edit_file", "read_file",
    "list_directory", "create_directory", "search_in_files", "update_plan",
    "investigate_target", "trace_feature", "analyze_structure", "build_similar",
    "record_unknown", "record_comparison", "finish_investigation",
    "boundary_accuracy", "model_performance_comparison", "reasoning_chain",
]
print("count", len(names))
print("missing", [n for n in expected if n not in names])
print("extra", [n for n in names if n not in expected])
words = len(agent.SYSTEM_PROMPT.split())
print("words", words)
PYEOF
)"
say "${D}$(printf '%s\n' "$tools_out" | sed 's/^/    /')${N}"

if printf '%s\n' "$tools_out" | grep -q '^missing \[\]$' \
   && printf '%s\n' "$tools_out" | grep -q '^extra \[\]$'; then
    pass "18 tools, exact registry (8 base + 7 investigation + 3 reporting)"
else
    fail "tool registry mismatch" "$tools_out"
fi

if printf '%s\n' "$tools_out" | awk '/^words /{exit !($2 <= 400)}'; then
    pass "system prompt within the 400-word budget"
else
    fail "system prompt over budget" "$tools_out"
fi

# ------------------------------------------------------------ 2. test gate
head1 "2. test gate - the one number that must not regress"

if [ -f test_agent.py ] && [ -f test_tui_features.py ] && [ -f test_premium_features.py ]; then
    run_check "pytest: agent + TUI + premium surfaces + docs integrity" zero "passed" \
        "$PY" -m pytest test_agent.py test_tui_features.py test_premium_features.py tests/test_docs_integrity.py -q
else
    fail "test files missing"
fi

# ---------------------------------------------------------- 3. boundary
head1 "3. boundary - policy engine, all layers"

run_check "check_boundary: 17/17 probes match the policy (CI exit code)" zero \
    "17/17 probes matched the boundary" \
    "$PY" demo/check_boundary.py

run_check "showcase: to-do fence 18/18, roster and rotation loaded" zero \
    "boundary probes: 18/18 matched expectation" \
    "$PY" demo/showcase.py

if [ "$FAST" -eq 1 ]; then
    skip "todoinc demo (skipped by --fast)"
    skip "acme demo (skipped by --fast)"
else
    run_check "todo_show: 2 worked, 3 refused at the scope gate, \$0 spent" zero \
        "2 request(s) worked, 3 refused at the scope gate" \
        bash demo/todo_show.sh

    run_check "show: 7 acts including the full gate check" zero \
        "17/17 probes matched the boundary" \
        bash demo/show.sh
fi

# ------------------------------------------------- 4. behavioral walkthroughs
head1 "4. behavioral walkthroughs - REA lifecycle, switching, cost"

run_check "rea_style_workflow: investigate -> trace -> compare -> finish" zero \
    "INVESTIGATION" \
    "$PY" demo/rea_style_workflow.py

run_check "final_behavioral_showcase: all behaviors in one run" zero \
    "ALL BEHAVIORS COMPLETE" \
    "$PY" demo/final_behavioral_showcase.py

# --------------------------------------------------------- 5. mock agent loop
head1 "5. mock model - the real agent loop, no network"

if [ "$FAST" -eq 1 ]; then
    skip "mock out-of-scope write (skipped by --fast)"
    skip "mock in-scope write (skipped by --fast)"
else
    run_check "mock: out-of-scope write dies at the boundary" nonzero \
        "outside the write scope" \
        timeout 90 bash demo/mock_act.sh --company-id todoinc \
            --policy policies/todoinc-todo.toml \
            --task "create todo in desktop" --plain

    run_check "mock: in-scope write is ask-gated, headless fails closed" nonzero \
        "ask denied" \
        timeout 90 bash demo/mock_act.sh --company-id todoinc \
            --policy policies/todoinc-todo.toml \
            --task "add a due date to the todo app" --plain
fi

# ---------------------------------------------------------------- 6. live
head1 "6. live model - only if asked"

if [ "$LIVE" -ne 1 ]; then
    skip "live rehearsal (pass --live to attempt it; needs key + network)"
elif [ "$key_state" != "yes" ]; then
    skip "live rehearsal (no api key resolved)"
else
    # Repo rule: a live run counts only after two consecutive passes.
    #
    # Both attempts are read-only. A headless write is ask-gated and must fail
    # closed - there is no human to confirm - so a write task can never pass
    # here; writes are demoed in the TUI, where the gate has someone to ask.
    #
    # attempt 1 proves a real model -> tool -> boundary turn on one model.
    # attempt 2 proves the visible switch: rotation moves the turn onto a
    # second free model between steps and prints the "Model switched" card.
    READ_TASK="read company/work/todoinc/apps/todo/src/todo.py and explain what add() does in one sentence"
    ROTATE_POOL="nvidia/nemotron-3.5-lightning:free,nvidia/nemotron-3-ultra-550b-a55b:free"
    live_pass=0; live_note=""

    run_attempt() {  # $1 label, $2 outfile, $3 ""|rotate
        local label="$1" out="$2" mode="$3" rc=0

        if [ "$mode" = "rotate" ]; then
            AGENT_MODEL_ROTATE=step AGENT_MODEL_POOL="$ROTATE_POOL" \
            timeout 180 "$PY" agent.py \
                --company-id todoinc --policy policies/todoinc-todo.toml \
                --task-id TODO-42 --assignee todo-bot \
                --task "$READ_TASK" --max-steps 4 --max-task-cost 0.05 \
                >"$out" 2>&1 || rc=$?
        else
            timeout 180 "$PY" agent.py \
                --company-id todoinc --policy policies/todoinc-todo.toml \
                --task-id TODO-42 --assignee todo-bot \
                --task "$READ_TASK" --max-steps 6 --max-task-cost 0.05 \
                >"$out" 2>&1 || rc=$?
        fi

        if [ $rc -eq 0 ] && [ "$mode" = "rotate" ] \
                && ! grep -q "Model switched" "$out"; then
            rc=97   # the turn passed but the switch never happened
            live_note="no switch card in the rotating attempt"
        fi

        if [ $rc -eq 0 ]; then
            live_pass=$((live_pass+1))
        elif grep -qiE '429|rate.?limit' "$out"; then
            live_note="rate-limited (free tier)"
        elif grep -qi 'connection error' "$out"; then
            live_note="no network"
        else
            live_note="exit $rc"
        fi

        say "${D}  $label: exit $rc${live_note:+, $live_note}${N}"
        grep -E 'Model switched|Model ─|▶ nvidia|◀ nvidia|spent:' "$out" 2>/dev/null \
            | head -5 | sed 's/^/        /'
    }

    run_attempt "attempt 1 (one model, real tool call)" "$TMP/live.1" ""
    run_attempt "attempt 2 (rotation: two models, switch card)" "$TMP/live.2" "rotate"

    if [ "$live_pass" -eq 2 ]; then
        pass "live: two consecutive passes, including a visible model switch"
    else
        skip "live: ${live_pass}/2 passed${live_note:+ - $live_note}; not claimed as proven"
    fi
fi

# -------------------------------------------------------------- summary
ELAPSED=$((SECONDS - T0))
head1 "summary"

printf '  %s%d passed%s   %s%d failed%s   %s%d skipped%s   %ds\n' \
    "$G" "$PASS" "$N" "$R" "$FAIL" "$N" "$Y" "$SKIP" "$N" "$ELAPSED"

if [ "$FAIL" -ne 0 ]; then
    say ""
    say "  ${R}FAILED:${N}"
    for f in "${FAILED[@]}"; do say "    - $f"; done
    say ""
    say "  ${R}NOT READY${N} - fix the failures above before demoing."
    exit 1
fi

if [ "$FAST" -eq 1 ]; then
    cat <<'TRUTH'

  what this fast run proved, and what it did not:
    proven      registry, prompt budget, test gate, policy engine
    not run     the offline demos and the mock agent loop (--fast skips them)
                so loop rendering, switching and cost panels are NOT proven here

  drop --fast for the full offline sweep before demoing.
TRUTH
else
    cat <<'TRUTH'

  what this run proved, and what it did not:
    proven      boundary blocks at scope / plan / action layers, for $0
    proven      the agent loop runs and refuses correctly (mock model)
    proven      investigation lifecycle, signed-plan/dossier gates, switching and cost panels render
TRUTH
    if [ "$LIVE" -eq 1 ] && [ "$live_pass" -eq 2 ]; then
        cat <<'TRUTH'
    proven      a real free model called a tool, and rotation switched the
                turn onto a second model with a "Model switched" card
    not proven  per-model perf table and reasoning chain (they populate in a
                real run_turn, but no live attempt checks them here)
TRUTH
    else
        cat <<'TRUTH'
    not proven  live model behaviour (run again with --live)
                per-model perf table, reasoning chain
TRUTH
    fi
    cat <<'TRUTH'

  say "the model is a mock" whenever you demo section 5. it is not live.
TRUTH
fi

say ""
if [ "$LIVE" -eq 1 ] && [ "$live_pass" -eq 2 ]; then
    say "  ${G}READY (offline + live)${N} - live model, tool call and visible switch all passed."
else
    say "  ${G}READY (offline)${N} - run with --live to rehearse the real model."
fi
exit 0
