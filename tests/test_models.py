import unittest

from src.models import (
    NPC,
    AgentNote,
    Clue,
    ConsequenceEntry,
    EffectEntry,
    GameItem,
    PowerTag,
    Status,
    StoryTag,
    WeaknessTag,
)
from src.state.character_state import CharacterState


class TestPowerTag(unittest.TestCase):
    def test_create(self):
        t = PowerTag(name="快速拔枪", description="枪法快")
        self.assertEqual(t.name, "快速拔枪")
        self.assertEqual(t.description, "枪法快")

    def test_default_description(self):
        t = PowerTag(name="快速拔枪")
        self.assertEqual(t.description, "")


class TestWeaknessTag(unittest.TestCase):
    def test_create(self):
        t = WeaknessTag(name="信用破产")
        self.assertEqual(t.name, "信用破产")
        self.assertEqual(t.description, "")

    def test_with_description(self):
        t = WeaknessTag(name="信用破产", description="名声不好")
        self.assertEqual(t.description, "名声不好")


class TestStatus(unittest.TestCase):
    def test_defaults(self):
        s = Status(name="受伤")
        self.assertEqual(s.name, "受伤")
        self.assertEqual(s.current_tier, 0)
        self.assertEqual(s.ticked_boxes, set())


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


class TestCharacter(unittest.TestCase):
    def test_defaults(self):
        c = CharacterState(name="Test")
        self.assertEqual(c.name, "Test")
        self.assertEqual(c.power_tags, [])
        self.assertEqual(c.weakness_tags, [])
        self.assertEqual(c.statuses, {})
        self.assertEqual(c.description, "")

    def test_with_tags(self):
        from src.models import Theme

        c = CharacterState(
            name="Kael",
            description="佣兵",
            themes=[
                Theme(
                    name="测试",
                    theme_type="测试",
                    concept="测试",
                    motivation="测试",
                    power_tags=[PowerTag(name="前公司安保")],
                    weakness_tags=[WeaknessTag(name="信用破产")],
                )
            ],
        )
        self.assertEqual(len(c.power_tags), 1)
        self.assertEqual(len(c.weakness_tags), 1)

    def test_is_incapacitated_tier_six(self):
        c = CharacterState(name="Test")
        c.statuses["受伤"] = Status(name="受伤", current_tier=6, ticked_boxes={6})
        self.assertTrue(c.is_incapacitated())

    def test_is_incapacitated_explicit_status(self):
        c = CharacterState(name="Test")
        c.statuses["昏迷"] = Status(name="昏迷", current_tier=2, ticked_boxes={1, 2})
        self.assertTrue(c.is_incapacitated())

    def test_not_incapacitated_low_tier(self):
        c = CharacterState(name="Test")
        c.statuses["受伤"] = Status(name="受伤", current_tier=3, ticked_boxes={1, 2, 3})
        self.assertFalse(c.is_incapacitated())

    def test_not_incapacitated_no_statuses(self):
        c = CharacterState(name="Test")
        self.assertFalse(c.is_incapacitated())

    def test_items_visible_default_empty(self):
        c = CharacterState(name="Test")
        self.assertEqual(c.items_visible, {})

    def test_items_hidden_default_empty(self):
        c = CharacterState(name="Test")
        self.assertEqual(c.items_hidden, {})


class TestGameItem(unittest.TestCase):
    def test_defaults(self):
        item = GameItem()
        self.assertEqual(item.item_id, "")
        self.assertEqual(item.name, "")
        self.assertEqual(item.description, "")
        self.assertEqual(item.location, "")
        self.assertEqual(item.tags, [])
        self.assertEqual(item.weakness_tags, [])

    def test_item_id_defaults_to_name(self):
        item = GameItem(name="急救包")
        self.assertEqual(item.item_id, "急救包")

    def test_custom_item_id(self):
        item = GameItem(item_id="medkit_01", name="急救包")
        self.assertEqual(item.item_id, "medkit_01")
        self.assertEqual(item.name, "急救包")

    def test_with_location(self):
        item = GameItem(name="芯片", location="夹克内袋")
        self.assertEqual(item.location, "夹克内袋")

    def test_with_tags(self):
        t = PowerTag("小型", "易于隐藏")
        item = GameItem(name="匕首", tags=[t])
        self.assertEqual(len(item.tags), 1)
        self.assertEqual(item.tags[0].name, "小型")

    def test_with_weakness(self):
        w = WeaknessTag("易碎", "承受不住重击")
        item = GameItem(name="瓷瓶", weakness_tags=[w])
        self.assertEqual(len(item.weakness_tags), 1)
        self.assertEqual(item.weakness_tags[0].name, "易碎")

    def test_multiple_instances_same_name(self):
        a = GameItem(item_id="aidkit_01", name="急救包", location="吧台")
        b = GameItem(item_id="aidkit_02", name="急救包", location="储藏室")
        self.assertEqual(a.name, b.name)
        self.assertNotEqual(a.item_id, b.item_id)


class TestClue(unittest.TestCase):
    def test_defaults(self):
        clue = Clue()
        self.assertEqual(clue.clue_id, "")
        self.assertEqual(clue.name, "")
        self.assertEqual(clue.description, "")

    def test_clue_id_defaults_to_name(self):
        clue = Clue(name="加密数据芯片")
        self.assertEqual(clue.clue_id, "加密数据芯片")

    def test_custom_clue_id(self):
        clue = Clue(clue_id="clue_001", name="加密数据芯片")
        self.assertEqual(clue.clue_id, "clue_001")

    def test_with_description(self):
        clue = Clue(name="通讯记录", description="腕部终端的短讯记录")
        self.assertEqual(clue.description, "腕部终端的短讯记录")


class TestNPC(unittest.TestCase):
    def test_defaults(self):
        npc = NPC()
        self.assertEqual(npc.npc_id, "")
        self.assertEqual(npc.name, "")
        self.assertEqual(npc.description, "")
        self.assertEqual(npc.tags, [])
        self.assertEqual(npc.statuses, {})
        self.assertEqual(npc.known_clue_ids, [])
        self.assertEqual(npc.known_item_ids, [])
        self.assertEqual(npc.items_visible, {})
        self.assertEqual(npc.items_hidden, {})

    def test_npc_id_defaults_to_name(self):
        npc = NPC(name="Miko")
        self.assertEqual(npc.npc_id, "Miko")

    def test_custom_npc_id(self):
        npc = NPC(npc_id="miko_npc", name="Miko")
        self.assertEqual(npc.npc_id, "miko_npc")

    def test_with_tags(self):
        t = PowerTag("精明的谈判者")
        npc = NPC(name="Miko", tags=[t])
        self.assertEqual(len(npc.tags), 1)
        self.assertEqual(npc.tags[0].name, "精明的谈判者")

    def test_with_statuses(self):
        s = Status(name="被威胁", current_tier=2, ticked_boxes={1, 2})
        npc = NPC(name="Miko", statuses={"被威胁": s})
        self.assertIn("被威胁", npc.statuses)
        self.assertEqual(npc.statuses["被威胁"].current_tier, 2)

    def test_with_known_references(self):
        npc = NPC(
            name="Miko",
            known_clue_ids=["clue_001", "clue_002"],
            known_item_ids=["chip_encrypted"],
        )
        self.assertEqual(len(npc.known_clue_ids), 2)
        self.assertEqual(len(npc.known_item_ids), 1)
        self.assertIn("chip_encrypted", npc.known_item_ids)

    def test_items_visible_and_hidden(self):
        item = GameItem(item_id="chip", name="加密芯片", location="夹克内袋")
        npc = NPC(
            name="Miko",
            items_hidden={"chip": item},
        )
        self.assertIn("chip", npc.items_hidden)
        self.assertEqual(npc.items_visible, {})
        self.assertEqual(npc.items_hidden["chip"].item_id, "chip")


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
