from src.agents.rhythm import RhythmAgent
from src.agents.move_gatekeeper import MoveGatekeeperAgent
from src.agents.intent import IntentAgent
from src.agents.tag_matcher import TagMatcherAgent
from src.agents.effect_actualization import EffectActualizationAgent
from src.agents.consequence import ConsequenceAgent
from src.agents.narrator import NarratorAgent, LiteNarratorAgent
from src.agents.limit_break import LimitBreakAgent
from src.agents.continuation_check import ContinuationCheckAgent

AGENT_REGISTRY = {
    "rhythm": RhythmAgent,
    "move_gatekeeper": MoveGatekeeperAgent,
    "intent": IntentAgent,
    "tag_matcher": TagMatcherAgent,
    "effect_actualization": EffectActualizationAgent,
    "consequence": ConsequenceAgent,
    "narrator": NarratorAgent,
    "lite_narrator": LiteNarratorAgent,
    "limit_break": LimitBreakAgent,
    "continuation_check": ContinuationCheckAgent,
}

__all__ = [
    "RhythmAgent",
    "MoveGatekeeperAgent",
    "IntentAgent",
    "TagMatcherAgent",
    "EffectActualizationAgent",
    "ConsequenceAgent",
    "NarratorAgent",
    "LiteNarratorAgent",
    "LimitBreakAgent",
    "ContinuationCheckAgent",
    "AGENT_REGISTRY",
]
