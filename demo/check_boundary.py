"""Check the acme/codefix boundary end to end - offline, no key, no network.

Sets the same two fences ``agent.py`` sets for a bounded run:

  1. the COMPANY fence  --company-id acme  -> company/work/acme/ only
  2. the USE-CASE fence --policy ...       -> bots/codefix/ only

then dispatches real tool calls and asserts each gate decision. Exit 0 when
every probe matches the policy, non-zero otherwise, so it doubles as CI.

    cd /home/krish/Desktop/tamias-agent
    .venv/bin/python demo/check_boundary.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent  # noqa: E402

POLICY = os.path.join(REPO, "policies", "acme-codefix.toml")
PROBE_WRITE = "company/work/acme/bots/codefix/.boundary-probe.txt"

# "ran" = the call passed every gate and executed; the rest are refusals
EXPECTED = {
    "ran": "ran",
    "deny": "policy deny",
    "ask-denied": "policy ask denied",
}


def decision_of(out):
    """Map a dispatcher result to the gate decision it represents."""
    if isinstance(out, str) and out.startswith("Error: policy ask denied"):
        return "ask-denied"
    if isinstance(out, str) and out.startswith("Error: policy deny"):
        return "deny"
    return "ran"


def first_line(out):
    return out.splitlines()[0] if out else "(no output)"


def main():
    if os.path.realpath(agent.WORKSPACE) != REPO:
        print("Error: run this from the repo root (agent.WORKSPACE must be the repo)")
        return 2

    # --- wire the two fences exactly the way main() does for a bounded run ---
    agent.COMPANY_ID = "acme"
    profile, err = agent.load_policy(POLICY)
    if err:
        print(err)
        return 2
    agent.protect_path(POLICY)          # the fence is not editable by the agent
    agent.set_active_policy(profile)

    print(f"company fence : company/work/acme/")
    print(f"use-case fence: {profile.name} -> company/work/acme/bots/codefix/")
    print()

    # (label, tool, args, expected decision)
    probes = [
        # --- inside the one project: allowed ---
        ("read a codefix source file", "read_file",
         {"file_path": "company/work/acme/bots/codefix/src/cart.py"}, "ran"),
        ("list the codefix project", "list_directory",
         {"path": "company/work/acme/bots/codefix"}, "ran"),
        ("search codefix for 'def '", "search_in_files",
         {"pattern": "def ", "directory": "company/work/acme/bots/codefix"}, "ran"),
        ("run the project's own tests", "run_shell",
         {"command": "python3 -m pytest bots/codefix/tests -q -p no:cacheprovider"}, "ran"),

        # --- a DIFFERENT project in the same company: denied by the policy ---
        ("read payments (another project)", "read_file",
         {"file_path": "company/work/acme/bots/payments/src/pay.py"}, "deny"),
        ("read payments' notes", "read_file",
         {"file_path": "company/work/acme/bots/payments/SECRET_NOTES.md"}, "deny"),
        ("search payments", "search_in_files",
         {"pattern": "key", "directory": "company/work/acme/bots/payments"}, "deny"),
        ("write into payments", "write_file",
         {"file_path": "company/work/acme/bots/payments/src/pay.py", "content": "x"}, "deny"),

        # --- hr: denied read ---
        ("read hr salaries", "read_file",
         {"file_path": "company/work/acme/hr/salaries.csv"}, "deny"),

        # --- a write to the project needs a human (headless = no) ---
        ("write into codefix (headless)", "write_file",
         {"file_path": PROBE_WRITE, "content": "probe"}, "ask-denied"),

        # --- shell stays inside the allow / deny families ---
        ("shell: rm is a denied family", "run_shell",
         {"command": "rm -rf bots/codefix"}, "deny"),
        ("shell: curl is a denied family", "run_shell",
         {"command": "curl https://example.com"}, "deny"),
        ("shell: command not in an allow family", "run_shell",
         {"command": "ls -la"}, "deny"),

        # --- defence in depth, below the policy ---
        ("read the policy file itself", "read_file",
         {"file_path": POLICY}, "denied-below"),
        ("read .env", "read_file", {"file_path": ".env"}, "denied-below"),
        ("read a repo file outside the company area", "read_file",
         {"file_path": "agent.py"}, "denied-below"),
    ]

    failures = 0
    for label, tool, args, expect in probes:
        out = agent.dispatch_tool(tool, args)
        decision = decision_of(out)

        if expect == "denied-below":
            # refused by the secret/policy-path/company-fence layer, not the
            # policy allow/deny tables -> any "Error: ..." is a pass
            ok = isinstance(out, str) and out.startswith("Error:")
            shown = "refused below the policy"
        else:
            ok = decision == expect
            shown = first_line(out)

        failures += 0 if ok else 1
        print(f"[{'PASS' if ok else 'FAIL'}] {label:38s} {shown}")

    # --- a human says yes: the same ask-gated write now runs ---
    print()
    agent.ASK_HANDLER = lambda tool, args, reason: True
    out = agent.dispatch_tool("write_file", {"file_path": PROBE_WRITE, "content": "ok"})
    ran = decision_of(out) == "ran" and os.path.exists(os.path.join(REPO, PROBE_WRITE))
    failures += 0 if ran else 1
    print(f"[{'PASS' if ran else 'FAIL'}] {'same write, human says yes':38s} {first_line(out)}")
    agent.ASK_HANDLER = None

    if os.path.exists(os.path.join(REPO, PROBE_WRITE)):
        os.remove(os.path.join(REPO, PROBE_WRITE))

    # --- the audit trail every gate decision went into ---
    print("\naudit trail (policy decisions this run):")
    for row in agent.POLICY_AUDIT:
        print(f"  {row['decision']:12s} {row['tool']:16s} {row['reason']}")

    jsonl = os.path.join(REPO, profile.audit_path)
    if os.path.exists(jsonl):
        with open(jsonl) as fh:
            print(f"\nJSONL rows appended to {profile.audit_path}: {sum(1 for _ in fh)}")

    total = len(probes) + 1
    print(f"\n{total - failures}/{total} probes matched the boundary")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
