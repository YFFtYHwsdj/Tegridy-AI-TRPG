from __future__ import annotations

from dataclasses import dataclass

from src.models import AgentNote, RollResult


@dataclass
class PipelineResult:
    tag_note: AgentNote
    roll: RollResult
    narrator_note: AgentNote
    effect_note: AgentNote | None = None
    consequence_note: AgentNote | None = None
