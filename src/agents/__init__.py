"""Agent 基类 —— 所有 LLM Agent 的抽象基类和注册表。

BaseAgent 提供统一的 LLM 调用、日志记录和输出解析流程。
每个具体 Agent 只需设定 system_prompt 和 agent_name。
AGENT_REGISTRY 维护所有 Agent 类的全局注册表。
"""

from src.agents.compressor import CompressorAgent
from src.agents.continuation_check import ContinuationCheckAgent
from src.agents.inquiry import InquiryAgent
from src.agents.intent import IntentAgent
from src.agents.narrator import LiteNarratorAgent, NarratorAgent, QuickNarratorAgent
from src.agents.outcome import OutcomeAgent, QuickOutcomeAgent
from src.agents.resolution_mode import ResolutionModeAgent
from src.agents.rhythm import RhythmAgent
from src.agents.scene_creator import SceneCreatorAgent
from src.agents.scene_director import SceneDirectorAgent
from src.agents.tag_matcher import TagMatcherAgent

AGENT_REGISTRY = {
    "rhythm": RhythmAgent,
    "intent": IntentAgent,
    "inquiry": InquiryAgent,
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

# 在此处统一配置需要覆盖默认 LLM 设定的 Agent
# 未配置的 Agent 将使用全局的 LLMClient 配置（默认 deepseek-v4-flash，Thinking 关闭）
AGENT_CONFIGS = {
    "intent": {"model": "deepseek-v4-flash", "thinking": False},
    "outcome": {"model": "deepseek-v4-flash", "thinking": False},
    "narrator": {"model": "deepseek-v4-flash", "thinking": False},
    "scene_director": {"model": "deepseek-v4-flash", "thinking": False},
    "scene_creator": {"model": "deepseek-v4-pro", "thinking": True},
    "inquiry": {"model": "deepseek-v4-flash", "thinking": False},
    "tag_matcher": {"model": "deepseek-v4-flash", "thinking": False},
    "quick_outcome": {"model": "deepseek-v4-flash", "thinking": False},
    "compressor": {"model": "deepseek-v4-pro", "thinking": True},
    "lite_narrator": {"model": "deepseek-v4-flash", "thinking": False},
    "quick_narrator": {"model": "deepseek-v4-flash", "thinking": False},
    "continuation_check": {
        "model": "deepseek-v4-flash",
        "thinking": False,
    },
    "resolution_mode": {"model": "deepseek-v4-flash", "thinking": False},
    "rhythm": {"model": "deepseek-v4-pro", "thinking": True},
}

# 模块初始化时，将配置动态注入到类属性中
for _name, _cls in AGENT_REGISTRY.items():
    if _name in AGENT_CONFIGS:
        _conf = AGENT_CONFIGS[_name]
        if "model" in _conf:
            _cls.model = _conf["model"]
        if "thinking" in _conf:
            _cls.thinking = _conf["thinking"]

__all__ = [
    "AGENT_CONFIGS",
    "AGENT_REGISTRY",
    "CompressorAgent",
    "ContinuationCheckAgent",
    "InquiryAgent",
    "IntentAgent",
    "LiteNarratorAgent",
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
