"""控制台显示模块 —— 调试模式下的信息可视化输出。

ConsoleDisplay 负责格式化各 Agent 的内部信息和游戏状态，
通过日志系统的 DEBUG 通道输出。

调试模式下（set_debug_mode(True)）：INFO+ 和 DEBUG 信息同时出现在终端和日志文件。
正常模式下（set_debug_mode(False)）：DEBUG 信息仅写入日志文件，终端不可见。

输出内容的可见性由日志系统的 ConsoleHandler 等级自动控制，
无需在 ConsoleDisplay 内部维护 debug_mode 状态。
"""

from __future__ import annotations

import logging

from src.formatter import format_limit_progress, format_statuses, format_story_tags
from src.pipeline._tag_utils import extract_status_names, extract_tag_names


class ConsoleDisplay:
    """调试信息显示器。

    所有输出委托给日志系统（DEBUG 级别）。
    """

    def __init__(self, logger: logging.Logger):
        self._log = logger

    def print_tag_and_roll(self, tag_note, roll):
        """打印标签匹配和掷骰详情。

        Args:
            tag_note: Tag 匹配 Agent 的分析便签
            roll: 掷骰结果
        """
        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = extract_tag_names(matched_power)
        weakness_tag_names = extract_tag_names(matched_weakness)

        helping_statuses = tag_note.structured.get("helping_statuses", [])
        hindering_statuses = tag_note.structured.get("hindering_statuses", [])
        help_names = extract_status_names(helping_statuses)
        hinder_names = extract_status_names(hindering_statuses)

        self._log.debug("  匹配标签: %s | 弱点: %s", power_tag_names, weakness_tag_names)
        if help_names or hinder_names:
            status_parts = []
            if help_names:
                status_parts.append(f"帮助状态: {help_names}")
            if hinder_names:
                status_parts.append(f"阻碍状态: {hinder_names}")
            self._log.debug("  状态影响: %s", " | ".join(status_parts))
        self._log.debug(
            "  力量: %d | 掷骰: %d+%d = %d → %s",
            roll.power,
            roll.dice[0],
            roll.dice[1],
            roll.total,
            roll.outcome,
        )

    def print_effects(self, effect_note):
        """打印效果推演结果。

        Args:
            effect_note: 效果推演 Agent 的分析便签
        """
        if effect_note is None:
            return
        effects = effect_note.structured.get("effects", [])
        if effects:
            eff_summary = ", ".join(
                f"{e.get('label', '?')} ({e.get('effect_type', '?')} {e.get('tier', '?')})"
                for e in effects
            )
            self._log.debug("  实际效果: %s", eff_summary)
        else:
            self._log.debug("  实际效果: 无")

    def print_effects_or_quick_note(self, effect_note, quick=False):
        """根据模式打印效果或快速结算提示。

        Args:
            effect_note: 效果推演便签（标准模式）或 None（快速模式）
            quick: 是否为快速结算模式
        """
        if quick:
            self._log.debug("  实际效果: 无（快速结算不花费力量）")
        elif effect_note is not None:
            self.print_effects(effect_note)

    def print_strategy(self, narrator_note):
        """打印叙述者的叙事策略。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
        """
        strategy = narrator_note.structured.get("scene_update") or narrator_note.reasoning[:60]
        if strategy:
            self._log.debug("  叙事策略: %s", strategy)

    def print_consequences(self, consequence_note):
        """打印后果摘要。

        Args:
            consequence_note: 后果 Agent 的分析便签
        """
        if not consequence_note:
            return
        cons_list = consequence_note.structured.get("consequences", [])
        if not cons_list:
            return
        cons_summary = ", ".join(
            c.get("threat_manifested") or c.get("description", "?") for c in cons_list
        )
        self._log.debug("  后果: %s", cons_summary)

    def print_status(self, state):
        """打印当前游戏状态快照。

        包含角色状态、故事标签、持有物品，以及挑战的极限进度和状态。

        Args:
            state: 当前 GameState
        """
        if state.character is None:
            return
        challenge = state.scene.primary_challenge()
        if challenge is None:
            return
        self._log.debug("")
        self._log.debug("  [角色: %s]", state.character.name)
        self._log.debug("  状态: %s", format_statuses(state.character.statuses))
        self._log.debug("  故事标签: %s", format_story_tags(state.character.story_tags))
        char_items = state.character.items_visible
        if char_items:
            item_names = ", ".join(item.name for item in char_items.values())
            self._log.debug("  持有: %s", item_names)

        scene = state.scene
        scene_items = scene.scene_items_visible
        if scene_items:
            item_names = ", ".join(f"{item.name}({item.location})" for item in scene_items.values())
            self._log.debug("  场景物品: %s", item_names)

        self._log.debug("")
        self._log.debug("  [挑战: %s]", challenge.name)
        progress = challenge.get_limit_progress()
        for limit in challenge.limits:
            current = progress[limit.name]
            self._log.debug("  %s", format_limit_progress(limit, current))
        self._log.debug("  故事标签: %s", format_story_tags(challenge.story_tags))
        self._log.debug("  状态: %s", format_statuses(challenge.statuses))

    def print_split_action_header(self, count: int):
        """打印复合 action 拆分提示。

        Args:
            count: 子 action 数量
        """
        self._log.debug("  ⚡ 行动拆分为 %d 个子行动", count)

    def print_split_sub_header(self, index: int, total: int, summary: str):
        """打印子 action 执行提示。

        Args:
            index: 当前子 action 序号
            total: 子 action 总数
            summary: 子 action 摘要
        """
        self._log.debug("\n  --- 子行动 %d/%d: %s ---", index, total, summary)

    def print_split_blocked(self, action_summary: str, reason: str):
        """打印子 action 被阻止提示。

        Args:
            action_summary: 被阻止的子 action 摘要
            reason: 阻止原因
        """
        self._log.debug("\n  ⛔ 子行动 [%s] 无法继续: %s", action_summary, reason)

    def print_incapacitated_break(self):
        """打印角色丧失行动能力提示。"""
        self._log.debug("\n  💀 角色已丧失行动能力，剩余子行动中断")
