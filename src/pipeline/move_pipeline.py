from __future__ import annotations

from typing import Any
from src.llm_client import LLMClient
from src.state.game_state import GameState
from src.engine import calculate_power, roll_dice
from src.logger import log_roll
from src.pipeline._tag_utils import extract_tag_names, extract_status_tiers
from src.pipeline.pipeline_result import PipelineResult
from src.display.console import ConsoleDisplay
from src.agents import (
    TagMatcherAgent, EffectActualizationAgent, ConsequenceAgent,
    QuickConsequenceAgent, NarratorAgent, QuickNarratorAgent,
    ContinuationCheckAgent,
)


def _summarize_last_sub(roll, effects, cons) -> str:
    if roll is None:
        return "（上一步无有效掷骰）"
    parts = [f"掷骰结果: {roll.outcome}"]
    if effects:
        parts.append("效果: " + ", ".join(
            e.get("label", e.get("operation", "?")) for e in effects
        ))
    if cons:
        parts.append("后果: " + ", ".join(
            c.get("threat_manifested", "?") for c in cons
        ))
    return "; ".join(parts) if parts else "（无效果信息）"


class MovePipeline:
    def __init__(self, llm: LLMClient, state: GameState, display: ConsoleDisplay):
        self.state = state
        self.display = display
        self.tag_agent = TagMatcherAgent(llm)
        self.effect_agent = EffectActualizationAgent(llm)
        self.consequence_agent = ConsequenceAgent(llm)
        self.quick_consequence_agent = QuickConsequenceAgent(llm)
        self.narrator = NarratorAgent(llm)
        self.quick_narrator = QuickNarratorAgent(llm)
        self.continuation_check = ContinuationCheckAgent(llm)

    def _run_tag_and_roll(self, intent_note, ctx, sub_action=None):
        tag_note = self.tag_agent.execute(intent_note, ctx, sub_action=sub_action)

        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = extract_tag_names(matched_power)
        weakness_tag_names = extract_tag_names(matched_weakness)

        best_status_tier, worst_status_tier = extract_status_tiers(tag_note)

        power = calculate_power(
            power_tag_names, weakness_tag_names,
            best_status_tier=best_status_tier,
            worst_status_tier=worst_status_tier,
        )
        roll = roll_dice(power)

        log_roll(power, roll.dice, roll.total, roll.outcome, power_tag_names, weakness_tag_names)

        return tag_note, roll

    def run_single_move_pipeline(self, intent_note, ctx, sub_action=None) -> PipelineResult:
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx, sub_action)

        effect_note = self.effect_agent.execute(
            intent_note, tag_note, roll, ctx, sub_action=sub_action
        )

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.consequence_agent.execute(
                intent_note, effect_note, roll, ctx
            )

        narrator_note = self.narrator.execute(
            intent_note, effect_note, roll, ctx,
            consequence_note=consequence_note,
        )

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=effect_note,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def run_quick_pipeline(self, intent_note, ctx) -> PipelineResult:
        tag_note, roll = self._run_tag_and_roll(intent_note, ctx)

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.quick_consequence_agent.execute(
                intent_note, roll, ctx
            )

        narrator_note = self.quick_narrator.execute(
            intent_note, roll, ctx,
            consequence_note=consequence_note,
        )

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=None,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def process_split_actions(self, intent_note, split_actions) -> list:
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

            self.display.print_split_sub_header(i + 1, len(split_actions), sub.get("action_summary", "?"))

            if i > 0:
                ctx = self.state.make_context()
                check_note = self.continuation_check.execute(
                    sub, ctx,
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

            prev_roll = result.roll
            prev_effects = result.effect_note.structured.get("effects", []) if result.effect_note else []
            prev_cons = result.consequence_note.structured.get("consequences", []) if result.consequence_note else []

        return results
