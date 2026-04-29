"""ConsequenceAgent 和 QuickConsequenceAgent 测试 —— 后果生成 Agent 的 prompt 组装验证。

验证 execute 方法正确组装后果生成所需的上下文信息。
"""

from __future__ import annotations

import unittest

from src.agents.consequence import ConsequenceAgent, QuickConsequenceAgent
from tests.helpers import MockLLMClient, make_agent_note, make_roll_result, make_test_context


class TestConsequenceAgentExecute(unittest.TestCase):
    """测试 ConsequenceAgent.execute 的 prompt 组装。"""

    def test_includes_effect_note_reasoning(self):
        """user_message 包含效果推演的推理过程。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n后果分析\n=====STRUCTURED=====\n"
                    '{"consequences": [{"threat_manifested": "保镖介入"}]}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(
            reasoning="造成伤害",
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "挑战", "label": "受伤", "tier": 2}
                ]
            },
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("造成伤害", mock_llm.call_history[0]["user_message"])

    def test_includes_roll_outcome_partial(self):
        """user_message 标注 partial_success。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("部分成功", mock_llm.call_history[0]["user_message"])

    def test_includes_roll_outcome_failure(self):
        """user_message 标注 failure。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="failure")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("失败", mock_llm.call_history[0]["user_message"])

    def test_includes_challenge_state(self):
        """user_message 包含挑战完整状态。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("Miko 与她的保镖", mock_llm.call_history[0]["user_message"])

    def test_includes_effects_json(self):
        """user_message 包含已产生效果的 JSON。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(
            structured={"effects": [{"operation": "inflict_status", "label": "受伤"}]}
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, effect_note, roll, ctx)

        self.assertIn("inflict_status", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n保镖介入\n=====STRUCTURED=====\n"
                    '{"consequences": [{"threat_manifested": "保镖介入", "effects": []}]}',
                    {},
                )
            ]
        )
        agent = ConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        effect_note = make_agent_note(structured={"effects": []})
        roll = make_roll_result(outcome="partial_success")

        result = agent.execute(intent_note, effect_note, roll, ctx)

        self.assertEqual(result.reasoning, "保镖介入")
        self.assertEqual(result.structured["consequences"][0]["threat_manifested"], "保镖介入")


class TestQuickConsequenceAgentExecute(unittest.TestCase):
    """测试 QuickConsequenceAgent.execute 的 prompt 组装。"""

    def test_omits_effect_note(self):
        """快速模式不包含效果推演信息。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = QuickConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(
            structured={"action_type": "combat", "action_summary": "拔枪"}
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, roll, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertNotIn("效果推演", user_msg)

    def test_includes_action_type(self):
        """user_message 包含 action_type。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = QuickConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(
            structured={"action_type": "combat", "action_summary": "拔枪"}
        )
        roll = make_roll_result(outcome="partial_success")

        agent.execute(intent_note, roll, ctx)

        self.assertIn("combat", mock_llm.call_history[0]["user_message"])

    def test_includes_roll_info(self):
        """user_message 包含掷骰结果。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n后果\n=====STRUCTURED=====\n{"consequences": []}',
                    {},
                )
            ]
        )
        agent = QuickConsequenceAgent(mock_llm)
        ctx = make_test_context()
        intent_note = make_agent_note(structured={"action_summary": "拔枪"})
        roll = make_roll_result(outcome="failure")

        agent.execute(intent_note, roll, ctx)

        self.assertIn("failure", mock_llm.call_history[0]["user_message"])


if __name__ == "__main__":
    unittest.main()
