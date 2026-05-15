import unittest

from src.models import Clue
from src.pipeline.managers.clue_manager import ClueManager
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class TestClueManager(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.state.scene = SceneState(place_id="loc1")
        self.manager = ClueManager(self.state)

    def test_reveal_clue_success(self):
        clue = Clue(clue_id="c1", name="Secret Document")
        self.state.scene.clues_hidden["c1"] = clue

        result = self.manager.reveal_clue("c1")

        self.assertTrue(result)
        self.assertNotIn("c1", self.state.scene.clues_hidden)
        self.assertIn("c1", self.state.scene.clues_visible)
        self.assertEqual(self.state.scene.clues_visible["c1"].name, "Secret Document")

    def test_reveal_clue_fails_if_not_found(self):
        result = self.manager.reveal_clue("nonexistent")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
