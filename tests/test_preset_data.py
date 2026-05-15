import unittest

from src.preset_data import DEMO_CHARACTER, DEMO_WORLDVIEW, build_demo_scene
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


if __name__ == "__main__":
    unittest.main()
