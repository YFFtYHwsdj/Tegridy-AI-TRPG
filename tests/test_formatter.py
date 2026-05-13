import unittest

from src.formatter import (
    format_role_tags,
    format_statuses,
    format_story_tags,
)
from src.models import PowerTag, Status, StoryTag, WeaknessTag


class TestFormatRoleTags(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(format_role_tags([]), "")

    def test_with_description(self):
        tags = [PowerTag(name="快速拔枪", description="枪法快")]
        result = format_role_tags(tags)
        self.assertIn("[power]", result)
        self.assertIn("快速拔枪", result)
        self.assertIn("(枪法快)", result)

    def test_without_description(self):
        tags = [WeaknessTag(name="信用破产")]
        result = format_role_tags(tags)
        self.assertIn("[weakness]", result)
        self.assertIn("信用破产", result)
        self.assertNotIn("()", result)


class TestFormatStatuses(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_statuses({}), "  (无当前状态)")

    def test_single(self):
        statuses = {"受伤": Status(name="受伤", current_tier=2, ticked_boxes={2})}
        result = format_statuses(statuses)
        self.assertIn("受伤", result)
        self.assertIn("等级2", result)
        self.assertIn("[2]", result)

    def test_multiple(self):
        statuses = {
            "受伤": Status(name="受伤", current_tier=3, ticked_boxes={1, 3}),
            "被说服": Status(name="被说服", current_tier=1, ticked_boxes={1}),
        }
        result = format_statuses(statuses)
        self.assertIn("受伤", result)
        self.assertIn("被说服", result)
        self.assertIn("[1, 3]", result)


class TestFormatStoryTags(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(format_story_tags({}), "  (无故事标签)")

    def test_basic(self):
        tags = {"掩体": StoryTag(name="掩体", description="翻倒的桌子")}
        result = format_story_tags(tags)
        self.assertIn("掩体", result)
        self.assertIn("翻倒的桌子", result)

    def test_single_use(self):
        tags = {"闪光弹": StoryTag(name="闪光弹", is_single_use=True)}
        result = format_story_tags(tags)
        self.assertIn("闪光弹", result)
        self.assertIn("单次使用", result)

    def test_consumable(self):
        tags = {"急救包": StoryTag(name="急救包", is_consumable=True)}
        result = format_story_tags(tags)
        self.assertIn("急救包", result)
        self.assertIn("消耗品", result)

    def test_single_use_and_consumable(self):
        tags = {"医疗无人机": StoryTag(name="医疗无人机", is_single_use=True, is_consumable=True)}
        result = format_story_tags(tags)
        self.assertIn("单次使用", result)
        self.assertIn("消耗品", result)


if __name__ == "__main__":
    unittest.main()
