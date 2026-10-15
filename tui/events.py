import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

@dataclass
class TUIEvent:
    """Base class for all events emitted by the agent core."""
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
        
    def to_json(self) -> str:
        return json.dumps(self.to_dict())

@dataclass
class TurnStart(TUIEvent):
    """Emitted when a new turn begins (user input received)."""
    user_prompt: str
    session_id: str

@dataclass
class StatusUpdate(TUIEvent):
    """Emitted for 'thinking...' indicators or general agent status."""
    message: str
    is_busy: bool

@dataclass
class MessageDelta(TUIEvent):
    """Emitted when the LLM streams text."""
    content: str
    model: str
    
@dataclass
class ToolStart(TUIEvent):
    """Emitted when the agent decides to call a tool."""
    tool_call_id: str
    tool_name: str
    arguments: str # JSON string of arguments

@dataclass
class ToolProgress(TUIEvent):
    """Emitted for long-running tools to update the UI."""
    tool_call_id: str
    output_chunk: str

@dataclass
class ToolEnd(TUIEvent):
    """Emitted when a tool finishes executing."""
    tool_call_id: str
    result: str
    success: bool
    duration_sec: float

@dataclass
class ToolAsk(TUIEvent):
    """Emitted when a tool call needs a human yes/no before it can run.

    The agent worker is blocked until the view answers; with no view (or a
    timeout) the answer is no, so an ask only ever fails closed.
    """
    tool_name: str
    arguments: str   # JSON string of arguments
    reason: str

@dataclass
class TurnEnd(TUIEvent):
    """Emitted when the agent finishes its response loop."""
    prompt_tokens: int
    completion_tokens: int
    total_duration_sec: float
    # provider-billed USD for the turn; None when the provider reported none,
    # so a missing cost is never mistaken for a free turn
    cost_usd: Optional[float] = None
    # how many API steps in the turn came back without a reported cost, so the
    # session total can be shown as partial rather than silently complete
    unpriced_steps: int = 0

@dataclass
class ErrorEvent(TUIEvent):
    """Emitted when a critical agent error occurs."""
    error_type: str
    message: str
    fatal: bool
