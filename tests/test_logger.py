"""测试系统日志组件。"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from src.logger import (
    log_call,
    log_roll,
    log_status_update,
    log_system,
)
from src.models import Status


class TestLogger(unittest.TestCase):
    @patch("src.logger.get_game_logger")
    def test_log_system(self, mock_get_game):
        mock_game = MagicMock()
        mock_get_game.return_value = mock_game

        log_system("测试警告", level="warning")

        mock_game.warning.assert_called_once_with("[系统] %s", "测试警告")

    @patch("src.logger.get_llm_logger")
    @patch("src.logger.get_game_logger")
    def test_log_call_with_usage(self, mock_get_game, mock_get_llm):
        mock_game = MagicMock()
        mock_llm = MagicMock()
        mock_get_game.return_value = mock_game
        mock_get_llm.return_value = mock_llm

        usage = {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
            "cached_tokens": 2,
        }
        log_call("TestAgent", "sys_prompt", "user_msg", "response", usage)

        # 检查 INFO 摘要
        expected_summary = "LLM调用 · TestAgent | 提示10(缓存2+未缓存8) | 生成5 | 合计15"
        mock_game.info.assert_called_with(expected_summary)
        mock_llm.info.assert_called_with(expected_summary)

        # 检查 DEBUG 完整输出
        self.assertTrue(mock_llm.debug.called)

    @patch("src.logger.get_game_logger")
    def test_log_roll(self, mock_get_game):
        mock_game = MagicMock()
        mock_get_game.return_value = mock_game

        log_roll(1, (2, 3), 6, "partial_success", ["力量大"], ["没眼光"])

        mock_game.info.assert_any_call(
            "掷骰 | 力量标签:%s | 弱点标签:%s | 力量:%d | 掷骰:%d+%d=%d → %s",
            ["力量大"],
            ["没眼光"],
            1,
            2,
            3,
            6,
            "partial_success",
        )

    @patch("src.logger.get_game_logger")
    def test_log_status_update(self, mock_get_game):
        mock_game = MagicMock()
        mock_get_game.return_value = mock_game

        st = Status(name="中毒", current_tier=2, ticked_boxes={1, 2})
        log_status_update("Kael", {"中毒": st})

        mock_game.info.assert_any_call("[状态] %s:", "Kael")
        mock_game.info.assert_any_call("  %s: 等级%d (格子: %s)", "中毒", 2, [1, 2])

    @patch("src.logger.get_game_logger")
    def test_log_status_update_empty(self, mock_get_game):
        mock_game = MagicMock()
        mock_get_game.return_value = mock_game

        log_status_update("Kael", {})

        mock_game.info.assert_called_once_with("[状态] %s → (无状态)", "Kael")

    def test_create_file_handler_success(self):
        import logging
        import os
        import shutil
        import tempfile

        from src.logger import _create_file_handler

        temp_dir = tempfile.mkdtemp()
        filepath = os.path.join(temp_dir, "test.log")
        handler = _create_file_handler(filepath, logging.INFO)
        self.assertIsNotNone(handler)
        handler.close()
        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("logging.FileHandler", side_effect=OSError("Permission denied"))
    def test_create_file_handler_oserror(self, mock_handler):
        import logging
        import os

        from src.logger import _create_file_handler

        filepath = os.path.join("dummy_dir", "test.log")
        handler = _create_file_handler(filepath, logging.INFO)
        self.assertIsNone(handler)

    def test_init_logging(self):
        import logging
        import os
        import shutil
        import tempfile

        from src.logger import GAME_LOGGER_NAME, LLM_LOGGER_NAME, init_logging

        temp_dir = tempfile.mkdtemp()
        session_file, llm_file = init_logging(temp_dir, debug_mode=True)
        self.assertTrue(os.path.exists(session_file))
        self.assertTrue(os.path.exists(llm_file))

        game_logger = logging.getLogger(GAME_LOGGER_NAME)
        self.assertTrue(len(game_logger.handlers) > 0)

        llm_logger = logging.getLogger(LLM_LOGGER_NAME)
        self.assertTrue(len(llm_logger.handlers) > 0)

        # Cleanup loggers so it doesn't affect other tests
        for handler in game_logger.handlers:
            handler.close()
        for handler in llm_logger.handlers:
            handler.close()

        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_set_debug_mode(self):
        import logging
        import shutil
        import tempfile

        from src.logger import init_logging, set_debug_mode

        temp_dir = tempfile.mkdtemp()
        init_logging(temp_dir, debug_mode=False)
        set_debug_mode(True)

        from src.logger import _console_handler

        self.assertEqual(_console_handler.level, logging.DEBUG)

        set_debug_mode(False)
        self.assertEqual(_console_handler.level, logging.INFO)

        shutil.rmtree(temp_dir, ignore_errors=True)

    @patch("src.logger.get_llm_logger")
    @patch("src.logger.get_game_logger")
    def test_log_call_without_cached_tokens(self, mock_get_game, mock_get_llm):
        mock_game = MagicMock()
        mock_llm = MagicMock()
        mock_get_game.return_value = mock_game
        mock_get_llm.return_value = mock_llm

        usage = {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
        log_call("TestAgent", "system", "user", "response", usage)

        expected_summary = "LLM调用 · TestAgent | 提示100(无缓存) | 生成50 | 合计150"
        mock_game.info.assert_called_with(expected_summary)
        mock_llm.info.assert_called_with(expected_summary)


if __name__ == "__main__":
    unittest.main()

    @patch("src.logger.get_llm_logger")
    @patch("src.logger.get_game_logger")
    def test_log_call_no_usage(self, mock_get_game, mock_get_llm):
        mock_game = MagicMock()
        mock_llm = MagicMock()
        mock_get_game.return_value = mock_game
        mock_get_llm.return_value = mock_llm

        log_call("TestAgent", "system", "user", "response", None)

        expected_summary = "LLM调用 · TestAgent | token 用量未知"
        mock_game.info.assert_called_with(expected_summary)
        mock_llm.info.assert_called_with(expected_summary)
