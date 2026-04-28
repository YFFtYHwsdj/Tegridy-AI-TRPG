from __future__ import annotations

from typing import Any
from src.llm_client import LLMClient
from src.state.game_state import GameState
from src.engine import calculate_power, roll_dice
from src.logger import log_roll, log_system
from src.pipeline._tag_utils import extract_tag_names, extract_status_tiers
from src.pipeline.pipeline_result import PipelineResult
from src.display.console import ConsoleDisplay
from src.agents import (
    TagMatcherAgent, EffectActualizationAgent, ConsequenceAgent,
    QuickConsequenceAgent, NarratorAgent, QuickNarratorAgent,
    ContinuationCheckAgent, ValidatorAgent,
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
        self.llm = llm
        self.state = state
        self.display = display
        self.tag_agent = TagMatcherAgent(llm)
        self.effect_agent = EffectActualizationAgent(llm)
        self.consequence_agent = ConsequenceAgent(llm)
        self.quick_consequence_agent = QuickConsequenceAgent(llm)
        self.narrator = NarratorAgent(llm)
        self.quick_narrator = QuickNarratorAgent(llm)
        self.continuation_check = ContinuationCheckAgent(llm)
        self.validator = ValidatorAgent(llm)

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

        self.validate_and_apply(narrator_note)

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

        self.validate_and_apply(narrator_note)

        return PipelineResult(
            tag_note=tag_note,
            roll=roll,
            effect_note=None,
            consequence_note=consequence_note,
            narrator_note=narrator_note,
        )

    def validate_and_apply(self, narrator_note):
        scene = self.state.scene
        hidden_clues = scene.clues_hidden
        hidden_items = {
            iid: item
            for npc in scene.npcs.values()
            for iid, item in npc.items_hidden.items()
        }
        scene_hidden = scene.scene_items_hidden

        valid_note = self.validator.execute(
            narrator_note,
            hidden_clues=hidden_clues,
            hidden_items=hidden_items,
            visible_clues=scene.clues_visible,
            visible_items=self.state.character.items_visible if self.state.character else {},
            scene_items_hidden=scene_hidden,
            scene_items_visible=scene.scene_items_visible,
            npcs=scene.npcs,
        )

        if valid_note.structured.get("verdict") == "reject":
            return

        self._apply_revelations(narrator_note)
        self._apply_item_transfers(narrator_note)

    def _apply_revelations(self, narrator_note):
        scene = self.state.scene
        decisions = narrator_note.structured.get("revelation_decisions", {})

        for clue_id in decisions.get("reveal_clue_ids", []):
            if clue_id in scene.clues_hidden:
                clue = scene.clues_hidden.pop(clue_id)
                scene.clues_visible[clue_id] = clue

        for item_id in decisions.get("reveal_item_ids", []):
            found = False
            if item_id in scene.scene_items_hidden:
                item = scene.scene_items_hidden.pop(item_id)
                scene.scene_items_visible[item_id] = item
                found = True
            else:
                for npc in scene.npcs.values():
                    if item_id in npc.items_hidden:
                        item = npc.items_hidden.pop(item_id)
                        npc.items_visible[item_id] = item
                        found = True
                        break
            if not found:
                log_system(f"[揭示执行] 未找到物品 '{item_id}'")

    def _apply_item_transfers(self, narrator_note):
        scene = self.state.scene
        transfers = narrator_note.structured.get("item_transfers", [])
        location_updates = narrator_note.structured.get("location_text_updates", [])
        loc_map = {u["item_id"]: u["new_location"] for u in location_updates if isinstance(u, dict)}

        for t in transfers:
            if not isinstance(t, dict):
                continue
            item_id = t.get("item_id") or t.get("item", "")
            from_loc = t.get("from", "")
            to_loc = t.get("to", "")
            if not item_id or not from_loc or not to_loc:
                continue

            item = self._pop_item(item_id, from_loc)
            if item is None:
                created = self._create_emergent_item(item_id, narrator_note)
                if not created:
                    log_system(f"[物品转移] 未找到且无法创建 '{item_id}' (from={from_loc})")
                    continue
                item = created
                log_system(f"[emergent物品] 转移时自动创建 '{item_id}'")

            if item_id in loc_map:
                item.location = loc_map[item_id]

            self._insert_item(item_id, item, to_loc)

    def _create_emergent_item(self, item_name: str, narrator_note):
        from src.agents.item_creator import ItemCreatorAgent
        if not hasattr(self, 'item_creator'):
            self.item_creator = ItemCreatorAgent(self.llm)

        narrative = narrator_note.structured.get("narrative", "")
        creator_note = self.item_creator.execute(item_name, narrative)
        item_data = creator_note.structured
        if not item_data:
            return None

        from src.models import GameItem, Tag
        tags = []
        for t in item_data.get("tags", []):
            if isinstance(t, dict):
                tags.append(Tag(
                    name=t.get("name", ""),
                    tag_type=t.get("tag_type", "power"),
                    description=t.get("description", ""),
                ))
            elif isinstance(t, str):
                tags.append(Tag(name=t, tag_type="power"))

        weakness = None
        w = item_data.get("weakness")
        if w and isinstance(w, dict):
            weakness = Tag(
                name=w.get("name", ""),
                tag_type="weakness",
                description=w.get("description", ""),
            )

        item_id = item_data.get("item_id") or item_name
        return GameItem(
            item_id=item_id,
            name=item_name,
            description=item_data.get("description", ""),
            tags=tags,
            weakness=weakness,
            location=item_data.get("location", ""),
        )

    def _pop_item(self, item_id: str, location: str):
        scene = self.state.scene
        if location == "scene":
            for d in (scene.scene_items_visible, scene.scene_items_hidden):
                if item_id in d:
                    return d.pop(item_id)
        elif location == "character":
            char = self.state.character
            if char:
                for d in (char.items_visible, char.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                for d in (npc.items_visible, npc.items_hidden):
                    if item_id in d:
                        return d.pop(item_id)
        return None

    def _insert_item(self, item_id: str, item, location: str):
        scene = self.state.scene
        if location == "scene":
            scene.scene_items_visible[item_id] = item
        elif location == "character":
            if self.state.character:
                self.state.character.items_visible[item_id] = item
        elif location.startswith("npc."):
            npc_id = location[4:]
            npc = scene.npcs.get(npc_id)
            if npc:
                npc.items_visible[item_id] = item

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
