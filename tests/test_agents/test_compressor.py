"""场景压缩 Agent 测试。"""

from __future__ import annotations

import json
import unittest

from src.agents.compressor import CompressorAgent
from src.models import Challenge, Limit
from src.state.scene_state import SceneState
from tests.helpers import MockLLMClient


class TestCompressorAgentExecute(unittest.TestCase):
    """测试 CompressorAgent.execute。"""

    def _make_response(self):
        structured = json.dumps(
            {
                "scene_summary": "Kael在酒吧与Miko谈判并成功获取芯片。",
                "key_events": [
                    "Kael向Miko展示了雇主的情报",
                    "Miko被迫交出了加密芯片",
                    "保镖在后巷发起了追击",
                ],
                "character_changes": "Kael获得了加密芯片；与Miko达成了不稳定的交易",
                "unresolved_threads": "赤色数据帮派可能会追查芯片的下落",
            },
            ensure_ascii=False,
        )
        return f"=====REASONING=====\n选择了三个关键转折点\n=====STRUCTURED=====\n{structured}"

    def _make_scene(self):
        scene = SceneState(
            scene_description="赛博朋克酒吧「最后一杯」",
        )
        challenge = Challenge(
            name="Miko 与她的保镖",
            description="帮派中间人",
            limits=[Limit(name="说服或威胁", max_tier=3)],
        )
        scene.add_challenge(challenge)
        scene.append_narrative("Kael走进了昏暗的酒吧。")
        scene.append_narrative("Miko在吧台尽头等着他，两个保镖如影随形。")
        scene.append_narrative("Kael亮出了证据，Miko的脸色变了。")
        return scene

    def test_returns_compression(self):
        """应返回包含 scene_summary 的 AgentNote。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(), {})])
        agent = CompressorAgent(mock_llm)
        scene = self._make_scene()

        result = agent.execute(scene)

        self.assertIn("Miko谈判", result.structured["scene_summary"])
        self.assertEqual(len(result.structured["key_events"]), 3)
        self.assertIn("赤色数据", result.structured["unresolved_threads"])

    def test_includes_scene_description(self):
        """user_message 应包含场景描述。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(), {})])
        agent = CompressorAgent(mock_llm)
        scene = self._make_scene()

        agent.execute(scene)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("「最后一杯」", user_msg)

    def test_includes_narrative_history(self):
        """user_message 应包含完整叙事历史。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(), {})])
        agent = CompressorAgent(mock_llm)
        scene = self._make_scene()

        agent.execute(scene)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Kael走进了昏暗的酒吧", user_msg)
        self.assertIn("Miko在吧台尽头等着他", user_msg)
        self.assertIn("Kael亮出了证据", user_msg)

    def test_includes_challenge_and_npc_info(self):
        """user_message 应包含挑战名称和 NPC 列表。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(), {})])
        agent = CompressorAgent(mock_llm)
        scene = self._make_scene()

        agent.execute(scene)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Miko 与她的保镖", user_msg)

    def test_empty_scene_handled(self):
        """空场景不应导致崩溃。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(), {})])
        agent = CompressorAgent(mock_llm)
        scene = SceneState(scene_description="空场景")

        result = agent.execute(scene)

        self.assertIsNotNone(result)
        self.assertIn("scene_summary", result.structured)


if __name__ == "__main__":
    unittest.main()
