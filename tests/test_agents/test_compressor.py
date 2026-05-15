import unittest

from src.agents.compressor import CompressorAgent
from src.models import NPC
from src.state.global_state import GlobalState
from src.state.scene_state import SceneState
from tests.helpers import MockLLMClient


class TestCompressorAgentExecute(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLMClient()
        self.agent = CompressorAgent(self.llm)

    def _make_scene(self) -> SceneState:
        scene = SceneState(place_id="loc1", situation="酒吧混乱", active_npc_ids=["thug1"])
        scene.append_narrative("第一回合交火")
        scene.append_narrative("你躲在掩体后")
        return scene

    def test_returns_compression(self):
        self.llm.responses = [
            ('{"reasoning": "压缩测试", "scene_summary": "玩家与暴徒在酒吧交火，目前躲避中"}', {})
        ]
        scene = self._make_scene()
        global_state = GlobalState()
        global_state.npcs["thug1"] = NPC(npc_id="thug1", name="暴徒")
        note = self.agent.execute(scene, global_state)
        self.assertEqual(note.structured.get("scene_summary"), "玩家与暴徒在酒吧交火，目前躲避中")

    def test_empty_scene_handled(self):
        self.llm.responses = [('{"reasoning": "空", "scene_summary": "无事发生"}', {})]
        scene = SceneState(place_id="", situation="空场景")
        global_state = GlobalState()
        note = self.agent.execute(scene, global_state)
        self.assertEqual(note.structured.get("scene_summary"), "无事发生")


if __name__ == "__main__":
    unittest.main()
