"""故事标签管理器 —— 负责管理场景的环境与叙事标签。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.engine import add_story_tag, remove_story_tag

if TYPE_CHECKING:
    from src.state.game_state import GameState


class StoryTagManager:
    """管理场景（环境）上的故事标签（Story Tags）。"""

    def __init__(self, state: GameState):
        self.state = state

    def add_scene_tag(self, name: str, description: str = "", is_single_use: bool = False):
        """向场景中添加一个故事标签。"""
        if not name:
            return
        add_story_tag(self.state.scene, name, description, is_single_use)

    def remove_scene_tag(self, name: str) -> bool:
        """从场景中移除一个故事标签。"""
        if not name:
            return False
        return remove_story_tag(self.state.scene, name) is not None
