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
                    '=====REASONING=====\n叙事策略\n=====STRUCTURED=====\n{"narrative": "你拔出了枪..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("隐藏", mock_llm.call_history[0]["user_message"])

    def test_includes_effects_and_consequences(self):
        """user_message 包含效果和后果的 JSON。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(
            structured={"effects": [{"operation": "inflict_status", "label": "受伤"}]}
        )
        roll = make_roll_result(outcome="partial_success")
        consequence_note = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        agent.execute(intent_note, effect_note, roll, ctx, consequence_note=consequence_note)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("inflict_status", user_msg)
        self.assertIn("保镖介入", user_msg)

    def test_without_consequence_note(self):
        """consequence_note 为 None 时后果部分为空。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="full_success")

        agent.execute(intent_note, effect_note, roll, ctx, consequence_note=None)

        user_msg = mock_llm.call_history[0]["user_message"]
        # 后果推理应为空字符串，但字段存在
        self.assertIn("后果推理", user_msg)

    def test_includes_roll_summary(self):
        """user_message 包含掷骰摘要。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success", power=1, dice=(4, 3))

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("4+3+1=8", mock_llm.call_history[0]["user_message"])

    def test_includes_player_input(self):
        """user_message 包含玩家输入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        ctx.player_input = "我要拔枪"
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("我要拔枪", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n叙事策略\n=====STRUCTURED=====\n"
                    '{"narrative": "你迅速拔枪...", "revelation_decisions": {}}',
                    {},
                )
            ]
        )
        agent = NarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        result = agent.execute(intent_note, effect_note, roll, ctx)

        self.assertEqual(result.structured["narrative"], "你迅速拔枪...")


class TestLiteNarratorAgentExecute(unittest.TestCase):
    """测试 LiteNarratorAgent.execute 的 prompt 组装。"""

    def test_includes_gatekeeper_reasoning(self):
        """user_message 包含守门人判断推理。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
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
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
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
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
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
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertNotIn("效果推演", user_msg)

    def test_includes_roll_summary(self):
        """user_message 包含掷骰摘要。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="partial_success", power=1, dice=(3, 4))

        agent.execute(intent_note, roll, ctx)

        self.assertIn("3+4+1=8", mock_llm.call_history[0]["user_message"])

    def test_with_consequence_note(self):
        """包含后果时后果信息被传入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n叙事\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = QuickNarratorAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="partial_success")
        consequence_note = make_agent_note(
            structured={"consequences": [{"threat_manifested": "保镖介入"}]}
        )

        agent.execute(intent_note, roll, ctx, consequence_note=consequence_note)

        self.assertIn("保镖介入", mock_llm.call_history[0]["user_message"])


if __name__ == "__main__":
    unittest.main()
