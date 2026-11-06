"""TODOINC: one company, one product (a to-do app), two fences.

Shows the whole story in one run, offline - no key, no network:

  * a request about the to-do app          -> works
  * a request about anything else          -> refused at the *scope* gate,
                                              before a single token is spent
  * a to-do request that reaches for the
    chatbot project anyway                 -> refused at the *action* gate

and the session keeps running after every refusal.

    cd /home/krish/Desktop/tamias-agent
    .venv/bin/python demo/todo_boundary_demo.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent  # noqa: E402

POLICY = os.path.join(REPO, "policies", "todoinc-todo.toml")
TODO = "company/work/todoinc/apps/todo"
CHATBOT = "company/work/todoinc/apps/chatbot"


def decision_of(out):
    if isinstance(out, str) and out.startswith("Error: policy ask denied"):
        return "ask-denied"
    if isinstance(out, str) and out.startswith("Error: policy deny"):
        return "deny"
    if isinstance(out, str) and out.startswith("Error:"):
        return "refused"
    return "ran"


LABEL = {"ran": "RAN", "deny": "DENIED", "ask-denied": "ASK-DENIED",
         "refused": "REFUSED"}


def rule(char="─", width=72):
    print(char * width)


# each request: (what the user types, tool calls the model would then emit)
REQUESTS = [
    ("add a due date to each todo item and run the tests",
     [("read_file", {"file_path": f"{TODO}/src/todo.py"}),
      ("edit_file", {"file_path": f"{TODO}/src/todo.py",
                     "old_text": '"due": None', "new_text": '"due": "today"'}),
      ("run_shell", {"command": "python3 -m pytest apps/todo/tests -q -p no:cacheprovider"})]),

    ("build me a ChatGPT clone", None),

    ("add a task, and also build a chatbot", None),

    ("write me a crypto trading bot", None),

    ("add a to-do export feature",
     [("read_file", {"file_path": f"{TODO}/src/todo.py"}),
      ("read_file", {"file_path": f"{CHATBOT}/src/bot.py"}),
      ("write_file", {"file_path": f"{CHATBOT}/src/bot.py", "content": "x"})]),
]


def main():
    if os.path.realpath(agent.WORKSPACE) != REPO:
        print("Error: run this from the repo root")
        return 2

    agent.COMPANY_ID = "todoinc"
    profile, err = agent.load_policy(POLICY)
    if err:
        print(err)
        return 2
    agent.protect_path(POLICY)
    agent.set_active_policy(profile)
    agent.ASK_HANDLER = lambda tool, args, reason: True  # a human who says yes

    rule("═")
    print("  TODOINC - the company works on ONE thing: a to-do app")
    rule("═")
    print(f"  use case  : {profile.name}")
    print(f"  product   : {TODO}/")
    print("  off-limits: apps/chatbot/ · hr/   (different projects, same company)")
    print()
    print("  The company sets a task like this:")
    print("    agent.py --company-id todoinc --policy policies/todoinc-todo.toml \\")
    print("             --task-id TODO-42 --task \"add a due date to each item\"")
    print()
    print("  Layer 1 (scope):  the request text must be about the to-do app")
    print("  Layer 2 (action): even then, tool calls may only touch the product")
    rule()

    allowed = refused = 0
    todo_src = os.path.join(REPO, TODO, "src", "todo.py")
    original = open(todo_src).read()
    try:
        for text, calls in REQUESTS:
            print(f"\nYou ▸ {text}")

            refusal = agent.domain_check(text)
            if refusal:
                refused += 1
                print(f"  ⛔ BOUNDARY (scope)  {refusal}")
                agent.policy_audit("turn", {"input": text}, "refuse-domain",
                                   refusal)
                continue

            allowed += 1
            print("  ✓ in scope - working")
            for tool, args in (calls or []):
                out = agent.dispatch_tool(tool, args)
                d = decision_of(out)
                detail = out.splitlines()[0] if out else "(no output)"
                print(f"    [{LABEL[d]:10s}] {tool:12s} {detail[:78]}")
    finally:
        with open(todo_src, "w") as fh:
            fh.write(original)

    # --- the plan check: the whole plan is verified before any of it runs ----
    print()
    rule("─")
    print("  Verify before execute: the model proposes a plan, the WHOLE plan")
    print("  is checked against the project, and only then does any of it run.")
    plan = [
        ("read_file", {"file_path": f"{TODO}/src/todo.py"}),
        ("read_file", {"file_path": f"{CHATBOT}/src/bot.py"}),
        ("write_file", {"file_path": f"{TODO}/src/export.py", "content": "x"}),
    ]
    failures = agent.verify_plan(plan)
    for tool, args in plan:
        reason = agent.policy_check(tool, args)
        target = args.get("file_path", "")
        verdict = "out of scope" if reason else "in scope"
        print(f"    [{verdict:12s}] {tool:11s} {target}")
    if failures:
        print(f"  ⛔ {len(failures)} of {len(plan)} call(s) leave the project "
              "-> the plan is refused, NONE of it runs")
    else:
        print("  ✓ plan verified - executing")

    print()

    print()
    rule("═")
    print(f"  {allowed} request(s) worked, {refused} refused at the scope gate.")
    print("  Every refusal returned control: the session kept running, and no")
    print("  off-topic request ever reached the model.")
    rule("═")
    print("\naudit trail (every decision this run):")
    for row in agent.POLICY_AUDIT:
        print(f"  {row['decision']:13s} {row['tool']:8s} {row['reason']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
