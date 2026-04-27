import json
from typing import Optional
from src.llm_client import LLMClient
from src.models import Character, Challenge, EffectEntry, ConsequenceEntry
from src.engine import calculate_power, roll_dice, apply_status, check_limits
from src.agent_runner import AgentRunner, format_challenge_state, format_statuses, format_limit_progress
from src.logger import log_roll, log_status_update, log_system

MAX_HISTORY_ENTRIES = 6


class GameLoop:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.runner = AgentRunner(llm)
        self.character: Optional[Character] = None
        self.challenge: Optional[Challenge] = None
        self.scene_context: str = ""
        self.narrative_history: list[str] = []

    def setup(self, character: Character, challenge: Challenge, scene_desc: str):
        self.character = character
        self.challenge = challenge
        self.scene_context = scene_desc
        self.narrative_history = []

        print("\n" + "═" * 50)
        print("       :OTHERSCAPE · AI 主持 · 单场景 Demo")
        print("═" * 50)

        rhythm = self.runner.run_rhythm_agent(scene_desc)
        narrative = rhythm.structured.get("scene_establishment", "")
        print(f"\n{narrative}")
        self.narrative_history.append(narrative)

        print(f"\n{'─' * 50}")
        print("挑战状态:")
        print(format_challenge_state(self.challenge))
        print("─" * 50)

        spotlight = rhythm.structured.get("spotlight_handoff", "你要做什么？")
        print(f"\n{spotlight}")

    def _build_context_block(self) -> str:
        if self.character is None or self.challenge is None:
            return ""

        char_tags = ", ".join(t.name for t in self.character.power_tags)
        char_weak = ", ".join(t.name for t in self.character.weakness_tags)
        char_status = format_statuses(self.character.statuses)

        limits = ""
        for limit in self.challenge.limits:
            matching = self.challenge.get_matching_statuses(limit.name)
            current = max((s.current_tier for s in matching), default=0)
            limits += f"  {format_limit_progress(limit, current)}, "
        limits = limits.rstrip(", ")

        lines = [
            f"场景: {self.scene_context}",
            f"角色: {self.character.name} - {self.character.description}",
            f"  力量标签: {char_tags}",
            f"  弱点标签: {char_weak}",
            f"  状态: {char_status}",
            f"挑战: {self.challenge.name} - {self.challenge.description}",
            f"  极限进度: {limits}",
        ]
        if self.challenge.broken_limits:
            lines.append(f"  已突破极限: {', '.join(self.challenge.broken_limits)}")
        if self.challenge.transformation:
            lines.append(f"  挑战转变: {self.challenge.transformation}")
        return "\n".join(lines)

    def _build_narrative_block(self) -> str:
        if not self.narrative_history:
            return "（无历史）"
        recent = self.narrative_history[-MAX_HISTORY_ENTRIES:]
        lines = []
        for i, entry in enumerate(recent, 1):
            lines.append(f"[{i}] {entry}")
        return "\n".join(lines)

    def _append_narrative(self, entry: str):
        self.narrative_history.append(entry)
        if len(self.narrative_history) > MAX_HISTORY_ENTRIES + 2:
            self.narrative_history = self.narrative_history[-(MAX_HISTORY_ENTRIES + 2):]

    def process_action(self, player_input: str) -> str:
        if player_input.strip().lower() in ("quit", "exit", "q"):
            return "QUIT"

        print("\n" + "─" * 50)

        narrative_block = self._build_narrative_block()
        context_block = self._build_context_block()

        gatekeeper_note = self.runner.run_move_gatekeeper(
            player_input, context_block, narrative_block,
            self.character, self.challenge
        )
        is_move = gatekeeper_note.structured.get("is_move", True)

        if not is_move:
            rationale = gatekeeper_note.structured.get("rationale", "")
            print(f"  [叙事模式] {rationale}")

            narrator_note = self.runner.run_lite_narrator(
                player_input, context_block, narrative_block,
                self.character, self.challenge,
                gatekeeper_note.reasoning
            )
            print("─" * 50)
            narrative = narrator_note.structured.get("narrative", "")
            print(f"\n{narrative}")
            self._append_narrative(narrative)

            self._print_status()
            return narrative

        print("  [管道开始 · 掷骰模式]")

        intent_note = self.runner.run_intent_agent(
            player_input, context_block, narrative_block
        )
        is_split = intent_note.structured.get("is_split_action", False)
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        print(f"  行动类型: {action_type} | 行动: {action_summary}")
        if is_split:
            print(f"  ⚠ 检测到行动拆分，当前仅处理第一个子行动")

        tag_note = self.runner.run_tag_agent(
            intent_note, context_block, narrative_block,
            self.character, self.challenge
        )

        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_power]
        weakness_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_weakness]

        helping_statuses = tag_note.structured.get("helping_statuses", [])
        hindering_statuses = tag_note.structured.get("hindering_statuses", [])
        best_status_tier = max(
            (s["tier"] for s in helping_statuses if isinstance(s, dict) and s.get("tier")), default=0
        )
        worst_status_tier = max(
            (s["tier"] for s in hindering_statuses if isinstance(s, dict) and s.get("tier")), default=0
        )

        power = calculate_power(
            power_tag_names, weakness_tag_names,
            best_status_tier=best_status_tier,
            worst_status_tier=worst_status_tier,
        )
        roll = roll_dice(power)

        log_roll(power, roll.dice, roll.total, roll.outcome, power_tag_names, weakness_tag_names)

        print(f"  匹配标签: {power_tag_names} | 弱点: {weakness_tag_names}")
        print(f"  力量: {power} | 掷骰: {roll.dice[0]}+{roll.dice[1]} = {roll.total} → {roll.outcome}")

        suggestion_note = self.runner.run_effect_suggestion_agent(
            intent_note, tag_note, roll, context_block, narrative_block,
            self.challenge
        )
        suggested = suggestion_note.structured.get("suggested_effect_types", [])
        if suggested:
            print(f"  建议效果: {', '.join(suggested)}")

        effect_note = self.runner.run_effect_actualization_agent(
            intent_note, tag_note, suggestion_note, roll,
            context_block, narrative_block,
            self.character, self.challenge
        )
        effects = effect_note.structured.get("effects", [])
        if effects:
            eff_summary = ", ".join(f"{e.get('label','?')} ({e.get('effect_type','?')} {e.get('tier','?')})" for e in effects)
            print(f"  实际效果: {eff_summary}")
        else:
            print(f"  实际效果: 无")

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.runner.run_consequence_agent(
                intent_note, effect_note, roll, context_block, narrative_block,
                self.challenge
            )
            cons_list = consequence_note.structured.get("consequences", [])
            if cons_list:
                cons_summary = ", ".join(c.get("threat_manifested", "?") for c in cons_list)
                print(f"  后果: {cons_summary}")

        narrator_note = self.runner.run_narrator_agent(
            intent_note, effect_note, consequence_note, roll,
            context_block, narrative_block,
            self.character, self.challenge, player_input
        )
        strat = narrator_note.structured.get("scene_update") or narrator_note.reasoning[:60]
        if strat:
            print(f"  叙事策略: {strat}")

        self._apply_results(effect_note, consequence_note, roll.outcome)

        if self.character and self.challenge:
            log_status_update(self.character.name, self.character.statuses)
            log_status_update(self.challenge.name, self.challenge.statuses)

        print("─" * 50)

        narrative = narrator_note.structured.get("narrative", "")
        print(f"\n{narrative}")
        self._append_narrative(narrative)

        self._print_status()

        if self.challenge is not None:
            triggered_limits = check_limits(self.challenge)
            if triggered_limits:
                limit_names = [l.name for l in triggered_limits]
                print(f"\n  ⚡ 极限突破: {', '.join(limit_names)}!")

                fresh_context = self._build_context_block()
                fresh_narrative = self._build_narrative_block()

                limit_break_note = self.runner.run_limit_break_agent(
                    limit_names, self.challenge,
                    fresh_context, fresh_narrative,
                )
                break_narrative = limit_break_note.structured.get("narrative", "")
                if break_narrative:
                    print("\n" + "─" * 50)
                    print(f"\n{break_narrative}")
                    self._append_narrative(break_narrative)

                transformation = limit_break_note.structured.get("challenge_transformation", "")
                if transformation:
                    self.challenge.transformation = transformation
                    print(f"\n  [场景转变] {transformation}")

                scene_direction = limit_break_note.structured.get("scene_direction", "")
                if scene_direction:
                    print(f"  [走向] {scene_direction}")

                self.challenge.mark_limits_broken(limit_names)

        return narrative

    def _resolve_target(self, target_name: str):
        if not target_name or self.character is None or self.challenge is None:
            return None
        name_lower = target_name.lower().strip()

        if name_lower == "挑战":
            return self.challenge
        if name_lower in ("自身", "self"):
            return self.character

        char_name_lower = self.character.name.lower()
        chal_name_lower = self.challenge.name.lower()

        if name_lower in char_name_lower or char_name_lower in name_lower:
            return self.character
        if name_lower in chal_name_lower or chal_name_lower in name_lower:
            return self.challenge

        log_system(f"[目标解析] 无法匹配效果目标 '{target_name}'，已忽略")
        return None

    def _apply_results(self, effect_note, consequence_note, outcome):
        if self.character is None or self.challenge is None:
            return

        def _apply_effect_list(eff_list):
            for eff in eff_list:
                label = eff.get("label", "")
                tier = eff.get("tier", 0)
                if not label or tier <= 0:
                    continue
                target = self._resolve_target(eff.get("target", ""))
                if target is None:
                    continue
                limit_category = eff.get("limit_category", "")
                apply_status(target, label, tier, limit_category)

        effects = effect_note.structured.get("effects", [])
        _apply_effect_list(effects)

        if consequence_note:
            consequences = consequence_note.structured.get("consequences", [])
            for cons in consequences:
                _apply_effect_list(cons.get("effects", []))

    def _print_status(self):
        if self.character is None or self.challenge is None:
            return
        print(f"\n  [角色: {self.character.name}]")
        print(f"  状态: {format_statuses(self.character.statuses)}")

        print(f"\n  [挑战: {self.challenge.name}]")
        for limit in self.challenge.limits:
            matching = self.challenge.get_matching_statuses(limit.name)
            current = max((s.current_tier for s in matching), default=0)
            print(f"  {format_limit_progress(limit, current)}")
