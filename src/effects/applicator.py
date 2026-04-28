"""效果执行层 —— 将 Agent 产出的效果描述翻译为实际的游戏状态变更。

本模块是 Agent 流水线的"落地层"。效果推演 Agent 和后果 Agent 产出的
结构化效果条目（inflict_status、nudge_status、reduce_status 等），
由 EffectApplicator 解析并调用 engine.py 的纯 Python 函数执行。
同时负责目标名称解析（_resolve_target），将 LLM 产出的自然语言目标名
映射到实际的 Character/Challenge 对象。
"""

from __future__ import annotations

from src.engine import add_story_tag, apply_status, nudge_status, reduce_status, remove_story_tag
from src.logger import log_system
from src.models import AgentNote, Challenge, Character


class EffectApplicator:
    """效果执行器 —— Agent 输出到游戏状态的桥梁。

    所有方法均为静态方法，无内部状态。接收效果推演/后果 Agent 的结构化输出，
    解析 operation 类型并调用对应的 engine 函数执行实际的状态变更。
    """

    @staticmethod
    def apply_results(
        effect_note: AgentNote | None,
        consequence_note: AgentNote | None,
        character: Character | None,
        challenge: Challenge | None,
    ) -> list[str]:
        """应用效果推演和后果的全部效果到游戏状态。

        先处理效果推演 Agent 的效果列表，再处理后果 Agent 的后果列表。
        每个后果条目内部可能包含嵌套的效果列表。

        Args:
            effect_note: 效果推演 Agent 的分析便签
            consequence_note: 后果 Agent 的分析便签
            character: 当前玩家角色
            challenge: 当前挑战

        Returns:
            执行过程中产生的错误信息列表（空列表表示全部成功）
        """
        errors: list[str] = []
        if character is None or challenge is None:
            return errors

        effects = effect_note.structured.get("effects", []) if effect_note is not None else []
        errors.extend(EffectApplicator._apply_effect_list(effects, character, challenge))

        if consequence_note:
            consequences = consequence_note.structured.get("consequences", [])
            for cons in consequences:
                errors.extend(
                    EffectApplicator._apply_effect_list(
                        cons.get("effects", []), character, challenge
                    )
                )

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

        # 优先级1: 关键字匹配
        if name_lower == "挑战":
            log_system(f"[目标解析] 关键字匹配: '{target_name}' → 挑战")
            return challenge
        if name_lower in ("自身", "self"):
            log_system(f"[目标解析] 关键字匹配: '{target_name}' → 角色")
            return character

        char_name_lower = character.name.lower()
        chal_name_lower = challenge.name.lower()

        # 优先级2: 名称精确匹配
        if name_lower == char_name_lower:
            log_system(f"[目标解析] 精确匹配: '{target_name}' → 角色 '{character.name}'")
            return character
        if name_lower == chal_name_lower:
            log_system(f"[目标解析] 精确匹配: '{target_name}' → 挑战 '{challenge.name}'")
            return challenge

        # 优先级3: 模糊匹配（仅名称长度≥3时启用，避免短词误匹配）
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
    def _apply_effect_list(
        eff_list: list[dict], character: Character, challenge: Challenge
    ) -> list[str]:
        """遍历并执行效果列表中的每个效果条目。

        支持的操作类型（operation）：
            - inflict_status: 施加状态
            - nudge_status: 恶化状态
            - reduce_status: 降低/恢复状态
            - add_story_tag: 添加叙事标签
            - scratch_story_tag: 移除叙事标签
            - discover: 揭示信息（仅日志）
            - extra_feat: 额外特技（仅日志）

        Args:
            eff_list: 效果条目列表，每个条目为 dict
            character: 当前玩家角色
            challenge: 当前挑战

        Returns:
            错误信息列表
        """
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
                    log_system(
                        f"[效果应用] {eff_type}: nudge {status_to_nudge} → 等级{result.current_tier}"
                    )

                elif operation == "reduce_status":
                    status_to_reduce = eff.get("status_to_reduce", "")
                    reduce_by = eff.get("reduce_by", 1)
                    if not status_to_reduce or reduce_by <= 0:
                        continue
                    result = reduce_status(target, status_to_reduce, reduce_by)
                    eff_type = eff.get("effect_type", "?")
                    if result:
                        log_system(
                            f"[效果应用] {eff_type}: {status_to_reduce} 降低{reduce_by}级 → 剩余{result.current_tier}"
                        )
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
                    # 纯叙事操作，仅记录日志
                    detail = eff.get("detail", "")
                    if detail:
                        log_system(f"[效果应用] discover: {detail}")

                elif operation == "extra_feat":
                    # 纯叙事操作，仅记录日志
                    description = eff.get("description", "")
                    if description:
                        log_system(f"[效果应用] extra_feat: {description}")

            except Exception as e:
                eff_type = eff.get("effect_type", "?")
                msg = f"[效果应用错误] {eff_type} ({operation}): {e}"
                log_system(msg)
                errors.append(msg)
        return errors
