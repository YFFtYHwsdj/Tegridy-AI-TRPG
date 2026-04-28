from __future__ import annotations

from typing import Optional
from src.models import Character, Challenge
from src.context import AgentContext
from src.state.scene_state import SceneState, MAX_HISTORY_ENTRIES, HISTORY_BUFFER


class GameState:
    def __init__(self):
        self.character: Optional[Character] = None
        self.scene: SceneState = SceneState()
        self.scene_history: list[SceneState] = []

    def setup(self, character: Character, challenge: Challenge, scene_desc: str):
        self.character = character
        if self.scene.scene_description or self.scene.active_challenges:
            self.scene_history.append(self.scene)
        self.scene = SceneState(scene_description=scene_desc)
        self.scene.add_challenge(challenge)

    def append_narrative(self, entry: str):
        self.scene.append_narrative(entry)

    def make_context(self, player_input: str = "") -> AgentContext:
        return self.scene.make_context(self.character, player_input)
