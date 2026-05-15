import unittest

from src.pipeline.managers.character_manager import CharacterManager
from src.state.character_state import CharacterState
from src.state.game_state import GameState


class TestCharacterManager(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.state.character = CharacterState(name="Hero")
        self.manager = CharacterManager(self.state)
        self.char = self.state.character

    def test_apply_status_to_character(self):
        self.manager.apply_status("injured", 2)
        self.assertEqual(self.char.statuses["injured"].current_tier, 2)

    def test_apply_status_ignores_invalid_tier(self):
        self.manager.apply_status("injured", 0)
        self.assertNotIn("injured", self.char.statuses)

    def test_nudge_status_on_character(self):
        self.manager.nudge_status("tired")
        self.assertEqual(self.char.statuses["tired"].current_tier, 1)
        self.manager.nudge_status("tired")
        self.assertEqual(self.char.statuses["tired"].current_tier, 2)

    def test_nudge_status_ignores_empty_label(self):
        self.manager.nudge_status("")
        self.assertEqual(len(self.char.statuses), 0)

    def test_reduce_status_on_character(self):
        self.manager.apply_status("injured", 1)
        self.manager.apply_status("injured", 1)  # overflows to 2
        self.manager.reduce_status("injured", 1)
        self.assertEqual(self.char.statuses["injured"].current_tier, 1)

    def test_reduce_status_removes_if_zero(self):
        self.manager.apply_status("injured", 1)
        self.manager.reduce_status("injured", 1)
        self.assertNotIn("injured", self.char.statuses)

    def test_reduce_status_ignores_invalid_params(self):
        self.manager.apply_status("injured", 2)
        self.manager.reduce_status("", 1)
        self.manager.reduce_status("injured", 0)
        self.assertEqual(self.char.statuses["injured"].current_tier, 2)

    def test_add_personal_tag(self):
        self.manager.add_personal_tag("angry", "Very angry", True)
        self.assertIn("angry", self.char.story_tags)
        tag = self.char.story_tags["angry"]
        self.assertEqual(tag.description, "Very angry")
        self.assertTrue(tag.is_single_use)

    def test_add_personal_tag_ignores_empty_name(self):
        self.manager.add_personal_tag("")
        self.assertEqual(len(self.char.story_tags), 0)

    def test_remove_personal_tag(self):
        self.manager.add_personal_tag("angry")
        result = self.manager.remove_personal_tag("angry")
        self.assertTrue(result)
        self.assertNotIn("angry", self.char.story_tags)

    def test_remove_personal_tag_fails_if_not_found(self):
        result = self.manager.remove_personal_tag("angry")
        self.assertFalse(result)

    def test_remove_personal_tag_fails_if_empty_name(self):
        result = self.manager.remove_personal_tag("")
        self.assertFalse(result)

    def test_methods_ignore_if_character_none(self):
        self.state.character = None
        # Should not raise any exceptions
        self.manager.apply_status("injured", 2)
        self.manager.nudge_status("tired")
        self.manager.reduce_status("injured", 1)
        self.manager.add_personal_tag("angry")
        self.assertFalse(self.manager.remove_personal_tag("angry"))


if __name__ == "__main__":
    unittest.main()
