"""游戏主循环 —— 玩家与 AI Agent 流水线的交互桥梁。

本模块的 GameLoop 类是系统的"前台控制器"，负责两层循环：
    场景循环（scene loop）：场景间切换，由 SceneDirectorAgent 判定结束条件
    行动循环（action loop）：场景内单次玩家行动处理

核心流程（场景内）：
    玩家输入 → Move 判定 → 意图解析 → 结算模式选择
    → 流水线执行 → 效果落地 → 叙事输出 → 极限检查

场景切换流程：
    SceneDirector 判定结束 → Compressor 压缩当前场景
    → SceneCreator 创作下一场景 → transition_to 切换状态
    → RhythmAgent 开场新场景

公开 API：
    step(player_input) → StepResult：单步推进，封装行动处理 + 场景导演判定 +
        场景切换为原子操作。适用于自动化测试、Web UI 等非终端前端。

输出通道划分：
    - 叙事文本、系统命令响应 → INFO（终端始终可见）
    - 管道状态、结算模式、行动类型等内部追踪 → DEBUG（仅调试模式终端可见）
"""

from __future__ import annotations

from dataclasses import dataclass

from src.agents import (
    CompressorAgent,
    IntentAgent,
    LimitBreakAgent,
    LiteNarratorAgent,
    MoveGatekeeperAgent,
    ResolutionModeAgent,
    RhythmAgent,
    SceneCreatorAgent,
    SceneDirectorAgent,
)
from src.agents.scene_creator import build_scene_from_creator
from src.display.console import ConsoleDisplay
from src.effects.applicator import EffectApplicator
from src.engine import check_limits
from src.formatter import format_challenge_state
from src.llm_client import LLMClient
from src.logger import get_logger, log_status_update, log_system, set_debug_mode
from src.models import Character
from src.pipeline.move_pipeline import MovePipeline
from src.state.game_state import GameState
from src.state.scene_state import SceneState


@dataclass
class StepResult:
    """单步推进结果 —— step() 方法的返回值。

    封装一次 step() 调用的完整结果，供调用方（如 AutoRunner）
    判断游戏进展和终止条件。

    Attributes:
        narrative: 本轮产出的叙事文本（空字符串表示命令或空输入）
        is_quit: 玩家是否请求退出（/quit, /exit）
        scene_changed: 本轮是否触发了场景切换
        scene_end_reason: 场景导演给出的结束原因（仅 scene_changed=True 时有值）
        is_empty: 是否为空输入或已处理的命令（无叙事产出）
    """

    narrative: str = ""
    is_quit: bool = False
    scene_changed: bool = False
    scene_end_reason: str = ""
    is_empty: bool = False


class GameLoop:
    """游戏主循环控制器。

    持有所有 Agent 实例和流水线。run() 方法驱动完整的游戏体验，
    包含场景循环和场景内行动循环。

    核心入口：
        run(): 启动完整游戏循环（场景循环 + 行动循环）
        setup(): 初始化首个场景
        process_action(): 处理单次玩家行动（命令/Move/非Move）
    """

    def __init__(self, llm: LLMClient, debug_mode: bool = False):
        self.llm = llm
        self.state = GameState()
        self._log = get_logger()
        self.display = ConsoleDisplay(self._log)
        self.pipeline = MovePipeline(llm, self.state, self.display)
        self.debug_mode = debug_mode
        set_debug_mode(debug_mode)

        # 行动层 Agent
        self.rhythm_agent = RhythmAgent(llm)
        self.gatekeeper = MoveGatekeeperAgent(llm)
        self.intent_agent = IntentAgent(llm)
        self.lite_narrator = LiteNarratorAgent(llm)
        self.limit_break_agent = LimitBreakAgent(llm)
        self.resolution_agent = ResolutionModeAgent(llm)

        # 场景切换层 Agent
        self.scene_director = SceneDirectorAgent(llm)
        self.compressor = CompressorAgent(llm)
        self.scene_creator = SceneCreatorAgent(llm)

        # 场景切换间传递的过渡提示
        self._transition_hint = ""
        # 是否为首个场景（控制标题显示）
        self._first_scene = True

    def toggle_debug(self):
        """切换调试模式开关。

        Returns:
            切换后的调试模式状态
        """
        self.debug_mode = not self.debug_mode
        set_debug_mode(self.debug_mode)
        return self.debug_mode

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
            self._log.info("  [系统] 调试模式已切换为: %s", label)
            return ""
        if cmd == "/help":
            self._log.info("  [命令列表]")
            self._log.info("    /quit, /exit  — 退出游戏")
            self._log.info("    /debug        — 切换调试显示模式")
            self._log.info("    /help         — 显示此帮助")
            return ""
        self._log.info("  [系统] 未知命令: %s。输入 /help 查看可用命令。", cmd)
        return ""

    # ───────────────────── 单步推进 API ─────────────────────

    def step(self, player_input: str) -> StepResult:
        """单步推进游戏 —— 处理一次玩家输入并检查场景结束条件。

        将 process_action() + 场景导演判定 + 场景切换封装为一个原子操作。
        适用于自动化测试、Web UI 等非终端前端，无需 input() 阻塞。

        调用前必须先调用 setup() 初始化首个场景。

        流程：
            1. process_action(player_input) → 叙事文本
            2. 如果产出了叙事，询问场景导演是否该结束场景
            3. 如果场景应结束，执行场景过渡

        Args:
            player_input: 玩家输入文本

        Returns:
            StepResult: 本轮推进的完整结果
        """
        result, needs_director = self.process_action(player_input)

        # 退出请求
        if result == "QUIT":
            return StepResult(is_quit=True)

        # 空输入或命令 —— 无叙事产出，不触发场景导演
        if not result:
            return StepResult(is_empty=True)

        # 有叙事产出 → 检查场景导演
        if needs_director:
            ctx = self.state.make_context()
            director_note = self.scene_director.execute(ctx, result)
            if director_note.structured.get("scene_should_end", False):
                reason = director_note.structured.get("reason", "")
                self._transition_hint = director_note.structured.get("transition_hint", "")
                self._log.info("")
                self._log.info("  [场景导演] 场景结束: %s", reason)

                # 执行场景过渡
                self._transition_scene()

                return StepResult(
                    narrative=result,
                    scene_changed=True,
                    scene_end_reason=reason,
                )

        return StepResult(narrative=result)

    # ───────────────────── 场景管理 ─────────────────────

    def setup(self, character: Character, scene: SceneState):
        """初始化首个场景。

        设置角色和场景状态，调用 RhythmAgent 输出开场叙事。

        Args:
            character: 玩家角色
            scene: 初始场景
        """
        self.state.setup(character, scene)
        self._open_scene()

    def _open_scene(self):
        """为当前场景生成开场叙事。

        调用 RhythmAgent 建立场景氛围，输出场景建立叙事、
        挑战状态概览和聚光灯传递。首个场景额外显示标题。
        """
        scene = self.state.scene
        challenge = scene.primary_challenge()

        if self._first_scene:
            self._log.info("")
            self._log.info("═" * 50)
            self._log.info("       :OTHERSCAPE · AI 主持")
            self._log.info("═" * 50)
            self._first_scene = False
        else:
            self._log.info("")
            self._log.info("═" * 50)
            self._log.info("       场景切换")
            self._log.info("═" * 50)

        rhythm = self.rhythm_agent.execute(scene.scene_description)
        narrative = rhythm.structured.get("scene_establishment", "")
        self._log.info("")
        self._log.info(narrative)
        self.state.append_narrative(narrative)

        self._log.info("")
        self._log.info("─" * 50)
        self._log.info("挑战状态:")
        self._log.info(format_challenge_state(challenge))
        self._log.info("─" * 50)

        spotlight = rhythm.structured.get("spotlight_handoff", "你要做什么？")
        self._log.info("")
        self._log.info(spotlight)

    def _transition_scene(self):
        """执行场景过渡流水线。

        1. CompressorAgent 压缩当前场景 → scene.compression
        2. SceneCreatorAgent 创作下一个场景 → 新 SceneState
        3. GameState.transition_to() 切换状态（归档到 GlobalState）
        4. _open_scene() 为新场景生成开场叙事
        """
        old_scene = self.state.scene

        # 1. 压缩当前场景
        compressor_note = self.compressor.execute(old_scene)
        compression = compressor_note.structured.get("scene_summary", "")
        old_scene.compression = compression

        # 2. 构建场景创作者的上下文块
        # 包含刚刚结束的场景信息 + 跨场景历史
        just_finished = (
            "=== 刚刚结束的场景（需基于此创作下一场景） ===\n"
            f"场景描述: {old_scene.scene_description}\n"
            f"场景压缩摘要: {compression}\n"
        )
        existing = self.state.global_state.build_block()
        creator_block = f"{just_finished}\n{existing}" if existing else just_finished

        # 3. 创作下一个场景
        creator_note = self.scene_creator.execute(
            creator_block,
            self.state.character,
            self._transition_hint,
        )
        new_scene = build_scene_from_creator(creator_note.structured)

        # 4. 切换状态（归档到 GlobalState）
        self.state.transition_to(new_scene)

        # 5. 开场新场景
        self._open_scene()

    # ───────────────────── 行动处理 ─────────────────────

    def process_action(self, player_input: str) -> tuple[str, bool]:
        """处理单次玩家行动。

        入口方法，负责三层路由：
        1. 命令处理（以 / 开头）
        2. Move 判定（守门人 Agent 判断是否需要规则引擎）
        3. 非 Move 叙事（轻量叙述者 Agent 直接处理）

        Move 流程中还包含结算模式判定和复合 action 拆分。

        Args:
            player_input: 玩家原始输入

        Returns:
            (叙事文本, 是否需要检查场景结束); "QUIT" 叙事表示退出; "" 表示空输入或命令已处理
        """
        raw = player_input.strip()

        # 第1层: 系统命令
        if raw.startswith("/"):
            return self._handle_command(raw), False

        if not raw:
            return "", False

        self._log.info("")
        self._log.info("─" * 50)

        ctx = self.state.make_context(raw)

        # 第2层: Move 判定
        gatekeeper_note = self.gatekeeper.execute(raw, ctx)
        is_move = gatekeeper_note.structured.get("is_move", True)

        if not is_move:
            return self._handle_non_move(raw, ctx, gatekeeper_note)

        self._log.debug("  [管道开始 · 掷骰模式]")

        # 第3层: 意图解析 + 结算模式判定
        intent_note = self.intent_agent.execute(raw, ctx)
        is_split = intent_note.structured.get("is_split_action", False)
        split_actions = intent_note.structured.get("split_actions", [])
        action_type = intent_note.structured.get("action_type", "unknown")
        action_summary = intent_note.structured.get("action_summary", "")

        self._log.debug("  行动类型: %s | 行动: %s", action_type, action_summary)

        # 复合 action（如"先撬门，再偷文件"）→ 拆分流水线
        if is_split and isinstance(split_actions, list) and len(split_actions) >= 2:
            return self._process_split_moves(intent_note, split_actions)

        # 结算模式判定（detailed vs quick）
        resolution_note = self.resolution_agent.execute(intent_note, ctx)
        resolution_mode = resolution_note.structured.get("resolution_mode", "detailed")
        self._log.debug("  结算模式: %s", resolution_mode)

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
        self._log.debug("  [叙事模式]")

        narrator_note = self.lite_narrator.execute(player_input, ctx, "")
        self._log.info("─" * 50)

        self.pipeline.validate_and_apply(narrator_note, ctx)

        narrative = narrator_note.structured.get("narrative", "")
        needs_director = narrator_note.structured.get("suggest_scene_end", False)
        self._log.info("")
        self._log.info(narrative)
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)
        return narrative, needs_director

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
            log_system(f"共 {len(effect_errors)} 个效果应用失败", level="warning")

        self._finalize_move()

        self._log.info("─" * 50)

        narrative = ""
        needs_director = False
        if result.narrator_note:
            narrative = result.narrator_note.structured.get("narrative", "")
            needs_director = result.narrator_note.structured.get("suggest_scene_end", False)
        self._log.info("")
        self._log.info(narrative)
        self.state.append_narrative(narrative)

        self.display.print_status(self.state)

        # 检查极限是否触发
        if challenge is not None:
            triggered_limits = check_limits(challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)
                needs_director = True

        return narrative, needs_director

    def _process_split_moves(self, intent_note, split_actions) -> tuple[str, bool]:
        """处理复合 action 的拆分流水线（统一叙事版）。

        对多个子 action 逐个执行解算流水线，每步显示解算信息并应用效果。
        所有子 action 完成后，统一输出一次叙事（由 pipeline 层的统一叙述者生成）。

        Args:
            intent_note: 意图解析便签
            split_actions: 子 action 列表

        Returns:
            (统一叙事文本, 是否需要检查场景结束)
        """
        results = self.pipeline.process_split_actions(intent_note, split_actions)

        # 逐个子行动显示解算信息并应用效果
        for result in results:
            self.display.print_tag_and_roll(result.tag_note, result.roll)
            self.display.print_effects(result.effect_note)
            self.display.print_consequences(result.consequence_note)

            challenge = self.state.scene.primary_challenge()
            effect_errors = EffectApplicator.apply_results(
                result.effect_note,
                result.consequence_note,
                self.state.character,
                challenge,
            )
            if effect_errors:
                log_system(f"共 {len(effect_errors)} 个效果应用失败", level="warning")

            self._finalize_move()

            # 角色失去行动能力 → 中断后续子 action 的效果应用
            if self.state.character and self.state.character.is_incapacitated():
                self.display.print_incapacitated_break()
                break

        # 统一叙事输出（来自最后一个 result 的 narrator_note）
        narrative = ""
        needs_director = False
        if results:
            last_result = results[-1]
            if last_result.narrator_note:
                self.display.print_strategy(last_result.narrator_note)
                self._log.info("─" * 50)
                narrative = last_result.narrator_note.structured.get("narrative", "")
                needs_director = last_result.narrator_note.structured.get(
                    "suggest_scene_end", False
                )
                self._log.info("")
                self._log.info(narrative)
                self.state.append_narrative(narrative)

        self.display.print_status(self.state)

        challenge = self.state.scene.primary_challenge()
        if challenge is not None:
            triggered_limits = check_limits(challenge)
            if triggered_limits:
                self._handle_limit_break(triggered_limits)
                needs_director = True

        return narrative, needs_director

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
        self._log.info("")
        self._log.info("  ⚡ 极限突破: %s!", ", ".join(limit_names))

        ctx = self.state.make_context()

        limit_break_note = self.limit_break_agent.execute(
            limit_names,
            challenge,
            ctx,
        )
        break_narrative = limit_break_note.structured.get("narrative", "")
        if break_narrative:
            self._log.info("")
            self._log.info("─" * 50)
            self._log.info("")
            self._log.info(break_narrative)
            self.state.append_narrative(break_narrative)

        transformation = limit_break_note.structured.get("challenge_transformation", "")
        if transformation:
            challenge.transformation = transformation
            self._log.info("")
            self._log.info("  [场景转变] %s", transformation)

        scene_direction = limit_break_note.structured.get("scene_direction", "")
        if scene_direction:
            self._log.info("  [走向] %s", scene_direction)

        challenge.mark_limits_broken(limit_names)
        log_status_update(challenge.name, challenge.statuses)

    # ───────────────────── 主循环 ─────────────────────

    def run(self, character: Character, first_scene: SceneState):
        """启动完整的游戏循环。

        包含两层循环：
            - 场景循环：场景间切换，由 SceneDirectorAgent 判定结束
            - 行动循环：场景内逐次处理玩家输入

        返回条件：玩家输入 /quit 或 EOF/KeyboardInterrupt。

        Args:
            character: 玩家角色
            first_scene: 初始场景
        """
        self.setup(character, first_scene)

        self._log.info("")
        self._log.info("输入你的行动（输入 /quit 退出，/help 查看命令）")

        while True:
            should_quit = self._run_scene_loop()
            if should_quit:
                self._log.info("游戏结束。")
                return

    def _run_scene_loop(self) -> bool:
        """运行单个场景的行动循环，并在结束时执行场景过渡。

        Returns:
            True 表示玩家请求退出，False 表示场景正常结束需要过渡
        """
        while True:
            try:
                player_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                self._log.info("")
                return True

            if not player_input:
                continue

            result, needs_director = self.process_action(player_input)
            if result == "QUIT":
                return True

            # 命令处理或空结果不触发场景导演检查
            if not result:
                continue

            # 每轮行动后询问场景导演是否该结束场景
            if needs_director:
                ctx = self.state.make_context()
                director_note = self.scene_director.execute(ctx, result)
                if director_note.structured.get("scene_should_end", False):
                    self._transition_hint = director_note.structured.get("transition_hint", "")
                    self._log.info("")
                    self._log.info(
                        "  [场景导演] 场景结束: %s", director_note.structured.get("reason", "")
                    )
                    break

        # 场景正常结束 → 执行过渡
        self._transition_scene()
        return False
