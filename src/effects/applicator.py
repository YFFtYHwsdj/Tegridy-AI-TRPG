from __future__ import annotations

from typing import Optional
from src.models import AgentNote, Character, Challenge
from src.engine import apply_status, reduce_status, add_story_tag, remove_story_tag, nudge_status
from src.logger import log_system


class EffectApplicator:

    @staticmethod
    def apply_results(effect_note: Optional[AgentNote], consequence_note: Optional[AgentNote], character: Optional[Character], challenge: Optional[Challenge]) -> list[str]:
        errors: list[str] = []
        if character is None or challenge is None:
            return errors

        effects = effect_note.structured.get("effects", []) if effect_note is not None else []
        errors.extend(EffectApplicator._apply_effect_list(effects, character, challenge))

        if consequence_note:
            consequences = consequence_note.structured.get("consequences", [])
            for cons in consequences:
                errors.extend(EffectApplicator._apply_effect_list(cons.get("effects", []), character, challenge))

        return errors

    @staticmethod
    def _resolve_target(target_name: str, character: Character, challenge: Challenge):
        """将效果目标名称解析为角色或挑战对象。

        匹配策略（按优先级）：
        1. 关键字精确匹配: "挑战" → challenge, "自身"/"self" → character
        2. 名称精确匹配: 目标名 == 角色名或挑战名
        3. 模糊匹配(长度>=3): 子串包含 + 长度占比>=60%,
           歧义时取占比高者(差距>=10%), 否则无法判定返回 None
        未匹配返回 None。
        """
        if not target_name:
            return None
        name_lower = target_name.lower().strip()

        if name_lower == "挑战":
            log_system(f"[目标解析] 关键字匹配: '{target_name}' → 挑战")
            return challenge
        if name_lower in ("自身", "self"):
            log_system(f"[目标解析] 关键字匹配: '{target_name}' → 角色")
            return character

        char_name_lower = character.name.lower()
        chal_name_lower = challenge.name.lower()

        if name_lower == char_name_lower:
            log_system(f"[目标解析] 精确匹配: '{target_name}' → 角色 '{character.name}'")
            return character
        if name_lower == chal_name_lower:
            log_system(f"[目标解析] 精确匹配: '{target_name}' → 挑战 '{challenge.name}'")
            return challenge

        if len(name_lower) >= 3:
            char_match = name_lower in char_name_lower
            chal_match = name_lower in chal_name_lower
            char_ratio = len(name_lower) / max(len(char_name_lower), 1)
            chal_ratio = len(name_lower) / max(len(chal_name_lower), 1)
            char_qualifies = char_match and char_ratio >= 0.6
            chal_qualifies = chal_match and chal_ratio >= 0.6

            if char_qualifies and not chal_qualifies:
                log_system(
                    f"[目标解析] 模糊匹配: '{target_name}' → 角色 '{character.name}' "
                    f"(in={char_match}, ratio={char_ratio:.0%})"
                )
                return character
            if chal_qualifies and not char_qualifies:
                log_system(
                    f"[目标解析] 模糊匹配: '{target_name}' → 挑战 '{challenge.name}' "
                    f"(in={chal_match}, ratio={chal_ratio:.0%})"
                )
                return challenge
            if char_qualifies and chal_qualifies:
                ratio_diff = abs(char_ratio - chal_ratio)
                if ratio_diff >= 0.1:
                    if char_ratio > chal_ratio:
                        log_system(
                            f"[目标解析] 歧义消解(比): '{target_name}' → 角色 '{character.name}' "
                            f"({char_ratio:.0%} vs 挑战 {chal_ratio:.0%})"
                        )
                        return character
                    else:
                        log_system(
                            f"[目标解析] 歧义消解(比): '{target_name}' → 挑战 '{challenge.name}' "
                            f"({chal_ratio:.0%} vs 角色 {char_ratio:.0%})"
                        )
                        return challenge
                else:
                    log_system(
                        f"[目标解析] 歧义(比例接近): '{target_name}' 同时匹配角色和挑战"
                        f"(角色{char_ratio:.0%}, 挑战{chal_ratio:.0%}), 差距<10%, 无法判定"
                    )

        log_system(f"[目标解析] 无法匹配效果目标 '{target_name}', 已忽略")
        return None

    @staticmethod
    def _apply_effect_list(eff_list: list[dict], character: Character, challenge: Challenge) -> list[str]:
        errors: list[str] = []
        for eff in eff_list:
            operation = eff.get("operation", "inflict_status")
            target = EffectApplicator._resolve_target(eff.get("target", ""), character, challenge)
            if target is None:
                target_name = eff.get("target", "?")
                errors.append(f"无法解析效果目标 '{target_name}' ({operation})")
                continue

            try:
                if operation == "inflict_status":
                    label = eff.get("label", "")
                    tier = eff.get("tier", 0)
                    if not label or tier <= 0:
                        continue
                    limit_category = eff.get("limit_category", "")
                    apply_status(target, label, tier, limit_category)
                    eff_type = eff.get("effect_type", "?")
                    log_system(f"[效果应用] {eff_type}: {label}-{tier} → {target.name}")

                elif operation == "nudge_status":
                    status_to_nudge = eff.get("status_to_nudge", eff.get("label", ""))
                    if not status_to_nudge:
                        continue
                    result = nudge_status(target, status_to_nudge)
                    eff_type = eff.get("effect_type", "?")
                    log_system(f"[效果应用] {eff_type}: nudge {status_to_nudge} → 等级{result.current_tier}")

                elif operation == "reduce_status":
                    status_to_reduce = eff.get("status_to_reduce", "")
                    reduce_by = eff.get("reduce_by", 1)
                    if not status_to_reduce or reduce_by <= 0:
                        continue
                    result = reduce_status(target, status_to_reduce, reduce_by)
                    eff_type = eff.get("effect_type", "?")
                    if result:
                        log_system(f"[效果应用] {eff_type}: {status_to_reduce} 降低{reduce_by}级 → 剩余{result.current_tier}")
                    else:
                        log_system(f"[效果应用] {eff_type}: {status_to_reduce} 已完全移除")

                elif operation == "add_story_tag":
                    name = eff.get("story_tag_name", "")
                    description = eff.get("story_tag_description", "")
                    if not name:
                        continue
                    is_single_use = eff.get("is_single_use", False)
                    add_story_tag(target, name, description, is_single_use)
                    eff_type = eff.get("effect_type", "?")
                    log_system(f"[效果应用] {eff_type}: 添加故事标签 [{name}] → {target.name}")

                elif operation == "scratch_story_tag":
                    name = eff.get("story_tag_to_scratch", "")
                    if not name:
                        continue
                    result = remove_story_tag(target, name)
                    eff_type = eff.get("effect_type", "?")
                    if result:
                        log_system(f"[效果应用] {eff_type}: 移除故事标签 [{name}]")
                    else:
                        log_system(f"[效果应用] {eff_type}: 故事标签 [{name}] 不存在，已忽略")

                elif operation == "discover":
                    detail = eff.get("detail", "")
                    if detail:
                        log_system(f"[效果应用] discover: {detail}")

                elif operation == "extra_feat":
                    description = eff.get("description", "")
                    if description:
                        log_system(f"[效果应用] extra_feat: {description}")

            except Exception as e:
                eff_type = eff.get("effect_type", "?")
                msg = f"[效果应用错误] {eff_type} ({operation}): {e}"
                log_system(msg)
                errors.append(msg)
        return errors
