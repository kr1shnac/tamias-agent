import contextlib
import os
import pathlib
import subprocess
import sys
import types
import unittest.mock as mock
from copy import deepcopy
from types import SimpleNamespace

# agent.py needs dotenv / openai / rich, none of them are installed in .venv,
# so stub them out. every stub records what it was asked to do.
os.environ.setdefault("OPENROUTER_API_KEY", "test-key-not-a-real-key")

PRINTED = []      # every console.print line, raw
ASKED = []        # console.input answers
OPENAI_CALLS = [] # kwargs handed to OpenAI(...)


class FakeConsole:
    def print(self, *args, **kwargs):
        PRINTED.extend(str(a) for a in args)

    def log(self, *args, **kwargs):
        PRINTED.extend(str(a) for a in args)

    def input(self, *args, **kwargs):
        if not ASKED:
            raise EOFError
        return ASKED.pop(0)

    @contextlib.contextmanager
    def status(self, *args, **kwargs):
        #real console prints nothing when it is not a terminal
        yield self


class FakeText:
    """enough of rich.text.Text to keep agent.py honest"""

    def __init__(self, text="", style=None):
        self.parts = [(text, style)]

    def append(self, text="", style=None):
        self.parts.append((text, style))

    def __str__(self):
        return "".join(part for part, _ in self.parts)


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        OPENAI_CALLS.append(kwargs)


def _install_stubs():
    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda *a, **k: False
    sys.modules["dotenv"] = dotenv

    openai = types.ModuleType("openai")
    openai.OpenAI = FakeOpenAI
    sys.modules["openai"] = openai

    rich = types.ModuleType("rich")
    console_mod = types.ModuleType("rich.console")
    console_mod.Console = FakeConsole
    rich.console = console_mod
    sys.modules["rich"] = rich
    sys.modules["rich.console"] = console_mod

    for name, attribute in (("rich.markdown", "Markdown"),
                            ("rich.rule", "Rule"),
                            ("rich.text", "Text"),
                            ("rich.align", "Align"),
                            ("rich.panel", "Panel")):
        mod = types.ModuleType(name)
        setattr(mod, attribute, lambda *a, **k: a[0] if a else "")
        sys.modules[name] = mod

    sys.modules["rich.text"].Text = FakeText

    # Align.center has to exist as an attribute of rich.align
    sys.modules["rich.align"].Align = SimpleNamespace(
        center=lambda *a, **k: a[0] if a else ""
    )


_install_stubs()

import agent  # noqa: E402  (import after the stubs are in place)


# ---------- fakes ----------

class RateLimitError(Exception):
    pass


def tool_call(id_, name, arguments):
    return SimpleNamespace(
        id=id_,
        function=SimpleNamespace(name=name, arguments=arguments)
    )


def response(content=None, tool_calls=None, model="fake/model",
             prompt_tokens=None, completion_tokens=None):
    usage = None
    if prompt_tokens is not None or completion_tokens is not None:
        usage = SimpleNamespace(prompt_tokens=prompt_tokens,
                                completion_tokens=completion_tokens)

    return SimpleNamespace(
        model=model,
        usage=usage,
        choices=[SimpleNamespace(
            message=SimpleNamespace(content=content, tool_calls=tool_calls or [])
        )]
    )


class FakeClient:
    """replays a script of responses / exceptions, no network ever"""

    def __init__(self, script):
        self.script = list(script)
        self.calls = []       # kwargs of each create()
        self.snapshots = []   # history as it looked on each create()
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create)
        )

    def create(self, **kwargs):
        self.calls.append(kwargs)
        self.snapshots.append(deepcopy(agent.history))

        item = self.script.pop(0) if self.script else response("nothing left")

        if isinstance(item, Exception):
            raise item

        return item


def reset(client=None):
    agent.history.clear()
    PRINTED.clear()
    ASKED.clear()
    agent.client = client or FakeClient([])


# ---------- history rules ----------

def assert_history_valid(history):
    """no assistant tool_calls message without its tool results, ever"""
    index = 0

    while index < len(history):
        message = history[index]

        if message["role"] == "assistant" and message.get("tool_calls"):
            expected = sorted(tc["id"] for tc in message["tool_calls"])
            got = []

            index += 1
            while index < len(history) and history[index]["role"] == "tool":
                got.append(history[index]["tool_call_id"])
                index += 1

            assert sorted(got) == expected, (
                f"orphan tool_calls: expected {expected}, got {got}"
            )
            continue

        assert message["role"] != "tool", (
            f"tool message without tool_calls before it: {message}"
        )

        index += 1


# ---------- tests ----------

def test_defaults_are_env_overridable():
    source = pathlib.Path(agent.__file__).read_text(encoding="utf-8")

    assert 'os.environ.get("TAMIAS_BASE_URL", "https://openrouter.ai/api/v1")' in source
    assert 'os.environ.get("AGENT_MODEL", "poolside/laguna-s-2.1:free")' in source
    assert OPENAI_CALLS[-1]["base_url"] == agent.BASE_URL


def test_ask_default_is_25():
    args = agent.parse_args([])

    assert args.max_steps == 25
    assert args.task is None
    assert agent.parse_args(["--task", "hi", "--max-steps", "3"]).max_steps == 3


def test_name_is_the_project_name():
    source = pathlib.Path(agent.__file__).read_text(encoding="utf-8")

    assert "Krish" not in source
    assert "krish" not in source
    assert "TAMIAS" in source

    # six coloured rows, one per letter of TAMIAS
    assert len(agent.BANNER) == 6
    assert all(style for _, style in agent.BANNER)
    assert len({style for _, style in agent.BANNER}) >= 4

    reset()
    agent.print_banner()

    # the whole wordmark is one bordered card
    assert len(PRINTED) == 1
    assert PRINTED[0].startswith("██╗  ██╗")
    assert "a terminal coding agent" in PRINTED[0]
    assert agent.MODEL in PRINTED[0]
    assert "/quit to leave" in PRINTED[0]


def test_agent_calls_itself_tamias():
    reset(FakeClient([response("ready", prompt_tokens=1, completion_tokens=1)]))

    assert agent.run_turn("who are you?", 25, agent.new_stats()) == "done"

    system = agent.client.calls[0]["messages"][0]["content"]

    assert system.startswith("You are TAMIAS")
    assert any("TAMIAS ›" in line for line in PRINTED)


def test_usage_line_is_printed_and_none_safe():
    reset(FakeClient([
        response(None, [tool_call("c1", "list_directory", '{"path": "."}')],
                 prompt_tokens=11, completion_tokens=7),
        response("no usage reported on this one"),
    ]))

    stats = agent.new_stats()

    assert agent.run_turn("hello", 25, stats) == "done"

    joined = "\n".join(PRINTED)

    assert "step 1" in joined and "prompt 11" in joined and "completion 7" in joined
    assert "step 2" in joined and "prompt None" in joined
    assert stats["steps"] == 2
    assert stats["prompt_tokens"] == 11
    assert stats["completion_tokens"] == 7


def test_tool_loop_then_reply_keeps_history_valid():
    reset(FakeClient([
        response(None, [tool_call("c1", "list_directory", '{"path": "."}')],
                 prompt_tokens=10, completion_tokens=2),
        response("here you go", prompt_tokens=20, completion_tokens=3),
    ]))

    stats = agent.new_stats()

    assert agent.run_turn("what is here?", 25, stats) == "done"
    assert_history_valid(agent.history)

    roles = [m["role"] for m in agent.history]

    assert roles == ["user", "assistant", "tool", "assistant"]
    assert agent.history[-1]["content"] == "here you go"
    assert [c["model"] for c in agent.client.calls] == [agent.MODEL] * 2


def test_429_mid_tool_loop_rolls_back_history():
    """the API dies after tool results are in - history must not stay broken"""
    client = FakeClient([
        response(None, [
            tool_call("c1", "list_directory", '{"path": "."}'),
            tool_call("c2", "read_file", "{not json at all"),
        ], prompt_tokens=10, completion_tokens=2),
        RateLimitError("429 rate limit exceeded, please retry"),
    ])

    reset(client)
    agent.history.append({"role": "user", "content": "older turn"})
    agent.history.append({"role": "assistant", "content": "older reply"})

    stats = agent.new_stats()
    checkpoint = len(agent.history)

    assert agent.run_turn("break the loop", 25, stats) == "error"

    # error printed, not raised
    assert any("429" in line for line in PRINTED)

    # rolled all the way back to where the turn started
    assert len(agent.history) == checkpoint
    assert agent.history == [
        {"role": "user", "content": "older turn"},
        {"role": "assistant", "content": "older reply"},
    ]

    # it really was mid tool loop (tool results existed before the 429)
    assert len(client.calls) == 2
    assert [m["role"] for m in client.snapshots[1]] == \
        ["user", "assistant", "user", "assistant", "tool", "tool"]

    for snapshot in client.snapshots:
        assert_history_valid(snapshot)

    assert_history_valid(agent.history)


def test_broken_arguments_become_an_error_result():
    reset(FakeClient([
        response(None, [tool_call("c1", "read_file", "{broken")]),
        response("recovered"),
    ]))

    assert agent.run_turn("read something odd", 25, agent.new_stats()) == "done"
    assert_history_valid(agent.history)

    tool_message = [m for m in agent.history if m["role"] == "tool"][0]

    assert tool_message["tool_call_id"] == "c1"
    assert tool_message["content"].startswith("Error:")
    assert "read_file" in tool_message["content"]


def test_tool_crash_never_ends_the_program():
    def boom(tool_name, args):
        raise RuntimeError("tool exploded")

    reset(FakeClient([
        response(None, [tool_call("c1", "list_directory", '{"path": "."}')]),
        response("still alive"),
    ]))

    with mock.patch.object(agent, "dispatch_tool", boom):
        assert agent.run_turn("go", 25, agent.new_stats()) == "done"

    assert_history_valid(agent.history)

    tool_message = [m for m in agent.history if m["role"] == "tool"][0]

    assert tool_message["content"] == "Error: list_directory failed: tool exploded"
    assert agent.history[-1]["content"] == "still alive"

    #the card shows the failed tool, not a crash
    assert any("Error: list_directory failed" in line for line in PRINTED)


def test_step_cap_exits_1_and_rolls_back():
    looping = [tool_call("c1", "list_directory", '{"path": "."}')]

    client = FakeClient([response(None, looping, prompt_tokens=5,
                                  completion_tokens=1)] * 5)
    reset(client)

    assert agent.run_task("loop forever", 2) == 1
    assert len(client.calls) == 2  # capped, no third call
    assert agent.history == []
    assert_history_valid(agent.history)
    assert any("step cap of 2" in line for line in PRINTED)


def test_task_success_exits_0_with_one_line_summary():
    reset(FakeClient([
        response(None, [tool_call("c1", "list_directory", '{"path": "."}')],
                 prompt_tokens=10, completion_tokens=2),
        response("done", prompt_tokens=20, completion_tokens=4),
    ]))

    assert agent.run_task("look around", 25) == 0

    summary = [line for line in PRINTED if line.startswith("[dim]steps:")]

    assert len(summary) == 1
    assert "steps: 2" in summary[0]
    assert "prompt tokens: 30" in summary[0]
    assert "completion tokens: 6" in summary[0]


def test_task_api_error_exits_1():
    reset(FakeClient([RateLimitError("429 slow down")]))

    assert agent.run_task("do a thing", 25) == 1
    assert agent.history == []


def test_interactive_keeps_going_after_api_error():
    reset(FakeClient([
        RateLimitError("429 slow down"),
        response("second try worked"),
    ]))

    ASKED.extend(["", "first ask", "second ask", "/quit"])

    assert agent.interactive_loop(25) == 0
    assert_history_valid(agent.history)

    # "first ask" was rolled back by the 429, "second ask" is what stuck
    assert [m["content"] for m in agent.history] == \
        ["second ask", "second try worked"]


def test_interactive_help_command():
    reset(FakeClient([]))

    ASKED.extend(["/help", "/quit"])

    assert agent.interactive_loop(25) == 0

    printed = "\n".join(PRINTED)

    assert "--max-steps" in printed
    assert "run_shell" in printed
    assert agent.history == []  # help never reaches the model


def test_interactive_survives_eof():
    reset(FakeClient([]))

    assert agent.interactive_loop(25) == 0  # nothing queued -> EOFError
    assert "see you soon" in "\n".join(PRINTED)


def test_run_shell_uses_timeout_60():
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen.update(kwargs)
        raise subprocess.TimeoutExpired(command, 60)

    with mock.patch.object(subprocess, "run", fake_run):
        result = agent.run_shell("sleep 600")

    assert seen["timeout"] == 60
    assert seen["shell"] is True
    assert seen["capture_output"] is True
    assert result == "Error: command timed out after 60s"


def test_run_shell_returns_output():
    assert agent.run_shell("echo hello").strip() == "hello"


def test_cli_rejects_zero_steps():
    try:
        agent.main(["--max-steps", "0"])
    except SystemExit as exit_error:
        assert exit_error.code == 2
    else:
        raise AssertionError("--max-steps 0 should not be accepted")


def test_main_routes_task_mode():
    reset(FakeClient([response("answered", prompt_tokens=1, completion_tokens=2)]))

    assert agent.main(["--task", "what is 2+2?"]) == 0
    assert agent.client.calls[0]["messages"][1] == \
        {"role": "user", "content": "what is 2+2?"}


def _run_all():
    tests = [(name, fn) for name, fn in sorted(globals().items())
             if name.startswith("test_") and callable(fn)]
    failures = 0

    for name, fn in tests:
        try:
            fn()
        except Exception as error:
            failures += 1
            print(f"FAIL {name}: {type(error).__name__}: {error}")
        else:
            print(f"PASS {name}")

    print(f"\n{len(tests) - failures} passed, {failures} failed, "
          f"{len(tests)} total")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run_all())