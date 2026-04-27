import unittest
from src.models import Tag, Status, StoryTag, Limit, Challenge, Character, RollResult, EffectEntry, ConsequenceEntry, AgentNote


class TestTag(unittest.TestCase):

    def test_power_tag(self):
        t = Tag(name="快速拔枪", tag_type="power", description="枪法快")
        self.assertEqual(t.name, "快速拔枪")
        self.assertEqual(t.tag_type, "power")
        self.assertEqual(t.description, "枪法快")

    def test_weakness_tag(self):
        t = Tag(name="信用破产", tag_type="weakness")
        self.assertEqual(t.tag_type, "weakness")
        self.assertEqual(t.description, "")

    def test_invalid_tag_type_raises(self):
        with self.assertRaises(ValueError):
            Tag(name="bad", tag_type="neutral")


class TestStatus(unittest.TestCase):

    def test_defaults(self):
        s = Status(name="受伤")
        self.assertEqual(s.name, "受伤")
        self.assertEqual(s.current_tier, 0)
        self.assertEqual(s.ticked_boxes, set())
        self.assertEqual(s.limit_category, "")


class TestStoryTag(unittest.TestCase):

    def test_defaults(self):
        st = StoryTag(name="临时掩体")
        self.assertEqual(st.name, "临时掩体")
        self.assertEqual(st.description, "")
        self.assertFalse(st.is_single_use)
        self.assertFalse(st.is_consumable)

    def test_with_description(self):
        st = StoryTag(name="啤酒瓶", description="从桌上抓起的空瓶")
        self.assertEqual(st.description, "从桌上抓起的空瓶")

    def test_single_use(self):
        st = StoryTag(name="闪光弹", is_single_use=True)
        self.assertTrue(st.is_single_use)

    def test_consumable(self):
        st = StoryTag(name="急救包", is_consumable=True)
        self.assertTrue(st.is_consumable)


class TestLimit(unittest.TestCase):

    def test_valid_limit(self):
        l = Limit(name="伤害", max_tier=3)
        self.assertEqual(l.name, "伤害")
        self.assertEqual(l.max_tier, 3)
        self.assertFalse(l.is_progress)

    def test_is_progress(self):
        l = Limit(name="穿越", max_tier=4, is_progress=True)
        self.assertTrue(l.is_progress)

    def test_max_tier_too_low_raises(self):
        with self.assertRaises(ValueError):
            Limit(name="bad", max_tier=0)

    def test_max_tier_too_high_raises(self):
        with self.assertRaises(ValueError):
            Limit(name="bad", max_tier=7)


class TestRollResult(unittest.TestCase):

    def test_full_success(self):
        r = RollResult(power=2, dice=(5, 4), total=11, outcome="full_success")
        self.assertEqual(r.total, 11)
        self.assertEqual(r.outcome, "full_success")

    def test_invalid_outcome_raises(self):
        with self.assertRaises(ValueError):
            RollResult(power=0, dice=(3, 3), total=6, outcome="critical_success")


class TestChallenge(unittest.TestCase):

    def setUp(self):
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[
                Limit(name="说服或威胁", max_tier=3),
                Limit(name="伤害或制服", max_tier=4),
            ],
            notes="Miko 重视情报",
        )

    def test_get_matching_statuses_empty(self):
        self.assertEqual(self.challenge.get_matching_statuses("说服或威胁"), [])

    def test_get_matching_statuses_finds_match(self):
        s = Status(name="被说服", current_tier=2, ticked_boxes={2}, limit_category="说服或威胁")
        self.challenge.statuses["被说服"] = s
        results = self.challenge.get_matching_statuses("说服或威胁")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].name, "被说服")

    def test_get_matching_statuses_partial_match(self):
        s = Status(name="被说服", current_tier=2, ticked_boxes={2}, limit_category="说服")
        self.challenge.statuses["被说服"] = s
        results = self.challenge.get_matching_statuses("说服或威胁")
        self.assertEqual(len(results), 1)

    def test_check_limits_no_trigger(self):
        s = Status(name="被说服", current_tier=2, ticked_boxes={2}, limit_category="说服或威胁")
        self.challenge.statuses["被说服"] = s
        self.assertEqual(self.challenge.check_limits(), [])

    def test_check_limits_triggered(self):
        s = Status(name="被说服", current_tier=3, ticked_boxes={3}, limit_category="说服或威胁")
        self.challenge.statuses["被说服"] = s
        triggered = self.challenge.check_limits()
        self.assertEqual(len(triggered), 1)
        self.assertEqual(triggered[0].name, "说服或威胁")

    def test_get_matching_statuses_no_limit_category(self):
        s = Status(name="受伤", current_tier=2, ticked_boxes={2})
        self.challenge.statuses["受伤"] = s
        self.assertEqual(self.challenge.get_matching_statuses("伤害或制服"), [])

    def test_broken_limits_default_empty(self):
        self.assertEqual(self.challenge.broken_limits, set())

    def test_mark_limits_broken(self):
        s = Status(name="被说服", current_tier=3, ticked_boxes={3}, limit_category="说服或威胁")
        self.challenge.statuses["被说服"] = s
        triggered = self.challenge.check_limits()
        self.assertEqual(len(triggered), 1)
        self.challenge.mark_limits_broken([triggered[0].name])
        self.assertIn("说服或威胁", self.challenge.broken_limits)
        self.assertEqual(self.challenge.check_limits(), [])

    def test_already_broken_limit_not_triggered(self):
        s = Status(name="被说服", current_tier=3, ticked_boxes={3}, limit_category="说服或威胁")
        self.challenge.statuses["被说服"] = s
        self.challenge.mark_limits_broken(["说服或威胁"])
        self.assertEqual(self.challenge.check_limits(), [])

    def test_transformation_default_empty(self):
        self.assertEqual(self.challenge.transformation, "")

    def test_story_tags_default_empty(self):
        self.assertEqual(self.challenge.story_tags, {})


class TestCharacter(unittest.TestCase):

    def test_defaults(self):
        c = Character(name="Test")
        self.assertEqual(c.name, "Test")
        self.assertEqual(c.power_tags, [])
        self.assertEqual(c.weakness_tags, [])
        self.assertEqual(c.statuses, {})
        self.assertEqual(c.story_tags, {})
        self.assertEqual(c.burned_tags, set())
        self.assertEqual(c.description, "")

    def test_with_tags(self):
        c = Character(
            name="Kael",
            power_tags=[Tag(name="前公司安保", tag_type="power")],
            weakness_tags=[Tag(name="信用破产", tag_type="weakness")],
            description="佣兵",
        )
        self.assertEqual(len(c.power_tags), 1)
        self.assertEqual(len(c.weakness_tags), 1)

    def test_is_incapacitated_tier_six(self):
        c = Character(name="Test")
        c.statuses["受伤"] = Status(name="受伤", current_tier=6, ticked_boxes={6})
        self.assertTrue(c.is_incapacitated())

    def test_is_incapacitated_explicit_status(self):
        c = Character(name="Test")
        c.statuses["被打晕"] = Status(name="被打晕", current_tier=2, ticked_boxes={1, 2})
        self.assertTrue(c.is_incapacitated())

    def test_not_incapacitated_low_tier(self):
        c = Character(name="Test")
        c.statuses["受伤"] = Status(name="受伤", current_tier=3, ticked_boxes={1, 2, 3})
        self.assertFalse(c.is_incapacitated())

    def test_not_incapacitated_no_statuses(self):
        c = Character(name="Test")
        self.assertFalse(c.is_incapacitated())


class TestEffectEntry(unittest.TestCase):

    def test_defaults(self):
        e = EffectEntry(effect_type="attack", tier=2, target="敌人", label="受伤")
        self.assertEqual(e.effect_type, "attack")
        self.assertEqual(e.tier, 2)
        self.assertEqual(e.target, "敌人")
        self.assertEqual(e.label, "受伤")
        self.assertEqual(e.reasoning, "")


class TestConsequenceEntry(unittest.TestCase):

    def test_defaults(self):
        c = ConsequenceEntry(threat_manifested="保镖上前", narrative_description="保镖向前迈出一步")
        self.assertEqual(c.threat_manifested, "保镖上前")
        self.assertEqual(c.effects, [])
        self.assertEqual(c.narrative_description, "保镖向前迈出一步")


class TestAgentNote(unittest.TestCase):

    def test_basic(self):
        note = AgentNote(reasoning="分析过程", structured={"action_type": "combat"})
        self.assertEqual(note.reasoning, "分析过程")
        self.assertEqual(note.structured["action_type"], "combat")

    def test_empty_structured(self):
        note = AgentNote(reasoning="空分析", structured={})
        self.assertEqual(note.structured, {})


if __name__ == "__main__":
    unittest.main()
