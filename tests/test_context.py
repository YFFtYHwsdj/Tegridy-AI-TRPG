"""测试 AgentContext 与 MessageBuilder。"""

from __future__ import annotations

import unittest

from src.context import AgentContext, MessageBuilder


class TestMessageBuilder(unittest.TestCase):
    def test_add_block_skips_empty(self):
        builder = MessageBuilder()
        builder.add_block("标题", "")
        builder.add_block("标题2", "  \n  ")
        self.assertEqual(len(builder.blocks), 0)

    def test_add_block_formatting(self):
        builder = MessageBuilder()
        builder.add_block("测试1", "内容1", wrap_title=False)
        builder.add_block("测试2", "内容2", wrap_title=True)

        blocks = builder.blocks
        self.assertEqual(len(blocks), 2)
        self.assertEqual(blocks[0], "测试1: 内容1")
        self.assertEqual(blocks[1], "=== 测试2 ===\n内容2")

    def test_add_text_skips_empty(self):
        builder = MessageBuilder()
        builder.add_text("")
        builder.add_text("   \t  ")
        self.assertEqual(len(builder.blocks), 0)

    def test_build(self):
        builder = MessageBuilder()
        builder.add_block("T1", "C1")
        builder.add_text("T2")

        result = builder.build()
        self.assertEqual(result, "T1: C1\n\nT2")


class TestAgentContext(unittest.TestCase):
    def test_build_message_skips_empty_blocks(self):
        ctx = AgentContext(
            worldview_block="赛博朋克设定",
            global_block="",  # 会被跳过
            assets_block="一些资产",
            context_block="   ",  # 只有空格，会被跳过
            narrative_block="叙事内容",
        )

        builder = ctx.build_message(include_global=True)
        result = builder.build()

        self.assertIn("=== 世界观设定 ===\n赛博朋克设定", result)
        self.assertNotIn("跨场景历史", result)
        self.assertIn("=== 当前场景资产 (Assets) ===\n一些资产", result)
        self.assertNotIn("当前场景环境", result)
        self.assertIn("=== 本场景局部叙事 (Narrative) ===\n叙事内容", result)

    def test_build_message_exclude_global(self):
        ctx = AgentContext(global_block="全局信息")

        builder = ctx.build_message(include_global=False)
        result = builder.build()

        self.assertNotIn("全局信息", result)
        self.assertNotIn("跨场景历史", result)


if __name__ == "__main__":
    unittest.main()
