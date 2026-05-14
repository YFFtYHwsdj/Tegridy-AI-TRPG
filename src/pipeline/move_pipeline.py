"""Action 流程编排 —— 多 Agent 接力执行的 Pipe-and-Filter 流水线。

本模块是系统的核心控制器。MovePipeline 协调 Tag 匹配、掷骰、效果推演、
后果生成、叙事渲染和校验应用的全流程。每条流水线对应一次玩家行动，
按照 PBTA 规则完成"意图 → 判定 → 效果 → 后果 → 叙事"的完整序列。

流水线模式：
    - run_single_move_pipeline: 标准完整流水线（单步 action）
    - run_quick_pipeline: 快速流水线（跳过效果推演 Agent）
    - process_split_actions: 复合 action 拆分流水线（多步子 action 接力）
"""

from __future__ import annotations

import json
from typing import Any

from src.agents import (
    ContinuationCheckAgent,
    NarratorAgent,
    OutcomeAgent,
    QuickNarratorAgent,
    QuickOutcomeAgent,
    TagMatcherAgent,
)
from src.display.console import ConsoleDisplay
from src.engine import calculate_power, resolve_matched_tags, roll_dice
from src.llm_client import LLMClient
from src.logger import log_roll, log_system
from src.pipeline._tag_utils import extract_status_tiers, extract_tag_names
from src.pipeline.managers import (
    CharacterManager,
    ClueManager,
    ItemManager,
    NPCManager,
    StoryTagManager,
)
from src.pipeline.pipeline_result import PipelineResult
from src.state.game_state import GameState


def _summarize_last_sub(roll, effects, cons) -> str:
    """生成上一步子 action 的摘要文本，用于继续性检查。

    Args:
        roll: 上一步的 RollResult
        effects: 上一步的效果列表
        cons: 上一步的后果列表

    Returns:
        格式化的摘要字符串
    """
    if roll is None:
        return "（上一步无有效掷骰）"
    parts = [f"掷骰结果: {roll.outcome}"]
    if effects:
        parts.append("效果: " + ", ".join(e.get("label", e.get("operation", "?")) for e in effects))
    if cons:
        parts.append("后果: " + ", ".join(c.get("threat_manifested", "?") for c in cons))
    return "; ".join(parts) if parts else "（无效果信息）"


class MovePipeline:
    """Action 流水线 —— 多 Agent 接力执行的核心控制器。

    初始化时创建所有所需的 Agent 实例（Tag 匹配、效果推演、后果、
    叙述者、继续性检查、校验），每条流水线调用时按固定顺序执行它们。

    关键方法：
        run_single_move_pipeline: 完整流水线，适用于一般 action
        run_quick_pipeline: 快速流水线，跳过效果推演，适用于简单 action
        process_split_actions: 复合 action 拆分执行
        validate_and_apply: 校验叙事输出并将其中的线索/物品揭示应用到游戏状态
    """

    def __init__(self, llm: LLMClient, state: GameState, display: ConsoleDisplay):
        self.llm = llm
        self.state = state
        self.display = display

        # 创建所有 Agent 实例
        self.tag_agent = TagMatcherAgent(llm)
        self.outcome_agent = OutcomeAgent(llm)
        self.quick_outcome_agent = QuickOutcomeAgent(llm)
        self.narrator = NarratorAgent(llm)
        self.quick_narrator = QuickNarratorAgent(llm)
        self.continuation_check = ContinuationCheckAgent(llm)

        # 创建领域驱动的状态管理器
        self.item_manager = ItemManager(state, llm)
        self.clue_manager = ClueManager(state)
        self.story_tag_manager = StoryTagManager(state)
        self.character_manager = CharacterManager(state)
        self.npc_manager = NPCManager(state)

    def _run_tag_and_roll(self, intent_note, ctx, sub_action=None):
        """流水线阶段1: 标签匹配 + 掷骰。

        执行 Tag 匹配 Agent 获取命中的力量/弱点标签，
        提取标签名和状态 tier，计算力量值并掷骰。

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文
            sub_action: 子 action 数据（复合 action 场景），可选

        Returns:
            (tag_note, roll) 元组
        """
        tag_note = self.tag_agent.execute(intent_note, ctx, sub_action=sub_action)

        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = extract_tag_names(matched_power)
        weakness_tag_names = extract_tag_names(matched_weakness)

        best_status_tier, worst_status_tier = extract_status_tiers(tag_note)

        if ctx is None or ctx.character is None:
            raise ValueError("MovePipeline._run_tag_and_roll 需要有效的上下文和角色信息")
        char = ctx.character
        scene = ctx.extra.get("scene_state")
        npcs = scene.npcs if scene else None
        resolved_power, resolved_weakness = resolve_matched_tags(
            char, npcs, power_tag_names, weakness_tag_names
        )

        power = calculate_power(
            resolved_power,
            resolved_weakness,
            best_status_tier=best_status_tier,
            worst_status_tier=worst_status_tier,
        )
        roll = roll_dice(power)

        log_roll(power, roll.dice, roll.total, roll.outcome, power_tag_names, weakness_tag_names)

        return tag_note, roll

    def run_single_move_pipeline(self, intent_note, ctx, sub_action=None) -> PipelineResult:
        """执行标准完整流水线。

        阶段顺序：
            1. 标签匹配 + 掷骰 (_run_tag_and_roll)
            2. 效果推演 (EffectActualizationAgent)
            3. 后果生成 (ConsequenceAgent) — 仅在 partial_success 或 failure 时
            4. 叙事渲染 (NarratorAgent)
            5. 校验与生效 (validate_and_apply)

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文
            sub_action: 子 action 数据（复合 action 场景），可选

        Returns:
            PipelineResult: 包含各阶段 AgentNote 和掷骰结果的完整数据
        """
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx, sub_action)

        outcome_note = self.outcome_agent.execute(
            intent_note, tag_note, roll, ctx, sub_action=sub_action
        )

        self._process_auto_mitigation(outcome_note, ctx)

        narrator_note = self.narrator.execute(
            intent_note,
            outcome_note,
            roll,
            ctx,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            outcome_note=outcome_note,
            narrator_note=narrator_note,
        )

    def run_quick_pipeline(self, intent_note, ctx) -> PipelineResult:
        """执行快速流水线（跳过效果推演 Agent）。

        适用于效果由系统直接裁定、不需要 LLM 推演的简单 action。
        阶段顺序：标签匹配+掷骰 → 快速后果 → 快速叙事 → 校验生效。

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文

        Returns:
            PipelineResult（effect_note 为 None）
        """
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx)

        outcome_note = self.quick_outcome_agent.execute(intent_note, roll, ctx)

        self._process_auto_mitigation(outcome_note, ctx)

        narrator_note = self.quick_narrator.execute(
            intent_note,
            outcome_note,
            roll,
            ctx,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            outcome_note=outcome_note,
            narrator_note=narrator_note,
        )

    def _run_resolution_only(self, intent_note, ctx, sub_action=None) -> PipelineResult:
        """执行解算流水线（不含叙述者和 validate_and_apply）。

        仅执行标签匹配 → 掷骰 → 效果推演 → 后果生成，
        用于拆分 action 场景中收集各子行动的规则结果，
        最后由统一叙述者一次性生成叙事。

        Args:
            intent_note: 意图解析 Agent 的分析便签
            ctx: 当前场景上下文
            sub_action: 子 action 数据（复合 action 场景），可选

        Returns:
            PipelineResult（narrator_note 为 None）
        """
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx, sub_action)

        outcome_note = self.outcome_agent.execute(
            intent_note, tag_note, roll, ctx, sub_action=sub_action
        )

        self._process_auto_mitigation(outcome_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            outcome_note=outcome_note,
            # narrator_note 留空，由调用方统一处理
        )

    def _process_auto_mitigation(self, outcome_note, ctx) -> None:
        """后台拦截处理自动缓解。

        如果后果中带有 mitigation_tags，根据标签数量计算效力并暗中掷骰，
        然后根据结果自动削减该后果包含的不利 effects。
        """
        if not outcome_note or not outcome_note.structured:
            return

        consequences = outcome_note.structured.get("consequences", [])
        for cons in consequences:
            mitigation_tags = cons.get("mitigation_tags", [])
            if not mitigation_tags:
                continue

            power = len(mitigation_tags)
            roll = roll_dice(power)

            if roll.outcome == "failure":
                spent_power = 0
            elif roll.outcome == "partial_success":
                spent_power = power
            else:
                spent_power = power + 1

            original_effects = list(cons.get("effects", []))
            remaining_power = spent_power

            if remaining_power > 0:
                for eff in original_effects:
                    op = eff.get("operation")
                    if op == "inflict_status" and remaining_power > 0:
                        tier = eff.get("tier", 0)
                        reduce = min(tier, remaining_power)
                        eff["tier"] = tier - reduce
                        remaining_power -= reduce
                    elif op == "scratch_story_tag" and remaining_power >= 2:
                        eff["_mitigated_out"] = True
                        remaining_power -= 2

                filtered_effects = []
                for eff in cons.get("effects", []):
                    if eff.get("operation") == "inflict_status" and eff.get("tier", 0) <= 0:
                        continue
                    if eff.get("_mitigated_out"):
                        continue
                    filtered_effects.append(eff)
                cons["effects"] = filtered_effects

            tags_str = "、".join(mitigation_tags)
            cons["mitigation_result_text"] = (
                f"玩家触发了自动缓解（使用标签：{tags_str}），后台掷骰结果为 {roll.total} "
                f"({roll.outcome})，获得 {spent_power} 点减免效力。"
            )

            log_system(
                f"执行自动缓解掷骰: tags={tags_str}, result={roll.outcome}, spent_power={spent_power}",
                level="info",
            )

    def validate_and_apply(self, narrator_note, ctx=None):
        """应用叙事输出中的揭示和物品转移及纯叙事故事标签。

        委托给各领域 Manager 执行，不经过 LLM 校验。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        if not narrator_note or not narrator_note.structured:
            return

        structured = narrator_note.structured

        # 线索揭示
        decisions = structured.get("revelation_decisions", {})
        for clue_id in decisions.get("reveal_clue_ids", []):
            self.clue_manager.reveal_clue(clue_id)

        # 物品揭示与转移
        for item_id in decisions.get("reveal_item_ids", []):
            self.item_manager.reveal_item(item_id)

        for transfer in structured.get("item_transfers", []):
            if isinstance(transfer, dict):
                self.item_manager.transfer_item(transfer, ctx)

        for update in structured.get("location_text_updates", []):
            if isinstance(update, dict):
                self.item_manager.update_item_location_text(
                    update.get("item_id", ""), update.get("new_location", "")
                )

        # 叙事级故事标签更新
        tag_updates = structured.get("story_tag_updates", {})
        for tag in tag_updates.get("add", []):
            if isinstance(tag, dict):
                self.story_tag_manager.add_scene_tag(
                    tag.get("name", ""), tag.get("description", "")
                )
        for tag_name in tag_updates.get("remove", []):
            if isinstance(tag_name, str):
                self.story_tag_manager.remove_scene_tag(tag_name)

    def apply_results(self, outcome_note, ctx) -> list[str]:
        """应用效果推演和后果的全部效果到游戏状态。

        Args:
            outcome_note: 结算推演 Agent 的分析便签
            ctx: 当前场景上下文

        Returns:
            执行过程中产生的错误信息列表
        """
        errors = []
        if not outcome_note:
            return errors

        effects = outcome_note.structured.get("effects", [])
        errors.extend(self._apply_effects(effects, ctx))

        consequences = outcome_note.structured.get("consequences", [])
        for cons in consequences:
            errors.extend(self._apply_effects(cons.get("effects", []), ctx))

        return errors

    def _apply_effects(self, effects: list[dict], ctx) -> list[str]:
        errors = []
        for eff in effects:
            op = eff.get("operation", "inflict_status")
            target_name = eff.get("target", "")

            # 解析目标
            target_type = None
            target_id = None
            if not target_name:
                continue

            name_lower = target_name.lower().strip()

            if name_lower in ("自身", "self", "自身(玩家)", "自己") or (
                self.state.character and name_lower == self.state.character.name.lower()
            ):
                target_type = "character"
            elif name_lower in ("场景", "环境", "scene", "environment"):
                target_type = "scene"
            else:
                for npc_id, npc in self.state.scene.npcs.items():
                    if (
                        name_lower == npc.name.lower()
                        or name_lower in npc.name.lower()
                        or npc.name.lower() in name_lower
                    ):
                        target_type = "npc"
                        target_id = npc_id
                        break

            if not target_type:
                # 只在 DEBUG 级别打印找不到的目标，避免刷屏
                log_system(
                    f"目标 '{target_name}' 可能是环境阻力或非生命物体，已忽略其数据绑定",
                    level="debug",
                )
                continue

            try:
                if op == "inflict_status":
                    label = eff.get("label", "")
                    tier = eff.get("tier", 0)
                    if target_type == "character":
                        self.character_manager.apply_status(label, tier)
                    elif target_type == "npc" and target_id:
                        self.npc_manager.apply_status(target_id, label, tier)
                elif op == "nudge_status":
                    label = eff.get("status_to_nudge", eff.get("label", ""))
                    if target_type == "character":
                        self.character_manager.nudge_status(label)
                    elif target_type == "npc" and target_id:
                        self.npc_manager.nudge_status(target_id, label)
                elif op == "reduce_status":
                    label = eff.get("status_to_reduce", "")
                    reduce_by = eff.get("reduce_by", 1)
                    if target_type == "character":
                        self.character_manager.reduce_status(label, reduce_by)
                    elif target_type == "npc" and target_id:
                        self.npc_manager.reduce_status(target_id, label, reduce_by)
                elif op == "add_story_tag":
                    name = eff.get("story_tag_name", "")
                    desc = eff.get("story_tag_description", "")
                    is_single_use = eff.get("is_single_use", False)
                    if target_type == "scene":
                        self.story_tag_manager.add_scene_tag(name, desc, is_single_use)
                    elif target_type == "character":
                        self.character_manager.add_personal_tag(name, desc, is_single_use)
                    elif target_type == "npc" and target_id:
                        self.npc_manager.add_personal_tag(target_id, name, desc, is_single_use)
                elif op == "scratch_story_tag":
                    name = eff.get("story_tag_to_scratch", "")
                    if target_type == "scene":
                        self.story_tag_manager.remove_scene_tag(name)
                    elif target_type == "character":
                        self.character_manager.remove_personal_tag(name)
                    elif target_type == "npc" and target_id:
                        self.npc_manager.remove_personal_tag(target_id, name)
                elif op == "discover":
                    detail = eff.get("detail", "")
                    if detail:
                        log_system(f"discover: {detail}", level="debug")
                elif op == "extra_feat":
                    desc = eff.get("description", "")
                    if desc:
                        log_system(f"extra_feat: {desc}", level="debug")
            except Exception as e:
                msg = f"执行效果失败 ({op}): {e}"
                log_system(msg, level="error")
                errors.append(msg)

        return errors

    def process_split_actions(self, intent_note, split_actions) -> list:
        """执行复合 action 的拆分流水线（统一叙事版）。

        当一个意图被意图解析 Agent 拆分为多个子 action（split_actions）时，
        按顺序逐个执行解算流水线（不含叙述者），所有子行动解算完毕后，
        调用统一叙述者一次性生成连贯叙事。

        流程：
            1. 对每个子 action 运行解算流水线（_run_resolution_only）
            2. 执行前检查上一步结果是否阻止继续（continuation_check）
            3. 收集所有子行动的解算结果
            4. 调用 narrator.execute_split 生成统一叙事
            5. 将统一叙事的 narrator_note 附加到最后一个 result
            6. 调用 validate_and_apply 处理揭示和物品转移

        Args:
            intent_note: 意图解析 Agent 的分析便签
            split_actions: 子 action 列表

        Returns:
            PipelineResult 列表（最后一个 result 包含统一 narrator_note）
        """
        self.display.print_split_action_header(len(split_actions))

        prev_roll = None
        prev_effects = []
        prev_cons = []
        results = []

        for i, sub in enumerate(split_actions):
            if sub is None:
                continue
            if not isinstance(sub, dict):
                sub = {"action_summary": str(sub)}
            sub: dict[str, Any] = dict(sub, _index=i)

            self.display.print_split_sub_header(
                i + 1, len(split_actions), sub.get("action_summary", "?")
            )

            # 非首步：检查上一步结果是否允许继续
            if i > 0:
                ctx = self.state.make_context()
                check_note = self.continuation_check.execute(
                    sub,
                    ctx,
                    _summarize_last_sub(prev_roll, prev_effects, prev_cons),
                )
                can_continue = check_note.structured.get("can_continue", True)
                if not can_continue:
                    reason = check_note.structured.get("reason", "")
                    self.display.print_split_blocked(sub.get("action_summary", "?"), reason)
                    break

            ctx = self.state.make_context(sub.get("fragment", ""))
            # 仅执行解算，不调用叙述者
            result = self._run_resolution_only(intent_note, ctx, sub_action=sub)
            results.append(result)

            # 保存当前步的结果供下一步的继续性检查使用
            prev_roll = result.roll
            prev_effects = (
                result.outcome_note.structured.get("effects", []) if result.outcome_note else []
            )
            prev_cons = (
                result.outcome_note.structured.get("consequences", [])
                if result.outcome_note
                else []
            )

        # 所有子行动解算完毕后，统一生成叙事
        if results:
            sub_results_for_narrator = []
            for result in results:
                roll = result.roll
                roll_summary = (
                    f"{roll.dice[0]}+{roll.dice[1]}+{roll.power}={roll.total} ({roll.outcome})"
                )
                effects_json = json.dumps(
                    result.outcome_note.structured.get("effects", [])
                    if result.outcome_note
                    else [],
                    ensure_ascii=False,
                )
                narrative_hints = (
                    result.outcome_note.structured.get("narrative_hints", "")
                    if result.outcome_note
                    else ""
                )
                consequences_json = json.dumps(
                    result.outcome_note.structured.get("consequences", [])
                    if result.outcome_note
                    else [],
                    ensure_ascii=False,
                )
                # 从 result 的 tag_note 获取子行动摘要
                summary = result.tag_note.structured.get(
                    "action_summary",
                    f"子行动 {len(sub_results_for_narrator) + 1}",
                )
                sub_results_for_narrator.append(
                    {
                        "summary": summary,
                        "roll_summary": roll_summary,
                        "effects_json": effects_json,
                        "narrative_hints": narrative_hints,
                        "consequences_json": consequences_json,
                    }
                )

            # 使用最新的上下文调用统一叙述者
            ctx = self.state.make_context()
            narrator_note = self.narrator.execute_split(sub_results_for_narrator, ctx)

            # 将统一叙事附加到最后一个 result
            results[-1].narrator_note = narrator_note

            # 统一执行揭示和物品转移
            self.validate_and_apply(narrator_note, ctx)

        return results
