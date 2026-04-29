import unittest

from src.engine import (
    add_story_tag,
    apply_status,
    calculate_power,
    check_limits,
    nudge_status,
    reduce_status,
    remove_status,
    remove_story_tag,
    resolve_matched_tags,
    roll_dice,
)
from src.models import Challenge, Character, Limit, PowerTag, RollResult, WeaknessTag


class TestCalculatePower(unittest.TestCase):
    def setUp(self):
        self.p1 = PowerTag(name="前公司安保")
        self.p2 = PowerTag(name="快速拔枪")
        self.p3 = PowerTag(name="读懂房间")
        self.w1 = WeaknessTag(name="信用破产")
        self.w2 = WeaknessTag(name="另一个弱点")

    def test_no_tags_no_status(self):
        self.assertEqual(calculate_power([], []), 1)

    def test_power_tags_only(self):
        self.assertEqual(calculate_power([self.p1, self.p2], []), 2)

    def test_weakness_tags_only(self):
        self.assertEqual(calculate_power([], [self.w1]), 1)

    def test_mixed_tags(self):
        self.assertEqual(calculate_power([self.p1, self.p2, self.p3], [self.w1]), 2)

    def test_status_helping(self):
        self.assertEqual(calculate_power([], [], best_status_tier=2), 2)

    def test_status_hindering(self):
        self.assertEqual(calculate_power([], [], worst_status_tier=1), 1)

    def test_status_both(self):
        self.assertEqual(calculate_power([], [], best_status_tier=3, worst_status_tier=2), 1)

    def test_tags_and_statuses_combined(self):
        result = calculate_power(
            [self.p1, self.p2],
            [self.w1],
            best_status_tier=2,
            worst_status_tier=1,
        )
        self.assertEqual(result, 2)

    def test_power_minimum_one(self):
        self.assertEqual(calculate_power([], [self.w1, self.w2], worst_status_tier=2), 1)


class TestResolveMatchedTags(unittest.TestCase):
    def setUp(self):
        self.character = Character(
            name="Kael",
            power_tags=[
                PowerTag(name="快速拔枪"),
                PowerTag(name="前公司安保"),
            ],
            weakness_tags=[
                WeaknessTag(name="信用破产"),
            ],
        )
        self.challenge = Challenge(
            name="Miko",
            description="中间人",
            limits=[],
            base_tags=[PowerTag(name="主场优势")],
        )

    def test_resolve_power_from_character(self):
        power, weakness = resolve_matched_tags(self.character, self.challenge, ["快速拔枪"], [])
        self.assertEqual(len(power), 1)
        self.assertEqual(power[0].name, "快速拔枪")
        self.assertEqual(len(weakness), 0)

    def test_resolve_weakness_from_character(self):
        power, weakness = resolve_matched_tags(self.character, self.challenge, [], ["信用破产"])
        self.assertEqual(len(power), 0)
        self.assertEqual(len(weakness), 1)
        self.assertEqual(weakness[0].name, "信用破产")

    def test_resolve_power_from_challenge_base_tags(self):
        power, weakness = resolve_matched_tags(self.character, self.challenge, ["主场优势"], [])
        self.assertEqual(len(power), 1)
        self.assertEqual(power[0].name, "主场优势")
        self.assertEqual(len(weakness), 0)

    def test_resolve_unknown_name_filtered(self):
        power, weakness = resolve_matched_tags(
            self.character, self.challenge, ["不存在的能力"], ["不存在的弱点"]
        )
        self.assertEqual(len(power), 0)
        self.assertEqual(len(weakness), 0)

    def test_challenge_none_does_not_crash(self):
        power, weakness = resolve_matched_tags(self.character, None, ["快速拔枪"], ["信用破产"])
        self.assertEqual(len(power), 1)
        self.assertEqual(len(weakness), 1)

    def test_resolve_multiple_from_all_sources(self):
        power, weakness = resolve_matched_tags(
            self.character,
            self.challenge,
            ["快速拔枪", "前公司安保", "主场优势"],
            ["信用破产"],
        )
        self.assertEqual(len(power), 3)
        self.assertEqual(len(weakness), 1)


class TestRollDice(unittest.TestCase):
    def test_returns_roll_result(self):
        result = roll_dice(1)
        self.assertIsInstance(result, RollResult)
        self.assertEqual(result.power, 1)

    def test_dice_range(self):
        for _ in range(50):
            result = roll_dice(0)
            self.assertIn(result.dice[0], range(1, 7))
            self.assertIn(result.dice[1], range(1, 7))
            raw_total = result.dice[0] + result.dice[1]
            self.assertEqual(result.total, raw_total + result.power)

    def test_outcome_full_success(self):
        for _ in range(100):
            result = roll_dice(100)
            # 箱车（双6）总是成功，但蛇眼（双1）总是失败
            # 当 power=100 时，total 总是 >= 10，但蛇眼例外
            if result.dice == (1, 1):
                self.assertEqual(result.outcome, "failure")
            else:
                self.assertEqual(result.outcome, "full_success")

    def test_outcome_failure(self):
        for _ in range(100):
            result = roll_dice(-100)
            # 蛇眼（双1）总是失败，但箱车（双6）总是成功
            # 当 power=-100 时，total 总是 < 7，但箱车例外
            if result.dice == (6, 6):
                self.assertEqual(result.outcome, "full_success")
            else:
                self.assertEqual(result.outcome, "failure")

    def test_outcome_boundaries(self):
        for power, expected in [
            (-2, "failure"),
            (-1, "failure"),
            (0, "partial_success"),
            (1, "partial_success"),
            (2, "full_success"),
        ]:
            found = set()
            for _ in range(200):
                found.add(roll_dice(power).outcome)
            self.assertIn(expected, found, f"power={power} should be capable of {expected}")


class TestApplyStatus(unittest.TestCase):
    def setUp(self):
        self.character = Character(name="Test", power_tags=[], weakness_tags=[])

    def test_new_status_tier_1(self):
        s = apply_status(self.character, "受伤", 1)
        self.assertEqual(s.name, "受伤")
        self.assertEqual(s.current_tier, 1)
        self.assertIn(1, s.ticked_boxes)

    def test_new_status_tier_3(self):
        s = apply_status(self.character, "受伤", 3)
        self.assertEqual(s.current_tier, 3)
        self.assertIn(3, s.ticked_boxes)
        self.assertNotIn(1, s.ticked_boxes)
        self.assertNotIn(2, s.ticked_boxes)

    def test_overflow_shifts_up(self):
        apply_status(self.character, "受伤", 3)
        s = apply_status(self.character, "受伤", 3)
        self.assertEqual(s.current_tier, 4)
        self.assertIn(3, s.ticked_boxes)
        self.assertIn(4, s.ticked_boxes)

    def test_multiple_overflow_steps(self):
        apply_status(self.character, "受伤", 5)
        apply_status(self.character, "受伤", 5)
        s = apply_status(self.character, "受伤", 5)
        self.assertIn(5, s.ticked_boxes)
        self.assertIn(6, s.ticked_boxes)
        self.assertEqual(s.current_tier, 6)

    def test_overflow_past_six_is_noop(self):
        for _ in range(10):
            apply_status(self.character, "受伤", 6)
        s = self.character.statuses["受伤"]
        self.assertIn(6, s.ticked_boxes)
        self.assertNotIn(7, s.ticked_boxes)
        self.assertEqual(s.current_tier, 6)

    def test_limit_category_set_on_create(self):
        s = apply_status(self.character, "被说服", 2, limit_category="说服")
        self.assertEqual(s.limit_category, "说服")

    def test_limit_category_not_overwritten(self):
        apply_status(self.character, "被说服", 1, limit_category="first")
        apply_status(self.character, "被说服", 2)
        self.assertEqual(self.character.statuses["被说服"].limit_category, "first")

    def test_tier_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            apply_status(self.character, "受伤", 0)
        with self.assertRaises(ValueError):
            apply_status(self.character, "受伤", 7)

    def test_applies_to_challenge(self):
        challenge = Challenge(
            name="敌人",
            description="test",
            limits=[Limit(name="伤害", max_tier=4)],
        )
        s = apply_status(challenge, "流血", 2, limit_category="伤害")
        self.assertIn("流血", challenge.statuses)
        self.assertEqual(s.limit_category, "伤害")
        self.assertEqual(s.current_tier, 2)

    def test_noncontiguous_ticked_boxes(self):
        apply_status(self.character, "受伤", 2)
        s = apply_status(self.character, "受伤", 5)
        self.assertIn(2, s.ticked_boxes)
        self.assertIn(5, s.ticked_boxes)
        self.assertNotIn(3, s.ticked_boxes)
        self.assertEqual(s.current_tier, 5)


class TestRemoveStatus(unittest.TestCase):
    def setUp(self):
        self.character = Character(name="Test", power_tags=[], weakness_tags=[])

    def test_remove_nonexistent_returns_none(self):
        self.assertIsNone(remove_status(self.character, "受伤", 1))

    def test_remove_highest_box(self):
        apply_status(self.character, "受伤", 3)
        s = remove_status(self.character, "受伤", 3)
        self.assertIsNone(s)
        self.assertNotIn("受伤", self.character.statuses)

    def test_remove_partial(self):
        apply_status(self.character, "受伤", 2)
        apply_status(self.character, "受伤", 4)
        s = remove_status(self.character, "受伤", 3)
        self.assertIsNotNone(s)
        self.assertEqual(s.current_tier, 4)
        self.assertNotIn(2, s.ticked_boxes)
        self.assertIn(4, s.ticked_boxes)

    def test_remove_from_below_finds_highest_at_or_below(self):
        apply_status(self.character, "受伤", 4)
        s = remove_status(self.character, "受伤", 5)
        self.assertIsNone(s)
        self.assertNotIn("受伤", self.character.statuses)


class TestCheckLimits(unittest.TestCase):
    def setUp(self):
        self.challenge = Challenge(
            name="敌人",
            description="test",
            limits=[
                Limit(name="说服或威胁", max_tier=3),
                Limit(name="伤害或制服", max_tier=4),
            ],
        )

    def test_no_triggered_limits(self):
        self.assertEqual(check_limits(self.challenge), [])

    def test_limit_triggered(self):
        apply_status(self.challenge, "被说服", 3, limit_category="说服或威胁")
        triggered = check_limits(self.challenge)
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0].name, "说服或威胁")

    def test_limit_not_triggered_below_max(self):
        apply_status(self.challenge, "被说服", 2, limit_category="说服或威胁")
        self.assertEqual(check_limits(self.challenge), [])

    def test_multiple_limits_triggered(self):
        apply_status(self.challenge, "被说服", 3, limit_category="说服或威胁")
        apply_status(self.challenge, "流血", 4, limit_category="伤害或制服")
        triggered = check_limits(self.challenge)
        self.assertEqual(len(triggered), 2)
        triggered_names = {lim.name for lim in triggered}
        self.assertEqual(triggered_names, {"说服或威胁", "伤害或制服"})


class TestReduceStatus(unittest.TestCase):
    def setUp(self):
        self.character = Character(name="Test", power_tags=[], weakness_tags=[])

    def test_reduce_nonexistent_returns_none(self):
        self.assertIsNone(reduce_status(self.character, "受伤", 1))

    def test_reduce_one_level(self):
        apply_status(self.character, "受伤", 2)
        apply_status(self.character, "受伤", 4)
        # ticked: {2, 4}, current_tier=4
        s = reduce_status(self.character, "受伤", 1)
        # 移除最高盒子4 → ticked: {2}, current_tier=2
        self.assertIsNotNone(s)
        self.assertEqual(s.current_tier, 2)
        self.assertNotIn(4, s.ticked_boxes)
        self.assertIn(2, s.ticked_boxes)

    def test_reduce_to_zero_removes_status(self):
        apply_status(self.character, "受伤", 3)
        s = reduce_status(self.character, "受伤", 1)
        # 只有盒子3，移除后状态归零删除
        self.assertIsNone(s)
        self.assertNotIn("受伤", self.character.statuses)

    def test_reduce_multiple_levels(self):
        apply_status(self.character, "受伤", 1)
        apply_status(self.character, "受伤", 1)
        apply_status(self.character, "受伤", 1)
        # overflow: 1→2→3, ticked: {1,2,3}, current_tier=3
        s = reduce_status(self.character, "受伤", 2)
        # 移除3, 移除2 → ticked: {1}, current_tier=1
        self.assertIsNotNone(s)
        self.assertEqual(s.current_tier, 1)
        self.assertIn(1, s.ticked_boxes)
        self.assertNotIn(3, s.ticked_boxes)
        self.assertNotIn(2, s.ticked_boxes)

    def test_reduce_more_than_exists(self):
        apply_status(self.character, "受伤", 2)
        # ticked: {2}, current_tier=2
        s = reduce_status(self.character, "受伤", 5)
        # 移除2, 没有更多, 状态归零删除
        self.assertIsNone(s)
        self.assertNotIn("受伤", self.character.statuses)

    def test_reduce_on_challenge(self):
        challenge = Challenge(
            name="敌人", description="test", limits=[Limit(name="伤害", max_tier=4)]
        )
        apply_status(challenge, "受伤", 2)
        apply_status(challenge, "受伤", 5)
        # ticked: {2, 5}, current_tier=5
        s = reduce_status(challenge, "受伤", 1)
        # 移除5 → ticked: {2}, current_tier=2
        self.assertIsNotNone(s)
        self.assertEqual(s.current_tier, 2)


class TestNudgeStatus(unittest.TestCase):
    def setUp(self):
        self.character = Character(name="Test", power_tags=[], weakness_tags=[])

    def test_nudge_new_status_creates_at_tier_1(self):
        s = nudge_status(self.character, "被说服")
        self.assertEqual(s.current_tier, 1)
        self.assertIn(1, s.ticked_boxes)

    def test_nudge_advances_status_by_one(self):
        apply_status(self.character, "被说服", 2)
        # current_tier=2, ticked={2}
        s = nudge_status(self.character, "被说服")
        # 应该勾选盒子3
        self.assertEqual(s.current_tier, 3)
        self.assertIn(2, s.ticked_boxes)
        self.assertIn(3, s.ticked_boxes)

    def test_nudge_at_tier_6_is_noop(self):
        apply_status(self.character, "受伤", 6)
        s = nudge_status(self.character, "受伤")
        self.assertEqual(s.current_tier, 6)
        self.assertIn(6, s.ticked_boxes)
        self.assertNotIn(7, s.ticked_boxes)

    def test_nudge_on_challenge(self):
        challenge = Challenge(
            name="敌人", description="test", limits=[Limit(name="说服或威胁", max_tier=3)]
        )
        apply_status(challenge, "愿意交易", 2, limit_category="说服")
        # current_tier=2, ticked={2}
        s = nudge_status(challenge, "愿意交易")
        # 应该勾选盒子3 → 极限触发！
        self.assertEqual(s.current_tier, 3)
        self.assertIn(3, s.ticked_boxes)

    def test_nudge_retains_limit_category(self):
        apply_status(self.character, "被说服", 1, limit_category="说服")
        s = nudge_status(self.character, "被说服")
        self.assertEqual(s.limit_category, "说服")

    def test_double_nudge(self):
        apply_status(self.character, "受伤", 1)
        nudge_status(self.character, "受伤")
        s = nudge_status(self.character, "受伤")
        self.assertEqual(s.current_tier, 3)
        self.assertIn(1, s.ticked_boxes)
        self.assertIn(2, s.ticked_boxes)
        self.assertIn(3, s.ticked_boxes)


class TestStoryTagEngine(unittest.TestCase):
    def setUp(self):
        self.character = Character(name="Test", power_tags=[], weakness_tags=[])
        self.challenge = Challenge(name="敌人", description="test", limits=[])

    def test_add_story_tag_to_character(self):
        tag = add_story_tag(self.character, "临时掩体", "翻倒的桌子")
        self.assertIn("临时掩体", self.character.story_tags)
        self.assertEqual(tag.name, "临时掩体")
        self.assertEqual(tag.description, "翻倒的桌子")
        self.assertFalse(tag.is_single_use)

    def test_add_story_tag_single_use(self):
        tag = add_story_tag(self.character, "闪光弹", "一发闪光弹", is_single_use=True)
        self.assertTrue(tag.is_single_use)

    def test_add_story_tag_to_challenge(self):
        _tag = add_story_tag(self.challenge, "增援", "帮派成员到达")
        self.assertIn("增援", self.challenge.story_tags)

    def test_remove_story_tag(self):
        add_story_tag(self.character, "临时掩体", "翻倒的桌子")
        result = remove_story_tag(self.character, "临时掩体")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "临时掩体")
        self.assertNotIn("临时掩体", self.character.story_tags)

    def test_remove_nonexistent_story_tag(self):
        result = remove_story_tag(self.character, "不存在")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
