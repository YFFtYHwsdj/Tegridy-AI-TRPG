"""场景创作者 Agent 测试 + build_scene_from_creator 测试。"""

from __future__ import annotations

import json
import unittest

from src.agents.scene_creator import SceneCreatorAgent, build_scene_from_creator
from src.models import Character, PowerTag, WeaknessTag
from tests.helpers import MockLLMClient


def _make_creator_response():
    """构造一个典型的 SceneCreator 完整输出。"""
    structured = json.dumps(
        {
            "scene_description": "深夜的赤色数据帮派据点——一座废弃的冷链仓库。",
            "challenge": {
                "name": "赤色数据追兵",
                "description": "赤色数据的打手队追踪芯片信号找到了Kael。",
                "limits": [
                    {"name": "伤害或制服", "max_tier": 4},
                    {"name": "逃脱或消失", "max_tier": 3},
                ],
                "base_tags": [
                    {"name": "街头追踪者", "description": "擅长在底层追踪目标"},
                    {"name": "人数优势", "description": "四人打手队，配合默契"},
                ],
                "notes": "威胁参考：打手会先尝试包围再动手。",
            },
            "npcs": [
                {
                    "npc_id": "leader",
                    "name": "打手头目",
                    "description": "赤色数据的追捕队长，脸上有刀疤。",
                    "tags": [{"name": "冷酷无情", "description": "不达目的不罢休"}],
                }
            ],
            "items_visible": [
                {
                    "item_id": "crate",
                    "name": "可疑的货箱",
                    "description": "角落里堆叠的金属货箱",
                    "location": "仓库角落",
                }
            ],
            "clues_hidden": [
                {
                    "clue_id": "tracker",
                    "name": "信号追踪器",
                    "description": "他们通过芯片内置的追踪信号找到了Kael。",
                }
            ],
        },
        ensure_ascii=False,
    )
    return f"=====REASONING=====\n创作意图\n=====STRUCTURED=====\n{structured}"


class TestSceneCreatorAgentExecute(unittest.TestCase):
    """测试 SceneCreatorAgent.execute。"""

    def setUp(self):
        self.character = Character(
            name="Kael",
            description="佣兵",
            power_tags=[PowerTag(name="快速拔枪")],
            weakness_tags=[WeaknessTag(name="信用破产")],
        )

    def test_includes_global_block(self):
        """user_message 应包含全局历史块。"""
        mock_llm = MockLLMClient(responses=[(_make_creator_response(), {})])
        agent = SceneCreatorAgent(mock_llm)

        agent.execute("=== 故事至今 ===\n酒吧场景", self.character, "切到仓库")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("酒吧场景", user_msg)

    def test_includes_character_info(self):
        """user_message 应包含角色标签和状态。"""
        mock_llm = MockLLMClient(responses=[(_make_creator_response(), {})])
        agent = SceneCreatorAgent(mock_llm)

        agent.execute("", self.character, "")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("Kael", user_msg)
        self.assertIn("快速拔枪", user_msg)
        self.assertIn("信用破产", user_msg)

    def test_includes_transition_hint(self):
        """user_message 应包含过渡提示。"""
        mock_llm = MockLLMClient(responses=[(_make_creator_response(), {})])
        agent = SceneCreatorAgent(mock_llm)

        agent.execute("", self.character, "场景切到后巷")

        user_msg = mock_llm.call_history[0]["user_message"]
        self.assertIn("场景切到后巷", user_msg)

    def test_returns_agent_note_with_challenge(self):
        """返回的 structured 应包含 challenge。"""
        mock_llm = MockLLMClient(responses=[(_make_creator_response(), {})])
        agent = SceneCreatorAgent(mock_llm)

        result = agent.execute("", self.character, "")

        self.assertIn("challenge", result.structured)
        self.assertEqual(result.structured["challenge"]["name"], "赤色数据追兵")

    def test_handles_none_character(self):
        """角色为 None 时不应崩溃。"""
        mock_llm = MockLLMClient(responses=[(_make_creator_response(), {})])
        agent = SceneCreatorAgent(mock_llm)

        result = agent.execute("", None, "")

        self.assertIsNotNone(result)


class TestBuildSceneFromCreator(unittest.TestCase):
    """测试 build_scene_from_creator() 防御性转换。"""

    def test_full_output(self):
        """完整 JSON 应正确转换为 SceneState。"""
        data = {
            "scene_description": "冷链仓库",
            "challenge": {
                "name": "追兵",
                "description": "追兵到了",
                "limits": [{"name": "战斗", "max_tier": 4}],
                "base_tags": [{"name": "追踪", "description": "擅长追踪"}],
                "notes": "威胁",
            },
            "npcs": [
                {
                    "npc_id": "boss",
                    "name": "头目",
                    "description": "老大",
                    "tags": [{"name": "冷酷", "description": ""}],
                }
            ],
        }

        scene = build_scene_from_creator(data)

        self.assertEqual(scene.scene_description, "冷链仓库")
        self.assertIn("追兵", scene.active_challenges)
        self.assertEqual(scene.active_challenges["追兵"].name, "追兵")
        self.assertEqual(len(scene.active_challenges["追兵"].limits), 1)
        self.assertEqual(len(scene.active_challenges["追兵"].base_tags), 1)
        self.assertIn("boss", scene.npcs)
        self.assertEqual(scene.npcs["boss"].name, "头目")

    def test_empty_dict(self):
        """空字典应返回空 SceneState 而不崩溃。"""
        scene = build_scene_from_creator({})
        self.assertEqual(scene.scene_description, "")
        self.assertEqual(scene.active_challenges, {})
        self.assertEqual(scene.npcs, {})

    def test_missing_challenge(self):
        """缺少 challenge 字段时应安全跳过。"""
        scene = build_scene_from_creator({"scene_description": "测试场景", "npcs": []})
        self.assertEqual(scene.scene_description, "测试场景")
        self.assertEqual(scene.active_challenges, {})

    def test_limit_tier_clamped(self):
        """max_tier 应被钳制在 1-6 范围内。"""
        data = {
            "challenge": {
                "name": "测试",
                "description": "",
                "limits": [
                    {"name": "极限A", "max_tier": 0},
                    {"name": "极限B", "max_tier": 10},
                    {"name": "极限C", "max_tier": "invalid"},
                ],
            }
        }

        scene = build_scene_from_creator(data)
        challenge = scene.primary_challenge()
        assert challenge is not None
        self.assertEqual(challenge.limits[0].max_tier, 1)
        self.assertEqual(challenge.limits[1].max_tier, 6)
        self.assertEqual(challenge.limits[2].max_tier, 3)

    def test_npc_without_id_skipped(self):
        """没有 npc_id 的 NPC 应被跳过。"""
        data = {
            "npcs": [
                {"name": "无名氏", "description": "没有ID"},
            ]
        }
        scene = build_scene_from_creator(data)
        self.assertEqual(scene.npcs, {})

    def test_npc_with_items(self):
        """NPC 的随身物品应正确构造。"""
        data = {
            "npcs": [
                {
                    "npc_id": "guard",
                    "name": "守卫",
                    "description": "打手",
                    "items_visible": [
                        {
                            "item_id": "gun",
                            "name": "手枪",
                            "description": "一把旧手枪",
                            "location": "腰间的枪套",
                        }
                    ],
                    "items_hidden": [
                        {
                            "item_id": "keycard",
                            "name": "门禁卡",
                            "description": "通往后台的门禁卡",
                            "location": "内袋",
                        }
                    ],
                    "known_clue_ids": ["tracker"],
                    "known_item_ids": ["gun"],
                }
            ]
        }
        scene = build_scene_from_creator(data)
        npc = scene.npcs["guard"]
        self.assertIn("gun", npc.items_visible)
        self.assertEqual(npc.items_visible["gun"].name, "手枪")
        self.assertIn("keycard", npc.items_hidden)
        self.assertEqual(npc.known_clue_ids, ["tracker"])

    def test_scene_items(self):
        """场景物品应正确添加到 SceneState。"""
        data = {
            "items_visible": [
                {
                    "item_id": "terminal",
                    "name": "终端机",
                    "description": "一台还在运转的终端",
                    "location": "桌上",
                }
            ],
            "items_hidden": [
                {
                    "item_id": "safe",
                    "name": "隐藏保险柜",
                    "description": "藏在画后面的保险柜",
                    "location": "办公室",
                }
            ],
        }
        scene = build_scene_from_creator(data)
        self.assertIn("terminal", scene.scene_items_visible)
        self.assertEqual(scene.scene_items_visible["terminal"].name, "终端机")
        self.assertIn("safe", scene.scene_items_hidden)

    def test_clues_hidden(self):
        """隐藏线索应正确添加。"""
        data = {
            "clues_hidden": [
                {
                    "clue_id": "note",
                    "name": "纸条",
                    "description": "一张写着密码的纸条",
                }
            ]
        }
        scene = build_scene_from_creator(data)
        self.assertIn("note", scene.clues_hidden)
        self.assertEqual(scene.clues_hidden["note"].name, "纸条")

    def test_malformed_lists_handled(self):
        """字段类型不正确时不应崩溃。"""
        data = {
            "scene_description": "测试",
            "challenge": "不是字典",
            "npcs": "不是列表",
            "items_visible": "不是列表",
            "clues_hidden": None,
        }
        scene = build_scene_from_creator(data)
        self.assertEqual(scene.scene_description, "测试")
        self.assertEqual(scene.active_challenges, {})
        self.assertEqual(scene.npcs, {})


if __name__ == "__main__":
    unittest.main()
