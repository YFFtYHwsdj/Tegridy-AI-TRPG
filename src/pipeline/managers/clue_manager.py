"""线索管理器 —— 负责管理信息的揭示。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from src.logger import log_system

if TYPE_CHECKING:
    from src.state.game_state import GameState


class ClueManager:
    """管理场景中隐藏线索的揭示。"""

    def __init__(self, state: GameState):
        self.state = state

    def reveal_clue(self, clue_id: str) -> bool:
        """将隐藏线索揭示为可见线索。

        Args:
            clue_id: 线索ID

        Returns:
            bool: 是否成功找到并揭示
        """
        scene = self.state.scene
        if clue_id in scene.clues_hidden:
            clue = scene.clues_hidden.pop(clue_id)
            scene.clues_visible[clue_id] = clue
            return True

        log_system(f"未找到线索 '{clue_id}'", level="warning")
        return False
