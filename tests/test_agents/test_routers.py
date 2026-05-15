"""测试各路由与推演 Agent。"""

from __future__ import annotations

import unittest

from src.agents.scene_router import SceneRouterAgent
from src.agents.world_updater import EdgeMergeAgent, WorldAnalyzerAgent
from tests.helpers import MockLLMClient, make_test_game_state


class TestSceneRouterAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "决定去向", '
                    '"target_place": {"id": "bar", "is_new": false}, '
                    '"target_npcs": [], "target_items": [], "target_challenges": [], '
                    '"situation_prompt": "安静"}',
                    {},
                )
            ]
        )
        agent = SceneRouterAgent(mock_llm)
        state = make_test_game_state()
        from src.models import GameItem, Place

        state.global_state.places["test_loc"] = Place(place_id="test_loc", name="测试地点")
        state.global_state.items["test_item"] = GameItem(item_id="test_item", name="测试物品")

        result = agent.execute("去酒吧", state.global_state)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("去酒吧", user_msg)
        self.assertIn("=== 全局世界资产表 ===", user_msg)

        data = result.structured
        self.assertEqual(data.get("target_place", {}).get("id"), "bar")
        self.assertEqual(data.get("situation_prompt"), "安静")


class TestWorldAnalyzerAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "分析世界变动", '
                    '"entity_updates": [], "proposed_relationships": [], "new_entities_mentioned": []}',
                    {},
                )
            ]
        )
        agent = WorldAnalyzerAgent(mock_llm)
        state = make_test_game_state()
        state.scene.narrative_history.append("一段发生的故事。")

        result = agent.execute(state.scene, state.global_state)

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("当前场景图上下文", user_msg)
        self.assertIn("刚刚结束的场景叙事", user_msg)

        self.assertIn("entity_updates", result.structured)


class TestEdgeMergeAgent(unittest.TestCase):
    def test_execute(self):
        mock_llm = MockLLMClient(
            responses=[
                (
                    '{"reasoning": "融合边", '
                    '"merged_source_id": "a", "merged_target_id": "b", "merged_description": "好朋友"}',
                    {},
                )
            ]
        )
        agent = EdgeMergeAgent(mock_llm)

        result = agent.execute("a", "描述a", "b", "描述b", ["a -> b: 认识", "b -> a: 朋友"])

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("描述a", user_msg)
        self.assertIn("认识", user_msg)

        data = result.structured
        self.assertEqual(data.get("merged_description"), "好朋友")


if __name__ == "__main__":
    unittest.main()
