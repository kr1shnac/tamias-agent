#!/usr/bin/env python3
"""Show the to-do boundary and the model roster, offline and deterministically.

    .venv/bin/python demo/showcase.py            # full run

Two claims are checked here, and both are checked through the *real* code the
agent uses (``domain_check``, ``policy_check``, ``policy_ask``, ``rotate_model``),
not through a copy:

  1. the to-do fence: in-scope work is allowed, anything else is refused, and
     paths/tools outside the product are denied;
  2. the roster: how many models exist, which are free, and what a rotation
     across them looks like.

What this script does **not** do is call a model. The rotation section is a
selection walk - it shows which model each turn would use and why. It prints
"selection only" next to it and never claims tokens or spend. For a live run,
use ``demo/live_show.sh``.

Exit code is 0 only when every boundary probe matches its expectation.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import agent  # noqa: E402
import model_catalog  # noqa: E402
import providers  # noqa: E402

POLICY = os.path.join(ROOT, "policies", "todoinc-todo.toml")

PASS = "ALLOW"
BLOCK = "BLOCK"
ASK = "ASK"


def rule(char="─", width=78):
    return char * width


def head(title):
    print()
    print(rule("═"))
    print(title)
    print(rule("═"))


def load_policy_or_die():
    policy, error = agent.load_policy(POLICY)

    if error:
        print(f"cannot load {POLICY}: {error}")
        raise SystemExit(2)

    agent.set_active_policy(policy)
    return policy


def describe_policy(policy):
    print(f"policy      : {policy.name}  (company: {policy.company or 'none'})")
    print(f"project     : {policy.root}")
    print(f"writes      : {', '.join(policy.allow_write) or 'none'}")
    print(f"reads denied: {', '.join(policy.deny_read) or 'none'}")
    print(f"shell allow : {', '.join(policy.shell_allow) or 'none'}")
    print(f"shell deny  : {', '.join(policy.shell_deny) or 'none'}")
    print(f"ask before  : {', '.join(policy.tool_ask) or 'nothing'}")


def check_domain(policy, probes, failures):
    print()
    print("REQUEST SCOPE  (domain_check - runs before any model call)")
    print(rule())

    for text, expected in probes:
        refusal = agent.domain_check(text)
        got = BLOCK if refusal else PASS
        ok = got == expected
        failures.append(ok)
        mark = "ok  " if ok else "FAIL"
        print(f"  [{mark}] {got:<5}  {text!r}")
        if refusal:
            print(f"          {refusal}")

    print()
    print("  deny wins over allow: a request that says 'todo' and 'chatbot'")
    print("  is refused on 'chatbot', not allowed on 'todo'.")
    refusal = agent.domain_check("build a todo app that is also a chatbot")
    ok = refusal is not None and "chatbot" in refusal
    failures.append(ok)
    print(f"  [{'ok  ' if ok else 'FAIL'}] {refusal}")


def check_tools(probes, failures):
    print()
    print("REACH  (policy_check / policy_ask - what the agent may touch)")
    print(rule())

    for label, tool, args, expected in probes:
        deny = agent.policy_check(tool, args)
        ask = agent.policy_ask(tool, args) if not deny else None
        got = BLOCK if deny else (ASK if ask else PASS)
        ok = got == expected
        failures.append(ok)
        mark = "ok  " if ok else "FAIL"
        print(f"  [{mark}] {got:<5}  {label}")
        if deny:
            print(f"          {deny}")
        elif ask:
            print(f"          {ask} (answer it in the TUI; headless = no)")


def show_roster():
    print()
    print("MODEL ROSTER  (models/catalog.json - fetched from the provider)")
    print(rule())

    for line in model_catalog.summary_lines():
        print(f"  {line}")

    for tier in model_catalog.TIERS:
        entries = model_catalog.models(tier)
        print()
        print(f"  {tier.upper()} ({len(entries)})")
        for model in entries[:4]:
            price = ("free" if tier == "free"
                     else f"${model['prompt_usd_per_1k']:.6f}/1k in")
            print(f"    {model['id']:<46} {price:<18}")
        if len(entries) > 4:
            print(f"    ... {len(entries) - 4} more")

    print()
    for line in providers.report_lines():
        print(f"  {line}")


def show_rotation(turns=6):
    print()
    print("ROTATION  (selection only - no API call, no tokens billed)")
    print(rule())

    previous_mode = agent.MODEL_ROTATE
    agent.MODEL_ROTATE = "turn"
    agent.reset_model_pool()

    try:
        pool = agent.model_pool()
        if not pool:
            print("  no pool: models/catalog.json is missing or empty")
            return 1

        print(f"  pool: {len(pool)} free models (billed at $0.00)")
        switches = 0
        previous = None

        for turn in range(turns):
            chosen = agent.rotate_model(turn, step=1)
            tier = agent._tier_of_model(chosen)
            price = model_catalog.price_note(chosen)

            if previous is None:
                action = "start"
            elif chosen != previous:
                switches += 1
                action = f"SWITCH {previous} -> {chosen}"
            else:
                action = "same"
            previous = chosen

            print()
            print(f"  turn {turn + 1}: {chosen}  [{tier}]  {price}")
            print(f"           {action if action != 'same' else 'no change'}")

        print()
        print(f"  {switches} switches across {turns} turns; every model is $0.00")
        print("  (in a live run each entry above is a real provider call:")
        print("   demo/live_show.sh)")
        return 0
    finally:
        agent.MODEL_ROTATE = previous_mode
        agent.reset_model_pool()


DOMAIN_PROBES = [
    ("build a todo app with add and complete", PASS),
    ("make the to-do list sort by due date", PASS),
    ("refactor the task list", PASS),
    ("build a to do app", PASS),
    ("write a chatbot for support", BLOCK),
    ("clone linkedin", BLOCK),
    ("what is the weather today", BLOCK),
    ("hi", BLOCK),
]

TOOL_PROBES = [
    ("read the product source", "read_file",
     {"file_path": "company/work/todoinc/apps/todo/src/todo.py"}, PASS),
    ("write inside the product", "write_file",
     {"file_path": "company/work/todoinc/apps/todo/src/todo.py", "content": "x"}, ASK),
    ("write into the chatbot app", "write_file",
     {"file_path": "company/work/todoinc/apps/chatbot/src/bot.py", "content": "x"}, BLOCK),
    ("read HR records", "read_file",
     {"file_path": "company/work/todoinc/hr/salaries.csv"}, BLOCK),
    ("read a private key", "read_file", {"file_path": "deploy/key.pem"}, BLOCK),
    ("run the product tests", "run_shell",
     {"command": "python3 -m pytest company/work/todoinc/apps/todo"}, PASS),
    ("delete the workspace", "run_shell", {"command": "rm -rf company"}, BLOCK),
    ("push to the remote", "run_shell", {"command": "git push origin main"}, BLOCK),
    ("read a file outside the tool allowlist", "fetch_url",
     {"url": "https://example.com"}, BLOCK),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()

    policy = load_policy_or_die()
    failures = []

    head("TAMIAS - to-do boundary and model roster")
    print("checked with the real gates in agent.py; nothing here is simulated")
    print()
    describe_policy(policy)

    check_domain(policy, DOMAIN_PROBES, failures)
    check_tools(TOOL_PROBES, failures)
    show_roster()
    show_rotation()

    matched = sum(1 for ok in failures if ok)
    total = len(failures)

    head("RESULT")
    print(f"  boundary probes: {matched}/{total} matched expectation")
    print(f"  models in catalog: {model_catalog.counts().get('total', 0)} "
          f"({model_catalog.counts().get('free', 0)} free)")
    print(f"  paid models: {'enabled' if providers.paid_enabled() else 'off (free only)'}")
    print()
    print("  live run:  ./demo/live_show.sh          (TUI, rotation on)")
    print("             ./demo/live_show.sh --task \"list the todo app files\"")
    print("  CI gate :  ./demo/check_all.sh --fast")
    print()

    if matched != total:
        print("  FAIL: some probe did not match its expectation")
        return 1

    print("  PASS: the to-do fence holds and the roster is loaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
