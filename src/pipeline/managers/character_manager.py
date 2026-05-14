"""玩家角色管理器 —— 负责管理玩家角色的状态与标签。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine import add_story_tag, apply_status, nudge_status, reduce_status, remove_story_tag

if TYPE_CHECKING:
    from src.state.game_state import GameState


class CharacterManager:
    """管理玩家角色（PC）的自身数据：状态、故事标签等。"""

    def __init__(self, state: GameState):
        self.state = state

    def apply_status(self, label: str, tier: int):
        """为角色施加状态。

        如果目标状态等级已存在，则自动触发溢出机制。

        Args:
            label: 状态名称
            tier: 状态等级 (1-6)
        """
        if not label or tier <= 0 or not self.state.character:
            return
        apply_status(self.state.character, label, tier)

    def nudge_status(self, label: str):
        """将角色状态恶化一级。

        来自 Otherscape 机制的轻推效果。如果该状态尚未存在，则默认从 tier 1 开始。

        Args:
            label: 状态名称
        """
        if not label or not self.state.character:
            return
        nudge_status(self.state.character, label)

    def reduce_status(self, label: str, reduce_by: int = 1):
        """降低角色状态。

        Args:
            label: 状态名称
            reduce_by: 降低的等级数，默认为 1
        """
        if not label or reduce_by <= 0 or not self.state.character:
            return
        reduce_status(self.state.character, label, reduce_by)

    def add_personal_tag(self, name: str, description: str = "", is_single_use: bool = False):
        """为角色添加个人故事标签。

        Args:
            name: 标签名称
            description: 标签描述文本
            is_single_use: 是否为单次消耗品
        """
        if not name or not self.state.character:
            return
        add_story_tag(self.state.character, name, description, is_single_use)

    def remove_personal_tag(self, name: str) -> bool:
        """移除角色身上的个人故事标签。

        Args:
            name: 标签名称

        Returns:
            bool: 成功移除返回 True，未找到该标签则返回 False
        """
        if not name or not self.state.character:
            return False
        return remove_story_tag(self.state.character, name) is not None
