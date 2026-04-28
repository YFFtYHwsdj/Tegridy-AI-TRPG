from src.llm_client import LLMClient
from src.models import Character, Challenge
from src.engine import check_limits
from src.formatter import format_challenge_state
from src.agents import (
    RhythmAgent, MoveGatekeeperAgent, IntentAgent,
    LiteNarratorAgent, LimitBreakAgent, ResolutionModeAgent,
)
from src.logger import log_status_update, log_system
from src.state.game_state import GameState
from src.effects.applicator import EffectApplicator
from src.pipeline.move_pipeline import MovePipeline
from src.display.console import ConsoleDisplay


class GameLoop:
    def __init__(self, llm: LLMClient):
        self.llm = llm
        self.state = GameState()
        self.display = ConsoleDisplay()
        self.pipeline = MovePipeline(llm, self.state, self.display)

        self.rhythm_agent = RhythmAgent(llm)
        self.gatekeeper = MoveGatekeeperAgent(llm)
        self.intent_agent = IntentAgent(llm)
        self.lite_narrator = LiteNarratorAgent(llm)
        self.limit_break_agent = LimitBreakAgent(llm)
        self.resolution_agent = ResolutionModeAgent(llm)

    def setup(self, character: Character, challenge: Challenge, scene_desc: str):
        self.state.setup(character, challenge, scene_desc)

        challenge = self.state.scene.primary_challenge()

        print("\n" + "═" * 50)
        print("       :OTHERSCAPE · AI 主持 · 单场景 Demo")
        print("═" * 50)

        rhythm = self.rhythm_agent.execute(scene_desc)
        narrative = rhythm.structured.get("scene_establishment", "")
        print(f"\n{narrative}")
        self.state.append_narrative(narrative)

        print(f"\n{'─' * 50}")
        print("挑战状态:")
        print(format_challenge_state(challenge))
        print("─" * 50)

        spotlight = rhythm.structured.get("spotlight_handoff", "你要做什么？")
        print(f"\n{spotlight}")

    def process_action(self, player_input: str) -> str:
        if player_input.strip().lower() in ("quit", "exit", "q"):
            return "QUIT"

        print("\n" + "─" * 50)

        ctx = self.state.make_context(player_input)

        gatekeeper_note = self.gatekeeper.execute(player_input, ctx)
        is_move = gatekeeper_note.structured.get("is_move", True)

        if not is_move:
            return self._handle_non_move(player_input, ctx, gatekeeper_note)

        print("  [管道开始 · 掷骰模式]")

        intent_note = self.intent_agent.execute(player_input, ctx)
        is_split = intent_note.structured.get("is_split_action", False)
        split_actions = intent_note.structured.get("split_actions", [])
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        print(f"  行动类型: {action_type} | 行动: {action_summary}")

        if is_split and isinstance(split_actions, list) and len(split_actions) >= 2:
            return self._process_split_moves(intent_note, split_actions)

        resolution_note = self.resolution_agent.execute(intent_note, ctx)
        resolution_mode = resolution_note.structured.get("resolution_mode", "detailed")
        resolution_reason = resolution_note.structured.get("reason", "")
        print(f"  结算模式: {resolution_mode} ({resolution_reason})")

        if resolution_mode == "quick":
            return self._process_move(intent_note, ctx, quick=True)
        return self._process_move(intent_note, ctx, quick=False)

    def _handle_non_move(self, player_input, ctx, gatekeeper_note):
        rationale = gatekeeper_note.structured.get("rationale", "")
        print(f"  [叙事模式] {rationale}")

        narrator_note = self.lite_narrator.execute(
            player_input, ctx, gatekeeper_note.reasoning
        )
        print("─" * 50)
        narrative = narrator_note.structured.get("narrative", "")
        print(f"\n{narrative}")
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)
        return narrative

    def _process_move(self, intent_note, ctx, quick=False):
        if quick:
            result = self.pipeline.run_quick_pipeline(intent_note, ctx)
        else:
            result = self.pipeline.run_single_move_pipeline(intent_note, ctx)

        self.display.print_tag_and_roll(result.tag_note, result.roll)
        self.display.print_effects_or_quick_note(result.effect_note, quick=quick)

        self.display.print_consequences(result.consequence_note)
        self.display.print_strategy(result.narrator_note)

        challenge = self.state.scene.primary_challenge()
        effect_errors = EffectApplicator.apply_results(
            result.effect_note, result.consequence_note,
            self.state.character, challenge,
        )
        if effect_errors:
            log_system(f"[效果应用警告] 共 {len(effect_errors)} 个效果应用失败")

        self._finalize_move()

        print("─" * 50)

        narrative = result.narrator_note.structured.get("narrative", "")
        print(f"\n{narrative}")
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)

        if challenge is not None:
            triggered_limits = check_limits(challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)

        return narrative

    def _process_split_moves(self, intent_note, split_actions) -> str:
        results = self.pipeline.process_split_actions(
            intent_note, split_actions
        )

        narratives = []
        for result in results:
            self.display.print_tag_and_roll(result.tag_note, result.roll)
            self.display.print_effects(result.effect_note)
            self.display.print_consequences(result.consequence_note)
            self.display.print_strategy(result.narrator_note)

            challenge = self.state.scene.primary_challenge()
            effect_errors = EffectApplicator.apply_results(
                result.effect_note, result.consequence_note,
                self.state.character, challenge,
            )
            if effect_errors:
                log_system(f"[效果应用警告] 共 {len(effect_errors)} 个效果应用失败")

            self._finalize_move()

            print("─" * 50)

            narrative = result.narrator_note.structured.get("narrative", "")
            print(f"\n{narrative}")
            self.state.append_narrative(narrative)
            narratives.append(narrative)

            if self.state.character and self.state.character.is_incapacitated():
                self.display.print_incapacitated_break()
                break

        self.display.print_status(self.state)

        challenge = self.state.scene.primary_challenge()
        if challenge is not None:
            triggered_limits = check_limits(challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)

        return "\n".join(narratives)

    def _finalize_move(self):
        character = self.state.character
        challenge = self.state.scene.primary_challenge()
        if character and challenge:
            log_status_update(character.name, character.statuses)
            log_status_update(challenge.name, challenge.statuses)

    def _handle_limit_break(self, triggered_limits):
        challenge = self.state.scene.primary_challenge()
        assert challenge is not None
        limit_names = [l.name for l in triggered_limits]
        print(f"\n  ⚡ 极限突破: {', '.join(limit_names)}!")

        ctx = self.state.make_context()

        limit_break_note = self.limit_break_agent.execute(
            limit_names, challenge, ctx,
        )
        break_narrative = limit_break_note.structured.get("narrative", "")
        if break_narrative:
            print("\n" + "─" * 50)
            print(f"\n{break_narrative}")
            self.state.append_narrative(break_narrative)

        transformation = limit_break_note.structured.get("challenge_transformation", "")
        if transformation:
            challenge.transformation = transformation
            print(f"\n  [场景转变] {transformation}")

        scene_direction = limit_break_note.structured.get("scene_direction", "")
        if scene_direction:
            print(f"  [走向] {scene_direction}")

        challenge.mark_limits_broken(limit_names)
        log_status_update(challenge.name, challenge.statuses)
