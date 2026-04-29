"""全局状态管理测试 —— GlobalState 的追加和上下文构建。"""

import unittest

from src.state.global_state import GlobalState


class TestGlobalState(unittest.TestCase):
    def setUp(self):
        self.gs = GlobalState()

    def test_defaults(self):
        self.assertEqual(self.gs.scene_count, 0)
        self.assertEqual(self.gs.build_block(), "")

    def test_append_and_scene_count(self):
        self.gs.append("abc123", "酒吧场景", "压缩摘要", ["叙事1", "叙事2"])
        self.assertEqual(self.gs.scene_count, 1)

    def test_build_block_single_scene(self):
        """只有一个已完成场景时，应输出完整叙事。"""
        self.gs.append(
            "abc123",
            "酒吧场景",
            "Kael在酒吧与Miko谈判，最终拿到了芯片。",
            ["你走进了酒吧", "Miko抬头看着你", "你亮出了证据"],
        )

        block = self.gs.build_block()
        self.assertIn("=== 故事至今 ===", block)
        self.assertIn("酒吧场景", block)
        self.assertIn("Kael在酒吧与Miko谈判", block)
        self.assertIn("上一场景完整叙事", block)
        self.assertIn("[T1] 你走进了酒吧", block)
        self.assertIn("[T2] Miko抬头看着你", block)
        self.assertIn("[T3] 你亮出了证据", block)

    def test_build_block_multiple_scenes(self):
        """多个已完成场景时，更早场景只输出压缩摘要，最后场景输出完整叙事。"""
        self.gs.append(
            "id1",
            "酒吧场景",
            "压缩摘要A",
            ["酒吧叙事1", "酒吧叙事2"],
        )
        self.gs.append(
            "id2",
            "后巷场景",
            "压缩摘要B",
            ["后巷叙事1", "后巷叙事2"],
        )
        self.gs.append(
            "id3",
            "屋顶场景",
            "压缩摘要C",
            ["屋顶叙事1", "屋顶叙事2"],
        )

        block = self.gs.build_block()

        # 场景1（更早）→ 只输出压缩摘要，不输出完整叙事
        self.assertIn("酒吧场景", block)
        self.assertIn("压缩摘要A", block)
        self.assertNotIn("酒吧叙事1", block)

        # 场景2（更早）→ 只输出压缩摘要
        self.assertIn("后巷场景", block)
        self.assertIn("压缩摘要B", block)
        self.assertNotIn("后巷叙事1", block)

        # 场景3（最后一个）→ 压缩摘要 + 完整叙事
        self.assertIn("屋顶场景", block)
        self.assertIn("压缩摘要C", block)
        self.assertIn("上一场景完整叙事", block)
        self.assertIn("[T1] 屋顶叙事1", block)
        self.assertIn("[T2] 屋顶叙事2", block)

    def test_build_block_empty_narrative(self):
        """空叙事列表也应安全输出。"""
        self.gs.append("id1", "空场景", "无内容的压缩", [])

        block = self.gs.build_block()
        self.assertIn("上一场景完整叙事", block)
        self.assertIn("（无叙事记录）", block)

    def test_build_block_no_compression(self):
        """无压缩摘要时应输出占位文本。"""
        self.gs.append("id1", "测试场景", "", ["叙事1"])

        block = self.gs.build_block()
        self.assertIn("（无压缩摘要）", block)
        self.assertIn("[T1] 叙事1", block)

    def test_append_copies_narrative(self):
        """append 应对叙事列表做浅拷贝，避免外部修改影响存储。"""
        narratives = ["原始叙事"]
        self.gs.append("id1", "场景", "", narratives)
        narratives.append("后加的叙事")

        block = self.gs.build_block()
        self.assertNotIn("后加的叙事", block)

    def test_build_block_preserves_scene_description_in_earlier_scenes(self):
        """更早场景的描述应出现在上下文中。"""
        self.gs.append("id1", "第一个场景", "摘要1", ["叙事A"])
        self.gs.append("id2", "第二个场景", "摘要2", ["叙事B"])

        block = self.gs.build_block()
        self.assertIn("第一个场景", block)
        self.assertNotIn("叙事A", block)
        self.assertIn("第二个场景", block)
        self.assertIn("叙事B", block)


if __name__ == "__main__":
    unittest.main()
