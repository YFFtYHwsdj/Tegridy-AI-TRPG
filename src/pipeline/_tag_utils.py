from __future__ import annotations

from src.models import AgentNote


def _extract_names_from_tags(items: list, key: str = "name") -> list[str]:
    result = []
    for item in items:
        if isinstance(item, dict):
            val = item.get(key)
            if val:
                result.append(val)
        elif isinstance(item, str):
            result.append(item)
    return result


extract_tag_names = _extract_names_from_tags
extract_status_names = _extract_names_from_tags


def extract_status_tiers(tag_note: AgentNote):
    helping = tag_note.structured.get("helping_statuses", [])
    hindering = tag_note.structured.get("hindering_statuses", [])

    best_tier = max(
        (s["tier"] for s in helping if isinstance(s, dict) and s.get("tier")), default=0
    )
    worst_tier = max(
        (s["tier"] for s in hindering if isinstance(s, dict) and s.get("tier")), default=0
    )
    return best_tier, worst_tier
