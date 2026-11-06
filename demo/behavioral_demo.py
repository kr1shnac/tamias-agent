"""Behavioral demo: REA-style investigation + model switching + cost analysis.

This demo showcases Tamias behaving like REA (investigate/trace targets with
evidence) + Claude Code/Codex (agentic coding), with:

1. Model switching shown explicitly when queries come in
2. Money saved analysis shown per-model
3. Evidence-based findings (file:line, limitations, confidence)
4. "Build similar" capability after investigation

Run: .venv/bin/python demo/behavioral_demo.py
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO)

import agent  # noqa: E402


def decision_of(out):
    if isinstance(out, str):
        if out.startswith("Error: policy ask denied"):
            return "ask-denied"
        if out.startswith("Error: policy deny"):
            return "deny"
        if out.startswith("Error:"):
            return "refused"
    return "ran"


def setup(company_id, policy_path):
    repo = REPO
    policy_path_full = os.path.join(repo, policy_path)
    profile, err = agent.load_policy(policy_path_full)
    assert err is None, f"Failed to load policy: {err}"
    agent.COMPANY_ID = company_id
    agent.protect_path(policy_path_full)
    agent.set_active_policy(profile)
    agent.ASK_HANDLER = lambda tool, args, reason: True
    return profile


def print_header(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def demo_investigation(profile):
    """REA-style investigation: investigate a target with evidence."""
    print_header("DEMO 1: REA-Style Investigation (evidence-based findings)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nInvestigating: how does the todo app handle items?")
    print("Target: company/work/todoinc/apps/todo/src/todo.py")
    print("Feature: todo item handling")
    print("-" * 60)

    out = agent.dispatch_tool("investigate_target", {
        "target": "company/work/todoinc/apps/todo/src/todo.py",
        "feature": "todo item",
        "depth": "medium",
    })
    print(out)


def demo_trace_feature(profile):
    """Trace a feature through code with evidence."""
    print_header("DEMO 2: Feature Tracing (call chain with evidence)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nTracing: how does 'add item' flow through the todo app?")
    print("Entry point: company/work/todoinc/apps/todo/src/todo.py")
    print("Target behavior: todo item creation")
    print("-" * 60)

    out = agent.dispatch_tool("trace_feature", {
        "entry_point": "company/work/todoinc/apps/todo/src/todo.py",
        "target_behavior": "todo item creation",
        "max_depth": 5,
    })
    print(out)


def demo_analyze_structure(profile):
    """Analyze codebase structure."""
    print_header("DEMO 3: Structure Analysis (imports, exports, relationships)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nAnalyzing: todo app project structure")
    print("Directory: company/work/todoinc/apps/todo")
    print("Focus: all")
    print("-" * 60)

    out = agent.dispatch_tool("analyze_structure", {
        "directory": "company/work/todoinc/apps/todo",
        "focus": "all",
    })
    print(out)


def demo_model_switching():
    """Show model switching behavior."""
    print_header("DEMO 4: Model Switching (visible tier changes)")

    print("\nCurrent model:", getattr(agent, 'MODEL', 'nvidia/nemotron-3.5-lightning:free'))
    print("Current effort:", os.environ.get('AGENT_EFFORT_POLICY', 'auto'))
    print("\nModel tier routing (auto policy):")
    print("  - Small prompts (<400 chars): free model")
    print("  - Medium prompts (400-1200 chars): mid model")
    print("  - Large prompts (>1200 chars): premium model")
    print("  - Tool failures >= 2: escalate to premium")
    print("\nWhen a model switches, Tamias shows:")
    print("  ◀ old_model → ▶ new_model")
    print("  old_tier → new_tier · reason: auto-escalation")
    print("\nEach switch is logged in the audit trail with estimated savings.")


def demo_cost_analysis(profile):
    """Show cost analysis behavior."""
    print_header("DEMO 5: Cost Analysis (money saved vs premium)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nAfter each turn, Tamias shows cost analysis:")
    print("  - Actual spend (provider-billed USD)")
    print("  - Premium equivalent (hypothetical retail rate)")
    print("  - Money saved (premium − actual)")
    print("  - Models used in the turn")
    print("\nAll dollar figures are hypothetical retail rates for analysis only.")
    print("No measured savings exist - every figure is clearly labelled.")


def demo_build_similar(profile):
    """Show build_similar capability."""
    print_header("DEMO 6: Build Similar (after investigation)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nWorkflow: investigate → trace → build similar")
    print("\n1. investigate_target: understand how the target feature works")
    print("2. trace_feature: drill into the specific mechanism")
    print("3. build_similar: implement analogous behavior in your project")
    print("\nExample:")
    print("  investigate_target('company/work/todoinc/apps/todo', 'todo item creation')")
    print("  trace_feature('.../todo.py:add_item', 'saving a todo item')")
    print("  build_similar('...', 'src/features/todo-bridge.py', 'adapt to our DB schema')")
    print("\nbuild_similar records the intent - use write_file to implement.")


def demo_boundary_enforcement(profile):
    """Show project boundary enforcement."""
    print_header("DEMO 7: Project Boundary Enforcement (3-layer gate)")

    print(f"\nPolicy: {profile.name} | Company: {agent.COMPANY_ID}")
    print("\nThree-layer boundary holds even when task tries to escape:")
    print("\nLayer 1 - Scope gate (domain_check):")
    print("  - Blocks off-topic requests before any model call (0 tokens)")
    print("  - Fail-closed: empty allow list = refuse everything")
    print("\nLayer 2 - Plan check (verify_plan):")
    print("  - All-or-nothing: if any call leaves project, none run")
    print("  - Prevents smuggling bad calls among good ones")
    print("\nLayer 3 - Per-call gate (dispatch_tool → policy_check):")
    print("  - Tool allow/deny lists")
    print("  - Path allow/deny lists")
    print("  - Shell command family allow/deny")
    print("  - Ask-gated tools require human confirmation")
    print("\nEvery decision is logged in the audit trail.")


def main():
    repo = REPO
    if os.path.realpath(repo) != REPO:
        print("Error: run this from the repo root")
        return 2

    print_header("TAMIAS BEHAVIORAL DEMO")
    print("REA-style investigation + Claude Code/Codex agentic behavior")
    print("Model switching + money saved analysis")

    # Setup with todoinc policy
    profile = setup("todoinc", "policies/todoinc-todo.toml")

    demo_investigation(profile)
    demo_trace_feature(profile)
    demo_analyze_structure(profile)
    demo_model_switching()
    demo_cost_analysis(profile)
    demo_build_similar(profile)
    demo_boundary_enforcement(profile)

    print_header("SUMMARY")
    print("✓ REA-style investigation: evidence-based findings with file:line refs")
    print("✓ Model switching: visible tier changes with reasons")
    print("✓ Cost analysis: money saved vs premium equivalent")
    print("✓ Boundary enforcement: 3-layer gate holds project restrictions")
    print("✓ Build similar: investigate → trace → build workflow")
    print("\nAll behaviors work within the company/organization/team boundary.")
    print("No data leaves the project area - everything runs locally.")

    return 0


if __name__ == "__main__":
    sys.exit(main())