"""GameLoop 测试 —— 主循环的路由逻辑、命令处理、Move/非Move分流。

验证 GameLoop 的核心行为：
    - 系统命令处理（/quit, /debug, /help）
    - Move 判定和流水线路由
    - 非 Move 叙事处理
    - 极限突破处理
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.game_loop import GameLoop
from src.pipeline.pipeline_result import PipelineResult
from tests.helpers import MockLLMClient, make_test_character, make_test_scene


class TestGameLoopCommands(unittest.TestCase):
    """测试系统命令处理。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

    def test_quit_command(self):
        """/quit 返回 QUIT。"""
        result = self.loop._handle_command("/quit")
        self.assertEqual(result, "QUIT")

    def test_exit_command(self):
        """/exit 返回 QUIT。"""
        result = self.loop._handle_command("/exit")
        self.assertEqual(result, "QUIT")

    def test_debug_command_toggles_mode(self):
        """/debug 切换调试模式。"""
        initial = self.loop.debug_mode
        self.loop._handle_command("/debug")
        self.assertEqual(self.loop.debug_mode, not initial)

    def test_help_command(self):
        """/help 显示帮助信息。"""
        with patch("builtins.print"):
            result = self.loop._handle_command("/help")
        self.assertEqual(result, "")

    def test_unknown_command(self):
        """未知命令显示错误提示。"""
        with patch("builtins.print"):
            result = self.loop._handle_command("/unknown")
        self.assertEqual(result, "")


class TestGameLoopSetup(unittest.TestCase):
    """测试 setup 方法。"""

    def setUp(self):
        self.mock_llm = MockLLMClient(
            [
                (
                    '{"reasoning": "场景建立", '
                    '"scene_establishment": "霓虹灯闪烁的酒吧...", "spotlight_handoff": "你要做什么？"}',
                    {},
                ),
            ]
        )
        self.loop = GameLoop(self.mock_llm)

    def test_setup_sets_character_and_scene(self):
        """setup 正确设置角色和场景。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import NPC

        challenge = NPC(
            name="测试挑战",
            description="测试",
        )
        self.loop.state.global_state.npcs[challenge.npc_id] = challenge
        scene.active_npc_ids.append(challenge.npc_id)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertIs(self.loop.state.character, character)
        self.assertEqual(self.loop.state.scene.situation, "赛博朋克酒吧")

    def test_setup_calls_rhythm_agent(self):
        """setup 调用 RhythmAgent 生成开场叙事。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import NPC

        challenge = NPC(
            name="测试挑战",
            description="测试",
        )
        self.loop.state.global_state.npcs[challenge.npc_id] = challenge
        scene.active_npc_ids.append(challenge.npc_id)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertEqual(len(self.mock_llm.call_history), 1)

    def test_setup_appends_scene_establishment(self):
        """开场叙事被追加到场景历史。"""
        character = make_test_character()
        scene = make_test_scene()
        from src.models import NPC

        challenge = NPC(
            name="测试挑战",
            description="测试",
        )
        self.loop.state.global_state.npcs[challenge.npc_id] = challenge
        scene.active_npc_ids.append(challenge.npc_id)

        with patch("builtins.print"):
            self.loop.setup(character, scene)

        self.assertTrue(len(self.loop.state.scene.narrative_history) > 0)


class TestGameLoopProcessAction(unittest.TestCase):
    """测试 process_action 的玩家行动处理。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

        # 初始化游戏状态
        character = make_test_character()
        scene = make_test_scene()
        from src.models import NPC

        challenge = NPC(
            name="测试挑战",
            description="测试",
        )
        self.loop.state.global_state.npcs[challenge.npc_id] = challenge
        scene.active_npc_ids.append(challenge.npc_id)
        self.loop.setup(character, scene)

        # Mock 各 Agent
        self.loop.intent_agent = MagicMock()
        self.loop.inquiry_agent = MagicMock()
        self.loop.lite_narrator = MagicMock()
        self.loop.lite_narrator = MagicMock()

        # Mock Pipeline
        self.loop.pipeline = MagicMock()

    def test_empty_input_returns_empty(self):
        """空输入返回空字符串。"""
        result = self.loop.process_action("")
        self.assertEqual(result, ("", False))

    def test_command_routing(self):
        """以 / 开头的输入走命令处理。"""
        result = self.loop.process_action("/quit")
        self.assertEqual(result, ("QUIT", False))

    def test_non_move_calls_lite_narrator(self):
        """意图判定非 Move 时调用 LiteNarratorAgent。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            reasoning="低风险观察",
            structured={"intent_type": "narrative", "rationale": "纯叙事"},
        )
        self.loop.lite_narrator.execute.return_value = MagicMock(
            structured={"narrative": "你环顾四周...", "revelation_decisions": {}}
        )

        with patch("builtins.print"):
            self.loop.process_action("看看周围")

        self.loop.lite_narrator.execute.assert_called_once()

    def test_non_move_backward_compat_is_move_false(self):
        """旧版 is_move=False 向后兼容，路由到叙事模式。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            reasoning="低风险观察",
            structured={"is_move": False, "rationale": "纯叙事"},
        )
        self.loop.lite_narrator.execute.return_value = MagicMock(
            structured={"narrative": "你环顾四周...", "revelation_decisions": {}}
        )

        with patch("builtins.print"):
            self.loop.process_action("看看周围")

        self.loop.lite_narrator.execute.assert_called_once()

    def test_inquiry_calls_inquiry_agent(self):
        """意图判定为 inquiry 时调用 InquiryAgent。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            reasoning="玩家在提问",
            structured={
                "intent_type": "inquiry",
                "action_type": "inquiry",
                "action_summary": "询问NPC名字",
            },
        )
        self.loop.inquiry_agent.execute.return_value = MagicMock(
            structured={"response": "他叫Miko。", "info_source": "history"}
        )

        with patch("builtins.print"):
            result, needs_director = self.loop.process_action("那个NPC叫什么？")

        self.loop.inquiry_agent.execute.assert_called_once()
        self.assertEqual(result, "他叫Miko。")
        self.assertFalse(needs_director)

    def test_inquiry_appends_to_narrative_history(self):
        """信息询问回复追加到叙事历史。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            reasoning="玩家在提问",
            structured={
                "intent_type": "inquiry",
                "action_type": "inquiry",
                "action_summary": "询问NPC名字",
            },
        )
        self.loop.inquiry_agent.execute.return_value = MagicMock(
            structured={"response": "他叫Miko。", "info_source": "history"}
        )

        with patch("builtins.print"):
            self.loop.process_action("那个NPC叫什么？")

        self.assertIn("他叫Miko。", self.loop.state.scene.narrative_history)

    def test_inquiry_does_not_call_lite_narrator(self):
        """信息询问不调用 LiteNarratorAgent。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            reasoning="玩家在提问",
            structured={
                "intent_type": "inquiry",
                "action_type": "inquiry",
                "action_summary": "询问NPC名字",
            },
        )
        self.loop.inquiry_agent.execute.return_value = MagicMock(
            structured={"response": "他叫Miko。", "info_source": "history"}
        )

        with patch("builtins.print"):
            self.loop.process_action("那个NPC叫什么？")

        self.loop.lite_narrator.execute.assert_not_called()

    def test_move_calls_intent_agent(self):
        """Move 调用 IntentAgent 解析意图。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "is_move": True,
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
                "resolution_mode": "detailed",
            }
        )
        self.loop.pipeline.run_single_move_pipeline.return_value = PipelineResult(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            outcome_note=MagicMock(structured={"effects": []}),
            narrator_note=MagicMock(
                structured={"narrative": "你拔出了枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.loop.intent_agent.execute.assert_called_once()

    def test_quick_resolution_calls_quick_pipeline(self):
        """resolution_mode=quick 时调用 run_quick_pipeline。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "is_move": True,
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
                "resolution_mode": "quick",
            }
        )
        self.loop.pipeline.run_quick_pipeline.return_value = PipelineResult(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            outcome_note=None,
            narrator_note=MagicMock(
                structured={"narrative": "你拔出了枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.loop.pipeline.run_quick_pipeline.assert_called_once()

    def test_split_action_calls_process_split_moves(self):
        """is_split_action=True 时调用 _process_split_moves。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "is_move": True,
                "action_type": "compound",
                "action_summary": "先拔枪再射击",
                "is_split_action": True,
                "split_actions": [
                    {
                        "action_type": "combat",
                        "action_summary": "拔枪",
                        "fragment": "拔枪",
                        "_index": 0,
                    },
                    {
                        "action_type": "combat",
                        "action_summary": "射击",
                        "fragment": "射击",
                        "_index": 1,
                    },
                ],
            }
        )
        self.loop.pipeline.process_split_actions.return_value = [
            PipelineResult(
                tag_note=MagicMock(),
                roll=MagicMock(outcome="partial_success"),
                outcome_note=MagicMock(structured={"effects": []}),
                narrator_note=MagicMock(structured={"narrative": "你拔出了枪..."}),
            ),
        ]

        with patch("builtins.print"):
            self.loop.process_action("先拔枪再射击")

        self.loop.pipeline.process_split_actions.assert_called_once()

    def test_move_appends_narrative_to_state(self):
        """叙事文本被追加到场景历史。"""
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={
                "is_move": True,
                "action_type": "combat",
                "action_summary": "拔枪",
                "is_split_action": False,
                "resolution_mode": "detailed",
            }
        )
        self.loop.pipeline.run_single_move_pipeline.return_value = PipelineResult(
            tag_note=MagicMock(),
            roll=MagicMock(outcome="partial_success", power=1, dice=(3, 4), total=8),
            outcome_note=MagicMock(structured={"effects": []}),
            narrator_note=MagicMock(
                structured={"narrative": "你迅速拔枪...", "revelation_decisions": {}}
            ),
        )

        with patch("builtins.print"):
            self.loop.process_action("我要拔枪")

        self.assertIn("你迅速拔枪...", self.loop.state.scene.narrative_history)


class TestGameLoopToggleDebug(unittest.TestCase):
    """测试调试模式切换。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)

    def test_toggle_debug_returns_new_state(self):
        """toggle_debug 返回切换后的状态。"""
        initial = self.loop.debug_mode
        result = self.loop.toggle_debug()
        self.assertEqual(result, not initial)

    def test_double_toggle_restores(self):
        """两次切换恢复原始状态。"""
        initial = self.loop.debug_mode
        self.loop.toggle_debug()
        self.loop.toggle_debug()
        self.assertEqual(self.loop.debug_mode, initial)


class TestGameLoopSpecialModes(unittest.TestCase):
    """测试特殊机制（成长、危机）的状态机拦截与处理。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)
        character = make_test_character()
        scene = make_test_scene()
        self.loop.setup(character, scene)

        self.loop.evolution_agent = MagicMock()
        self.loop.crisis_agent = MagicMock()

    def test_intercept_input_in_special_mode(self):
        """当 game_mode 不为 normal 时，拦截正常输入并交由 _run_special_mode_step 处理。"""
        self.loop.game_mode = "evolution"
        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={"status": "negotiating", "response_to_player": "请继续。"}
        )

        with patch("builtins.print"):
            result, needs_director = self.loop.process_action("我要突破")

        self.loop.evolution_agent.execute.assert_called_once()
        self.assertEqual(result, "请继续。")
        self.assertFalse(needs_director)

    def test_check_special_modes_trigger_crisis(self):
        """当存在崩溃的主题时，_check_special_modes_trigger 切换到 crisis 模式。"""
        self.loop.state.character.themes[0].crack_track = 3
        self.loop.crisis_agent.execute.return_value = MagicMock(
            structured={"status": "negotiating", "response_to_player": "危机降临。"}
        )

        with patch("builtins.print"):
            next_prompt = self.loop._check_special_modes_trigger()

        self.assertEqual(self.loop.game_mode, "crisis")
        self.assertEqual(self.loop.active_theme_name, self.loop.state.character.themes[0].name)
        self.assertEqual(next_prompt, "危机降临。")

    def test_check_special_modes_trigger_evolution(self):
        """当存在可成长的主题时，_check_special_modes_trigger 切换到 evolution 模式。"""
        self.loop.state.character.themes[0].attention_track = 3
        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={"status": "negotiating", "response_to_player": "迎来了突破。"}
        )

        with patch("builtins.print"):
            next_prompt = self.loop._check_special_modes_trigger()

        self.assertEqual(self.loop.game_mode, "evolution")
        self.assertEqual(self.loop.active_theme_name, self.loop.state.character.themes[0].name)
        self.assertEqual(next_prompt, "迎来了突破。")

    def test_apply_evolution_finalized(self):
        """evolution 谈判完成时落地成长效果并切回 normal 模式。"""
        theme = self.loop.state.character.themes[0]
        theme.attention_track = 4
        self.loop.game_mode = "evolution"
        self.loop.active_theme_name = theme.name

        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={
                "status": "finalized",
                "response_to_player": "突破完成。",
                "theme_update": {
                    "reset_crack": True,
                    "add_power_tag": {"name": "新力量", "description": ""},
                    "add_weakness_tag": {"name": "新弱点", "description": ""},
                },
            }
        )

        with patch("builtins.print"):
            self.loop._run_special_mode_step("好")

        self.assertEqual(self.loop.game_mode, "normal")
        self.assertEqual(theme.attention_track, 1)  # max(0, 4-3)
        self.assertEqual(theme.crack_track, 0)
        self.assertEqual(theme.power_tags[-1].name, "新力量")
        self.assertEqual(theme.weakness_tags[-1].name, "新弱点")

    def test_apply_crisis_finalized(self):
        """crisis 谈判完成时落地危机效果并切回 normal 模式。"""
        theme = self.loop.state.character.themes[0]
        self.loop.game_mode = "crisis"
        self.loop.active_theme_name = theme.name

        self.loop.crisis_agent.execute.return_value = MagicMock(
            structured={
                "status": "finalized",
                "response_to_player": "新特质觉醒。",
                "new_theme": {
                    "name": "新生主题",
                    "theme_type": "概念",
                    "concept": "",
                    "motivation": "",
                    "power_tags": [{"name": "新生力量"}],
                    "weakness_tags": [{"name": "新生弱点"}],
                },
            }
        )

        with patch("builtins.print"):
            self.loop._run_special_mode_step("好")

        self.assertEqual(self.loop.game_mode, "normal")
        self.assertEqual(self.loop.state.character.themes[0].name, "新生主题")
        self.assertEqual(self.loop.state.character.themes[0].power_tags[0].name, "新生力量")

    def test_run_special_mode_step_recursive_trigger(self):
        """当处理完一个机制后紧接着触发另一个机制，追加提示文本。"""
        theme = self.loop.state.character.themes[0]
        self.loop.game_mode = "crisis"
        self.loop.active_theme_name = theme.name

        self.loop.crisis_agent.execute.return_value = MagicMock(
            structured={
                "status": "finalized",
                "response_to_player": "新特质觉醒。",
                "new_theme": {
                    "name": "新生主题",
                    "theme_type": "概念",
                    "concept": "",
                    "motivation": "",
                    "power_tags": [],
                    "weakness_tags": [],
                },
            }
        )

        from src.models import Theme

        self.loop.state.character.themes.append(
            Theme(name="第二个主题", theme_type="mythos", concept="", motivation="")
        )
        self.loop.state.character.themes[1].attention_track = 3

        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={"status": "negotiating", "response_to_player": "紧接着的突破。"}
        )

        with patch("builtins.print"):
            response = self.loop._run_special_mode_step("好")

        self.assertIn("紧接着的突破。", response)


class TestGameLoopRunSceneLoop(unittest.TestCase):
    """测试 _run_scene_loop 及其相关功能。"""

    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)
        character = make_test_character()
        scene = make_test_scene()
        self.loop.setup(character, scene)
        self.loop.scene_director = MagicMock()
        self.loop._transition_scene = MagicMock()
        self.loop.process_action = MagicMock()

    @patch("builtins.input")
    def test_run_scene_loop_quits_on_eof(self, mock_input):
        mock_input.side_effect = EOFError()
        with patch("builtins.print"):
            self.assertTrue(self.loop._run_scene_loop())

    @patch("builtins.input")
    def test_run_scene_loop_quits_on_quit_command(self, mock_input):
        mock_input.return_value = "/quit"
        self.loop.process_action.return_value = ("QUIT", False)
        with patch("builtins.print"):
            self.assertTrue(self.loop._run_scene_loop())

    @patch("builtins.input")
    def test_run_scene_loop_transitions(self, mock_input):
        mock_input.side_effect = ["行动1"]
        self.loop.process_action.return_value = ("叙事", True)
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={"scene_should_end": True, "reason": "场景结束", "transition_hint": "提示"}
        )
        with patch("builtins.print"):
            self.assertFalse(self.loop._run_scene_loop())

        self.loop._transition_scene.assert_called_once()
        self.assertEqual(self.loop._transition_hint, "提示")

    def test_open_scene_special_modes_trigger(self):
        """_open_scene 遇到特殊机制触发时附加提示。"""
        self.loop.state.character.themes[0].crack_track = 3
        self.loop.crisis_agent = MagicMock()
        self.loop.crisis_agent.execute.return_value = MagicMock(
            structured={"status": "negotiating", "response_to_player": "危机降临。"}
        )
        self.loop.rhythm_agent = MagicMock()
        self.loop.rhythm_agent.execute.return_value = MagicMock(
            structured={"scene_establishment": "开场", "spotlight_handoff": "你要做什么？"}
        )

        with patch("builtins.print"):
            self.loop._open_scene()

        self.assertEqual(self.loop.game_mode, "crisis")


class TestGameLoopMissingBranches(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MockLLMClient()
        self.loop = GameLoop(self.mock_llm)
        character = make_test_character()
        scene = make_test_scene()
        self.loop.setup(character, scene)

    def test_step_all_branches(self):
        self.loop.process_action = MagicMock()
        self.loop.scene_director = MagicMock()
        self.loop._transition_scene = MagicMock()

        # quit
        self.loop.process_action.return_value = ("QUIT", False)
        self.assertTrue(self.loop.step("/quit").is_quit)

        # empty
        self.loop.process_action.return_value = ("", False)
        self.assertTrue(self.loop.step("").is_empty)

        # director needs end
        self.loop.process_action.return_value = ("narr", True)
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={"scene_should_end": True, "reason": "R"}
        )
        res = self.loop.step("act")
        self.assertTrue(res.scene_changed)

        # director no end
        self.loop.scene_director.execute.return_value = MagicMock(
            structured={"scene_should_end": False}
        )
        res = self.loop.step("act")
        self.assertFalse(res.scene_changed)

        # no director
        self.loop.process_action.return_value = ("narr", False)
        self.assertEqual(self.loop.step("act").narrative, "narr")

    def test_run(self):
        self.loop.setup = MagicMock()
        self.loop._run_scene_loop = MagicMock(return_value=True)
        with patch("builtins.print"):
            self.loop.run(MagicMock(), MagicMock())
        self.loop.setup.assert_called_once()

    def test_transition_scene(self):
        self.loop.scene_transition_pipeline = MagicMock()
        self.loop._open_scene = MagicMock()
        self.loop._transition_scene()
        self.loop.scene_transition_pipeline.execute.assert_called_once()
        self.loop._open_scene.assert_called_once()

    def test_process_action_append_next_prompt(self):
        self.loop.intent_agent = MagicMock()
        self.loop.intent_agent.execute.return_value = MagicMock(
            structured={"is_move": True, "intent_type": "move", "action_type": "combat"}
        )
        self.loop.pipeline = MagicMock()
        self.loop.pipeline.run_single_move_pipeline.return_value = PipelineResult(
            tag_note=MagicMock(),
            roll=MagicMock(),
            outcome_note=MagicMock(),
            narrator_note=MagicMock(structured={"narrative": "narr"}),
        )
        self.loop._check_special_modes_trigger = MagicMock(return_value="next")
        with patch("builtins.print"):
            res, _ = self.loop.process_action("act")
        self.assertEqual(res, "narr\n\nnext")

    def test_special_mode_step_unsupported(self):
        self.loop.game_mode = "unknown"
        with patch("builtins.print"):
            self.assertEqual(self.loop._run_special_mode_step(""), "")

    def test_special_mode_evolution_theme_not_found(self):
        self.loop.game_mode = "evolution"
        self.loop.active_theme_name = "not found"
        self.loop.evolution_agent = MagicMock()
        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={"status": "finalized", "response_to_player": "r"}
        )
        with patch("builtins.print"):
            self.loop._run_special_mode_step("a")

    def test_special_mode_crisis_theme_not_found(self):
        self.loop.game_mode = "crisis"
        self.loop.active_theme_name = "not found"
        self.loop.crisis_agent = MagicMock()
        self.loop.crisis_agent.execute.return_value = MagicMock(
            structured={"status": "finalized", "response_to_player": "r"}
        )
        with patch("builtins.print"):
            self.loop._run_special_mode_step("a")

    def test_special_mode_evolution_remove_weakness(self):
        from src.models import WeaknessTag

        theme = self.loop.state.character.themes[0]
        theme.weakness_tags.append(WeaknessTag(name="W1"))
        self.loop.game_mode = "evolution"
        self.loop.active_theme_name = theme.name
        self.loop.evolution_agent = MagicMock()
        self.loop.evolution_agent.execute.return_value = MagicMock(
            structured={
                "status": "finalized",
                "response_to_player": "r",
                "theme_update": {
                    "remove_weakness_tag": "W1",
                },
            }
        )
        with patch("builtins.print"):
            self.loop._run_special_mode_step("a")
        self.assertNotIn("W1", [w.name for w in theme.weakness_tags])

    def test_run_scene_loop_empty(self):
        self.loop.process_action = MagicMock(side_effect=[("", False), ("QUIT", False)])
        with patch("builtins.input", side_effect=["", "act", "/quit"]):
            self.assertTrue(self.loop._run_scene_loop())


if __name__ == "__main__":
    unittest.main()
