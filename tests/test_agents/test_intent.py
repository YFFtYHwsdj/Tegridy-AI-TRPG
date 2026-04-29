"""IntentAgent 测试 —— 意图解析 Agent 的 prompt 组装验证。

验证 execute 方法正确将玩家输入和上下文组装为 user_message，
并调用 LLM 获取意图解析结果。
"""

from __future__ import annotations

import unittest

from src.agents.intent import IntentAgent
from tests.helpers import MockLLMClient, make_test_context


class TestIntentAgentExecute(unittest.TestCase):
    """测试 IntentAgent.execute 的 prompt 组装。"""

    def test_includes_player_input(self):
        """user_message 包含玩家输入文本。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"action_type": "combat"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("我要拔枪", ctx)

        self.assertEqual(len(mock_llm.call_history), 1)
        self.assertIn("我要拔枪", mock_llm.call_history[0]["user_message"])

    def test_includes_assets_block(self):
        """user_message 包含场景资产块。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"action_type": "combat"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("场景资产", mock_llm.call_history[0]["user_message"])

    def test_includes_context_block(self):
        """user_message 包含上下文块。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"action_type": "combat"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("当前场景", mock_llm.call_history[0]["user_message"])

    def test_includes_narrative_block(self):
        """user_message 包含叙事历史。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"action_type": "combat"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("叙事历史", mock_llm.call_history[0]["user_message"])
        self.assertIn("你走进了酒吧", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n玩家想战斗\n=====STRUCTURED=====\n"
                    '{"action_type": "combat", "action_summary": "拔枪射击"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        result = agent.execute("我要拔枪", ctx)

        self.assertEqual(result.reasoning, "玩家想战斗")
        self.assertEqual(result.structured["action_type"], "combat")
        self.assertEqual(result.structured["action_summary"], "拔枪射击")

    def test_uses_intent_prompt(self):
        """验证 system_prompt 使用 INTENT_PROMPT。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n分析\n=====STRUCTURED=====\n{"action_type": "combat"}',
                    {},
                )
            ]
        )
        agent = IntentAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        from src.agents.prompts import INTENT_PROMPT

        self.assertEqual(mock_llm.call_history[0]["system_prompt"], INTENT_PROMPT)


if __name__ == "__main__":
    unittest.main()
