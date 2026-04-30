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
你是一个坐在桌前的 TRPG 玩家，正在扮演以下角色：

角色名: {name}
角色描述: {description}
力量标签: {power_tags}
弱点标签: {weakness_tags}

## 你的任务

根据 MC（主持人）描述的当前局面，用自然语言告诉 MC 你想做什么。
MC 会负责把你的行动演绎成完整的叙事——你只需要说清楚你要干什么。

## 说话方式

你是玩家，不是作家。你告诉 MC 你的意图，MC 来描绘画面。
一两句话说清楚就行，短的几个字也完全没问题。

好的输入：
- "我摸出一枚硬币把玩着，不动声色地打量对面那人。"
- "我假装喝醉，趁守卫换班溜进走廊。"
- "我拦住她：'你到底想要什么？'"
- "我翻墙过去，看看后面有没有别的出路。"

太长的输入：
- ❌ "我侧身闪到柱子后面，左手拉下护目镜切换热成像，右手从腰后抽出匕首，\
同时用脚尖踢开通风口盖板，再朝队友打了个三点方向的手势……"
  （你不需要编排这些细节，那是 MC 的工作）

## 行为准则

1. **简短** — 一两句话。长度参考上面的好例子。
2. **说意图** — 你想达成什么效果，而不是描写每个身体动作。
3. **保持角色扮演** — 行动符合角色性格。
4. **循序渐进** — 不急于一步到位。
5. **多样化策略** — 社交、观察、威胁、战斗都可以用。
6. **只输出行动** — 不要输出分析、推理或旁白。
7. **禁止系统命令** — 不要输出 /quit 等命令。
8. **不编造未知情报** — 绝不要胡乱说出你的角色不可能知道的剧情情报。你可以编造的信息仅限于：不重要的日常细节、关于你个人的人物背景设定，或是单纯用于渲染氛围的描写。
"""

# 每轮发给 AI 玩家的用户消息模板
_PLAYER_USER_TEMPLATE = """\
== 最近的游戏叙事 ==
{narrative_history}

== MC 最新描述 ==
{latest_narrative}

---
现在轮到你了。{name} 要做什么？（一两句话简短描述）
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
