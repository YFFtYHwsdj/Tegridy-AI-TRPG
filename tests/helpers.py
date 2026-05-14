"""测试辅助工具 —— Mock 工厂和常用 fixture。

为 Agent 层和流水线测试提供统一的 Mock 对象创建函数，
避免每个测试文件重复构造相同的测试数据。
"""

from __future__ import annotations

from src.context import AgentContext
from src.llm_client import LLMClient
from src.models import AgentNote, PowerTag, RollResult, WeaknessTag
from src.state.character_state import CharacterState
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class MockLLMClient(LLMClient):
    """模拟 LLM 客户端，返回预设响应。

    记录所有调用参数到 call_history，用于断言 prompt 组装是否正确。
    通过预设 responses 列表模拟 LLM 的逐次返回。

    Attributes:
        responses: 预设的 (raw_text, usage_info) 列表
        call_history: 每次调用的参数记录
        call_index: 当前响应索引
    """

    def __init__(self, responses: list[tuple[str, dict]] | None = None):
        self.responses = responses or []
        self.call_history: list[dict] = []
        self.call_index = 0
        self.model = "mock-model"
        self.thinking = False
        self.max_retries = 3

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
        model: str | None = None,
        thinking: bool | None = None,
    ) -> tuple[str, dict]:
        """模拟 LLM 调用，返回预设响应。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 生成温度
            model: 模型
            thinking: 思考模式

        Returns:
            (响应文本, token用量信息) 元组
        """
        self.call_history.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "temperature": temperature,
                "model": model,
                "thinking": thinking,
            }
        )
        if self.call_index < len(self.responses):
            raw, usage = self.responses[self.call_index]
            self.call_index += 1
            return raw, usage
        return (
            '{"reasoning": "默认推理"}',
            {},
        )


def make_agent_note(reasoning: str = "", structured: dict | None = None) -> AgentNote:
    """快速创建 AgentNote。

    Args:
        reasoning: 推理文本
        structured: 结构化数据字典

    Returns:
        AgentNote 实例
    """
    return AgentNote(reasoning=reasoning, structured=structured or {})


def make_test_character() -> CharacterState:
    """创建标准测试角色（Kael）。

    Returns:
        带有典型标签和状态的 CharacterState 实例
    """
    from src.models import Theme

    return CharacterState(
        name="Kael",
        description="佣兵",
        themes=[
            Theme(
                name="测试",
                theme_type="测试",
                concept="测试",
                motivation="测试",
                power_tags=[
                    PowerTag(name="快速拔枪", description="枪法快"),
                    PowerTag(name="前公司安保"),
                ],
                weakness_tags=[
                    WeaknessTag(name="信用破产"),
                ],
            )
        ],
    )


def make_test_scene() -> SceneState:
    """创建标准测试场景。

    Returns:
        带有描述和默认空集合的 SceneState 实例
    """
    return SceneState(scene_description="赛博朋克酒吧")


def make_test_game_state() -> GameState:
    """创建已 setup 的测试游戏状态。

    Returns:
        包含角色、场景和挑战的 GameState 实例
    """
    state = GameState()
    character = make_test_character()
    scene = make_test_scene()
    state.setup(character, scene)
    return state


def make_test_context() -> AgentContext:
    """创建标准测试 AgentContext。

    Returns:
        包含角色和挑战引用的 AgentContext 实例
    """
    character = make_test_character()
    return AgentContext(
        assets_block="=== 场景资产 ===\n场景人物: Miko",
        context_block="=== 上下文 ===\n当前场景: 赛博朋克酒吧",
        narrative_block="=== 叙事历史 ===\n[1] 你走进了酒吧",
        character=character,
        player_input="我要拔枪",
    )


def make_roll_result(
    outcome: str = "partial_success",
    power: int = 1,
    dice: tuple[int, int] = (3, 4),
) -> RollResult:
    """快速创建 RollResult。

    Args:
        outcome: 结果类型
        power: 力量值
        dice: 骰子结果

    Returns:
        RollResult 实例
    """
    total = dice[0] + dice[1] + power
    return RollResult(power=power, dice=dice, total=total, outcome=outcome)
