"""NPC 管理器 —— 负责管理场景中 NPC 的状态与标签。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine import add_story_tag, apply_status, nudge_status, reduce_status, remove_story_tag

if TYPE_CHECKING:
    from src.models import NPC
    from src.state.game_state import GameState


class NPCManager:
    """管理场景中各个 NPC 的状态与故事标签。"""

    def __init__(self, state: GameState):
        self.state = state

    def get_npc(self, npc_id: str) -> NPC | None:
        return self.state.scene.npcs.get(npc_id)

    def apply_status(self, npc_id: str, label: str, tier: int):
        """为特定 NPC 施加状态。"""
        if not label or tier <= 0:
            return
        npc = self.get_npc(npc_id)
        if npc:
            apply_status(npc, label, tier)

    def nudge_status(self, npc_id: str, label: str):
        """将特定 NPC 状态恶化一级。"""
        if not label:
            return
        npc = self.get_npc(npc_id)
        if npc:
            nudge_status(npc, label)

    def reduce_status(self, npc_id: str, label: str, reduce_by: int = 1):
        """降低特定 NPC 状态。"""
        if not label or reduce_by <= 0:
            return
        npc = self.get_npc(npc_id)
        if npc:
            reduce_status(npc, label, reduce_by)

    def add_personal_tag(
        self, npc_id: str, name: str, description: str = "", is_single_use: bool = False
    ):
        """为特定 NPC 添加个人故事标签。"""
        if not name:
            return
        npc = self.get_npc(npc_id)
        if npc:
            add_story_tag(npc, name, description, is_single_use)

    def remove_personal_tag(self, npc_id: str, name: str) -> bool:
        """移除特定 NPC 身上的个人故事标签。"""
        if not name:
            return False
        npc = self.get_npc(npc_id)
        if npc:
            return remove_story_tag(npc, name) is not None
        return False
