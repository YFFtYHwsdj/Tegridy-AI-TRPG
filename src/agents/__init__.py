"""Agent 基类 —— 所有 LLM Agent 的抽象基类和注册表。

BaseAgent 提供统一的 LLM 调用、日志记录和输出解析流程。
每个具体 Agent 只需设定 system_prompt 和 agent_name。
AGENT_REGISTRY 维护所有 Agent 类的全局注册表。
"""

from src.agents.consequence import ConsequenceAgent, QuickConsequenceAgent
from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.effect_actualization import EffectActualizationAgent
from src.agents.intent import IntentAgent
from src.agents.limit_break import LimitBreakAgent
from src.agents.move_gatekeeper import MoveGatekeeperAgent
from src.agents.narrator import LiteNarratorAgent, NarratorAgent, QuickNarratorAgent
from src.agents.resolution_mode import ResolutionModeAgent
from src.agents.rhythm import RhythmAgent
from src.agents.tag_matcher import TagMatcherAgent
from src.agents.validator import ValidatorAgent

AGENT_REGISTRY = {
    "rhythm": RhythmAgent,
    "move_gatekeeper": MoveGatekeeperAgent,
    "intent": IntentAgent,
    "tag_matcher": TagMatcherAgent,
    "effect_actualization": EffectActualizationAgent,
    "consequence": ConsequenceAgent,
    "quick_consequence": QuickConsequenceAgent,
    "narrator": NarratorAgent,
    "lite_narrator": LiteNarratorAgent,
    "quick_narrator": QuickNarratorAgent,
    "validator": ValidatorAgent,
    "limit_break": LimitBreakAgent,
    "continuation_check": ContinuationCheckAgent,
    "resolution_mode": ResolutionModeAgent,
}

__all__ = [
    "AGENT_REGISTRY",
    "ConsequenceAgent",
    "ContinuationCheckAgent",
    "EffectActualizationAgent",
    "IntentAgent",
    "LimitBreakAgent",
    "LiteNarratorAgent",
    "MoveGatekeeperAgent",
    "NarratorAgent",
    "QuickConsequenceAgent",
    "QuickNarratorAgent",
    "ResolutionModeAgent",
    "RhythmAgent",
    "TagMatcherAgent",
    "ValidatorAgent",
]
