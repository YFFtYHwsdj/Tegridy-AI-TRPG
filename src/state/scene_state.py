from __future__ import annotations

from dataclasses import dataclass, field

from src.context import AgentContext
from src.formatter import format_limit_progress, format_statuses, format_story_tags
from src.models import NPC, Challenge, Character, Clue, GameItem

MAX_HISTORY_ENTRIES = 6
HISTORY_BUFFER = 2


@dataclass
class SceneState:
    scene_description: str = ""

    scene_items_visible: dict[str, GameItem] = field(default_factory=dict)
    scene_items_hidden: dict[str, GameItem] = field(default_factory=dict)

    clues_visible: dict[str, Clue] = field(default_factory=dict)
    clues_hidden: dict[str, Clue] = field(default_factory=dict)

    npcs: dict[str, NPC] = field(default_factory=dict)
    active_challenges: dict[str, Challenge] = field(default_factory=dict)

    narrative_history: list[str] = field(default_factory=list)

    def primary_challenge(self) -> Challenge | None:
        if not self.active_challenges:
            return None
        return next(iter(self.active_challenges.values()))

    def get_challenge(self, name: str) -> Challenge | None:
        return self.active_challenges.get(name)

    def add_challenge(self, challenge: Challenge):
        self.active_challenges[challenge.name] = challenge

    def append_narrative(self, entry: str):
        self.narrative_history.append(entry)
        if len(self.narrative_history) > MAX_HISTORY_ENTRIES + HISTORY_BUFFER:
            self.narrative_history = self.narrative_history[
                -(MAX_HISTORY_ENTRIES + HISTORY_BUFFER) :
            ]

    def make_context(self, character: Character | None, player_input: str = "") -> AgentContext:
        challenge = self.primary_challenge()
        return AgentContext(
            context_block=self._build_context_block(character, challenge),
            narrative_block=self._build_narrative_block(),
            character=character,
            challenge=challenge,
            player_input=player_input,
            extra={"scene_state": self},
        )

    def _build_context_block(self, character: Character | None, challenge: Challenge | None) -> str:
        if character is None or challenge is None:
            return ""

        char_tags = ", ".join(t.name for t in character.power_tags)
        char_weak = ", ".join(t.name for t in character.weakness_tags)
        char_status = format_statuses(character.statuses)
        char_story = format_story_tags(character.story_tags)

        progress = challenge.get_limit_progress()
        limits = ", ".join(
            format_limit_progress(limit, progress[limit.name]) for limit in challenge.limits
        )
        if not limits:
            limits = "（无极限设置）"

        lines = [
            f"场景: {self.scene_description}",
            f"角色: {character.name} - {character.description}",
            f"  力量标签: {char_tags}",
            f"  弱点标签: {char_weak}",
            f"  状态: {char_status}",
            f"  故事标签: {char_story}",
            f"挑战: {challenge.name} - {challenge.description}",
            f"  极限进度: {limits}",
        ]
        if challenge.broken_limits:
            lines.append(f"  已突破极限: {', '.join(challenge.broken_limits)}")
        if challenge.transformation:
            lines.append(f"  挑战转变: {challenge.transformation}")
        return "\n".join(lines)

    def _build_narrative_block(self) -> str:
        if not self.narrative_history:
            return "（无历史）"
        recent = self.narrative_history[-MAX_HISTORY_ENTRIES:]
        lines = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)
