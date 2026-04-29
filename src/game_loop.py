"""游戏主循环 —— 玩家与 AI Agent 流水线的交互桥梁。

本模块的 GameLoop 类是系统的"前台控制器"，负责：
    1. 接收玩家自然语言输入
    2. 判断是否为系统命令（/quit, /debug, /help）
    3. 区分 Move（需要掷骰的规则行动）和非 Move（纯叙事互动）
    4. 根据结算模式选择流水线类型（标准/快速/拆分）
    5. 驱动效果执行、状态更新、极限突破处理
    6. 将最终叙事输出给玩家

核心流程：
    玩家输入 → Move 判定 → 意图解析 → 结算模式选择
    → 流水线执行 → 效果落地 → 叙事输出 → 极限检查
"""

from src.agents import (
    IntentAgent,
    LimitBreakAgent,
    LiteNarratorAgent,
    MoveGatekeeperAgent,
    ResolutionModeAgent,
    RhythmAgent,
)
from src.display.console import ConsoleDisplay
from src.effects.applicator import EffectApplicator
from src.engine import check_limits
from src.formatter import format_challenge_state
from src.llm_client import LLMClient
from src.logger import log_status_update, log_system
from src.models import Character
from src.pipeline.move_pipeline import MovePipeline
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class GameLoop:
    """游戏主循环控制器。

    初始化所有 Agent 实例（节奏、守门人、意图解析、结算模式、
    极限突破、轻量叙述者）和 MovePipeline。

    核心入口：
        setup(): 初始化场景，输出开场叙事
        process_action(): 处理单次玩家行动（命令/Move/非Move）
    """

    def __init__(self, llm: LLMClient, debug_mode: bool = False):
        self.llm = llm
        self.state = GameState()
        self.display = ConsoleDisplay(debug_mode=debug_mode)
        self.pipeline = MovePipeline(llm, self.state, self.display)

        # 创建各类 Agent 实例
        self.rhythm_agent = RhythmAgent(llm)
        self.gatekeeper = MoveGatekeeperAgent(llm)
        self.intent_agent = IntentAgent(llm)
        self.lite_narrator = LiteNarratorAgent(llm)
        self.limit_break_agent = LimitBreakAgent(llm)
        self.resolution_agent = ResolutionModeAgent(llm)

    def toggle_debug(self):
        """切换调试模式开关。

        Returns:
            切换后的调试模式状态
        """
        self.display.debug_mode = not self.display.debug_mode
        return self.display.debug_mode

    def _handle_command(self, raw: str) -> str:
        """处理系统命令。

        支持的命令：
            /quit, /exit — 退出游戏
            /debug — 切换调试模式
            /help — 显示帮助

        Args:
            raw: 原始输入文本

        Returns:
            "QUIT" 表示退出，"" 表示继续
        """
        cmd = raw.lower().split()[0]
        if cmd in ("/quit", "/exit"):
            return "QUIT"
        if cmd == "/debug":
            state = self.toggle_debug()
            label = "ON" if state else "OFF"
            print(f"  [系统] 调试模式已切换为: {label}")
            return ""
        if cmd == "/help":
            print("  [命令列表]")
            print("    /quit, /exit  — 退出游戏")
            print("    /debug        — 切换调试显示模式")
            print("    /help         — 显示此帮助")
            return ""
        print(f"  [系统] 未知命令: {cmd}。输入 /help 查看可用命令。")
        return ""

    def setup(self, character: Character, scene: SceneState):
        """初始化游戏场景。

        设置角色和场景，调用节奏 Agent 输出场景建立叙事和角色聚焦，
        显示挑战状态。

        Args:
            character: 玩家角色
            scene: 初始场景
        """
        self.state.setup(character, scene)

        challenge = self.state.scene.primary_challenge()

        print("\n" + "═" * 50)
        print("       :OTHERSCAPE · AI 主持 · 单场景 Demo")
        print("═" * 50)

        rhythm = self.rhythm_agent.execute(scene.scene_description)
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
        """处理单次玩家行动。

        入口方法，负责三层路由：
        1. 命令处理（以 / 开头）
        2. Move 判定（守门人 Agent 判断是否需要规则引擎）
        3. 非 Move 叙事（轻量叙述者 Agent 直接处理）

        Move 流程中还包含结算模式判定和复合 action 拆分。

        Args:
            player_input: 玩家原始输入

        Returns:
            叙事文本；"QUIT" 表示退出
        """
        raw = player_input.strip()

        # 第1层: 系统命令
        if raw.startswith("/"):
            return self._handle_command(raw)

        if not raw:
            return ""

        print("\n" + "─" * 50)

        ctx = self.state.make_context(raw)

        # 第2层: Move 判定
        gatekeeper_note = self.gatekeeper.execute(raw, ctx)
        is_move = gatekeeper_note.structured.get("is_move", True)

        if not is_move:
            return self._handle_non_move(raw, ctx, gatekeeper_note)

        print("  [管道开始 · 掷骰模式]")

        # 第3层: 意图解析 + 结算模式判定
        intent_note = self.intent_agent.execute(raw, ctx)
        is_split = intent_note.structured.get("is_split_action", False)
        split_actions = intent_note.structured.get("split_actions", [])
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        print(f"  行动类型: {action_type} | 行动: {action_summary}")

        # 复合 action（如"先撬门，再偷文件"）→ 拆分流水线
        if is_split and isinstance(split_actions, list) and len(split_actions) >= 2:
            return self._process_split_moves(intent_note, split_actions)

        # 结算模式判定（detailed vs quick）
        resolution_note = self.resolution_agent.execute(intent_note, ctx)
        resolution_mode = resolution_note.structured.get("resolution_mode", "detailed")
        print(f"  结算模式: {resolution_mode}")

        if resolution_mode == "quick":
            return self._process_move(intent_note, ctx, quick=True)
        return self._process_move(intent_note, ctx, quick=False)

    def _handle_non_move(self, player_input, ctx, gatekeeper_note):
        """处理非 Move 行动（纯叙事互动）。

        不触发掷骰和效果推演，由轻量叙述者 Agent 直接生成叙事回复。
        但仍会执行 validate_and_apply 以处理可能的揭示和物品转移。

        Args:
            player_input: 玩家输入
            ctx: Agent 上下文
            gatekeeper_note: 守门人 Agent 的判定便签

        Returns:
            叙事文本
        """
        print("  [叙事模式]")

        narrator_note = self.lite_narrator.execute(player_input, ctx, "")
        print("─" * 50)

        self.pipeline.validate_and_apply(narrator_note, ctx)

        narrative = narrator_note.structured.get("narrative", "")
        print(f"\n{narrative}")
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)
        return narrative

    def _process_move(self, intent_note, ctx, quick=False):
        """处理 Move 行动（需要掷骰的规则行动）。

        根据 quick 参数选择标准或快速流水线执行。

        Args:
            intent_note: 意图解析便签
            ctx: Agent 上下文
            quick: 是否使用快速流水线

        Returns:
            叙事文本
        """
        if quick:
            result = self.pipeline.run_quick_pipeline(intent_note, ctx)
        else:
            result = self.pipeline.run_single_move_pipeline(intent_note, ctx)

        # 显示流水线各阶段信息
        self.display.print_tag_and_roll(result.tag_note, result.roll)
        self.display.print_effects_or_quick_note(result.effect_note, quick=quick)
        self.display.print_consequences(result.consequence_note)
        self.display.print_strategy(result.narrator_note)

        # 将 Agent 产出的效果应用到游戏状态
        challenge = self.state.scene.primary_challenge()
        effect_errors = EffectApplicator.apply_results(
            result.effect_note,
            result.consequence_note,
            self.state.character,
            challenge,
        )
        if effect_errors:
            log_system(f"[效果应用警告] 共 {len(effect_errors)} 个效果应用失败")

        self._finalize_move()

        print("─" * 50)

        narrative = result.narrator_note.structured.get("narrative", "")
        print(f"\n{narrative}")
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)

        # 检查极限是否触发
        if challenge is not None:
            triggered_limits = check_limits(challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)

        return narrative

    def _process_split_moves(self, intent_note, split_actions) -> str:
        """处理复合 action 的拆分流水线。

        对多个子 action 逐个执行流水线，每步检查是否被阻止继续。
        如果角色在过程中失去行动能力，中断后续步骤。

        Args:
            intent_note: 意图解析便签
            split_actions: 子 action 列表

        Returns:
            所有子 action 的叙事拼接
        """
        results = self.pipeline.process_split_actions(intent_note, split_actions)

        narratives = []
        for result in results:
            self.display.print_tag_and_roll(result.tag_note, result.roll)
            self.display.print_effects(result.effect_note)
            self.display.print_consequences(result.consequence_note)
            self.display.print_strategy(result.narrator_note)

            challenge = self.state.scene.primary_challenge()
            effect_errors = EffectApplicator.apply_results(
                result.effect_note,
                result.consequence_note,
                self.state.character,
                challenge,
            )
            if effect_errors:
                log_system(f"[效果应用警告] 共 {len(effect_errors)} 个效果应用失败")

            self._finalize_move()

            print("─" * 50)

            narrative = result.narrator_note.structured.get("narrative", "")
            print(f"\n{narrative}")
            self.state.append_narrative(narrative)
            narratives.append(narrative)

            # 角色失去行动能力 → 中断后续子 action
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
        """完成一次 Move 后的收尾工作。

        记录角色和挑战的当前状态到日志。
        """
        character = self.state.character
        challenge = self.state.scene.primary_challenge()
        if character and challenge:
            log_status_update(character.name, character.statuses)
            log_status_update(challenge.name, challenge.statuses)

    def _handle_limit_break(self, triggered_limits):
        """处理极限突破事件。

        当挑战的状态达到 max_tier 阈值时触发。调用极限突破 Agent
        生成突破叙事、挑战转变描述和场景走向，并在挑战上标记已突破的极限。

        Args:
            triggered_limits: 被触发的 Limit 对象列表
        """
        challenge = self.state.scene.primary_challenge()
        assert challenge is not None
        limit_names = [lim.name for lim in triggered_limits]
        print(f"\n  ⚡ 极限突破: {', '.join(limit_names)}!")

        ctx = self.state.make_context()

        limit_break_note = self.limit_break_agent.execute(
            limit_names,
            challenge,
            ctx,
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
