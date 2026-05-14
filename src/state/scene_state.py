"""场景状态管理 —— 单个场景的完整数据和上下文构建。

本模块定义了 SceneState 数据类，管理一个场景内的所有数据：
    - 场景描述与活跃挑战
    - NPC、线索、物品（可见/隐藏）
    - 叙事历史（场景内完整保留）
    - 场景压缩摘要与前驱场景引用
    - Agent 上下文构建（拼接场景资产、角色、挑战、叙事历史为上下文块）

场景作为上下文单元，叙事历史在场景内完整保留。
场景切换时产生压缩摘要，前驱场景引用支持回溯链。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from src.context import AgentContext
from src.formatter import format_statuses
from src.models import NPC, Clue, GameItem, StoryTag
from src.state.character_state import CharacterState


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
        narrative_history: 叙事历史列表（最新在后，场景内完整保留）
        compression: 场景结束后的压缩摘要（CompressorAgent 产出）
    """

    scene_description: str = ""

    scene_items_visible: dict[str, GameItem] = field(default_factory=dict)
    scene_items_hidden: dict[str, GameItem] = field(default_factory=dict)

    clues_visible: dict[str, Clue] = field(default_factory=dict)
    clues_hidden: dict[str, Clue] = field(default_factory=dict)

    npcs: dict[str, NPC] = field(default_factory=dict)
    story_tags: dict[str, StoryTag] = field(default_factory=dict)

    narrative_history: list[str] = field(default_factory=list)
    compression: str = ""

    def append_narrative(self, entry: str):
        """追加叙事条目。

        Args:
            entry: 叙事文本
        """
        self.narrative_history.append(entry)

    def make_context(
        self, character: CharacterState | None, player_input: str = ""
    ) -> AgentContext:
        """构建 Agent 上下文对象。

        将场景资产、状态快照、叙事历史拼接为三个文本块：
            - assets_block: 场景资产（NPC、线索、物品）
            - context_block: 当前状态快照（场景、角色、叙事历史）
            - narrative_block: 叙事历史

        Args:
            character: 玩家角色
            player_input: 玩家当前输入文本

        Returns:
            AgentContext: 完整的 Agent 上下文
        """
        return AgentContext(
            assets_block=self._build_assets_block(character),
            context_block=self._build_context_block(character),
            narrative_block=self._build_narrative_block(),
            character=character,
            player_input=player_input,
            extra={"scene_state": self},
        )

    def _build_context_block(self, character: CharacterState | None) -> str:
        """构建当前状态快照文本块。

        包含场景描述、角色标签/状态等，
        供 Agent 在推理时参考。

        Args:
            character: 玩家角色

        Returns:
            格式化的上下文文本块
        """
        lines = [f"场景: {self.scene_description}"]
        if character is None:
            return "\n".join(lines)

        lines.append(character.build_context_block(include_tracks=True))

        if self.npcs:
            lines.append("场景NPC:")
            for npc in self.npcs.values():
                npc_status = format_statuses(npc.statuses)
                lines.append(f"  - {npc.name}: 状态 {npc_status}")

        return "\n".join(lines)

    def _build_narrative_block(self) -> str:
        """构建叙事历史文本块。

        取场景内全部叙事记录，按时间顺序排列（最早在前）。

        Returns:
            格式化的叙事历史文本
        """
        if not self.narrative_history:
            return "（无历史）"
        lines = []
        for i, entry in enumerate(self.narrative_history, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)

    def _build_assets_block(self, character: CharacterState | None) -> str:
        """构建场景资产文本块。

        包含 NPC、线索、场景物品、角色随身物品等场景资产信息，
        供所有 Agent 了解场景中的实体分布。线索和物品标注可见/隐藏状态。

        Args:
            character: 玩家角色

        Returns:
            格式化的场景资产文本块
        """
        lines = ["=== 场景资产 ==="]

        # NPC
        if self.npcs:
            lines.append("\n场景人物:")
            for npc in self.npcs.values():
                parts = [f"  - {npc.name}: {npc.description}"]
                vis_items: list[str] = [f"{i.name}(可见)" for i in npc.items_visible.values()]
                hid_items: list[str] = [f"{i.name}(隐藏)" for i in npc.items_hidden.values()]
                npc_items: list[str] = vis_items + hid_items
                if npc_items:
                    parts.append(f" [携带: {', '.join(npc_items)}]")
                lines.append("".join(parts))
        else:
            lines.append("\n场景人物: （无）")

        # 线索
        all_clues: list[tuple[str, Clue, str]] = []
        for cid, clue in self.clues_visible.items():
            all_clues.append((cid, clue, "可见"))
        for cid, clue in self.clues_hidden.items():
            all_clues.append((cid, clue, "隐藏"))
        if all_clues:
            lines.append("\n线索:")
            for _cid, clue, vis in all_clues:
                lines.append(f"  - {clue.name}({vis}): {clue.description}")
        else:
            lines.append("\n线索: （无）")

        # 场景物品
        all_items: list[tuple[str, GameItem, str]] = []
        for iid, item in self.scene_items_visible.items():
            all_items.append((iid, item, "可见"))
        for iid, item in self.scene_items_hidden.items():
            all_items.append((iid, item, "隐藏"))
        if all_items:
            lines.append("\n场景物品:")
            for _iid, item, vis in all_items:
                loc = f" [{item.location}]" if item.location else ""
                lines.append(f"  - {item.name}{loc}: {item.description} ({vis})")
        else:
            lines.append("\n场景物品: （无）")

        # 角色随身物品
        if character and character.items_visible:
            lines.append(f"\n{character.name}的随身物品:")
            for item in character.items_visible.values():
                lines.append(f"  - {item.name}: {item.description}")
        else:
            lines.append(f"\n{character.name if character else '角色'}的随身物品: （无）")

        return "\n".join(lines)
