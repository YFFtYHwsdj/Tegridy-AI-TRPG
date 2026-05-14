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
        """为角色施加状态。"""
        if not label or tier <= 0 or not self.state.character:
            return
        apply_status(self.state.character, label, tier)

    def nudge_status(self, label: str):
        """将角色状态恶化一级。"""
        if not label or not self.state.character:
            return
        nudge_status(self.state.character, label)

    def reduce_status(self, label: str, reduce_by: int = 1):
        """降低角色状态。"""
        if not label or reduce_by <= 0 or not self.state.character:
            return
        reduce_status(self.state.character, label, reduce_by)

    def add_personal_tag(self, name: str, description: str = "", is_single_use: bool = False):
        """为角色添加个人故事标签。"""
        if not name or not self.state.character:
            return
        add_story_tag(self.state.character, name, description, is_single_use)

    def remove_personal_tag(self, name: str) -> bool:
        """移除角色身上的个人故事标签。"""
        if not name or not self.state.character:
            return False
        return remove_story_tag(self.state.character, name) is not None
