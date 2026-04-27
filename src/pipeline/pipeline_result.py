from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from src.models import AgentNote, RollResult


@dataclass
class PipelineResult:
    tag_note: AgentNote
    roll: RollResult
    narrator_note: AgentNote
    effect_note: Optional[AgentNote] = None
    consequence_note: Optional[AgentNote] = None
