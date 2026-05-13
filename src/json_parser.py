"""JSON 解析器 —— 从 LLM JSON mode 输出中提取 AgentNote。

启用 DeepSeek JSON mode 后，LLM 保证返回合法 JSON。
本模块仅需 json.loads() 即可完成解析，无需复杂修复策略。
解析失败时抛出 JSONParseError，由调用方（BaseAgent）决定重试或降级。
从 JSON 中提取 reasoning 字段（Agent 间传递的推理过程）
作为 AgentNote.reasoning，其余字段作为 AgentNote.structured。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from src.logger import log_system

if TYPE_CHECKING:
    from src.models import AgentNote


class JSONParseError(Exception):
    """JSON 解析失败异常。

    JSON mode 下不应发生，但网络截断、模型异常等极端情况
    仍可能产生非法 JSON。此异常供调用方捕获后决定重试或降级。
    """

    pass


def parse_json_output(raw_output: str) -> AgentNote:
    """解析 JSON mode 下 LLM 的纯 JSON 输出为 AgentNote。

    JSON mode 保证 raw_output 是合法 JSON。解析流程：
        1. json.loads() 直接解析
        2. 提取 reasoning 字段 → AgentNote.reasoning
        3. 剩余字段 → AgentNote.structured

    Args:
        raw_output: LLM 返回的 JSON 字符串

    Returns:
        AgentNote: 包含推理文本和结构化数据的分析便签

    Raises:
        JSONParseError: JSON 解析失败（JSON mode 下不应发生）
    """
    from src.models import AgentNote

    try:
        data = json.loads(raw_output)
    except (json.JSONDecodeError, TypeError) as e:
        # JSON mode 下不应发生，记录警告并抛出异常供调用方重试
        snippet = raw_output[:200] + ("..." if len(raw_output) > 200 else "")
        log_system(
            f"JSON 解析失败（不应发生在 JSON mode 下）: {snippet}",
            level="warning",
        )
        raise JSONParseError(f"LLM 返回了非法 JSON: {snippet}") from e

    # reasoning 字段承载 Agent 间传递的推理过程，
    # 从 structured 中弹出以避免重复存储
    reasoning = data.pop("reasoning", "")

    return AgentNote(reasoning=reasoning, structured=data)
