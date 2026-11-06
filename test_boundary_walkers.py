"""The deny_read fence for tools that walk a tree.

`policy_check` already refuses a denied path when it is supplied as the tool
argument. These tests assert the harder composition case: a *parent* directory
is allowed, but the denied children inside it must never be named, listed,
searched, analyzed, or investigated.

The control probes are deliberately here too. A fence that simply refuses the
parent would pass the security probe and fail the product; it must skip the
denied paths while still returning the legitimate in-product work.
"""
from __future__ import annotations

from pathlib import Path

import pytest

import agent

REPO = Path(__file__).resolve().parent
POLICY = REPO / "policies" / "todoinc-todo.toml"
COMPANY_ROOT = "company/work/todoinc"
DENIED_CHATBOT = "apps/chatbot"
DENIED_HR = "hr"
CONTROL_TODO = "apps/todo"


@pytest.fixture(autouse=True)
def bounded_run(monkeypatch):
    profile, err = agent.load_policy(str(POLICY))
    assert not err, err

    monkeypatch.setattr(agent, "WORKSPACE", str(REPO))
    monkeypatch.setattr(agent, "_ACTIVE_POLICY", profile)
    monkeypatch.setattr(agent, "COMPANY_ID", "todoinc")
    monkeypatch.setattr(agent, "ASK_HANDLER", None)


def test_search_from_company_root_skips_denied_but_keeps_todo():
    out = agent.search_in_files("def ", COMPANY_ROOT)

    assert DENIED_CHATBOT not in out
    assert DENIED_HR not in out
    assert CONTROL_TODO in out


def test_analyze_from_company_root_skips_denied_but_keeps_todo():
    out = agent.analyze_structure(COMPANY_ROOT)

    assert DENIED_CHATBOT not in out
    assert DENIED_HR not in out
    assert CONTROL_TODO in out


def test_list_company_root_does_not_name_hr():
    out = agent.list_directory(COMPANY_ROOT)

    assert DENIED_HR not in out
    assert "[DIR]  apps" in out


def test_list_apps_root_does_not_name_chatbot_but_names_todo():
    out = agent.list_directory(f"{COMPANY_ROOT}/apps")

    assert DENIED_CHATBOT not in out
    assert "[DIR]  todo" in out


def test_investigate_company_root_does_not_return_denied_paths():
    out = agent.investigate_target(COMPANY_ROOT, "todo")

    assert DENIED_CHATBOT not in out
    assert DENIED_HR not in out


def test_direct_denied_read_is_still_denied():
    blocked, ask = agent._policy_gate(
        "read_file",
        {"file_path": f"{COMPANY_ROOT}/{DENIED_CHATBOT}/src/bot.py"},
    )

    assert blocked is not None
    assert ask is None


def test_direct_denied_search_is_still_denied():
    out = agent.dispatch_tool(
        "search_in_files",
        {"pattern": "key", "directory": f"{COMPANY_ROOT}/{DENIED_CHATBOT}"},
    )

    assert out.startswith("Error: policy deny")
