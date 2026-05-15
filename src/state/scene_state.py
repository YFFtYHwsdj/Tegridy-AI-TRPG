"""场景状态管理 —— 单个场景的运行时切片。

SceneState 仅保存当前运行时的状态（当前发生在哪个 Place，
有哪些 NPC 和 Item 参与，当前突发情况是什么）。
具体的实体属性引用自 GlobalState。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from src.context import AgentContext
from src.formatter import format_statuses
from src.models import StoryTag

if TYPE_CHECKING:
    from src.state.character_state import CharacterState
    from src.state.global_state import GlobalState


@dataclass
class SceneState:
    """单个场景的运行时状态。

    Attributes:
        place_id: 当前所在地点 ID
        situation: 当前场景状况描述
        active_npc_ids: 场景中活跃的 NPC IDs
        active_item_ids: 场景中涉及的特殊物品 IDs
        story_tags: 当前场景临时的故事标签 (如 "起火了")
        narrative_history: 场景内的完整叙事历史
        compression: 场景结束后的压缩摘要
    """

    place_id: str = ""
    situation: str = ""

    active_npc_ids: list[str] = field(default_factory=list)
    active_item_ids: list[str] = field(default_factory=list)

    story_tags: dict[str, StoryTag] = field(default_factory=dict)

    narrative_history: list[str] = field(default_factory=list)
    compression: str = ""

    def append_narrative(self, entry: str):
        self.narrative_history.append(entry)

    def make_context(
        self, character: CharacterState | None, global_state: GlobalState, player_input: str = ""
    ) -> AgentContext:
        """构建 Agent 上下文对象。"""
        return AgentContext(
            assets_block=self._build_assets_block(global_state, character),
            context_block=self._build_context_block(global_state, character),
            narrative_block=self._build_narrative_block(),
            character=character,
            player_input=player_input,
            extra={"scene_state": self, "global_state": global_state},
        )

    def _build_context_block(
        self, global_state: GlobalState, character: CharacterState | None
    ) -> str:
        """构建当前状态快照文本块。"""
        lines = [f"当前状况: {self.situation}"]
        if character is None:
            return "\n".join(lines)

        lines.append(character.build_context_block(include_tracks=True))

        if self.active_npc_ids:
            lines.append("当前活跃的NPC状态:")
            for nid in self.active_npc_ids:
                npc = global_state.npcs.get(nid)
                if npc:
                    npc_status = format_statuses(npc.statuses)
                    lines.append(f"  - {npc.name}: 状态 {npc_status}")

        return "\n".join(lines)

    def _build_narrative_block(self) -> str:
        """构建叙事历史文本块。"""
        if not self.narrative_history:
            return "（无历史）"
        lines = []
        for i, entry in enumerate(self.narrative_history, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)

    def _build_assets_block(
        self, global_state: GlobalState, character: CharacterState | None
    ) -> str:
        """构建当前场景资产文本块。"""
        lines = ["=== 场景资产 ==="]

        if self.active_npc_ids:
            lines.append("\n场景人物:")
            for nid in self.active_npc_ids:
                npc = global_state.npcs.get(nid)
                if npc:
                    lines.append(f"  - {npc.name}: {npc.description}")
        else:
            lines.append("\n场景人物: （无）")

        if self.active_item_ids:
            lines.append("\n场景物品:")
            for iid in self.active_item_ids:
                item = global_state.items.get(iid)
                if item:
                    loc = f" [{item.location}]" if item.location else ""
                    lines.append(f"  - {item.name}{loc}: {item.description}")
        else:
            lines.append("\n场景物品: （无）")

        if character and character.items_visible:
            lines.append(f"\n{character.name}的随身物品:")
            for item in character.items_visible.values():
                lines.append(f"  - {item.name}: {item.description}")
        else:
            lines.append(f"\n{character.name if character else '角色'}的随身物品: （无）")

        return "\n".join(lines)
