import unittest
from src.effects.applicator import EffectApplicator
from src.models import Character, Challenge, Limit, Tag, AgentNote, Status, StoryTag


class TestResolveTarget(unittest.TestCase):

    def setUp(self):
        self.character = Character(name="Kael", description="佣兵")
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[Limit(name="伤害", max_tier=4)],
        )

    def test_empty_target(self):
        result = EffectApplicator._resolve_target("", self.character, self.challenge)
        self.assertIsNone(result)

    def test_keyword_challenge(self):
        result = EffectApplicator._resolve_target("挑战", self.character, self.challenge)
        self.assertIs(result, self.challenge)

    def test_keyword_self_cn(self):
        result = EffectApplicator._resolve_target("自身", self.character, self.challenge)
        self.assertIs(result, self.character)

    def test_keyword_self_en(self):
        result = EffectApplicator._resolve_target("self", self.character, self.challenge)
        self.assertIs(result, self.character)

    def test_exact_char_name(self):
        result = EffectApplicator._resolve_target("Kael", self.character, self.challenge)
        self.assertIs(result, self.character)

    def test_exact_chal_name(self):
        result = EffectApplicator._resolve_target(
            "Miko 与她的保镖", self.character, self.challenge
        )
        self.assertIs(result, self.challenge)

    def test_exact_case_insensitive(self):
        result = EffectApplicator._resolve_target("kael", self.character, self.challenge)
        self.assertIs(result, self.character)

    def test_no_match(self):
        result = EffectApplicator._resolve_target("外星人", self.character, self.challenge)
        self.assertIsNone(result)

    def test_short_no_match(self):
        result = EffectApplicator._resolve_target("Ka", self.character, self.challenge)
        self.assertIsNone(result)

    def test_fuzzy_char_only(self):
        char = Character(name="Kael", description="")
        chal = Challenge(name="Miko", description="", limits=[])
        result = EffectApplicator._resolve_target("Kae", char, chal)
        self.assertIs(result, char)

    def test_fuzzy_chal_only(self):
        char = Character(name="Kael", description="")
        chal = Challenge(name="Miko", description="", limits=[])
        result = EffectApplicator._resolve_target("Mik", char, chal)
        self.assertIs(result, chal)

    def test_fuzzy_ambiguous_resolved_to_char(self):
        char = Character(name="Kael", description="")
        chal = Challenge(name="KaelM", description="", limits=[])
        result = EffectApplicator._resolve_target("Kael", char, chal)
        self.assertIs(result, char)

    def test_fuzzy_ambiguous_resolved_to_chal(self):
        char = Character(name="KaelM", description="")
        chal = Challenge(name="Kael", description="", limits=[])
        result = EffectApplicator._resolve_target("Kael", char, chal)
        self.assertIs(result, chal)

    def test_fuzzy_ambiguous_unresolved(self):
        char = Character(name="KaelX", description="")
        chal = Challenge(name="KaelY", description="", limits=[])
        result = EffectApplicator._resolve_target("Kael", char, chal)
        self.assertIsNone(result)


class TestApplyEffectList(unittest.TestCase):

    def setUp(self):
        self.character = Character(
            name="Kael",
            power_tags=[Tag(name="快速拔枪", tag_type="power")],
        )
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[Limit(name="伤害", max_tier=4)],
        )

    def test_inflict_status_new(self):
        effects = [{"operation": "inflict_status", "target": "自身", "label": "受伤", "tier": 2, "effect_type": "attack"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertIn("受伤", self.character.statuses)
        self.assertEqual(self.character.statuses["受伤"].current_tier, 2)

    def test_inflict_status_with_limit_category(self):
        effects = [{
            "operation": "inflict_status", "target": "挑战",
            "label": "被说服", "tier": 2,
            "limit_category": "说服或威胁"
        }]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertIn("被说服", self.challenge.statuses)
        self.assertEqual(self.challenge.statuses["被说服"].limit_category, "说服或威胁")

    def test_inflict_status_no_label_skipped(self):
        effects = [{"operation": "inflict_status", "target": "自身", "label": "", "tier": 2}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertEqual(self.character.statuses, {})

    def test_nudge_status_new(self):
        effects = [{"operation": "nudge_status", "target": "自身", "status_to_nudge": "被压制"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertIn("被压制", self.character.statuses)
        self.assertEqual(self.character.statuses["被压制"].current_tier, 1)

    def test_nudge_status_existing(self):
        self.character.statuses["被压制"] = Status(
            name="被压制", current_tier=2, ticked_boxes={2}
        )
        effects = [{"operation": "nudge_status", "target": "自身", "status_to_nudge": "被压制"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertEqual(self.character.statuses["被压制"].current_tier, 3)

    def test_reduce_status(self):
        self.character.statuses["受伤"] = Status(
            name="受伤", current_tier=3, ticked_boxes={2, 3}
        )
        effects = [{"operation": "reduce_status", "target": "自身", "status_to_reduce": "受伤", "reduce_by": 1}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertEqual(self.character.statuses["受伤"].current_tier, 2)

    def test_add_story_tag(self):
        effects = [{"operation": "add_story_tag", "target": "自身", "story_tag_name": "掩体", "story_tag_description": "翻倒的桌子"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertIn("掩体", self.character.story_tags)
        self.assertEqual(self.character.story_tags["掩体"].description, "翻倒的桌子")

    def test_scratch_story_tag(self):
        self.character.story_tags["掩体"] = StoryTag(name="掩体", description="翻倒的桌子")
        effects = [{"operation": "scratch_story_tag", "target": "自身", "story_tag_to_scratch": "掩体"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])
        self.assertNotIn("掩体", self.character.story_tags)

    def test_scratch_nonexistent_story_tag(self):
        effects = [{"operation": "scratch_story_tag", "target": "自身", "story_tag_to_scratch": "不存在"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])

    def test_discover(self):
        effects = [{"operation": "discover", "target": "自身", "detail": "发现隐藏的门"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])

    def test_extra_feat(self):
        effects = [{"operation": "extra_feat", "target": "自身", "description": "一个额外的回合"}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(errors, [])

    def test_unresolved_target_produces_error(self):
        effects = [{"operation": "inflict_status", "target": "外星人", "label": "受伤", "tier": 2}]
        errors = EffectApplicator._apply_effect_list(effects, self.character, self.challenge)
        self.assertEqual(len(errors), 1)
        self.assertIn("外星人", errors[0])
        self.assertNotIn("受伤", self.character.statuses)


class TestApplyResults(unittest.TestCase):

    def setUp(self):
        self.character = Character(
            name="Kael",
            power_tags=[Tag(name="快速拔枪", tag_type="power")],
        )
        self.challenge = Challenge(
            name="Miko 与她的保镖",
            description="中间人",
            limits=[Limit(name="伤害", max_tier=4)],
        )

    def test_apply_effects_and_consequences(self):
        effect_note = AgentNote(
            reasoning="效果推演",
            structured={
                "effects": [
                    {"operation": "inflict_status", "target": "自身", "label": "受伤", "tier": 2},
                ]
            },
        )
        consequence_note = AgentNote(
            reasoning="后果",
            structured={
                "consequences": [
                    {
                        "threat_manifested": "保镖介入",
                        "effects": [
                            {"operation": "nudge_status", "target": "挑战", "status_to_nudge": "被激怒"}
                        ]
                    }
                ]
            },
        )
        errors = EffectApplicator.apply_results(
            effect_note, consequence_note, self.character, self.challenge
        )
        self.assertEqual(errors, [])
        self.assertIn("受伤", self.character.statuses)
        self.assertEqual(self.character.statuses["受伤"].current_tier, 2)
        self.assertIn("被激怒", self.challenge.statuses)
        self.assertEqual(self.challenge.statuses["被激怒"].current_tier, 1)

    def test_no_character(self):
        errors = EffectApplicator.apply_results(None, None, None, self.challenge)
        self.assertEqual(errors, [])

    def test_none_notes(self):
        errors = EffectApplicator.apply_results(None, None, self.character, self.challenge)
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
