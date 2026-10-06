from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal, Container
from textual.widgets import Static, Markdown, Footer
from textual.color import Color

# The fake events to drive the UI
FAKE_EVENTS = [
    {"type": "TurnStart", "user_prompt": "Please scan the project for security vulnerabilities."},
    {"type": "StatusUpdate", "message": "Analyzing files..."},
    {"type": "ToolStart", "tool_name": "grep_search", "arguments": "{'Query': 'password'}"},
    {"type": "ToolEnd", "success": True, "result": "Found 3 hardcoded passwords."},
    {"type": "MessageDelta", "content": "I found some potential security issues. Here is the code:\n```python\npassword = '123'\n```"},
]

TCSS = """
Screen {
    background: transparent;
    layout: vertical;
}

#transcript {
    width: 100%;
    height: 1fr;
    overflow-y: auto;
}

.chat-bubble {
    width: auto;
    max-width: 80%;
    margin: 1 2;
    padding: 1 2;
    border: round rgba(255, 255, 255, 0.1);
    background: rgba(255, 255, 255, 0.05);
}

.user-bubble {
    dock: right;
    border-top: round #00ff9f;
}

.agent-bubble {
    dock: left;
    border-top: round #00b8ff;
}

.tool-card {
    margin: 0 4;
    padding: 0 1;
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.02);
    border: vkey rgba(255, 255, 255, 0.1);
}

#composer {
    height: 3;
    border-top: solid rgba(255, 255, 255, 0.2);
    padding: 0 2;
    background: #0f111a;
}
"""

class UIDemo(App):
    CSS = TCSS

    def compose(self) -> ComposeResult:
        with Vertical(id="transcript"):
            yield Static("❯ Please scan the project for security vulnerabilities.", classes="chat-bubble user-bubble")
            yield Static("⮑  grep_search({'Query': 'password'}) ✓ 1.2s", classes="tool-card")
            yield Markdown("I found some potential security issues. Here is the code:\n```python\npassword = '123'\n```", classes="chat-bubble agent-bubble")
        
        yield Static("│ ❯ type your message here...", id="composer")

    def on_mount(self) -> None:
        self.set_timer(0.5, self.take_screenshot)

    def take_screenshot(self) -> None:
        svg = self.export_screenshot()
        with open("docs/tui/iterations/01/hero2_120.svg", "w") as f:
            f.write(svg)
        self.exit()

if __name__ == "__main__":
    app = UIDemo()
    app.run()
