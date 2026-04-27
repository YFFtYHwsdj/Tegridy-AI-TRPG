from src.agents.rhythm import RhythmAgent
from src.agents.move_gatekeeper import MoveGatekeeperAgent
from src.agents.intent import IntentAgent
from src.agents.tag_matcher import TagMatcherAgent
from src.agents.effect_actualization import EffectActualizationAgent
from src.agents.consequence import ConsequenceAgent, QuickConsequenceAgent
from src.agents.narrator import NarratorAgent, LiteNarratorAgent, QuickNarratorAgent
from src.agents.limit_break import LimitBreakAgent
from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.resolution_mode import ResolutionModeAgent

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
    "limit_break": LimitBreakAgent,
    "continuation_check": ContinuationCheckAgent,
    "resolution_mode": ResolutionModeAgent,
}

__all__ = [
    "RhythmAgent",
    "MoveGatekeeperAgent",
    "IntentAgent",
    "TagMatcherAgent",
    "EffectActualizationAgent",
    "ConsequenceAgent",
    "QuickConsequenceAgent",
    "NarratorAgent",
    "LiteNarratorAgent",
    "QuickNarratorAgent",
    "LimitBreakAgent",
    "ContinuationCheckAgent",
    "ResolutionModeAgent",
    "AGENT_REGISTRY",
]
