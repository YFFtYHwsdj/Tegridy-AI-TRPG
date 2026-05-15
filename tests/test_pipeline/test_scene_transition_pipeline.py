"""测试 SceneTransitionPipeline。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.models import AgentNote
from src.pipeline.scene_transition_pipeline import SceneTransitionPipeline
from tests.helpers import make_test_game_state


class TestSceneTransitionPipeline(unittest.TestCase):
    """测试场景过渡流水线。"""

    def setUp(self):
        self.state = make_test_game_state()
        self.pipeline = SceneTransitionPipeline(MagicMock(), self.state)

        # Mock 所有 Agent
        self.pipeline.compressor = MagicMock()
        self.pipeline.world_analyzer = MagicMock()
        self.pipeline.edge_merge = MagicMock()
        self.pipeline.crack_evaluator = MagicMock()
        self.pipeline.scene_router = MagicMock()
        self.pipeline.place_gen = MagicMock()
        self.pipeline.npc_gen = MagicMock()
        self.pipeline.item_gen = MagicMock()
        self.pipeline.challenge_gen = MagicMock()

    def test_execute_full_flow(self):
        """测试完整的执行管线：压缩、推演、裂痕、路由、生成、切换。"""
        old_scene = self.state.scene

        self.pipeline.compressor.execute.return_value = AgentNote(
            reasoning="压缩", structured={"scene_summary": "旧场景压缩了"}
        )

        # 世界推演什么都不做
        self.pipeline.world_analyzer.execute.return_value = AgentNote(
            reasoning="分析", structured={}
        )

        # 裂痕评估，触发已有主题
        self.pipeline.crack_evaluator.execute.return_value = AgentNote(
            reasoning="裂痕评估",
            structured={"cracked_themes": [{"theme_name": "测试", "reason": "某原因"}]},
        )

        # 路由，要求生成四个新资产
        self.pipeline.scene_router.execute.return_value = AgentNote(
            reasoning="路由",
            structured={
                "target_place": {"id": "new_loc", "is_new": True, "generation_prompt": "地点P"},
                "target_npcs": [{"id": "npc1", "is_new": True, "generation_prompt": "NPCP"}],
                "target_items": [{"id": "item1", "is_new": True, "generation_prompt": "物品P"}],
                "target_challenges": [
                    {"id": "chal1", "is_new": True, "generation_prompt": "挑战P"}
                ],
                "situation_prompt": "新状况",
            },
        )

        self.pipeline.place_gen.execute.return_value = {"id": "new_loc", "name": "新地点"}
        self.pipeline.npc_gen.execute.return_value = {"id": "npc1", "name": "新NPC"}
        self.pipeline.item_gen.execute.return_value = {"id": "item1", "name": "新物品"}
        self.pipeline.challenge_gen.execute.return_value = {"id": "chal1", "name": "新挑战"}

        # 执行
        self.pipeline.execute("玩家提示：去酒吧")

        # 验证 1. 场景压缩
        self.pipeline.compressor.execute.assert_called_once_with(old_scene, self.state.global_state)
        self.assertEqual(old_scene.compression, "旧场景压缩了")

        # 验证 2. 裂痕添加
        self.pipeline.crack_evaluator.execute.assert_called_once()
        t = self.state.character.get_theme("测试")
        self.assertEqual(t.crack_track, 1)

        # 验证 3. 生成器调用
        self.pipeline.place_gen.execute.assert_called_once_with("地点P", "new_loc")
        self.pipeline.npc_gen.execute.assert_called_once_with("NPCP", "npc1")
        self.pipeline.item_gen.execute.assert_called_once_with("物品P", "item1")
        self.pipeline.challenge_gen.execute.assert_called_once_with("挑战P", "chal1")

        # 验证 4. global state 更新
        self.assertIn("new_loc", self.state.global_state.places)
        self.assertIn("npc1", self.state.global_state.npcs)
        self.assertIn("item1", self.state.global_state.items)
        self.assertIn("chal1", self.state.global_state.challenges)

        # 验证 5. 场景切换
        self.assertNotEqual(self.state.scene, old_scene)
        self.assertEqual(self.state.scene.place_id, "new_loc")
        self.assertEqual(self.state.scene.situation, "新状况")
        self.assertIn("npc1", self.state.scene.active_npc_ids)
        self.assertIn("item1", self.state.scene.active_item_ids)
        self.assertIn("chal1", self.state.scene.active_challenge_ids)

    def test_execute_with_empty_ids(self):
        """测试场景路由返回空 id 时的防御逻辑。"""
        self.pipeline.compressor.execute.return_value = AgentNote(reasoning="", structured={})
        self.pipeline.world_analyzer.execute.return_value = AgentNote(reasoning="", structured={})
        self.pipeline.scene_router.execute.return_value = AgentNote(
            reasoning="路由",
            structured={
                "target_place": {"id": "new_loc", "is_new": True, "generation_prompt": "地点P"},
                "target_npcs": [{"id": "", "is_new": True}],
                "target_items": [{"id": "", "is_new": True}],
                "target_challenges": [{"id": "", "is_new": True}],
                "situation_prompt": "新状况",
            },
        )
        self.pipeline.place_gen.execute.return_value = {"id": "new_loc", "name": "新地点"}

        self.pipeline.execute("去测试")

        self.pipeline.npc_gen.execute.assert_not_called()
        self.pipeline.item_gen.execute.assert_not_called()
        self.pipeline.challenge_gen.execute.assert_not_called()


if __name__ == "__main__":
    unittest.main()
