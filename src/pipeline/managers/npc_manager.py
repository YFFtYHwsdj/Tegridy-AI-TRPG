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
        """获取场景中指定的 NPC 对象。

        Args:
            npc_id: NPC 的唯一标识符

        Returns:
            返回找到的 NPC 对象，如果未找到则返回 None
        """
        return self.state.scene.npcs.get(npc_id)

    def apply_status(self, npc_id: str, label: str, tier: int):
        """为特定 NPC 施加状态。

        支持状态叠加溢出机制。如果 NPC 不存在，则静默忽略。

        Args:
            npc_id: 目标 NPC 的标识符
            label: 状态名称
            tier: 状态等级 (1-6)
        """
        if not label or tier <= 0:
            return
        npc = self.get_npc(npc_id)
        if npc:
            apply_status(npc, label, tier)

    def nudge_status(self, npc_id: str, label: str):
        """将特定 NPC 状态恶化一级。

        如果状态不存在则从 tier 1 开始。NPC 不存在则忽略。

        Args:
            npc_id: 目标 NPC 的标识符
            label: 状态名称
        """
        if not label:
            return
        npc = self.get_npc(npc_id)
        if npc:
            nudge_status(npc, label)

    def reduce_status(self, npc_id: str, label: str, reduce_by: int = 1):
        """降低特定 NPC 状态。

        Args:
            npc_id: 目标 NPC 的标识符
            label: 状态名称
            reduce_by: 降低的等级数，默认为 1
        """
        if not label or reduce_by <= 0:
            return
        npc = self.get_npc(npc_id)
        if npc:
            reduce_status(npc, label, reduce_by)

    def add_personal_tag(
        self, npc_id: str, name: str, description: str = "", is_single_use: bool = False
    ):
        """为特定 NPC 添加个人故事标签。

        通过在场景的故事标签字典中加上 "[NPC名]" 前缀来实现个人标签的效果。

        Args:
            npc_id: 目标 NPC 的标识符
            name: 标签名称
            description: 标签描述文本
            is_single_use: 是否为单次消耗品
        """
        if not name:
            return
        npc = self.get_npc(npc_id)
        if npc:
            add_story_tag(self.state.scene, f"[{npc.name}] {name}", description, is_single_use)

    def remove_personal_tag(self, npc_id: str, name: str) -> bool:
        """移除特定 NPC 身上的个人故事标签。

        Args:
            npc_id: 目标 NPC 的标识符
            name: 标签名称

        Returns:
            bool: 成功移除返回 True，未找到该标签则返回 False
        """
        if not name:
            return False
        npc = self.get_npc(npc_id)
        if npc:
            return remove_story_tag(self.state.scene, f"[{npc.name}] {name}") is not None
        return False
