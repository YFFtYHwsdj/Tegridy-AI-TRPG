"""OutcomeAgent 和 QuickOutcomeAgent 测试 —— 联合后果与效果生成的 LLM 代理。

验证 Agent 的 execute 方法是否正确向 LLM 发送包含 intent, tags 和 roll_result 的上下文。
"""

import unittest

from src.agents.outcome import OutcomeAgent, QuickOutcomeAgent
from tests.helpers import MockLLMClient, make_agent_note, make_roll_result, make_test_context


class TestOutcomeAgentExecute(unittest.TestCase):
    """测试 OutcomeAgent.execute 的 prompt 组装。"""

    def test_includes_intent_and_tags(self):
        """user_message 包含意图和匹配标签。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "...", "effects": [], "consequences": []}',
                    {},
                )
            ]
        )
        agent = OutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(
            structured={
                "action_type": "combat",
                "action_summary": "朝门开火",
            }
        )
        tag_note = make_agent_note(
            structured={
                "matched_power_tags": [{"name": "冲锋枪"}],
                "matched_weakness_tags": [],
            }
        )
        roll = make_roll_result(power=1, outcome="partial_success")

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("combat", user_msg)
        self.assertIn("朝门开火", user_msg)
        self.assertIn("冲锋枪", user_msg)

    def test_includes_roll_result(self):
        """user_message 包含掷骰详情。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "...", "effects": [], "consequences": []}',
                    {},
                )
            ]
        )
        agent = OutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={})
        tag_note = make_agent_note(structured={})
        roll = make_roll_result(power=3, outcome="full_success")

        agent.execute(intent_note, tag_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("full_success", user_msg)
        self.assertIn("可用力量: 3", user_msg)

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote，且清除了对冲内容。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "分析", "effects": [{"label": "受伤"}], "consequences": [{"threat_manifested": "警告"}]}',
                    {},
                )
            ]
        )
        agent = OutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={})
        tag_note = make_agent_note(structured={})
        # 因为 partial_success，二者都保留
        roll = make_roll_result(outcome="partial_success")

        result = agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(len(result.structured["effects"]), 1)
        self.assertEqual(len(result.structured["consequences"]), 1)

    def test_clears_consequences_on_full_success(self):
        """验证 full_success 时清空 consequences。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "分析", "effects": [{"label": "受伤"}], "consequences": [{"threat_manifested": "警告"}]}',
                    {},
                )
            ]
        )
        agent = OutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={})
        tag_note = make_agent_note(structured={})
        roll = make_roll_result(outcome="full_success")

        result = agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(len(result.structured["effects"]), 1)
        self.assertEqual(result.structured["consequences"], [])

    def test_clears_effects_on_failure(self):
        """验证 failure 时清空 effects。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "分析", "effects": [{"label": "受伤"}], "consequences": [{"threat_manifested": "警告"}]}',
                    {},
                )
            ]
        )
        agent = OutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={})
        tag_note = make_agent_note(structured={})
        roll = make_roll_result(outcome="failure")

        result = agent.execute(intent_note, tag_note, roll, ctx)

        self.assertEqual(result.structured["effects"], [])
        self.assertEqual(len(result.structured["consequences"]), 1)


class TestQuickOutcomeAgentExecute(unittest.TestCase):
    """测试 QuickOutcomeAgent.execute 的 prompt 组装。"""

    def test_includes_intent_and_roll(self):
        """user_message 包含意图摘要和掷骰结果。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "...", "consequences": []}',
                    {},
                )
            ]
        )
        agent = QuickOutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("拔枪", user_msg)
        self.assertIn("partial_success", user_msg)

    def test_clears_consequences_on_full_success(self):
        """完全成功时快速代理也清空后果。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "...", "consequences": [{"description": "摔倒"}]}',
                    {},
                )
            ]
        )
        agent = QuickOutcomeAgent(mock_llm)
        ctx = make_test_context()

        intent_note = make_agent_note(structured={})
        roll = make_roll_result(outcome="full_success")

        result = agent.execute(intent_note, roll, ctx)

        self.assertEqual(result.structured["consequences"], [])


if __name__ == "__main__":
    unittest.main()
