"""状态模块入口。"""

from __future__ import annotations

from src.state.game_state import GameState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState

__all__ = ["GameState", "GlobalState", "SceneState"]
