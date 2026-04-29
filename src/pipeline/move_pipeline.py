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

from typing import Any

from src.agents import (
    ConsequenceAgent,
    ContinuationCheckAgent,
    EffectActualizationAgent,
    NarratorAgent,
    QuickConsequenceAgent,
    QuickNarratorAgent,
    TagMatcherAgent,
)
from src.display.console import ConsoleDisplay
from src.engine import calculate_power, resolve_matched_tags, roll_dice
from src.llm_client import LLMClient
from src.logger import log_roll
from src.pipeline._item_manager import ItemManager
from src.pipeline._tag_utils import extract_status_tiers, extract_tag_names
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
        self.effect_agent = EffectActualizationAgent(llm)
        self.consequence_agent = ConsequenceAgent(llm)
        self.quick_consequence_agent = QuickConsequenceAgent(llm)
        self.narrator = NarratorAgent(llm)
        self.quick_narrator = QuickNarratorAgent(llm)
        self.continuation_check = ContinuationCheckAgent(llm)

        # 物品与揭示管理器，处理流水线最后一阶段的叙事生效
        self.item_manager = ItemManager(state, llm)

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
        challenge = ctx.challenge
        resolved_power, resolved_weakness = resolve_matched_tags(
            char, challenge, power_tag_names, weakness_tag_names
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

        effect_note = self.effect_agent.execute(
            intent_note, tag_note, roll, ctx, sub_action=sub_action
        )

        # 仅在未完全成功时生成后果（部分成功和失败都有代价）
        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.consequence_agent.execute(intent_note, effect_note, roll, ctx)

        narrator_note = self.narrator.execute(
            intent_note,
            effect_note,
            roll,
            ctx,
            consequence_note=consequence_note,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=effect_note,
            consequence_note=consequence_note,
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

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.quick_consequence_agent.execute(intent_note, roll, ctx)

        narrator_note = self.quick_narrator.execute(
            intent_note,
            roll,
            ctx,
            consequence_note=consequence_note,
        )

        self.validate_and_apply(narrator_note, ctx)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=None,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def validate_and_apply(self, narrator_note, ctx=None):
        """应用叙事输出中的揭示和物品转移。

        委托给 ItemManager 执行。ItemManager 直接信任叙述者的
        revelation_decisions 和 item_transfers，不经过 LLM 校验。

        Args:
            narrator_note: 叙述者 Agent 的分析便签
            ctx: 当前场景上下文（用于 emergent 物品创建）
        """
        self.item_manager.validate_and_apply(narrator_note, ctx)

    def process_split_actions(self, intent_note, split_actions) -> list:
        """执行复合 action 的拆分流水线。

        当一个意图被意图解析 Agent 拆分为多个子 action（split_actions）时，
        按顺序逐个执行，每步之前检查是否可以继续（continuation_check）。

        流程：
            1. 对每个子 action 运行完整流水线
            2. 执行前检查上一步结果是否阻止继续
            3. 将上一步的掷骰/效果/后果作为上下文传递给下一步

        Args:
            intent_note: 意图解析 Agent 的分析便签
            split_actions: 子 action 列表

        Returns:
            PipelineResult 列表（可能因 blocked 而提前终止）
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
                    return results

            ctx = self.state.make_context(sub.get("fragment", ""))
            result = self.run_single_move_pipeline(intent_note, ctx, sub_action=sub)
            results.append(result)

            # 保存当前步的结果供下一步的继续性检查使用
            prev_roll = result.roll
            prev_effects = (
                result.effect_note.structured.get("effects", []) if result.effect_note else []
            )
            prev_cons = (
                result.consequence_note.structured.get("consequences", [])
                if result.consequence_note
                else []
            )

        return results
