from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentContext:
    context_block: str
    narrative_block: str
    character: Optional["Character"] = None
    challenge: Optional["Challenge"] = None
    player_input: str = ""
    extra: dict = field(default_factory=dict)
