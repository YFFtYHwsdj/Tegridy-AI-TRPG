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
from src.models import NPC, AgentNote, Character
from src.state.scene_state import SceneState


class EffectApplicator:
    """效果执行器 —— Agent 输出到游戏状态的桥梁。

    所有方法均为静态方法，无内部状态。接收效果推演/后果 Agent 的结构化输出，
    解析 operation 类型并调用对应的 engine 函数执行实际的状态变更。
    """

    @staticmethod
    def apply_results(
        outcome_note: AgentNote | None,
        character: Character | None,
        scene: SceneState | None,
    ) -> list[str]:
        """应用效果推演和后果的全部效果到游戏状态。

        处理 Outcome Agent 的分析便签中的 effects 和 consequences。

        Args:
            outcome_note: 结算推演 Agent 的分析便签
            character: 当前玩家角色
            scene: 当前场景状态

        Returns:
            执行过程中产生的错误信息列表（空列表表示全部成功）
        """
        errors: list[str] = []
        if character is None or scene is None or outcome_note is None:
            return errors

        effects = outcome_note.structured.get("effects", [])
        errors.extend(EffectApplicator._apply_effect_list(effects, character, scene))

        consequences = outcome_note.structured.get("consequences", [])
        for cons in consequences:
            errors.extend(
                EffectApplicator._apply_effect_list(cons.get("effects", []), character, scene)
            )

        return errors

    @staticmethod
    def _resolve_target(target_name: str, character: Character, scene: SceneState):
        """将效果目标名称解析为角色或场景中的NPC对象。

        匹配策略（按优先级）：
        1. 关键字精确匹配: "自身"/"self" → character
        2. 名称精确匹配: 目标名 == 角色名或某个 NPC 名
        3. 模糊匹配(长度>=3): 子串包含。如果目标不存在则返回 None，交由纯叙事处理。
        未匹配返回 None。
        """
        if not target_name:
            return None
        name_lower = target_name.lower().strip()

        # 优先级1: 关键字匹配
        if name_lower in ("自身", "self", "自身(玩家)", "自己"):
            log_system(f"关键字匹配: '{target_name}' → 角色", level="debug")
            return character

        char_name_lower = character.name.lower()
        if name_lower == char_name_lower:
            log_system(f"精确匹配: '{target_name}' → 角色 '{character.name}'", level="debug")
            return character

        # 环境/场景匹配
        if name_lower in ("场景", "环境", "scene", "environment"):
            log_system(f"关键字匹配: '{target_name}' → 环境/场景", level="debug")
            return scene

        # 遍历 NPC 精确匹配
        for npc in scene.npcs.values():
            if name_lower == npc.name.lower():
                log_system(f"精确匹配: '{target_name}' → NPC '{npc.name}'", level="debug")
                return npc

        # 模糊匹配
        if len(name_lower) >= 3:
            matches = []
            if name_lower in char_name_lower:
                matches.append(character)

            for npc in scene.npcs.values():
                if name_lower in npc.name.lower() or npc.name.lower() in name_lower:
                    matches.append(npc)

            if len(matches) == 1:
                log_system(f"模糊匹配: '{target_name}' → '{matches[0].name}'", level="debug")
                return matches[0]
            elif len(matches) > 1:
                log_system(
                    f"模糊匹配: '{target_name}' 存在歧义，匹配到 {len(matches)} 个目标",
                    level="warning",
                )
                return None

        log_system(
            f"目标 '{target_name}' 可能是环境阻力或非生命物体，已忽略其数据绑定，将交由叙述者处理",
            level="debug",
        )
        return None

    @staticmethod
    def _apply_effect_list(
        eff_list: list[dict], character: Character, scene: SceneState
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
            scene: 当前场景状态

        Returns:
            错误信息列表
        """
        errors: list[str] = []
        for eff in eff_list:
            operation = eff.get("operation", "inflict_status")
            target = EffectApplicator._resolve_target(eff.get("target", ""), character, scene)
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
                    if not isinstance(target, (Character, NPC)):
                        raise TypeError(
                            f"{operation} requires Character or NPC target, got {type(target).__name__}"
                        )
                    apply_status(target, label, tier)
                    eff_type = eff.get("effect_type", "?")
                    log_system(f"{eff_type}: {label}-{tier} → {target.name}", level="debug")

                elif operation == "nudge_status":
                    status_to_nudge = eff.get("status_to_nudge", eff.get("label", ""))
                    if not status_to_nudge:
                        continue
                    if not isinstance(target, (Character, NPC)):
                        raise TypeError(
                            f"{operation} requires Character or NPC target, got {type(target).__name__}"
                        )
                    result = nudge_status(target, status_to_nudge)
                    eff_type = eff.get("effect_type", "?")
                    log_system(
                        f"{eff_type}: nudge {status_to_nudge} → 等级{result.current_tier}",
                        level="debug",
                    )

                elif operation == "reduce_status":
                    status_to_reduce = eff.get("status_to_reduce", "")
                    reduce_by = eff.get("reduce_by", 1)
                    if not status_to_reduce or reduce_by <= 0:
                        continue
                    if not isinstance(target, (Character, NPC)):
                        raise TypeError(
                            f"{operation} requires Character or NPC target, got {type(target).__name__}"
                        )
                    result = reduce_status(target, status_to_reduce, reduce_by)
                    eff_type = eff.get("effect_type", "?")
                    if result:
                        log_system(
                            f"{eff_type}: {status_to_reduce} 降低{reduce_by}级 → 剩余{result.current_tier}",
                            level="debug",
                        )
                    else:
                        log_system(f"{eff_type}: {status_to_reduce} 已完全移除", level="debug")

                elif operation == "add_story_tag":
                    name = eff.get("story_tag_name", "")
                    description = eff.get("story_tag_description", "")
                    if not name:
                        continue
                    is_single_use = eff.get("is_single_use", False)
                    if not isinstance(target, (Character, SceneState)):
                        raise TypeError(
                            f"{operation} requires Character or SceneState target, got {type(target).__name__}"
                        )
                    add_story_tag(target, name, description, is_single_use)
                    eff_type = eff.get("effect_type", "?")
                    log_system(
                        f"{eff_type}: 添加故事标签 [{name}] → {getattr(target, 'name', '环境')}",
                        level="debug",
                    )

                elif operation == "scratch_story_tag":
                    name = eff.get("story_tag_to_scratch", "")
                    if not name:
                        continue
                    if not isinstance(target, (Character, SceneState)):
                        raise TypeError(
                            f"{operation} requires Character or SceneState target, got {type(target).__name__}"
                        )
                    result = remove_story_tag(target, name)
                    eff_type = eff.get("effect_type", "?")
                    if result:
                        log_system(f"{eff_type}: 移除故事标签 [{name}]", level="debug")
                    else:
                        log_system(
                            f"{eff_type}: 故事标签 [{name}] 不存在，已忽略",
                            level="warning",
                        )

                elif operation == "discover":
                    # 纯叙事操作，仅记录日志
                    detail = eff.get("detail", "")
                    if detail:
                        log_system(f"discover: {detail}", level="debug")

                elif operation == "extra_feat":
                    # 纯叙事操作，仅记录日志
                    description = eff.get("description", "")
                    if description:
                        log_system(f"extra_feat: {description}", level="debug")

            except Exception as e:
                eff_type = eff.get("effect_type", "?")
                msg = f"{eff_type} ({operation}): {e}"
                log_system(msg, level="error")
                errors.append(msg)
        return errors
