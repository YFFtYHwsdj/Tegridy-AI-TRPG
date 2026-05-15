import unittest

from src.game_loop import GameLoop
from src.models import NPC
from tests.helpers import (
    MockLLMClient,
    make_test_character,
    make_test_scene,
)


class TestGameLoopStep(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLMClient()
        self.loop = GameLoop(self.llm)

        # 挂载基础状态
        character = make_test_character()
        scene = make_test_scene()
        self.loop.state.setup(character, scene)

        # 添加挑战目标到 global_state
        challenge = NPC(npc_id="thug1", name="Thug")
        self.loop.state.global_state.npcs[challenge.npc_id] = challenge
        scene.active_npc_ids.append(challenge.npc_id)

    def test_step_empty_input(self):
        """step('') 返回 is_empty=True。"""
        result = self.loop.step("   ")
        self.assertTrue(result.is_empty)
        self.assertEqual(result.narrative, "")

    def test_step_quit_command(self):
        """step('/quit') 返回 is_quit=True。"""
        result = self.loop.step("/quit")
        self.assertTrue(result.is_quit)

    def test_step_command_returns_empty(self):
        """step('/help') 返回 is_empty=True（命令已处理，无叙事）。"""
        result = self.loop.step("/help")
        self.assertTrue(result.is_empty)

    def test_step_move_with_narrative(self):
        """Move 行动产出叙事，场景不结束。"""
        self.llm.responses = [
            (
                '{"reasoning": "玩家意图是攻击", "intent_type": "move", "sub_action_count": 1, "split_actions": [{"action": "我拔枪射击"}]}',
                {},
            ),
            (
                '{"reasoning": "匹配到弱点标签", "power_tags": [], "weakness_tags": ["信用破产"], "npc_weakness_tags": []}',
                {},
            ),
            (
                '{"reasoning": "受到反击", "threat_manifested": "Thug 的反击", "effects": [{"effect_type": "physical", "tier": 1, "target": "Kael", "label": "擦伤", "reasoning": "被子弹擦伤"}], "narrative_description": "你开枪了，但他反击了。"}',
                {},
            ),
            (
                '{"reasoning": "生成叙事", "narrative": "你拔枪射击，但被擦伤了。"}',
                {},
            ),
            (
                '{"reasoning": "场景继续", "should_transition": false, "reason": "战斗仍在继续"}',
                {},
            ),
        ]
        result = self.loop.step("我拔枪射击")

        self.assertFalse(result.is_empty)
        self.assertFalse(result.is_quit)
        self.assertFalse(result.scene_changed)
        self.assertEqual(result.narrative, "你拔枪射击，但被擦伤了。")
        self.assertIn("你拔枪射击，但被擦伤了。", self.loop.state.scene.narrative_history)

    def test_step_non_move_no_scene_change(self):
        """非 Move 行动，场景导演判定不结束，返回叙事文本。"""
        self.llm.responses = [
            (
                '{"reasoning": "玩家只是观察", "intent_type": "narrative", "sub_action_count": 1, "split_actions": [{"action": "我看看四周"}]}',
                {},
            ),
            (
                '{"reasoning": "生成叙事", "narrative": "你环顾四周，这是一家破旧的酒吧。"}',
                {},
            ),
            (
                '{"reasoning": "无变化", "should_transition": false, "reason": "只是看看"}',
                {},
            ),
        ]
        result = self.loop.step("我看看四周")
        self.assertFalse(result.scene_changed)
        self.assertEqual(result.narrative, "你环顾四周，这是一家破旧的酒吧。")

    def test_step_scene_change_triggered(self):
        """场景导演判定结束时，step() 返回 scene_changed=True。"""
        self.llm.responses = [
            (
                '{"reasoning": "玩家离开", "intent_type": "narrative", "sub_action_count": 1, "split_actions": [{"action": "我离开这里"}]}',
                {},
            ),
            (
                '{"reasoning": "生成叙事", "narrative": "你推门而出。", "suggest_scene_end": true}',
                {},
            ),
            (
                '{"reasoning": "离开场景", "scene_should_end": true, "reason": "玩家明确离开", "transition_hint": "去医院"}',
                {},
            ),
            (
                '{"reasoning": "压缩场景", "scene_summary": "玩家离开酒吧去医院"}',
                {},
            ),
            (
                '{"reasoning": "更新关系", "notes": [], "proposed_relationships": []}',
                {},
            ),
            (
                '{"reasoning": "裂痕评估", "cracked_themes": []}',
                {},
            ),
            (
                '{"reasoning": "路由", "target_place": {"id": "hospital", "is_new": true, "generation_prompt": "医院"}, "target_npcs": [], "target_items": [], "situation_prompt": "来到医院"}',
                {},
            ),
            (
                '{"reasoning": "地点生成", "description": "一家破旧的医院", "notes": "", "connections": {}}',
                {},
            ),
            (
                '{"reasoning": "新场景叙事", "narrative": "你来到了破旧的医院。"}',
                {},
            ),
        ]
        result = self.loop.step("我离开这里去医院")

        self.assertTrue(result.scene_changed)
        self.assertEqual(result.narrative, "你推门而出。")
        self.assertEqual(self.loop.state.scene.place_id, "hospital")


if __name__ == "__main__":
    unittest.main()
