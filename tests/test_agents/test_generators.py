"""测试各生成类 Agent。"""

from __future__ import annotations

import unittest

from src.agents.challenge_generator import ChallengeGeneratorAgent
from src.agents.item_creator import ItemCreatorAgent
from src.agents.item_generator import ItemGeneratorAgent
from src.agents.npc_generator import NPCGeneratorAgent
from src.agents.place_generator import PlaceGeneratorAgent
from tests.helpers import MockLLMClient, make_test_context


class TestItemCreatorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "创建物品", "name": "等离子枪", "description": "一把很厉害的枪", '
                    '"tags": [{"name": "高伤", "description": "伤害很高"}]}',
                    {},
                )
            ]
        )
        agent = ItemCreatorAgent(mock_llm)
        ctx = make_test_context()

        result = agent.execute("等离子枪", ctx)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("等离子枪", user_msg)
        self.assertEqual(result.structured.get("name"), "等离子枪")


class TestNPCGeneratorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "创建NPC", "name": "黑客 V", "description": "街头黑客", '
                    '"tags": [{"name": "快速破解", "description": "骇入系统"}]}',
                    {},
                )
            ]
        )
        agent = NPCGeneratorAgent(mock_llm)

        result = agent.execute("生成一个街头黑客", "npc_v")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("生成一个街头黑客", user_msg)

        self.assertEqual(result.npc_id, "npc_v")
        self.assertEqual(result.name, "黑客 V")
        self.assertEqual(result.description, "街头黑客")
        self.assertEqual(len(result.tags), 1)
        self.assertEqual(result.tags[0].name, "快速破解")


class TestItemGeneratorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "创建物品", "name": "医疗包", "description": "补血用", '
                    '"tags": [{"name": "治疗", "description": "恢复生命"}]}',
                    {},
                )
            ]
        )
        agent = ItemGeneratorAgent(mock_llm)

        result = agent.execute("生成一个医疗包", "item_med")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("生成一个医疗包", user_msg)

        self.assertEqual(result.item_id, "item_med")
        self.assertEqual(result.name, "医疗包")
        self.assertEqual(len(result.tags), 1)


class TestPlaceGeneratorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "创建地点", "name": "黑市", "description": "交易违禁品的地方", '
                    '"items": [{"item_id": "item1", "name": "黑市步枪", "description": "便宜的枪", "location": "摊位"}]}',
                    {},
                )
            ]
        )
        agent = PlaceGeneratorAgent(mock_llm)

        result = agent.execute("生成一个黑市", "place_market")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("生成一个黑市", user_msg)

        self.assertEqual(result.place_id, "place_market")
        self.assertEqual(result.name, "黑市")
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items["item1"].name, "黑市步枪")


class TestChallengeGeneratorAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "创建挑战", "name": "高压电网", "description": "阻止入侵者", '
                    '"limits": {"核心": 4}, "base_tags": [{"name": "致命电击", "description": "高伤害"}], '
                    '"threats": ["电击玩家"], "consequences": ["受到伤害"]}',
                    {},
                )
            ]
        )
        agent = ChallengeGeneratorAgent(mock_llm)

        result = agent.execute("生成一个安保电网", "chal_grid")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("生成一个安保电网", user_msg)

        self.assertEqual(result.challenge_id, "chal_grid")
        self.assertEqual(result.name, "高压电网")
        self.assertEqual(result.limits["核心"], 4)
        self.assertEqual(len(result.base_tags), 1)
        self.assertEqual(result.threats[0], "电击玩家")


if __name__ == "__main__":
    unittest.main()
