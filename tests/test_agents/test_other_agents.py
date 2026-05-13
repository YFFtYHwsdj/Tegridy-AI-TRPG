"""其他 Agent 测试 —— MoveGatekeeper、ResolutionMode、ContinuationCheck、LimitBreak、Rhythm、ItemCreator。

验证各 Agent 的 execute 方法正确组装 prompt 并调用 LLM。
"""

from __future__ import annotations

import unittest

from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.resolution_mode import ResolutionModeAgent
from src.agents.rhythm import RhythmAgent
from tests.helpers import (
    MockLLMClient,
    make_agent_note,
    make_test_context,
)


class TestResolutionModeAgentExecute(unittest.TestCase):
    """测试 ResolutionModeAgent.execute。"""

    def test_includes_action_type(self):
        """user_message 包含 action_type。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "判断", "resolution_mode": "detailed"}',
                    {},
                )
            ]
        )
        agent = ResolutionModeAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})

        agent.execute(intent_note, ctx)

        self.assertIn("combat", mock_llm.call_history[0]["user_message"])

    def test_includes_player_input(self):
        """user_message 包含原始玩家输入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "判断", "resolution_mode": "quick"}',
                    {},
                )
            ]
        )
        agent = ResolutionModeAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})

        agent.execute(intent_note, ctx)

        self.assertIn("我要拔枪", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "简单行动", "resolution_mode": "quick", "reason": "低风险"}',
                    {},
                )
            ]
        )
        agent = ResolutionModeAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_type": "combat"})

        result = agent.execute(intent_note, ctx)

        self.assertEqual(result.structured["resolution_mode"], "quick")


class TestContinuationCheckAgentExecute(unittest.TestCase):
    """测试 ContinuationCheckAgent.execute。"""

    def test_includes_last_sub_summary(self):
        """user_message 包含上一步子 action 的结果摘要。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "判断", "can_continue": true}',
                    {},
                )
            ]
        )
        agent = ContinuationCheckAgent(mock_llm)
        ctx = make_test_context()
        next_sub = {"action_type": "combat", "action_summary": "射击", "fragment": "开枪"}

        agent.execute(next_sub, ctx, "上一步成功")

        self.assertIn("上一步成功", mock_llm.call_history[0]["user_message"])

    def test_includes_next_sub_action(self):
        """user_message 包含下一步子 action 的详情。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "判断", "can_continue": true}',
                    {},
                )
            ]
        )
        agent = ContinuationCheckAgent(mock_llm)
        ctx = make_test_context()
        next_sub = {"action_type": "combat", "action_summary": "射击", "fragment": "开枪"}

        agent.execute(next_sub, ctx, "")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("射击", user_msg)
        self.assertIn("开枪", user_msg)

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "可以继续", "can_continue": true}',
                    {},
                )
            ]
        )
        agent = ContinuationCheckAgent(mock_llm)
        ctx = make_test_context()
        next_sub = {"action_type": "combat", "action_summary": "射击"}

        result = agent.execute(next_sub, ctx, "")

        self.assertTrue(result.structured["can_continue"])


class TestRhythmAgentExecute(unittest.TestCase):
    """测试 RhythmAgent.execute。"""

    def test_includes_scene_description(self):
        """user_message 包含场景描述。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "场景建立", '
                    '"scene_establishment": "霓虹灯...", "spotlight_handoff": "你要做什么？"}',
                    {},
                )
            ]
        )
        agent = RhythmAgent(mock_llm)

        agent.execute("赛博朋克酒吧")

        self.assertIn("赛博朋克酒吧", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "场景建立", '
                    '"scene_establishment": "霓虹灯...", "spotlight_handoff": "你要做什么？"}',
                    {},
                )
            ]
        )
        agent = RhythmAgent(mock_llm)

        result = agent.execute("赛博朋克酒吧")

        self.assertEqual(result.structured["scene_establishment"], "霓虹灯...")


if __name__ == "__main__":
    unittest.main()
