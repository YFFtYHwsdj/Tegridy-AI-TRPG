"""InquiryAgent 测试 —— 信息补充 Agent 的 prompt 组装与行为验证。

验证 InquiryAgent 的 execute 方法正确将玩家提问和上下文组装为 user_message，
并调用 LLM 获取信息回复。
"""

from __future__ import annotations

import unittest

from src.agents.inquiry import InquiryAgent
from tests.helpers import MockLLMClient, make_test_context


class TestInquiryAgentExecute(unittest.TestCase):
    """测试 InquiryAgent.execute 的 prompt 组装。"""

    def test_includes_player_input(self):
        """user_message 包含玩家提问文本。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事历史中有记录", '
                    '"response": "他叫Miko", "info_source": "history"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("那个NPC叫什么名字？", ctx)

        self.assertEqual(len(mock_llm.call_history), 1)
        self.assertIn("那个NPC叫什么名字？", mock_llm.call_history[0]["user_message"])

    def test_includes_assets_block(self):
        """user_message 包含场景资产块。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "查找", "response": "回复", "info_source": "assets"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("场景资产", mock_llm.call_history[0]["user_message"])

    def test_includes_context_block(self):
        """user_message 包含上下文块。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "查找", "response": "回复", "info_source": "assets"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("当前场景", mock_llm.call_history[0]["user_message"])

    def test_includes_narrative_block(self):
        """user_message 包含叙事历史。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "查找", "response": "回复", "info_source": "history"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("叙事历史", mock_llm.call_history[0]["user_message"])
        self.assertIn("你走进了酒吧", mock_llm.call_history[0]["user_message"])

    def test_includes_hidden_notice(self):
        """user_message 包含隐藏信息安全提示。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "查找", "response": "回复", "info_source": "assets"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        self.assertIn("隐藏", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "叙事历史中有记录", '
                    '"response": "他叫Miko，是个情报贩子。", '
                    '"info_source": "history"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        result = agent.execute("那个NPC叫什么？", ctx)

        self.assertEqual(result.reasoning, "叙事历史中有记录")
        self.assertEqual(result.structured["response"], "他叫Miko，是个情报贩子。")
        self.assertEqual(result.structured["info_source"], "history")

    def test_uses_inquiry_prompt(self):
        """验证 system_prompt 使用 INQUIRY_PROMPT。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "查找", "response": "回复", "info_source": "assets"}',
                    {},
                )
            ]
        )
        agent = InquiryAgent(mock_llm)
        ctx = make_test_context()
        agent.execute("测试", ctx)

        from src.agents.prompts import INQUIRY_PROMPT

        self.assertEqual(mock_llm.call_history[0]["system_prompt"], INQUIRY_PROMPT)


if __name__ == "__main__":
    unittest.main()
