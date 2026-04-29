"""测试辅助工具 —— Mock 工厂和常用 fixture。

为 Agent 层和流水线测试提供统一的 Mock 对象创建函数，
避免每个测试文件重复构造相同的测试数据。
"""

from __future__ import annotations

from src.context import AgentContext
from src.models import AgentNote, Challenge, Character, Limit, RollResult, Tag
from src.state.game_state import GameState
from src.state.scene_state import SceneState


class MockLLMClient:
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

    def chat(
        self,
        system_prompt: str,
        user_message: str,
        temperature: float = 0.3,
    ) -> tuple[str, dict]:
        """模拟 LLM 调用，返回预设响应。

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            temperature: 生成温度

        Returns:
            (响应文本, token用量信息) 元组
        """
        self.call_history.append(
            {
                "system_prompt": system_prompt,
                "user_message": user_message,
                "temperature": temperature,
            }
        )
        if self.call_index < len(self.responses):
            raw, usage = self.responses[self.call_index]
            self.call_index += 1
            return raw, usage
        return (
            "=====REASONING=====\n默认推理\n=====STRUCTURED=====\n{}",
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


def make_test_character() -> Character:
    """创建标准测试角色（Kael）。

    Returns:
        带有典型标签和状态的 Character 实例
    """
    return Character(
        name="Kael",
        description="佣兵",
        power_tags=[
            Tag(name="快速拔枪", tag_type="power", description="枪法快"),
            Tag(name="前公司安保", tag_type="power"),
        ],
        weakness_tags=[
            Tag(name="信用破产", tag_type="weakness"),
        ],
    )


def make_test_challenge() -> Challenge:
    """创建标准测试挑战（Miko）。

    Returns:
        带有典型极限和标签的 Challenge 实例
    """
    return Challenge(
        name="Miko 与她的保镖",
        description="帮派中间人",
        limits=[
            Limit(name="说服或威胁", max_tier=3),
            Limit(name="伤害或制服", max_tier=4),
        ],
        base_tags=[
            Tag(name="精明的谈判者", tag_type="power"),
            Tag(name="两个专业保镖", tag_type="power"),
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
    challenge = make_test_challenge()
    scene.add_challenge(challenge)
    state.setup(character, scene)
    return state


def make_test_context() -> AgentContext:
    """创建标准测试 AgentContext。

    Returns:
        包含角色和挑战引用的 AgentContext 实例
    """
    character = make_test_character()
    challenge = make_test_challenge()
    return AgentContext(
        assets_block="=== 场景资产 ===\n场景人物: Miko",
        context_block="=== 上下文 ===\n当前场景: 赛博朋克酒吧",
        narrative_block="=== 叙事历史 ===\n[1] 你走进了酒吧",
        character=character,
        challenge=challenge,
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
