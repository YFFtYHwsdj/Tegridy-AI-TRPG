from __future__ import annotations

import json
import re
from src.logger import log_system


def _extract_json_object(text: str) -> str | None:
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
                return text[start:i + 1]
    return None


def _recover_json(text: str) -> dict | None:
    json_str = text.strip()
    if not json_str:
        return None

    # Step 1: Direct parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        last_error = e

    # Step 2: Fix trailing commas before ] and }
    fixed = re.sub(r",\s*([}\]])", r"\1", json_str)
    try:
        result = json.loads(fixed)
        log_system(f"[JSON修复] 尾随逗号修复成功: {last_error}")
        return result
    except json.JSONDecodeError:
        pass

    # Step 3: Balanced-brace extraction
    extracted = _extract_json_object(json_str)
    if extracted is not None and extracted != json_str:
        try:
            result = json.loads(extracted)
            log_system(f"[JSON修复] 平衡括号提取JSON成功")
            return result
        except json.JSONDecodeError:
            fixed_extracted = re.sub(r",\s*([}\]])", r"\1", extracted)
            try:
                result = json.loads(fixed_extracted)
                log_system(f"[JSON修复] 平衡括号提取 + 尾随逗号修复成功")
                return result
            except json.JSONDecodeError:
                pass

    # Step 4: Fix single quotes used as JSON string delimiters
    if '"' not in json_str and "'" in json_str:
        fixed_quotes = json_str.replace("'", '"')
        fixed_quotes = re.sub(r",\s*([}\]])", r"\1", fixed_quotes)
        try:
            result = json.loads(fixed_quotes)
            log_system(f"[JSON修复] 单引号替换为双引号修复成功")
            return result
        except json.JSONDecodeError:
            pass

    # Step 5: Fix unquoted keys
    fixed_keys = re.sub(
        r'([{,])\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:',
        r'\1"\2":',
        json_str
    )
    fixed_keys = re.sub(r",\s*([}\]])", r"\1", fixed_keys)
    try:
        result = json.loads(fixed_keys)
        log_system(f"[JSON修复] 未加引号的键名修复成功")
        return result
    except json.JSONDecodeError:
        pass

    return None


def parse_agent_output(raw_output: str) -> "AgentNote":
    from src.models import AgentNote

    reasoning = ""
    structured = {}

    # Extract REASONING: between REASONING and the next section marker
    reasoning_match = re.search(
        r"=====REASONING=====\s*(.*?)\s*=====(?:NARRATIVE|STRUCTURED)=====",
        raw_output, re.DOTALL
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

    # Extract STRUCTURED: from STRUCTURED to end of text
    structured_match = re.search(
        r"=====STRUCTURED=====\s*(.*?)$",
        raw_output, re.DOTALL
    )
    if structured_match:
        structured_str = structured_match.group(1).strip()
        result = _recover_json(structured_str)
        if result is not None:
            structured = result
        else:
            snippet = structured_str[:200] + ("..." if len(structured_str) > 200 else "")
            log_system(
                f"[JSON解析] 所有修复尝试均失败，回退为raw。"
                f" 原始内容前200字符: {snippet}"
            )
            structured = {"raw": structured_str}
    else:
        log_system(f"[JSON解析] 输出中未找到 =====STRUCTURED===== 标记。"
                   f" 原始输出前200字符: {raw_output[:200]}")

    # If structured has no "narrative" but there is a NARRATIVE section, extract it
    if "narrative" not in structured:
        narrative_match = re.search(
            r"=====NARRATIVE=====\s*(.*?)\s*=====STRUCTURED=====",
            raw_output, re.DOTALL
        )
        if narrative_match:
            structured["narrative"] = narrative_match.group(1).strip()

    return AgentNote(reasoning=reasoning, structured=structured)
