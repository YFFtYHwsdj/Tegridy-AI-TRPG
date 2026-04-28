from __future__ import annotations

from src.context import AgentContext
from src.models import Character
from src.state.scene_state import SceneState


class GameState:
    def __init__(self):
        self.character: Character | None = None
        self.scene: SceneState = SceneState()
        self.scene_history: list[SceneState] = []

    def setup(self, character: Character, scene: SceneState):
        self.character = character
        if self.scene.scene_description or self.scene.active_challenges:
            self.scene_history.append(self.scene)
        self.scene = scene

    def append_narrative(self, entry: str):
        self.scene.append_narrative(entry)

    def make_context(self, player_input: str = "") -> AgentContext:
        return self.scene.make_context(self.character, player_input)
