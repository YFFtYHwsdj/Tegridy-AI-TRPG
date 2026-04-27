import unittest
import random
from src.engine import calculate_power, roll_dice, apply_status, remove_status, check_limits
from src.models import Character, Challenge, Status, Limit, RollResult, Tag


class TestCalculatePower(unittest.TestCase):

    def test_no_tags_no_status(self):
        self.assertEqual(calculate_power([], []), 0)

    def test_power_tags_only(self):
        self.assertEqual(calculate_power(["前公司安保", "快速拔枪"], []), 2)

    def test_weakness_tags_only(self):
        self.assertEqual(calculate_power([], ["信用破产"]), -1)

    def test_mixed_tags(self):
        self.assertEqual(
            calculate_power(["前公司安保", "快速拔枪", "读懂房间"], ["信用破产"]),
            2
        )

    def test_status_helping(self):
        self.assertEqual(calculate_power([], [], best_status_tier=2), 2)

    def test_status_hindering(self):
        self.assertEqual(calculate_power([], [], worst_status_tier=1), -1)

    def test_status_both(self):
        self.assertEqual(calculate_power([], [], best_status_tier=3, worst_status_tier=2), 1)

    def test_tags_and_statuses_combined(self):
        result = calculate_power(
            ["前公司安保", "快速拔枪"],
            ["信用破产"],
            best_status_tier=2,
            worst_status_tier=1,
        )
        self.assertEqual(result, 2)

    def test_negative_power(self):
        self.assertEqual(calculate_power([], ["信用破产", "另一个弱点"], worst_status_tier=2), -4)


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
            self.assertEqual(result.outcome, "full_success")

    def test_outcome_failure(self):
        for _ in range(100):
            result = roll_dice(-100)
            self.assertEqual(result.outcome, "failure")

    def test_outcome_boundaries(self):
        for power, expected in [(-2, "failure"), (-1, "failure"), (0, "partial_success"),
                                (1, "partial_success"), (2, "full_success")]:
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
        triggered_names = {l.name for l in triggered}
        self.assertEqual(triggered_names, {"说服或威胁", "伤害或制服"})


if __name__ == "__main__":
    unittest.main()
