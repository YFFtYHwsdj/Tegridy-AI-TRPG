"""测试世界推演与图边融合管线。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from src.models import NPC, AgentNote
from src.pipeline.world_update_pipeline import apply_world_updates
from tests.helpers import make_test_game_state


class TestWorldUpdatePipeline(unittest.TestCase):
    """测试 world_update_pipeline 的 apply_world_updates 方法。"""

    def setUp(self):
        self.state = make_test_game_state()

        # 添加一些基础实体以供推演
        self.npc_a = NPC(name="Alice")
        self.npc_b = NPC(name="Bob")
        self.npc_a.relationships["bob_id"] = "朋友"

        self.state.global_state.npcs["alice_id"] = self.npc_a
        self.state.global_state.npcs["bob_id"] = self.npc_b

        self.analyzer = MagicMock()
        self.merger = MagicMock()

    def test_apply_world_updates_no_conflict(self):
        """测试没有冲突边时的情况：更新笔记，直接插入新边。"""
        self.analyzer.execute.return_value = AgentNote(
            reasoning="推演",
            structured={
                "entity_updates": [
                    {"entity_id": "alice_id", "entity_type": "npc", "revised_notes": "爱丽丝受伤了"}
                ],
                "proposed_relationships": [
                    {"source_id": "bob_id", "target_id": "charlie_id", "description": "认识新朋友"}
                ],
                "new_entities_mentioned": [{"name": "Charlie"}],
            },
        )

        # 临时添加 charlie 实体，否则获取不到会失败或无法插入关系
        self.state.global_state.npcs["charlie_id"] = NPC(name="Charlie")

        new_entities = apply_world_updates(
            self.analyzer, self.merger, self.state.scene, self.state.global_state
        )

        # 验证实体笔记被更新
        self.assertEqual(self.state.global_state.npcs["alice_id"].notes, "爱丽丝受伤了")

        # 验证原本的边依然存在（因为没有冲突，被加回）
        self.assertEqual(
            self.state.global_state.npcs["alice_id"].relationships.get("bob_id"), "朋友"
        )

        # 验证新边被插入
        self.assertEqual(
            self.state.global_state.npcs["bob_id"].relationships.get("charlie_id"), "认识新朋友"
        )

        self.merger.execute.assert_not_called()
        self.assertEqual(len(new_entities), 1)

    def test_apply_world_updates_with_conflict(self):
        """测试有冲突边时的情况：触发合并，插入合并后的边。"""
        # 原图中已经有 Alice -> Bob: 朋友
        # 现在推演提出 Alice -> Bob: 敌人
        self.analyzer.execute.return_value = AgentNote(
            reasoning="推演",
            structured={
                "entity_updates": [],
                "proposed_relationships": [
                    {"source_id": "alice_id", "target_id": "bob_id", "description": "变成敌人"}
                ],
                "new_entities_mentioned": [],
            },
        )

        self.merger.execute.return_value = AgentNote(
            reasoning="合并",
            structured={
                "merged_source_id": "alice_id",
                "merged_target_id": "bob_id",
                "merged_description": "曾经的朋友，现在的敌人",
            },
        )

        apply_world_updates(self.analyzer, self.merger, self.state.scene, self.state.global_state)

        # 验证触发了合并
        self.merger.execute.assert_called_once()

        # 验证新边覆盖了旧边
        self.assertEqual(
            self.state.global_state.npcs["alice_id"].relationships.get("bob_id"),
            "曾经的朋友，现在的敌人",
        )

    def test_apply_world_updates_edge_cases(self):
        from src.models import Place

        self.state.global_state.places["place_id"] = Place(name="地点1")

        self.analyzer.execute.return_value = AgentNote(
            reasoning="推演",
            structured={
                "entity_updates": [
                    {"entity_id": "", "entity_type": "npc", "revised_notes": "爱丽丝受伤了"},
                    {"entity_id": "alice_id", "entity_type": "npc", "revised_notes": ""},
                ],
                "proposed_relationships": [
                    {"source_id": "", "target_id": "bob_id", "description": "无效"},
                    {"source_id": "alice_id", "target_id": "bob_id", "description": ""},
                    {"source_id": "place_id", "target_id": "bob_id", "description": "关联地点"},
                ],
            },
        )

        apply_world_updates(self.analyzer, self.merger, self.state.scene, self.state.global_state)

        # alice_id note should not be updated
        self.assertEqual(self.state.global_state.npcs["alice_id"].notes, "")

        # place_id connections should have the new edge
        self.assertEqual(
            self.state.global_state.places["place_id"].connections.get("bob_id"), "关联地点"
        )


if __name__ == "__main__":
    unittest.main()
