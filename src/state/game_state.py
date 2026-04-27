from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from src.models import Character, Challenge
from src.formatter import format_statuses, format_story_tags, format_limit_progress
from src.context import AgentContext

MAX_HISTORY_ENTRIES = 6
HISTORY_BUFFER = 2


@dataclass
class GameState:
    character: Optional[Character] = None
    challenge: Optional[Challenge] = None
    scene_context: str = ""
    narrative_history: list[str] = field(default_factory=list)

    def setup(self, character: Character, challenge: Challenge, scene_desc: str):
        self.character = character
        self.challenge = challenge
        self.scene_context = scene_desc
        self.narrative_history = []

    def append_narrative(self, entry: str):
        self.narrative_history.append(entry)
        if len(self.narrative_history) > MAX_HISTORY_ENTRIES + HISTORY_BUFFER:
            self.narrative_history = self.narrative_history[-(MAX_HISTORY_ENTRIES + HISTORY_BUFFER):]

    def make_context(self, player_input: str = "") -> AgentContext:
        return AgentContext(
            context_block=self._build_context_block(),
            narrative_block=self._build_narrative_block(),
            character=self.character,
            challenge=self.challenge,
            player_input=player_input,
        )

    def _build_context_block(self) -> str:
        if self.character is None or self.challenge is None:
            return ""

        char_tags = ", ".join(t.name for t in self.character.power_tags)
        char_weak = ", ".join(t.name for t in self.character.weakness_tags)
        char_status = format_statuses(self.character.statuses)
        char_story = format_story_tags(self.character.story_tags)

        progress = self.challenge.get_limit_progress()
        limits = ", ".join(
            format_limit_progress(limit, progress[limit.name])
            for limit in self.challenge.limits
        )
        if not limits:
            limits = "（无极限设置）"

        lines = [
            f"场景: {self.scene_context}",
            f"角色: {self.character.name} - {self.character.description}",
            f"  力量标签: {char_tags}",
            f"  弱点标签: {char_weak}",
            f"  状态: {char_status}",
            f"  故事标签: {char_story}",
            f"挑战: {self.challenge.name} - {self.challenge.description}",
            f"  极限进度: {limits}",
        ]
        if self.challenge.broken_limits:
            lines.append(f"  已突破极限: {', '.join(self.challenge.broken_limits)}")
        if self.challenge.transformation:
            lines.append(f"  挑战转变: {self.challenge.transformation}")
        return "\n".join(lines)

    def _build_narrative_block(self) -> str:
        if not self.narrative_history:
            return "（无历史）"
        recent = self.narrative_history[-MAX_HISTORY_ENTRIES:]
        lines = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)
