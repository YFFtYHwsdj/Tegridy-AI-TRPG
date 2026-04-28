from __future__ import annotations

from src.formatter import format_statuses, format_story_tags, format_limit_progress
from src.pipeline._tag_utils import extract_tag_names, extract_status_names


class ConsoleDisplay:
    def __init__(self, debug_mode: bool = False):
        self.debug_mode = debug_mode

    def print_tag_and_roll(self, tag_note, roll):
        if not self.debug_mode:
            return
        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = extract_tag_names(matched_power)
        weakness_tag_names = extract_tag_names(matched_weakness)

        helping_statuses = tag_note.structured.get("helping_statuses", [])
        hindering_statuses = tag_note.structured.get("hindering_statuses", [])
        help_names = extract_status_names(helping_statuses)
        hinder_names = extract_status_names(hindering_statuses)

        print(f"  匹配标签: {power_tag_names} | 弱点: {weakness_tag_names}")
        if help_names or hinder_names:
            status_parts = []
            if help_names:
                status_parts.append(f"帮助状态: {help_names}")
            if hinder_names:
                status_parts.append(f"阻碍状态: {hinder_names}")
            print(f"  状态影响: {' | '.join(status_parts)}")
        print(f"  力量: {roll.power} | 掷骰: {roll.dice[0]}+{roll.dice[1]} = {roll.total} → {roll.outcome}")

    def print_effects(self, effect_note):
        if not self.debug_mode:
            return
        if effect_note is None:
            return
        effects = effect_note.structured.get("effects", [])
        if effects:
            eff_summary = ", ".join(f"{e.get('label','?')} ({e.get('effect_type','?')} {e.get('tier','?')})" for e in effects)
            print(f"  实际效果: {eff_summary}")
        else:
            print(f"  实际效果: 无")

    def print_effects_or_quick_note(self, effect_note, quick=False):
        if not self.debug_mode:
            return
        if quick:
            print(f"  实际效果: 无（快速结算不花费力量）")
        elif effect_note is not None:
            self.print_effects(effect_note)

    def print_strategy(self, narrator_note):
        if not self.debug_mode:
            return
        strategy = narrator_note.structured.get("scene_update") or narrator_note.reasoning[:60]
        if strategy:
            print(f"  叙事策略: {strategy}")

    def print_consequences(self, consequence_note):
        if not self.debug_mode:
            return
        if not consequence_note:
            return
        cons_list = consequence_note.structured.get("consequences", [])
        if not cons_list:
            return
        cons_summary = ", ".join(
            c.get("threat_manifested") or c.get("description", "?") for c in cons_list
        )
        print(f"  后果: {cons_summary}")

    def print_status(self, state):
        if not self.debug_mode:
            return
        if state.character is None:
            return
        challenge = state.scene.primary_challenge()
        if challenge is None:
            return
        print(f"\n  [角色: {state.character.name}]")
        print(f"  状态: {format_statuses(state.character.statuses)}")
        print(f"  故事标签: {format_story_tags(state.character.story_tags)}")
        char_items = state.character.items_visible
        if char_items:
            item_names = ", ".join(f"{item.name}({item.location})" for item in char_items.values())
            print(f"  物品: {item_names}")

        print(f"\n  [挑战: {challenge.name}]")
        progress = challenge.get_limit_progress()
        for limit in challenge.limits:
            current = progress[limit.name]
            print(f"  {format_limit_progress(limit, current)}")
        print(f"  故事标签: {format_story_tags(challenge.story_tags)}")
        print(f"  状态: {format_statuses(challenge.statuses)}")

    @staticmethod
    def print_split_action_header(count: int):
        print(f"  ⚡ 行动拆分为 {count} 个子行动")

    @staticmethod
    def print_split_sub_header(index: int, total: int, summary: str):
        print(f"\n  --- 子行动 {index}/{total}: {summary} ---")

    @staticmethod
    def print_split_blocked(action_summary: str, reason: str):
        print(f"\n  ⛔ 子行动 [{action_summary}] 无法继续: {reason}")

    @staticmethod
    def print_incapacitated_break():
        print(f"\n  💀 角色已丧失行动能力，剩余子行动中断")
