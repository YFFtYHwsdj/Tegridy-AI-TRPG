import json
from typing import Optional
from src.llm_client import LLMClient
from src.models import Character, Challenge, EffectEntry, ConsequenceEntry
from src.engine import calculate_power, roll_dice, apply_status, check_limits, reduce_status, add_story_tag, remove_story_tag, nudge_status
from src.agent_runner import AgentRunner, format_challenge_state, format_statuses, format_story_tags, format_limit_progress
from src.logger import log_roll, log_status_update, log_system

MAX_HISTORY_ENTRIES = 6


def _summarize_last_sub(roll, effects, cons) -> str:
    parts = [f"掷骰结果: {roll.outcome}"]
    if effects:
        parts.append("效果: " + ", ".join(
            e.get("label", e.get("operation", "?")) for e in effects
        ))
    if cons:
        parts.append("后果: " + ", ".join(
            c.get("threat_manifested", "?") for c in cons
        ))
    return "; ".join(parts)


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
        char_story = format_story_tags(self.character.story_tags)

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
            f"  故事标签: {char_story}",
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

    def _run_single_move_pipeline(self, intent_note, context_block, narrative_block,
                                   sub_action=None, player_input=""):
        tag_note = self.runner.run_tag_agent(
            intent_note, context_block, narrative_block,
            self.character, self.challenge, sub_action=sub_action
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

        effect_note = self.runner.run_effect_actualization_agent(
            intent_note, tag_note, roll,
            context_block, narrative_block,
            self.character, self.challenge, sub_action=sub_action
        )

        consequence_note = None
        if roll.outcome in ("partial_success", "failure"):
            consequence_note = self.runner.run_consequence_agent(
                intent_note, effect_note, roll, context_block, narrative_block,
                self.challenge
            )

        narrator_note = self.runner.run_narrator_agent(
            intent_note, effect_note, consequence_note, roll,
            context_block, narrative_block,
            self.character, self.challenge, player_input,
        )

        return tag_note, roll, effect_note, consequence_note, narrator_note

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
        split_actions = intent_note.structured.get("split_actions", [])
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        print(f"  行动类型: {action_type} | 行动: {action_summary}")

        if is_split and isinstance(split_actions, list) and len(split_actions) >= 2:
            return self._process_split_actions(intent_note, split_actions)

        tag_note, roll, effect_note, consequence_note, narrator_note = self._run_single_move_pipeline(
            intent_note, context_block, narrative_block, player_input=player_input
        )

        matched_power = tag_note.structured.get("matched_power_tags", [])
        matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
        power_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_power]
        weakness_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_weakness]

        helping_statuses = tag_note.structured.get("helping_statuses", [])
        hindering_statuses = tag_note.structured.get("hindering_statuses", [])
        help_names = [s["name"] for s in helping_statuses if isinstance(s, dict) and s.get("name")]
        hinder_names = [s["name"] for s in hindering_statuses if isinstance(s, dict) and s.get("name")]

        print(f"  匹配标签: {power_tag_names} | 弱点: {weakness_tag_names}")
        if help_names or hinder_names:
            status_parts = []
            if help_names:
                status_parts.append(f"帮助状态: {help_names}")
            if hinder_names:
                status_parts.append(f"阻碍状态: {hinder_names}")
            print(f"  状态影响: {' | '.join(status_parts)}")
        print(f"  力量: {roll.power} | 掷骰: {roll.dice[0]}+{roll.dice[1]} = {roll.total} → {roll.outcome}")

        effects = effect_note.structured.get("effects", [])
        if effects:
            eff_summary = ", ".join(f"{e.get('label','?')} ({e.get('effect_type','?')} {e.get('tier','?')})" for e in effects)
            print(f"  实际效果: {eff_summary}")
        else:
            print(f"  实际效果: 无")

        if consequence_note:
            cons_list = consequence_note.structured.get("consequences", [])
            if cons_list:
                cons_summary = ", ".join(c.get("threat_manifested", "?") for c in cons_list)
                print(f"  后果: {cons_summary}")

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
                self._handle_limit_break(triggered_limits)

        return narrative

    def _process_split_actions(self, intent_note, split_actions) -> str:
        print(f"  ⚡ 行动拆分为 {len(split_actions)} 个子行动")

        prev_roll = None
        prev_effects = []
        prev_cons = []

        for i, sub in enumerate(split_actions):
            sub["_index"] = i

            if i > 0:
                sub_context = self._build_context_block()
                sub_narrative = self._build_narrative_block()
                check_note = self.runner.run_continuation_check(
                    sub, sub_context, sub_narrative,
                    _summarize_last_sub(prev_roll, prev_effects, prev_cons),
                )
                can_continue = check_note.structured.get("can_continue", True)
                if not can_continue:
                    reason = check_note.structured.get("reason", "")
                    print(f"\n  ⛔ 子行动 [{sub.get('action_summary', '?')}] 无法继续: {reason}")
                    break

            sub_context = self._build_context_block()
            sub_narrative = self._build_narrative_block()

            print(f"\n  --- 子行动 {i + 1}/{len(split_actions)}: {sub.get('action_summary', '?')} ---")

            tag_note, roll, effect_note, consequence_note, narrator_note = self._run_single_move_pipeline(
                intent_note, sub_context, sub_narrative,
                sub_action=sub,
                player_input=sub.get("fragment", ""),
            )

            matched_power = tag_note.structured.get("matched_power_tags", [])
            matched_weakness = tag_note.structured.get("matched_weakness_tags", [])
            power_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_power]
            weakness_tag_names = [t["name"] if isinstance(t, dict) else t for t in matched_weakness]

            helping_statuses = tag_note.structured.get("helping_statuses", [])
            hindering_statuses = tag_note.structured.get("hindering_statuses", [])
            help_names = [s["name"] for s in helping_statuses if isinstance(s, dict) and s.get("name")]
            hinder_names = [s["name"] for s in hindering_statuses if isinstance(s, dict) and s.get("name")]

            print(f"  匹配标签: {power_tag_names} | 弱点: {weakness_tag_names}")
            if help_names or hinder_names:
                status_parts = []
                if help_names:
                    status_parts.append(f"帮助状态: {help_names}")
                if hinder_names:
                    status_parts.append(f"阻碍状态: {hinder_names}")
                print(f"  状态影响: {' | '.join(status_parts)}")
            print(f"  力量: {roll.power} | 掷骰: {roll.dice[0]}+{roll.dice[1]} = {roll.total} → {roll.outcome}")

            effects = effect_note.structured.get("effects", [])
            if effects:
                eff_summary = ", ".join(f"{e.get('label','?')} ({e.get('effect_type','?')} {e.get('tier','?')})" for e in effects)
                print(f"  实际效果: {eff_summary}")
            else:
                print(f"  实际效果: 无")

            if consequence_note:
                cons_list = consequence_note.structured.get("consequences", [])
                if cons_list:
                    cons_summary = ", ".join(c.get("threat_manifested", "?") for c in cons_list)
                    print(f"  后果: {cons_summary}")

            strat = narrator_note.structured.get("scene_update") or narrator_note.reasoning[:60]
            if strat:
                print(f"  叙事策略: {strat}")

            self._apply_results(effect_note, consequence_note, roll.outcome)

            if self.character and self.challenge:
                log_status_update(self.character.name, self.character.statuses)
                log_status_update(self.challenge.name, self.challenge.statuses)

            narrative = narrator_note.structured.get("narrative", "")
            print(f"\n{narrative}")
            self._append_narrative(narrative)

            if self.character and self.character.is_incapacitated():
                print(f"\n  💀 角色已丧失行动能力，剩余子行动中断")
                break

            prev_roll = roll
            prev_effects = effects
            prev_cons = consequence_note.structured.get("consequences", []) if consequence_note else []

        self._print_status()

        if self.challenge is not None:
            triggered_limits = check_limits(self.challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)

        return ""

    def _handle_limit_break(self, triggered_limits):
        challenge = self.challenge
        assert challenge is not None
        limit_names = [l.name for l in triggered_limits]
        print(f"\n  ⚡ 极限突破: {', '.join(limit_names)}!")

        fresh_context = self._build_context_block()
        fresh_narrative = self._build_narrative_block()

        limit_break_note = self.runner.run_limit_break_agent(
            limit_names, challenge,
            fresh_context, fresh_narrative,
        )
        break_narrative = limit_break_note.structured.get("narrative", "")
        if break_narrative:
            print("\n" + "─" * 50)
            print(f"\n{break_narrative}")
            self._append_narrative(break_narrative)

        transformation = limit_break_note.structured.get("challenge_transformation", "")
        if transformation:
            challenge.transformation = transformation
            print(f"\n  [场景转变] {transformation}")

        scene_direction = limit_break_note.structured.get("scene_direction", "")
        if scene_direction:
            print(f"  [走向] {scene_direction}")

        challenge.mark_limits_broken(limit_names)

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
                operation = eff.get("operation", "inflict_status")
                target = self._resolve_target(eff.get("target", ""))
                if target is None:
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
                        log_system(f"[效果应用] {eff_type}: {label}-{tier} → {target.name if hasattr(target, 'name') else target}")

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
                        log_system(f"[效果应用] {eff_type}: 添加故事标签 [{name}] → {target.name if hasattr(target, 'name') else target}")

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
                    log_system(f"[效果应用错误] {eff_type} ({operation}): {e}")

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
        print(f"  故事标签: {format_story_tags(self.character.story_tags)}")

        print(f"\n  [挑战: {self.challenge.name}]")
        for limit in self.challenge.limits:
            matching = self.challenge.get_matching_statuses(limit.name)
            current = max((s.current_tier for s in matching), default=0)
            print(f"  {format_limit_progress(limit, current)}")
        print(f"  故事标签: {format_story_tags(self.challenge.story_tags)}")
        print(f"  状态: {format_statuses(self.challenge.statuses)}")
