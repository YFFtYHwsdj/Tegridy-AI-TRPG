"""Agent 基类 —— 所有 LLM Agent 的抽象基类和注册表。

BaseAgent 提供统一的 LLM 调用、日志记录和输出解析流程。
每个具体 Agent 只需设定 system_prompt 和 agent_name。
AGENT_REGISTRY 维护所有 Agent 类的全局注册表。
"""

from src.agents.compressor import CompressorAgent
from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.intent import IntentAgent
from src.agents.move_gatekeeper import MoveGatekeeperAgent
from src.agents.narrator import LiteNarratorAgent, NarratorAgent, QuickNarratorAgent
from src.agents.outcome import OutcomeAgent, QuickOutcomeAgent
from src.agents.resolution_mode import ResolutionModeAgent
from src.agents.rhythm import RhythmAgent
from src.agents.scene_creator import SceneCreatorAgent
from src.agents.scene_director import SceneDirectorAgent
from src.agents.tag_matcher import TagMatcherAgent

AGENT_REGISTRY = {
    "rhythm": RhythmAgent,
    "move_gatekeeper": MoveGatekeeperAgent,
    "intent": IntentAgent,
    "tag_matcher": TagMatcherAgent,
    "outcome": OutcomeAgent,
    "quick_outcome": QuickOutcomeAgent,
    "compressor": CompressorAgent,
    "narrator": NarratorAgent,
    "lite_narrator": LiteNarratorAgent,
    "quick_narrator": QuickNarratorAgent,
    "continuation_check": ContinuationCheckAgent,
    "resolution_mode": ResolutionModeAgent,
    "scene_creator": SceneCreatorAgent,
    "scene_director": SceneDirectorAgent,
}

__all__ = [
    "AGENT_REGISTRY",
    "CompressorAgent",
    "ContinuationCheckAgent",
    "IntentAgent",
    "LiteNarratorAgent",
    "MoveGatekeeperAgent",
    "NarratorAgent",
    "OutcomeAgent",
    "QuickNarratorAgent",
    "QuickOutcomeAgent",
    "ResolutionModeAgent",
    "RhythmAgent",
    "SceneCreatorAgent",
    "SceneDirectorAgent",
    "TagMatcherAgent",
]
