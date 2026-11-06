#!/usr/bin/env python3
"""A tiny OpenAI-compatible *mock* model, for demos when the real provider is
unavailable (e.g. a free-tier 429).

This is NOT a model and NOT the agent. It is a deterministic stub that returns a
scripted tool call, so the agent's own loop - scope gate, plan check, path fence,
stop-on-block - can be shown end to end without a network call. Point the agent
at it with:

    TAMIAS_BASE_URL=http://127.0.0.1:8099/v1 TAMIAS_API_KEY=mock \
        .venv/bin/python agent.py --company-id todoinc \
        --policy policies/todoinc-todo.toml --task "create todo in desktop"

It answers:
  * first call  -> a `write_file` tool call whose target depends on the ask:
        - ask mentions "desktop" (or "outside") -> <home>/Desktop/todo.txt
          (outside the product, so the agent's own path fence must block it)
        - otherwise                            -> inside the product
  * after a tool result -> a short final sentence.

Say clearly in a demo that this is a mock model. Never present it as a live run.
"""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PRODUCT_TARGET = "company/work/todoinc/apps/todo/todo.txt"


def last_user_text(messages):
    for message in reversed(messages):
        if message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def tool_call_response(model, target):
    arguments = json.dumps({
        "file_path": target,
        "content": "- [ ] buy milk\n- [ ] walk the dog\n",
    })

    return {
        "id": "chatcmpl-mock-tools",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_mock_1",
                    "type": "function",
                    "function": {"name": "write_file", "arguments": arguments},
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 42, "completion_tokens": 12,
                  "total_tokens": 54},
    }


def text_response(model, content):
    return {
        "id": "chatcmpl-mock-text",
        "object": "chat.completion",
        "created": 0,
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4,
                  "total_tokens": 12},
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep the demo output clean

    def _send(self, payload, status=200):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/v1/models"):
            self._send({"object": "list", "data": [
                {"id": "mock/model", "object": "model"}]})
        else:
            self._send({"error": "not found"}, status=404)

    def do_POST(self):
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._send({"error": "not found"}, status=404)
            return

        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        messages = body.get("messages", [])
        model = body.get("model", "mock/model")

        if any(m.get("role") == "tool" for m in messages):
            payload = text_response(model, "Done - the todo item is created.")
        else:
            ask = last_user_text(messages).lower()
            if "desktop" in ask or "outside" in ask:
                target = str(Path.home() / "Desktop" / "todo.txt")
            else:
                target = PRODUCT_TARGET
            payload = tool_call_response(model, target)

        print(f"[mock] ask={last_user_text(messages)!r} -> "
              f"{payload['choices'][0]['finish_reason']}", file=sys.stderr)
        self._send(payload)


def main():
    parser = argparse.ArgumentParser(description="mock OpenAI-compatible model")
    parser.add_argument("--port", type=int,
                        default=int(os.environ.get("MOCK_PORT", "8099")))
    args = parser.parse_args()

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"[mock] OpenAI-compatible mock listening on "
          f"http://127.0.0.1:{args.port}/v1", file=sys.stderr)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
