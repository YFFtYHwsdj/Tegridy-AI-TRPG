import unittest
from src.formatter import (
    format_role_tags,
    format_statuses,
    format_story_tags,
    format_limit_progress,
    format_challenge_state,
    format_limit_gap,
)
from src.models import Tag, Status, StoryTag, Limit, Challenge


class TestFormatRoleTags(unittest.TestCase):

    def test_empty_list(self):
        self.assertEqual(format_role_tags([]), "")

    def test_with_description(self):
        tags = [Tag(name="快速拔枪", tag_type="power", description="枪法快")]
        result = format_role_tags(tags)
        self.assertIn("[power]", result)
        self.assertIn("快速拔枪", result)
        self.assertIn("(枪法快)", result)

    def test_without_description(self):
        tags = [Tag(name="信用破产", tag_type="weakness")]
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


class TestFormatLimitProgress(unittest.TestCase):

    def test_full(self):
        limit = Limit(name="伤害", max_tier=4)
        result = format_limit_progress(limit, 4)
        self.assertEqual(result, "伤害: [█/█/█/█] 4/4")

    def test_partial(self):
        limit = Limit(name="伤害", max_tier=4)
        result = format_limit_progress(limit, 2)
        self.assertEqual(result, "伤害: [█/█/░/░] 2/4")


class TestFormatChallengeState(unittest.TestCase):

    def setUp(self):
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[
                Limit(name="说服或威胁", max_tier=3),
                Limit(name="伤害或制服", max_tier=4),
            ],
            base_tags=[
                Tag(name="精明的谈判者", tag_type="power"),
                Tag(name="两个专业保镖", tag_type="power"),
            ],
            notes="Miko 重视情报",
        )

    def test_full_state(self):
        result = format_challenge_state(self.challenge)
        self.assertIn("挑战:", result)
        self.assertIn("Miko 与她的保镖", result)
        self.assertIn("描述:", result)
        self.assertIn("便签:", result)
        self.assertIn("极限:", result)
        self.assertIn("基础标签:", result)
        self.assertIn("精明的谈判者", result)
        self.assertIn("故事标签:", result)
        self.assertIn("当前状态:", result)

    def test_no_notes_no_base_tags(self):
        challenge = Challenge(
            name="简单挑战",
            description="测试",
            limits=[Limit(name="伤害", max_tier=3)],
        )
        result = format_challenge_state(challenge)
        self.assertNotIn("便签:", result)
        self.assertNotIn("基础标签:", result)
        self.assertIn("极限:", result)


class TestFormatLimitGap(unittest.TestCase):

    def setUp(self):
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[
                Limit(name="说服或威胁", max_tier=3),
                Limit(name="伤害或制服", max_tier=4),
            ],
        )

    def test_with_statuses(self):
        self.challenge.statuses["被说服"] = Status(
            name="被说服", current_tier=2, ticked_boxes={2}, limit_category="说服或威胁"
        )
        result = format_limit_gap(self.challenge)
        self.assertIn("说服或威胁", result)
        self.assertIn("2/3", result)
        self.assertIn("+1", result)
        self.assertIn("被说服", result)

    def test_no_statuses(self):
        result = format_limit_gap(self.challenge)
        self.assertIn("尚无状态", result)
        self.assertIn("+3", result)

    def test_empty_limits(self):
        challenge = Challenge(name="空", description="无极限", limits=[])
        result = format_limit_gap(challenge)
        self.assertIn("(无极限)", result)


if __name__ == "__main__":
    unittest.main()
