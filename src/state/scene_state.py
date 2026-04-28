"""场景状态管理 —— 单个场景的完整数据和上下文构建。

本模块定义了 SceneState 数据类，管理一个场景内的所有数据：
    - 场景描述与活跃挑战
    - NPC、线索、物品（可见/隐藏）
    - 叙事历史（带滚动窗口限制）
    - Agent 上下文构建（拼接角色、挑战、叙事历史为上下文块）

场景作为上下文单元，叙事历史保留最近 MAX_HISTORY_ENTRIES 条，
超出时自动丢弃最旧的条目，避免 Agent 上下文无限膨胀。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.context import AgentContext
from src.formatter import format_limit_progress, format_statuses, format_story_tags
from src.models import NPC, Challenge, Character, Clue, GameItem

# 叙事历史保留条数：Agent 上下文只取最近 6 条
MAX_HISTORY_ENTRIES = 6
# 额外缓冲：在丢弃之前多保留 2 条，减少频繁截断
HISTORY_BUFFER = 2


@dataclass
class SceneState:
    """单个场景的完整状态数据。

    Attributes:
        scene_description: 场景描述文本
        scene_items_visible: 场景中可见物品
        scene_items_hidden: 场景中隐藏物品（需探索）
        clues_visible: 已揭示的线索
        clues_hidden: 未揭示的线索
        npcs: 场景中的 NPC
        active_challenges: 活跃的挑战（通常一个场景只有一个主挑战）
        narrative_history: 叙事历史列表（最新在后，自动截断）
    """

    scene_description: str = ""

    scene_items_visible: dict[str, GameItem] = field(default_factory=dict)
    scene_items_hidden: dict[str, GameItem] = field(default_factory=dict)

    clues_visible: dict[str, Clue] = field(default_factory=dict)
    clues_hidden: dict[str, Clue] = field(default_factory=dict)

    npcs: dict[str, NPC] = field(default_factory=dict)
    active_challenges: dict[str, Challenge] = field(default_factory=dict)

    narrative_history: list[str] = field(default_factory=list)

    def primary_challenge(self) -> Challenge | None:
        """获取当前场景的主挑战（第一个活跃挑战）。

        Returns:
            Challenge 或 None
        """
        if not self.active_challenges:
            return None
        return next(iter(self.active_challenges.values()))

    def get_challenge(self, name: str) -> Challenge | None:
        """按名称查找挑战。

        Args:
            name: 挑战名称

        Returns:
            Challenge 或 None
        """
        return self.active_challenges.get(name)

    def add_challenge(self, challenge: Challenge):
        """向场景添加一个挑战。

        Args:
            challenge: 挑战对象
        """
        self.active_challenges[challenge.name] = challenge

    def append_narrative(self, entry: str):
        """追加叙事条目，自动维护滚动窗口。

        叙事历史保持在 MAX_HISTORY_ENTRIES + HISTORY_BUFFER 条以内。
        超出时截断保留最近的部分，避免 Agent 上下文无限膨胀。

        Args:
            entry: 叙事文本
        """
        self.narrative_history.append(entry)
        if len(self.narrative_history) > MAX_HISTORY_ENTRIES + HISTORY_BUFFER:
            self.narrative_history = self.narrative_history[
                -(MAX_HISTORY_ENTRIES + HISTORY_BUFFER) :
            ]

    def make_context(self, character: Character | None, player_input: str = "") -> AgentContext:
        """构建 Agent 上下文对象。

        将场景信息、角色信息、叙事历史拼接为两个文本块：
            - context_block: 当前状态快照（场景、角色、挑战、极限进度）
            - narrative_block: 最近叙事历史

        Args:
            character: 玩家角色
            player_input: 玩家当前输入文本

        Returns:
            AgentContext: 完整的 Agent 上下文
        """
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
        """构建当前状态快照文本块。

        包含场景描述、角色标签/状态、挑战信息、极限进度等，
        供 Agent 在推理时参考。

        Args:
            character: 玩家角色
            challenge: 当前挑战

        Returns:
            格式化的上下文文本块
        """
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
        """构建叙事历史文本块。

        取最近 MAX_HISTORY_ENTRIES 条叙事记录，编号排列。

        Returns:
            格式化的叙事历史文本
        """
        if not self.narrative_history:
            return "（无历史）"
        recent = self.narrative_history[-MAX_HISTORY_ENTRIES:]
        lines = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)
