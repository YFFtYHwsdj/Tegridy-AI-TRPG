from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tag:
    name: str
    tag_type: str
    description: str = ""

    def __post_init__(self):
        if self.tag_type not in ("power", "weakness"):
            raise ValueError(f"tag_type must be 'power' or 'weakness', got '{self.tag_type}'")


@dataclass
class Status:
    name: str
    current_tier: int = 0
    ticked_boxes: set[int] = field(default_factory=set)
    limit_category: str = ""


@dataclass
class StoryTag:
    name: str
    description: str = ""
    is_single_use: bool = False
    is_consumable: bool = False


@dataclass
class Limit:
    name: str
    max_tier: int
    is_progress: bool = False

    def __post_init__(self):
        if self.max_tier < 1 or self.max_tier > 6:
            raise ValueError(f"max_tier must be between 1 and 6, got {self.max_tier}")


@dataclass
class Challenge:
    name: str
    description: str
    limits: list[Limit] = field(default_factory=list)
    base_tags: list[Tag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    story_tags: dict[str, StoryTag] = field(default_factory=dict)
    notes: str = ""
    broken_limits: set[str] = field(default_factory=set)
    transformation: str = ""

    def get_matching_statuses(self, limit_name: str) -> list[Status]:
        results = []
        for status in self.statuses.values():
            if status.limit_category and status.limit_category in limit_name:
                results.append(status)
        return results

    def check_limits(self) -> list[Limit]:
        triggered = []
        for limit in self.limits:
            if limit.name in self.broken_limits:
                continue
            matching = self.get_matching_statuses(limit.name)
            for s in matching:
                if s.current_tier >= limit.max_tier:
                    triggered.append(limit)
                    break
        return triggered

    def mark_limits_broken(self, limit_names: list[str]):
        for name in limit_names:
            self.broken_limits.add(name)


@dataclass
class Character:
    name: str
    power_tags: list[Tag] = field(default_factory=list)
    weakness_tags: list[Tag] = field(default_factory=list)
    statuses: dict[str, Status] = field(default_factory=dict)
    story_tags: dict[str, StoryTag] = field(default_factory=dict)
    burned_tags: set[str] = field(default_factory=set)
    description: str = ""


@dataclass
class RollResult:
    power: int
    dice: tuple[int, int]
    total: int
    outcome: str

    def __post_init__(self):
        if self.outcome not in ("full_success", "partial_success", "failure"):
            raise ValueError(f"outcome must be full_success/partial_success/failure, got '{self.outcome}'")


@dataclass
class EffectEntry:
    effect_type: str
    tier: int
    target: str
    label: str
    reasoning: str = ""


@dataclass
class ConsequenceEntry:
    threat_manifested: str
    effects: list[EffectEntry] = field(default_factory=list)
    narrative_description: str = ""


@dataclass
class AgentNote:
    reasoning: str
    structured: dict
