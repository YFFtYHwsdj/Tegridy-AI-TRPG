import unittest

from src.models import NPC
from src.pipeline.managers.npc_manager import NPCManager
from src.state.game_state import GameState
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState


class TestNPCManager(unittest.TestCase):
    def setUp(self):
        self.state = GameState()
        self.state.global_state = GlobalState()
        self.state.scene = SceneState(place_id="loc1")
        self.manager = NPCManager(self.state)

        # Setup an NPC
        self.npc = NPC(npc_id="miko", name="Miko")
        self.state.global_state.npcs["miko"] = self.npc
        self.state.scene.active_npc_ids.append("miko")

    def test_get_npc_returns_npc_if_active(self):
        npc = self.manager.get_npc("miko")
        self.assertIsNotNone(npc)
        self.assertEqual(npc.name, "Miko")

    def test_get_npc_returns_none_if_inactive(self):
        npc = self.manager.get_npc("nonexistent")
        self.assertIsNone(npc)

    def test_apply_status_to_npc(self):
        self.manager.apply_status("miko", "injured", 2)
        self.assertEqual(self.npc.statuses["injured"].current_tier, 2)

    def test_apply_status_ignores_if_npc_not_found(self):
        self.manager.apply_status("nonexistent", "injured", 2)
        self.assertNotIn("injured", self.npc.statuses)

    def test_apply_status_ignores_if_invalid_tier(self):
        self.manager.apply_status("miko", "injured", 0)
        self.assertNotIn("injured", self.npc.statuses)

    def test_nudge_status_on_npc(self):
        self.manager.nudge_status("miko", "tired")
        self.assertEqual(self.npc.statuses["tired"].current_tier, 1)
        self.manager.nudge_status("miko", "tired")
        self.assertEqual(self.npc.statuses["tired"].current_tier, 2)

    def test_nudge_status_ignores_if_empty_label(self):
        self.manager.nudge_status("miko", "")
        self.assertEqual(len(self.npc.statuses), 0)

    def test_nudge_status_ignores_if_npc_not_found(self):
        self.manager.nudge_status("nonexistent", "tired")
        self.assertEqual(len(self.npc.statuses), 0)

    def test_reduce_status_on_npc(self):
        self.manager.apply_status("miko", "injured", 1)
        self.manager.apply_status("miko", "injured", 1)  # overflows to 2
        self.manager.reduce_status("miko", "injured", 1)
        self.assertEqual(self.npc.statuses["injured"].current_tier, 1)

    def test_reduce_status_removes_if_zero(self):
        self.manager.apply_status("miko", "injured", 1)
        self.manager.reduce_status("miko", "injured", 1)
        self.assertNotIn("injured", self.npc.statuses)

    def test_reduce_status_ignores_invalid_params(self):
        self.manager.apply_status("miko", "injured", 2)
        self.manager.reduce_status("miko", "", 1)
        self.manager.reduce_status("miko", "injured", 0)
        self.assertEqual(self.npc.statuses["injured"].current_tier, 2)

    def test_reduce_status_ignores_npc_not_found(self):
        self.manager.reduce_status("nonexistent", "injured", 1)

    def test_add_personal_tag(self):
        self.manager.add_personal_tag("miko", "angry", "She is angry", True)
        expected_tag_name = "[Miko] angry"
        self.assertIn(expected_tag_name, self.state.scene.story_tags)
        tag = self.state.scene.story_tags[expected_tag_name]
        self.assertEqual(tag.description, "She is angry")
        self.assertTrue(tag.is_single_use)

    def test_add_personal_tag_ignores_empty_name(self):
        self.manager.add_personal_tag("miko", "")
        self.assertEqual(len(self.state.scene.story_tags), 0)

    def test_add_personal_tag_ignores_npc_not_found(self):
        self.manager.add_personal_tag("nonexistent", "angry")
        self.assertEqual(len(self.state.scene.story_tags), 0)

    def test_remove_personal_tag(self):
        self.manager.add_personal_tag("miko", "angry")
        result = self.manager.remove_personal_tag("miko", "angry")
        self.assertTrue(result)
        self.assertNotIn("[Miko] angry", self.state.scene.story_tags)

    def test_remove_personal_tag_fails_if_not_found(self):
        result = self.manager.remove_personal_tag("miko", "angry")
        self.assertFalse(result)

    def test_remove_personal_tag_fails_if_empty_name(self):
        result = self.manager.remove_personal_tag("miko", "")
        self.assertFalse(result)

    def test_remove_personal_tag_fails_if_npc_not_found(self):
        result = self.manager.remove_personal_tag("nonexistent", "angry")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
