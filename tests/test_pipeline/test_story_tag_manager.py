import unittest

from src.pipeline.managers.story_tag_manager import StoryTagManager
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class TestStoryTagManager(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.state.scene = SceneState(place_id="loc1")
        self.manager = StoryTagManager(self.state)

    def test_add_scene_tag(self):
        self.manager.add_scene_tag("fire", "The place is burning", True)
        self.assertIn("fire", self.state.scene.story_tags)
        tag = self.state.scene.story_tags["fire"]
        self.assertEqual(tag.description, "The place is burning")
        self.assertTrue(tag.is_single_use)

    def test_add_scene_tag_ignores_empty_name(self):
        self.manager.add_scene_tag("")
        self.assertEqual(len(self.state.scene.story_tags), 0)

    def test_remove_scene_tag(self):
        self.manager.add_scene_tag("fire")
        result = self.manager.remove_scene_tag("fire")
        self.assertTrue(result)
        self.assertNotIn("fire", self.state.scene.story_tags)

    def test_remove_scene_tag_fails_if_not_found(self):
        result = self.manager.remove_scene_tag("fire")
        self.assertFalse(result)

    def test_remove_scene_tag_fails_if_empty_name(self):
        result = self.manager.remove_scene_tag("")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
