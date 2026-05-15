"""NarratorAgent、LiteNarratorAgent、QuickNarratorAgent 测试 —— 叙述者 Agent 的 prompt 组装验证。

验证各叙述者 Agent 的 execute 方法正确组装叙事生成所需的上下文信息。
"""

from __future__ import annotations

import unittest

from src.agents.narrator import LiteNarratorAgent, NarratorAgent, QuickNarratorAgent
from tests.helpers import MockLLMClient, make_agent_note, make_roll_result, make_test_context


class TestNarratorAgentExecute(unittest.TestCase):
    """测试 NarratorAgent.execute 的 prompt 组装。"""

    def test_includes_hidden_notice(self):
        """user_message 包含隐藏信息提示。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事策略", "narrative": "你拔出了枪..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertIn("隐藏", mock_llm.call_history[0]["user_message"])

    def test_includes_effects_and_consequences(self):
        """user_message 包含效果和后果的 JSON。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(
            structured={
                "effects": [{"operation": "inflict_status", "label": "受伤"}],
                "consequences": [{"threat_manifested": "保镖介入"}],
            }
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, outcome_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("inflict_status", user_msg)
        self.assertIn("保镖介入", user_msg)

    def test_without_consequences(self):
        """没有后果时 consequences 部分为空。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": [], "consequences": []})
        roll = make_roll_result(outcome="full_success")

        agent.execute(intent_note, outcome_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        # 后果应为空数组
        self.assertIn("后果: []", user_msg)

    def test_includes_roll_summary(self):
        """user_message 包含掷骰摘要。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success", power=1, dice=(4, 3))

        agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertIn("4+3+1=8", mock_llm.call_history[0]["user_message"])

    def test_includes_player_input(self):
        """user_message 包含玩家输入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        ctx.player_input = "我要拔枪"
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertIn("我要拔枪", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事策略", '
                    '"narrative": "你迅速拔枪...", "revelation_decisions": {}}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        result = agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertEqual(result.structured["narrative"], "你迅速拔枪...")

    def test_execute_split_includes_all_sub_results(self):
        """验证 execute_split 能正确合并所有子行动的解算结果。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "合并叙事", "narrative": "你踢开门，然后开枪了..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        ctx.player_input = "踢门并开枪"

        sub_results = [
            {
                "summary": "踢门",
                "roll_summary": "4+2+1=7 (partial_success)",
                "effects_json": '["门破损"]',
                "narrative_hints": "发出巨响",
                "consequences_json": "[]",
            },
            {
                "summary": "开枪",
                "roll_summary": "6+4+1=11 (full_success)",
                "effects_json": '["击中目标"]',
                "narrative_hints": "精准",
                "consequences_json": "[]",
            },
        ]

        result = agent.execute_split(sub_results, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("踢门并开枪", user_msg)
        self.assertIn("踢门", user_msg)
        self.assertIn("开枪", user_msg)
        self.assertIn("门破损", user_msg)
        self.assertIn("击中目标", user_msg)
        self.assertEqual(result.structured["narrative"], "你踢开门，然后开枪了...")


class TestLiteNarratorAgentExecute(unittest.TestCase):
    """测试 LiteNarratorAgent.execute 的 prompt 组装。"""

    def test_includes_gatekeeper_reasoning(self):
        """user_message 包含守门人判断推理。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LiteNarratorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute("看看周围", ctx, "这是低风险观察")

        self.assertIn("低风险观察", mock_llm.call_history[0]["user_message"])

    def test_marked_as_non_move(self):
        """prompt 明确标注为叙事性交互。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LiteNarratorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute("看看周围", ctx, "")

        self.assertIn("叙事性交互", mock_llm.call_history[0]["user_message"])

    def test_includes_player_input(self):
        """user_message 包含玩家输入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LiteNarratorAgent(mock_llm)
        ctx = make_test_context()

        agent.execute("看看周围", ctx, "")

        self.assertIn("看看周围", mock_llm.call_history[0]["user_message"])


class TestQuickNarratorAgentExecute(unittest.TestCase):
    """测试 QuickNarratorAgent.execute 的 prompt 组装。"""

    def test_omits_effect_note(self):
        """快速模式不包含效果推演信息。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, outcome_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertNotIn("效果推演", user_msg)

    def test_includes_roll_summary(self):
        """user_message 包含掷骰摘要。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        outcome_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success", power=1, dice=(3, 4))

        agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertIn("3+4+1=8", mock_llm.call_history[0]["user_message"])

    def test_with_consequences(self):
        """包含后果时后果信息被传入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事", "narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="partial_success")
        outcome_note = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        agent.execute(intent_note, outcome_note, roll, ctx)

        self.assertIn("保镖介入", mock_llm.call_history[0]["user_message"])


if __name__ == "__main__":
    unittest.main()
