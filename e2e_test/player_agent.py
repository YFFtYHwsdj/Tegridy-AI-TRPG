"""AI 玩家 Agent —— 用 LLM 自主扮演玩家角色。

PlayerAgent 是自动化测试的核心：它读取 GameLoop 的叙事输出，
根据角色设定和当前局面自主决策下一步行动。输出纯自然语言
行动描述，和真人玩家的输入格式完全一致。

设计原则：
    - system prompt 包含角色信息和行为准则
    - 每轮将最近 N 条叙事历史 + 最新叙事作为 user_message
    - 维护滑动窗口历史，避免上下文无限膨胀
    - 输出只有一句话或几句话的行动描述，不输出元信息
"""

from __future__ import annotations

from src.llm_client import LLMClient
from src.models import Character

# AI 玩家的系统提示词模板
# {name} / {description} / {power_tags} / {weakness_tags} 由运行时填充
_PLAYER_SYSTEM_PROMPT = """\
你是一个 TRPG 玩家，正在扮演以下角色：

角色名: {name}
角色描述: {description}
力量标签: {power_tags}
弱点标签: {weakness_tags}

## 你的任务

根据 MC（主持人）描述的当前局面，决定你的角色下一步要做什么。

## 行为准则

1. **保持角色扮演** — 你的行动必须符合角色的性格、能力和动机。
2. **行动要具体** — 不要说"我做点什么"，要说"我试着用枪指着 Miko 的保镖，逼她交出芯片"。
3. **多样化策略** — 混合使用社交、观察、威胁、战斗等不同手段，不要反复使用同一招。
4. **关注环境** — 利用场景中的物品、NPC、地形等元素。
5. **有目标感** — 每个行动都应推动某个目标（获取情报、建立优势、消除威胁等）。
6. **禁止系统命令** — 不要输出以 / 开头的命令（如 /quit, /help 等）。
7. **只输出行动描述** — 不要输出分析、推理过程或元评论。只用一两句话描述你的角色要做什么。

## 输出格式

直接输出角色的行动描述，例如：
- "我靠在吧台上，点了杯合成威士忌，用余光观察 Miko 的保镖换班规律。"
- "我把数据板推到 Miko 面前，低声说：'这是你要的东西的一半。剩下的，等你告诉我芯片在哪。'"
"""

# 每轮发给 AI 玩家的用户消息模板
_PLAYER_USER_TEMPLATE = """\
== 最近的游戏叙事 ==
{narrative_history}

== MC 最新描述 ==
{latest_narrative}

---
现在轮到你了。你的角色 {name} 要做什么？
"""


class PlayerAgent:
    """AI 玩家 Agent —— 用 LLM 自主扮演玩家角色。

    每轮读取 GameLoop 产出的叙事文本，生成角色行动描述。
    维护最近 max_history 条叙事的滑动窗口，避免上下文爆炸。

    Attributes:
        llm: LLM 客户端实例
        character: 扮演的角色
        max_history: 滑动窗口保留的最大叙事条数
        history: 叙事历史（最新在后）
    """

    def __init__(
        self,
        llm: LLMClient,
        character: Character,
        max_history: int = 50,
    ):
        """初始化 AI 玩家。

        Args:
            llm: LLM 客户端（与 GameLoop 共用同一实例）
            character: 扮演的玩家角色
            max_history: 叙事历史滑动窗口大小
        """
        self.llm = llm
        self.character = character
        self.max_history = max_history
        self.history: list[str] = []

        # 构建角色专属的系统提示词
        power_names = ", ".join(t.name for t in character.power_tags)
        weakness_names = ", ".join(t.name for t in character.weakness_tags)
        self._system_prompt = _PLAYER_SYSTEM_PROMPT.format(
            name=character.name,
            description=character.description,
            power_tags=power_names or "（无）",
            weakness_tags=weakness_names or "（无）",
        )

    def decide_action(self, latest_narrative: str) -> str:
        """基于最新叙事输出，决定下一步行动。

        将最新叙事追加到历史窗口，构造 user_message 调用 LLM，
        返回纯自然语言的行动描述。

        Args:
            latest_narrative: GameLoop 最新产出的叙事文本

        Returns:
            角色行动描述文本
        """
        # 更新历史窗口
        if latest_narrative:
            self.history.append(latest_narrative)
        # 保持窗口大小
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history :]

        # 构建叙事历史摘要
        if self.history:
            history_text = "\n".join(f"[{i}] {entry}" for i, entry in enumerate(self.history, 1))
        else:
            history_text = "（游戏刚开始）"

        user_msg = _PLAYER_USER_TEMPLATE.format(
            narrative_history=history_text,
            latest_narrative=latest_narrative or "（等待你的第一步行动）",
            name=self.character.name,
        )

        # 调用 LLM
        response, _usage = self.llm.chat(
            self._system_prompt,
            user_msg,
            temperature=0.7,  # 比 Agent 流水线略高，增加行动多样性
        )

        # 清理输出：去掉可能的引号和多余空白
        action = response.strip().strip('"').strip("'").strip()
        return action
