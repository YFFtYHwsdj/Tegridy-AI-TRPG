"""场景导演 Agent 测试。"""

from __future__ import annotations

import json
import unittest

from src.agents.scene_director import SceneDirectorAgent
from tests.helpers import MockLLMClient, make_test_context


class TestSceneDirectorAgentExecute(unittest.TestCase):
    """测试 SceneDirectorAgent.execute。"""

    def _make_response(self, scene_should_end: bool = False):
        reason = "高潮已过" if scene_should_end else "场景在发展中"
        hint = "切到安全屋" if scene_should_end else ""
        structured = json.dumps(
            {
                "scene_should_end": scene_should_end,
                "reason": reason,
                "transition_hint": hint,
            },
            ensure_ascii=False,
        )
        reasoning = "高潮已过，场景可以结束。" if scene_should_end else "场景仍在发展中。"
        return f"=====REASONING=====\n{reasoning}\n=====STRUCTURED=====\n{structured}"

    def test_returns_continue_when_scene_active(self):
        """场景活跃时应返回 scene_should_end=false。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute(ctx, "Kael拔出了枪，酒吧里一片寂静。")

        self.assertFalse(result.structured["scene_should_end"])
        self.assertEqual(result.structured["reason"], "场景在发展中")
        self.assertEqual(result.structured["transition_hint"], "")

    def test_returns_end_when_scene_resolved(self):
        """场景已解决时应返回 scene_should_end=true。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(True), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute(ctx, "Miko交出了芯片，转身消失在雨夜中。")

        self.assertTrue(result.structured["scene_should_end"])
        self.assertEqual(result.structured["reason"], "高潮已过")
        self.assertEqual(result.structured["transition_hint"], "切到安全屋")

    def test_includes_context_blocks(self):
        """user_message 应包含上下文块。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute(ctx, "叙事文本")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("当前场景", user_msg)
        self.assertIn("场景资产", user_msg)
        self.assertIn("叙事历史", user_msg)

    def test_includes_last_narrative(self):
        """user_message 应包含本轮行动叙事。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute(ctx, "Kael推开了后巷的铁门。")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("本轮行动叙事", user_msg)
        self.assertIn("Kael推开了后巷的铁门", user_msg)

    def test_empty_narrative_is_handled(self):
        """空叙事不应导致崩溃。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute(ctx, "")

        self.assertIsNotNone(result)
        self.assertFalse(result.structured["scene_should_end"])

    def test_includes_challenge_state(self):
        """user_message 应包含挑战状态。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute(ctx, "叙事")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Miko 与她的保镖", user_msg)

    def test_global_block_passed_to_user_message(self):
        """global_block 应出现在 user_message 中。"""
        mock_llm = MockLLMClient(responses=[(self._make_response(False), {})])
        agent = SceneDirectorAgent(mock_llm)
        ctx = make_test_context()
        ctx.global_block = "=== 故事至今 ===\n[场景1] 酒吧\n压缩摘要..."

        agent.execute(ctx, "叙事")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("=== 故事至今 ===", user_msg)
        self.assertIn("酒吧", user_msg)


if __name__ == "__main__":
    unittest.main()
