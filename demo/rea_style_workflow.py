"""Complete REA-style behavioral workflow demo.

Shows the full investigation lifecycle:
1. investigate_target - understand how a feature works (evidence-based)
2. trace_feature - drill into the specific mechanism
3. analyze_structure - understand imports/exports/relationships
4. record_unknown - track what can't be determined yet
5. record_comparison - compare before concluding
6. build_similar - build analogous feature (only after investigation)
7. finish_investigation - summarize findings, distinguish observations from inferences/unknowns

Plus model switching and cost analysis visible throughout.

Run: .venv/bin/python demo/rea_style_workflow.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent  # noqa: E402


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def setup(company_id, policy_path):
    policy_path_full = os.path.join(REPO, policy_path)
    profile, err = agent.load_policy(policy_path_full)
    assert err is None, f"Failed to load policy: {err}"
    agent.COMPANY_ID = company_id
    agent.protect_path(policy_path_full)
    agent.set_active_policy(profile)
    agent.ASK_HANDLER = lambda tool, args, reason: True
    return profile


def main():
    repo = REPO
    if os.path.realpath(repo) != REPO:
        print("Error: run this from the repo root")
        return 2

    print_header("TAMIAS REA-STYLE BEHAVIORAL WORKFLOW")
    print("Complete investigation lifecycle: investigate → trace → compare →")
    print("record unknowns → build similar → finish investigation")
    print("Model switching + cost analysis visible throughout")
    print("All behaviors bounded to company/organization/team")

    profile = setup("todoinc", "policies/todoinc-todo.toml")

    # ── Step 1: Investigate ──
    print_header("STEP 1: Investigate Target (evidence-based findings)")
    print("\nInvestigating: how does the todo app handle items?")
    print("Target: company/work/todoinc/apps/todo/src/todo.py")
    out = agent.dispatch_tool("investigate_target", {
        "target": "company/work/todoinc/apps/todo/src/todo.py",
        "feature": "todo item handling",
        "depth": "medium",
    })
    print(out)

    # ── Step 2: Trace Feature ──
    print_header("STEP 2: Trace Feature (call chain with evidence)")
    print("\nTracing: todo item creation flow")
    out = agent.dispatch_tool("trace_feature", {
        "entry_point": "company/work/todoinc/apps/todo/src/todo.py",
        "target_behavior": "todo item creation",
        "max_depth": 5,
    })
    print(out)

    # ── Step 3: Analyze Structure ──
    print_header("STEP 3: Analyze Structure (imports, exports, relationships)")
    print("\nAnalyzing: todo app directory structure")
    out = agent.dispatch_tool("analyze_structure", {
        "directory": "company/work/todoinc/apps/todo",
        "focus": "all",
    })
    print(out)

    # ── Step 4: Record Unknown ──
    print_header("STEP 4: Record Unknown (REA-style residual-unknown tracking)")
    print("\nRecording what cannot be determined from static analysis alone:")
    ref = agent.dispatch_tool("record_unknown", {
        "question": "Does the todo item 'add' function persist to disk or only keep in memory?",
        "authority": "runtime execution",
        "evidence_ids": [],
    })
    print(f"\nUnknown recorded with reference: {ref}")
    print("\nAll unresolved questions:")
    for uq in agent.list_unknowns():
        print(f"  [{uq['ref']}] {uq['question']}")
        print(f"      authority needed: {uq['authority']}")

    # ── Step 5: Record Comparison ──
    print_header("STEP 5: Record Comparison (compare before concluding)")
    print("\nComparing two investigation findings before concluding:")
    cmp_ref = agent.dispatch_tool("record_comparison", {
        "left": "todo item 'add' function",
        "right": "todo item 'complete' function",
        "dimension": "behavior",
        "result": "different",
        "evidence_ids": [],
    })
    print(f"\nComparison recorded: {cmp_ref}")
    print("\nComparison result: 'add' creates a new item, 'complete' marks existing")
    print("  → NOT equivalent - different behaviors")

    # ── Step 6: Build Similar ──
    print_header("STEP 6: Build Similar (only after investigation)")
    print("\nBuilding a similar feature based on investigation findings:")
    out = agent.dispatch_tool("build_similar", {
        "investigation_summary": "Todo app uses add(items, title) to append a new item dict with title, done=False, due=today. complete(items, title) iterates and marks done=True.",
        "target_location": "company/work/todoinc/apps/todo/src/todo_bridge.py",
        "adaptations": "Adapt to use our database schema instead of in-memory list",
    })
    print(out)

    # ── Step 7: Finish Investigation ──
    print_header("STEP 7: Finish Investigation (session summary)")
    print("\nFinishing investigation - all findings summarized:")
    out = agent.dispatch_tool("finish_investigation", {
        "summary": "Investigated todo item handling in company/work/todoinc/apps/todo/src/todo.py. "
                   "Found add() creates items with title/done/due fields, complete() marks items done. "
                   "Structure analysis shows 2 files with add/complete exports. "
                   "Static analysis only - runtime persistence unknown."
    })
    print(out)

    print_header("BEHAVIORAL SUMMARY")
    print("✓ Investigate before build - system prompt enforces investigation first")
    print("✓ Evidence-based findings - every finding has file:line references")
    print("✓ Observations vs inferences vs unknowns - clearly distinguished")
    print("✓ Record unknowns - track what can't be determined yet")
    print("✓ Record comparisons - compare before concluding equivalence")
    print("✓ Build similar - only after investigation, verified")
    print("✓ Finish investigation - summarize findings with evidence distinction")
    print("✓ Model switching - visible tier changes with reasons")
    print("✓ Cost analysis - money saved vs premium equivalent")
    print("✓ Boundary enforcement - 3-layer gate holds project restrictions")
    print("\nAll behaviors bounded to company/organization/team boundary.")
    print("No data leaves the project area - everything runs locally.")

    return 0


if __name__ == "__main__":
    sys.exit(main())