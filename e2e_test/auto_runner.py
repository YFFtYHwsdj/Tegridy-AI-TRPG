"""自动化 E2E 测试运行器 —— 编排 GameLoop 与 PlayerAgent 的交互。

AutoRunner 是端到端测试的编排器：
    1. 创建 GameLoop，调用 setup() 初始化场景
    2. 循环：PlayerAgent 决策 → GameLoop.step() → 收集结果
    3. 满足终止条件时停止，输出测试摘要

终止条件（满足任一即停止）：
    - 达到最大回合数
    - 角色失去行动能力
    - 场景切换次数达上限

设计原则：
    - 不修改 src/ 内的代码，只调用 GameLoop 的公开 API（setup, step）
    - PlayerAgent 与 GameLoop 共用同一个 LLM 客户端
    - 每轮记录行动和叙事到日志
    - 结束时输出可读的测试摘要
"""

from __future__ import annotations

import time

from e2e_test.player_agent import PlayerAgent
from src.game_loop import GameLoop
from src.llm_client import LLMClient
from src.logger import get_logger
from src.models import Character
from src.state.scene_state import SceneState


class AutoRunner:
    """自动化 E2E 测试运行器。

    编排 GameLoop 与 PlayerAgent 之间的交互循环。

    Attributes:
        llm: LLM 客户端实例
        max_rounds: 最大回合数（玩家输入次数）
        max_scenes: 最大场景切换次数
        player_history_window: PlayerAgent 叙事历史窗口大小
    """

    def __init__(
        self,
        llm: LLMClient,
        max_rounds: int = 150,
        max_scenes: int = 10,
        player_history_window: int = 50,
        debug_mode: bool = True,
    ):
        """初始化自动化运行器。

        Args:
            llm: LLM 客户端
            max_rounds: 最大回合数上限
            max_scenes: 最大场景切换次数上限
            player_history_window: AI 玩家叙事历史窗口大小
            debug_mode: 是否启用调试模式
        """
        self.llm = llm
        self.max_rounds = max_rounds
        self.max_scenes = max_scenes
        self.player_history_window = player_history_window
        self.debug_mode = debug_mode

    def run(self, character: Character, first_scene: SceneState) -> dict:
        """运行自动化测试。

        完整流程：
            1. 初始化 GameLoop 和 PlayerAgent
            2. setup() 产出开场叙事
            3. 循环 step()，每轮由 PlayerAgent 决策行动
            4. 达到终止条件后输出摘要

        Args:
            character: 玩家角色
            first_scene: 初始场景

        Returns:
            测试结果摘要字典，包含：
                - total_rounds: 实际执行的回合数
                - scene_changes: 场景切换次数
                - stop_reason: 停止原因
                - character_statuses: 角色最终状态
                - challenge_name: 最终挑战名
                - challenge_statuses: 挑战最终状态
                - actions: 所有玩家行动列表
                - elapsed_seconds: 总耗时（秒）
        """
        log = get_logger()

        # ── 初始化 ──
        game = GameLoop(self.llm, debug_mode=self.debug_mode)
        player = PlayerAgent(self.llm, character, max_history=self.player_history_window)
        game.setup(character, first_scene)

        # 收集开场叙事作为 PlayerAgent 的初始上下文
        opening_narrative = "\n".join(game.state.scene.narrative_history)

        log.info("")
        log.info("═" * 50)
        log.info("       E2E 自动测试开始")
        log.info("  最大回合: %d | 最大场景: %d", self.max_rounds, self.max_scenes)
        log.info("═" * 50)
        log.info("")

        # ── 主循环 ──
        round_count = 0
        scene_changes = 0
        stop_reason = "已达最大回合数"
        actions: list[str] = []
        start_time = time.time()

        # 初始叙事传给 PlayerAgent
        latest_narrative = opening_narrative

        while round_count < self.max_rounds:
            round_count += 1

            # 1. AI 玩家决策
            log.info("")
            log.info("┌─ 回合 %d/%d ─┐", round_count, self.max_rounds)

            try:
                action = player.decide_action(latest_narrative)
            except Exception as e:
                log.error("  PlayerAgent 决策失败: %s", e)
                stop_reason = f"PlayerAgent 决策异常: {e}"
                break

            log.info("  🎮 玩家行动: %s", action)
            actions.append(action)

            # 2. GameLoop 处理行动
            try:
                step_result = game.step(action)
            except Exception as e:
                log.error("  GameLoop.step() 执行失败: %s", e)
                stop_reason = f"GameLoop 执行异常: {e}"
                break

            # 3. 处理结果
            if step_result.is_quit:
                # AI 玩家不应该输出 /quit，但以防万一
                stop_reason = "玩家请求退出"
                break

            latest_narrative = step_result.narrative

            # 4. 场景切换检查
            if step_result.scene_changed:
                scene_changes += 1
                log.info(
                    "  🔄 场景切换 (%d/%d): %s",
                    scene_changes,
                    self.max_scenes,
                    step_result.scene_end_reason,
                )

                # 场景切换后，用新场景的开场叙事更新 PlayerAgent 的上下文
                new_opening = "\n".join(game.state.scene.narrative_history)
                if new_opening:
                    latest_narrative = new_opening

                if scene_changes >= self.max_scenes:
                    stop_reason = f"已达最大场景数 ({self.max_scenes})"
                    break

            # 5. 角色失去行动能力检查
            if game.state.character and game.state.character.is_incapacitated():
                stop_reason = "角色失去行动能力"
                log.info("  💀 角色已丧失行动能力，测试停止")
                break

        elapsed = time.time() - start_time

        # ── 构建摘要 ──
        summary = self._build_summary(
            game=game,
            round_count=round_count,
            scene_changes=scene_changes,
            stop_reason=stop_reason,
            actions=actions,
            elapsed=elapsed,
        )

        # ── 输出摘要 ──
        self._print_summary(log, summary)

        return summary

    def _build_summary(
        self,
        game: GameLoop,
        round_count: int,
        scene_changes: int,
        stop_reason: str,
        actions: list[str],
        elapsed: float,
    ) -> dict:
        """构建测试结果摘要字典。

        Args:
            game: GameLoop 实例
            round_count: 实际回合数
            scene_changes: 场景切换次数
            stop_reason: 停止原因
            actions: 所有玩家行动列表
            elapsed: 总耗时

        Returns:
            摘要字典
        """
        # 角色最终状态
        char_statuses = {}
        if game.state.character:
            char_statuses = {
                name: {"tier": s.current_tier, "boxes": sorted(s.ticked_boxes)}
                for name, s in game.state.character.statuses.items()
            }

        # 挑战最终状态
        challenge = game.state.scene.primary_challenge()
        challenge_name = challenge.name if challenge else "（无）"
        challenge_statuses = {}
        if challenge:
            challenge_statuses = {
                name: {"tier": s.current_tier, "boxes": sorted(s.ticked_boxes)}
                for name, s in challenge.statuses.items()
            }

        # 极限突破情况
        broken_limits = []
        if challenge:
            broken_limits = sorted(challenge.broken_limits)

        return {
            "total_rounds": round_count,
            "scene_changes": scene_changes,
            "stop_reason": stop_reason,
            "character_name": game.state.character.name if game.state.character else "",
            "character_statuses": char_statuses,
            "challenge_name": challenge_name,
            "challenge_statuses": challenge_statuses,
            "broken_limits": broken_limits,
            "actions": actions,
            "elapsed_seconds": round(elapsed, 1),
        }

    def _print_summary(self, log, summary: dict):
        """输出可读的测试摘要到日志。

        Args:
            log: Logger 实例
            summary: 摘要字典
        """
        log.info("")
        log.info("═" * 50)
        log.info("       E2E 测试摘要")
        log.info("═" * 50)
        log.info("  总回合数: %d", summary["total_rounds"])
        log.info("  场景切换: %d 次", summary["scene_changes"])
        log.info("  停止原因: %s", summary["stop_reason"])
        log.info("  总耗时: %.1f 秒", summary["elapsed_seconds"])
        log.info("")

        # 角色状态
        log.info("  [角色: %s]", summary["character_name"])
        if summary["character_statuses"]:
            for name, info in summary["character_statuses"].items():
                log.info("    %s: 等级%d (格子: %s)", name, info["tier"], info["boxes"])
        else:
            log.info("    （无状态）")

        # 挑战状态
        log.info("")
        log.info("  [挑战: %s]", summary["challenge_name"])
        if summary["challenge_statuses"]:
            for name, info in summary["challenge_statuses"].items():
                log.info("    %s: 等级%d (格子: %s)", name, info["tier"], info["boxes"])
        else:
            log.info("    （无状态）")

        if summary["broken_limits"]:
            log.info("  已突破极限: %s", ", ".join(summary["broken_limits"]))

        # 行动列表
        log.info("")
        log.info("  [玩家行动记录]")
        for i, action in enumerate(summary["actions"], 1):
            log.info("    %d. %s", i, action)

        log.info("═" * 50)
