import unittest

from src.preset_data import (
    ALLEY_PRESET,
    AVAILABLE_PRESETS,
    CYBER_SHRINE_PRESET,
    DEMO_CHARACTER,
    DEMO_WORLDVIEW,
    build_demo_scene,
)
from src.state.global_state import GlobalState


class TestPresetData(unittest.TestCase):
    def test_presets_exist(self):
        self.assertIsInstance(DEMO_WORLDVIEW, str)
        self.assertTrue(len(DEMO_WORLDVIEW) > 0)

        self.assertIsNotNone(DEMO_CHARACTER)
        self.assertEqual(DEMO_CHARACTER.name, "Kael")

        gs = GlobalState()
        scene = build_demo_scene(gs)
        self.assertEqual(scene.place_id, "alley_01")
        self.assertTrue(len(gs.places) > 0)

    def test_available_presets(self):
        """测试预设注册表是否包含应有的预设。"""
        self.assertIn("alley", AVAILABLE_PRESETS)
        self.assertIn("cyber_shrine", AVAILABLE_PRESETS)
        self.assertEqual(AVAILABLE_PRESETS["alley"], ALLEY_PRESET)
        self.assertEqual(AVAILABLE_PRESETS["cyber_shrine"], CYBER_SHRINE_PRESET)

    def test_cyber_shrine_preset(self):
        """测试赛博龛寺预设及场景构建。"""
        self.assertEqual(CYBER_SHRINE_PRESET.id, "cyber_shrine")
        self.assertEqual(CYBER_SHRINE_PRESET.character.name, "Rin")
        self.assertTrue(len(CYBER_SHRINE_PRESET.worldview) > 0)

        gs = GlobalState()
        scene = CYBER_SHRINE_PRESET.build_scene(gs)
        self.assertEqual(scene.place_id, "shrine_pond_01")
        
        # 验证实体是否正确注册到 GlobalState
        self.assertIn("shrine_pond_01", gs.places)
        self.assertIn("kappa_guardian", gs.npcs)
        self.assertIn("hacker_kirinaga", gs.npcs)
        self.assertIn("data_waterfall", gs.items)
        self.assertIn("firewall_gate", gs.items)
        
        # 验证场景内的活动实体
        self.assertIn("kappa_guardian", scene.active_npc_ids)
        self.assertIn("data_waterfall", scene.active_item_ids)
        self.assertIn("数据湍流", scene.story_tags)


if __name__ == "__main__":
    unittest.main()
