import unittest
from unittest.mock import MagicMock, patch

from src.game_loop import GameLoop
from tests.helpers import MockLLMClient, make_agent_note, make_test_game_state


class TestGameLoopCoverage(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLMClient()
        self.loop = GameLoop(self.llm, debug_mode=True)
        self.state = make_test_game_state()
        self.loop.state = self.state

    def test_open_scene_not_first(self):
        self.loop._first_scene = False
        self.loop.rhythm_agent = MagicMock()
        self.loop.rhythm_agent.execute.return_value = make_agent_note(
            structured={"scene_establishment": "new scene"}
        )
        self.loop._open_scene()
        self.assertIn("new scene", self.state.scene.narrative_history)

    def test_process_move_special_trigger(self):
        self.loop.pipeline.run_single_move_pipeline = MagicMock()
        self.loop.pipeline.run_single_move_pipeline.return_value = MagicMock(
            narrator_note=make_agent_note(
                structured={"narrative": "abc", "suggest_scene_end": False}
            ),
            outcome_note=None,
        )
        with patch.object(self.loop, "_check_special_modes_trigger", return_value="CRISIS!"):
            narrative, _ = self.loop._process_move(
                MagicMock(), self.state.make_context(), quick=False
            )
            self.assertIn("CRISIS!", narrative)

    def test_process_split_moves_incapacitated(self):
        self.loop.pipeline.process_split_actions = MagicMock()
        self.loop.pipeline.process_split_actions.return_value = [
            MagicMock(
                outcome_note=None,
                narrator_note=None,
                tag_note=make_agent_note(structured={}),
                roll=MagicMock(dice=(1, 1), power=1, total=2, outcome="failure"),
            ),
            MagicMock(
                outcome_note=None,
                narrator_note=None,
                tag_note=make_agent_note(structured={}),
                roll=MagicMock(),
            ),
        ]
        self.state.character.is_incapacitated = MagicMock(return_value=True)
        self.loop._process_split_moves(MagicMock(), [{"fragment": "a"}, {"fragment": "b"}])
        self.state.character.is_incapacitated.assert_called()

    def test_process_split_moves_special_trigger(self):
        self.loop.pipeline.process_split_actions = MagicMock()
        self.loop.pipeline.process_split_actions.return_value = [
            MagicMock(
                outcome_note=None,
                narrator_note=make_agent_note(structured={"narrative": "abc"}),
                tag_note=make_agent_note(structured={}),
                roll=MagicMock(dice=(1, 1), power=1, total=2, outcome="failure"),
            )
        ]
        with patch.object(self.loop, "_check_special_modes_trigger", return_value="EVOLVE!"):
            narrative, _ = self.loop._process_split_moves(MagicMock(), [{"fragment": "a"}])
            self.assertIn("EVOLVE!", narrative)

    def test_check_special_modes_trigger_not_normal(self):
        self.loop.game_mode = "crisis"
        self.assertEqual(self.loop._check_special_modes_trigger(), "")

    @patch("builtins.input", side_effect=EOFError)
    def test_run_scene_loop_eof(self, mock_input):
        should_quit = self.loop._run_scene_loop()
        self.assertTrue(should_quit)

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    def test_run_scene_loop_kbint(self, mock_input):
        should_quit = self.loop._run_scene_loop()
        self.assertTrue(should_quit)

    @patch("builtins.input", side_effect=["", "a", "/quit"])
    def test_run_scene_loop_empty_then_quit(self, mock_input):
        self.loop.process_action = MagicMock(side_effect=[("", False), ("QUIT", False)])
        should_quit = self.loop._run_scene_loop()
        self.assertTrue(should_quit)

    def test_apply_evolution_empty_weakness_remove(self):
        self.loop.state.character.get_theme = MagicMock()
        theme = MagicMock()
        theme.weakness_tags = [MagicMock(name="w1")]
        theme.name = "w1"
        theme.attention_track = 3
        self.loop.state.character.get_theme.return_value = theme
        self.loop.active_theme_name = "test"

        self.loop._apply_evolution({"remove_weakness_tag": "w1"})
        self.loop.state.character.get_theme.assert_called_with("test")

    def test_apply_crisis_not_found(self):
        self.loop.state.character.replace_theme = MagicMock(return_value=False)
        self.loop.active_theme_name = "test"
        self.loop._apply_crisis({"name": "new", "power_tags": [], "weakness_tags": []})
        self.loop.state.character.replace_theme.assert_called_once()

    @patch("builtins.input", side_effect=["/quit"])
    def test_run_interactive_loop(self, mock_input):
        self.loop.setup = MagicMock()
        from src.state.character_state import CharacterState

        char = CharacterState(name="Test")
        self.loop.run(char, self.state.scene)
        self.loop.setup.assert_called_once()

    def test_apply_evolution_no_character(self):
        self.loop.state.character = None
        with patch("src.game_loop.log_system") as mock_log:
            self.loop._apply_evolution({"add_power_tag": {"name": "test"}})
            mock_log.assert_not_called()

    def test_apply_evolution_theme_not_found(self):
        self.loop.state.character.get_theme = MagicMock(return_value=None)
        with patch("src.game_loop.log_system") as mock_log:
            self.loop._apply_evolution({"add_power_tag": {"name": "test"}})
            mock_log.assert_not_called()

    def test_apply_crisis_no_character(self):
        self.loop.state.character = None
        with patch("src.game_loop.log_system") as mock_log:
            self.loop._apply_crisis({"name": "new", "power_tags": [], "weakness_tags": []})
            mock_log.assert_not_called()

    def test_run_special_mode_step_invalid_mode(self):
        self.loop.game_mode = "invalid"
        res = self.loop._run_special_mode_step("test")
        self.assertEqual(res, "")


if __name__ == "__main__":
    unittest.main()
