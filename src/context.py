from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import Challenge, Character


@dataclass
class AgentContext:
    context_block: str
    narrative_block: str
    character: Character | None = None
    challenge: Challenge | None = None
    player_input: str = ""
    extra: dict = field(default_factory=dict)
