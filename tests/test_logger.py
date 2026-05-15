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


if __name__ == "__main__":
    unittest.main()
