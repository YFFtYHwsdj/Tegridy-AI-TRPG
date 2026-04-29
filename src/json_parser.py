"""JSON 解析器 —— 从 LLM 输出中提取和修复 JSON。

本模块处理 LLM Agent 输出中最棘手的部分：从混有推理文本的
自然语言输出中提取结构化 JSON。提供多层修复策略：
    1. 直接解析
    2. 尾随逗号修复
    3. 平衡括号提取
    4. 单引号替换
    5. 未加引号的键名修复

同时解析 Agent 的标准输出格式（REASONING / NARRATIVE / STRUCTURED 三段式）。
"""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

from src.logger import log_system

if TYPE_CHECKING:
    from src.models import AgentNote


def _extract_json_object(text: str) -> str | None:
    """从文本中提取第一个完整的 JSON 对象。

    使用括号深度计数和字符串状态机，正确处理嵌套对象和字符串内的括号。

    Args:
        text: 包含 JSON 的原始文本

    Returns:
        提取的 JSON 字符串，未找到返回 None
    """
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape_next = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _recover_json(text: str) -> dict | None:
    """多层 JSON 修复解析。

    依次尝试：
    1. 直接 json.loads
    2. 修复尾随逗号（LLM 常见错误）
    3. 平衡括号提取子串
    4. 平衡括号提取 + 尾随逗号修复
    5. 单引号替换为双引号
    6. 修复未加引号的键名

    Args:
        text: 可能包含 JSON 的文本

    Returns:
        解析成功的 dict，全部失败返回 None
    """
    json_str = text.strip()
    if not json_str:
        return None

    # Step 1: 直接解析
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        last_error = e

    # Step 2: 修复尾随逗号（如 {"a": 1,} → {"a": 1}）
    fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
    try:
        result = json.loads(fixed)
        log_system(f"尾随逗号修复成功: {last_error}", level="debug")
        return result
    except json.JSONDecodeError:
        pass

    # Step 3: 平衡括号提取
    extracted = _extract_json_object(json_str)
    if extracted is not None and extracted != json_str:
        try:
            result = json.loads(extracted)
            log_system("平衡括号提取JSON成功", level="debug")
            return result
        except json.JSONDecodeError:
            fixed_extracted = re.sub(r",\s*([}\]])", r"\1", extracted)
            try:
                result = json.loads(fixed_extracted)
                log_system("平衡括号提取 + 尾随逗号修复成功", level="debug")
                return result
            except json.JSONDecodeError:
                pass

    # Step 4: 修复单引号（LLM 偶尔使用单引号代替双引号）
    if '"' not in json_str and "'" in json_str:
        fixed_quotes = json_str.replace("'", '"')
        fixed_quotes = re.sub(r",\s*([}\]])", r"\1", fixed_quotes)
        try:
            result = json.loads(fixed_quotes)
            log_system("单引号替换为双引号修复成功", level="debug")
            return result
        except json.JSONDecodeError:
            pass

    # Step 5: 修复未加引号的键名（如 {key: "val"} → {"key": "val"}）
    fixed_keys = re.sub(r"([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:", r'\1"\2":', json_str)
    fixed_keys = re.sub(r",\s*([}\]])", r"\1", fixed_keys)
    try:
        result = json.loads(fixed_keys)
        log_system("未加引号的键名修复成功", level="debug")
        return result
    except json.JSONDecodeError:
        pass

    return None


def parse_agent_output(raw_output: str) -> AgentNote:
    """解析 Agent 的标准输出格式为 AgentNote。

    标准 Agent 输出格式为三段式：
        =====REASONING=====
        （推理过程文本）
        =====NARRATIVE=====
        （叙事文本，可选）
        =====STRUCTURED=====
        （JSON 结构化数据）

    Args:
        raw_output: Agent 的原始输出文本

    Returns:
        AgentNote: 包含推理文本和结构化数据的分析便签
    """
    from src.models import AgentNote

    reasoning = ""
    structured = {}

    # 提取 REASONING 段落
    reasoning_match = re.search(
        r"=====REASONING=====\s*(.*?)\s*=====(?:NARRATIVE|STRUCTURED)=====", raw_output, re.DOTALL
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # 提取 STRUCTURED 段落并解析为 JSON
    structured_match = re.search(r"=====STRUCTURED=====\s*(.*?)$", raw_output, re.DOTALL)
    if structured_match:
        structured_str = structured_match.group(1).strip()
        result = _recover_json(structured_str)
        if result is not None:
            structured = result
        else:
            snippet = structured_str[:200] + ("..." if len(structured_str) > 200 else "")
            log_system(
                f"所有修复尝试均失败，回退为raw。 原始内容前200字符: {snippet}",
                level="warning",
            )
            structured = {"raw": structured_str}
    else:
        # 叙述者等 Agent 可能在无揭示/转移时不输出 STRUCTURED，属正常情况
        pass

    # 补充提取 NARRATIVE 段落（如果 structured 中没有 narrative 字段）
    if "narrative" not in structured:
        narrative_match = re.search(
            r"=====NARRATIVE=====\s*(.*?)\s*=====STRUCTURED=====", raw_output, re.DOTALL
        )
        if narrative_match:
            structured["narrative"] = narrative_match.group(1).strip()
        else:
            narrative_match = re.search(r"=====NARRATIVE=====\s*(.*?)$", raw_output, re.DOTALL)
            if narrative_match:
                structured["narrative"] = narrative_match.group(1).strip()

    return AgentNote(reasoning=reasoning, structured=structured)
