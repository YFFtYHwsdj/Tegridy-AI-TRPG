"""其他 Agent 测试 —— MoveGatekeeper、ResolutionMode、ContinuationCheck、LimitBreak、Rhythm、ItemCreator。

验证各 Agent 的 execute 方法正确组装 prompt 并调用 LLM。
"""

from __future__ import annotations

import unittest

from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.limit_break import LimitBreakAgent
from src.agents.move_gatekeeper import MoveGatekeeperAgent
from src.agents.resolution_mode import ResolutionModeAgent
from src.agents.rhythm import RhythmAgent
from tests.helpers import (
    MockLLMClient,
    make_agent_note,
    make_test_challenge,
    make_test_context,
)


class TestMoveGatekeeperAgentExecute(unittest.TestCase):
    """测试 MoveGatekeeperAgent.execute。"""

    def test_includes_player_input(self):
        """user_message 包含玩家输入。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"is_move": true}',
                    {},
                )
            ]
        )
        agent = MoveGatekeeperAgent(mock_llm)
        ctx = make_test_context()

        agent.execute("我要拔枪", ctx)

        self.assertIn("我要拔枪", mock_llm.call_history[0]["user_message"])

    def test_includes_context(self):
        """user_message 包含上下文。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"is_move": true}',
                    {},
                )
            ]
        )
        agent = MoveGatekeeperAgent(mock_llm)
        ctx = make_test_context()

        agent.execute("测试", ctx)

        self.assertIn("场景资产", mock_llm.call_history[0]["user_message"])

    def test_returns_agent_note(self):
        """验证返回正确解析的 AgentNote。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n这是Move\n=====STRUCTURED=====\n"
                    '{"is_move": true, "rationale": "涉及战斗"}',
                    {},
                )
            ]
        )
        agent = MoveGatekeeperAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute("我要拔枪", ctx)

        self.assertTrue(result.structured["is_move"])
        self.assertEqual(result.structured["rationale"], "涉及战斗")


class TestResolutionModeAgentExecute(unittest.TestCase):
    """测试 ResolutionModeAgent.execute。"""

    def test_includes_action_type(self):
        """user_message 包含 action_type。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"resolution_mode": "detailed"}',
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
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"resolution_mode": "quick"}',
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
                    "=====REASONING=====\n简单行动\n=====STRUCTURED=====\n"
                    '{"resolution_mode": "quick", "reason": "低风险"}',
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
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"can_continue": true}',
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
                    '=====REASONING=====\n判断\n=====STRUCTURED=====\n{"can_continue": true}',
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
                    '=====REASONING=====\n可以继续\n=====STRUCTURED=====\n{"can_continue": true}',
                    {},
                )
            ]
        )
        agent = ContinuationCheckAgent(mock_llm)
        ctx = make_test_context()
        next_sub = {"action_type": "combat", "action_summary": "射击"}

        result = agent.execute(next_sub, ctx, "")

        self.assertTrue(result.structured["can_continue"])


class TestLimitBreakAgentExecute(unittest.TestCase):
    """测试 LimitBreakAgent.execute。"""

    def test_includes_limit_progress(self):
        """user_message 包含突破极限的当前进度。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n极限突破\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LimitBreakAgent(mock_llm)
        ctx = make_test_context()
        challenge = make_test_challenge()

        agent.execute(["说服或威胁"], challenge, ctx)

        self.assertIn("说服或威胁", mock_llm.call_history[0]["user_message"])
        self.assertIn("极限突破", mock_llm.call_history[0]["user_message"])

    def test_includes_challenge_state(self):
        """user_message 包含挑战完整状态。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n极限突破\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LimitBreakAgent(mock_llm)
        ctx = make_test_context()
        challenge = make_test_challenge()

        agent.execute(["说服或威胁"], challenge, ctx)

        self.assertIn("Miko 与她的保镖", mock_llm.call_history[0]["user_message"])

    def test_with_multiple_limits(self):
        """多个极限同时突破时全部列出。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    '=====REASONING=====\n极限突破\n=====STRUCTURED=====\n{"narrative": "..."}',
                    {},
                )
            ]
        )
        agent = LimitBreakAgent(mock_llm)
        ctx = make_test_context()
        challenge = make_test_challenge()

        agent.execute(["说服或威胁", "伤害或制服"], challenge, ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("说服或威胁", user_msg)
        self.assertIn("伤害或制服", user_msg)


class TestRhythmAgentExecute(unittest.TestCase):
    """测试 RhythmAgent.execute。"""

    def test_includes_scene_description(self):
        """user_message 包含场景描述。"""
        mock_llm = MockLLMClient(
            responses=[
                (
                    "=====REASONING=====\n场景建立\n=====STRUCTURED=====\n"
                    '{"scene_establishment": "霓虹灯...", "spotlight_handoff": "你要做什么？"}',
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
                    "=====REASONING=====\n场景建立\n=====STRUCTURED=====\n"
                    '{"scene_establishment": "霓虹灯...", "spotlight_handoff": "你要做什么？"}',
                    {},
                )
            ]
        )
        agent = RhythmAgent(mock_llm)

        result = agent.execute("赛博朋克酒吧")

        self.assertEqual(result.structured["scene_establishment"], "霓虹灯...")


if __name__ == "__main__":
    unittest.main()
