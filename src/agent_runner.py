from __future__ import annotations

import json
import re
from src.llm_client import LLMClient
from src.models import AgentNote, Challenge
from src.logger import log_call, log_system


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

    # Step 3: Balanced-brace extraction (handles nested JSON, avoids greedy .* ）
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

    # Step 5: Fix unquoted keys (common in some LLM outputs)
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


def parse_agent_output(raw_output: str) -> AgentNote:
    reasoning = ""
    structured = {}

    reasoning_match = re.search(
        r"=====REASONING=====\s*(.*?)\s*=====STRUCTURED=====",
        raw_output, re.DOTALL
    )
    if reasoning_match:
        reasoning = reasoning_match.group(1).strip()

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

    return AgentNote(reasoning=reasoning, structured=structured)


def format_role_tags(tags: list) -> str:
    lines = []
    for tag in tags:
        desc = f" ({tag.description})" if tag.description else ""
        lines.append(f"  - [{tag.tag_type}] {tag.name}{desc}")
    return "\n".join(lines)


def format_statuses(statuses: dict) -> str:
    if not statuses:
        return "  (无当前状态)"
    lines = []
    for name, status in statuses.items():
        ticked = sorted(status.ticked_boxes) if status.ticked_boxes else []
        lines.append(f"  - {name}: 等级{status.current_tier} (勾选: {ticked})")
    return "\n".join(lines)


def format_limit_progress(limit, current: int) -> str:
    prog = "/".join("█" * current + "░" * (limit.max_tier - current))
    return f"{limit.name}: [{prog}] {current}/{limit.max_tier}"


def format_challenge_state(challenge) -> str:
    lines = [
        f"挑战: {challenge.name}",
        f"描述: {challenge.description}",
    ]
    if challenge.notes:
        lines.append(f"便签: {challenge.notes}")
    lines.append("极限:")
    for limit in challenge.limits:
        matching = challenge.get_matching_statuses(limit.name)
        current = max((s.current_tier for s in matching), default=0)
        lines.append(f"  - {format_limit_progress(limit, current)}")
    if challenge.base_tags:
        lines.append(f"基础标签: {', '.join(t.name for t in challenge.base_tags)}")
    lines.append("威胁列表:")
    for i, threat in enumerate(challenge.threats, 1):
        lines.append(f"  {i}. {threat}")
    lines.append(f"当前状态: {format_statuses(challenge.statuses)}")
    return "\n".join(lines)


class AgentRunner:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run_agent(self, system_prompt: str, user_message: str, agent_name: str) -> AgentNote:
        print(f"\n  [{agent_name}] 调用中...", end=" ", flush=True)
        raw = self.llm.chat(system_prompt, user_message)
        log_call(agent_name, system_prompt, user_message, raw)
        print("完成")
        return parse_agent_output(raw)

    def run_rhythm_agent(self, scene_description: str) -> AgentNote:
        from src.agent_prompts import AGENT_0_RHYTHM
        user_msg = f"""{scene_description}

请用生动的叙事建立场景，最后把聚光灯交给玩家。"""
        return self.run_agent(AGENT_0_RHYTHM, user_msg, "节奏Agent")

    def run_move_gatekeeper(
        self, player_input: str,
        context_block: str, narrative_block: str,
        character, challenge,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_0_5_MOVE_GATEKEEPER
        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

---
玩家输入: {player_input}

请判断这个输入是否构成一个需要掷骰的Move。"""
        return self.run_agent(AGENT_0_5_MOVE_GATEKEEPER, user_msg, "Move守门人")

    def run_lite_narrator(
        self,
        player_input: str,
        context_block: str, narrative_block: str,
        character, challenge,
        gatekeeper_reasoning: str,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_4_LITE_NARRATOR
        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

守门人判断: {gatekeeper_reasoning}

玩家输入（叙事性交互，不掷骰）: {player_input}

请生成一段叙事回应，推动场景前进。"""
        return self.run_agent(AGENT_4_LITE_NARRATOR, user_msg, "叙述者(轻量)")

    def run_intent_agent(
        self, player_input: str,
        context_block: str, narrative_block: str,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_1A_INTENT
        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

---
玩家输入: {player_input}

请解析玩家的意图。"""
        return self.run_agent(AGENT_1A_INTENT, user_msg, "意图解析Agent")

    def run_tag_agent(
        self,
        intent_note: AgentNote,
        context_block: str, narrative_block: str,
        character, challenge,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_1B_TAGS

        power_tags_str = format_role_tags(character.power_tags)
        weakness_tags_str = format_role_tags(character.weakness_tags)
        status_str = format_statuses(character.statuses)

        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

角色力量标签:
{power_tags_str}

角色弱点标签:
{weakness_tags_str}

角色当前状态:
{status_str}

---
意图解析:
  行动类型: {intent_note.structured.get('action_type', 'unknown')}
  行动摘要: {intent_note.structured.get('action_summary', '')}
  是否拆分: {intent_note.structured.get('is_split_action', False)}

请判断哪些标签帮助/阻碍本次行动，以及角色当前状态中哪些帮助哪些阻碍。"""
        return self.run_agent(AGENT_1B_TAGS, user_msg, "标签匹配Agent")

    def run_effect_actualization_agent(
        self,
        intent_note: AgentNote,
        tag_note: AgentNote,
        roll_result,
        context_block: str, narrative_block: str,
        character, challenge,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_2_EFFECT_ACTUALIZATION

        if roll_result.outcome == "failure":
            return AgentNote(
                reasoning="掷骰结果为失败，不产生效果",
                structured={"effects": [], "narrative_hints": ""}
            )

        power_tags_str = format_role_tags(character.power_tags)
        available_power = max(roll_result.power, 0)
        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

角色能力标签:
{power_tags_str}

意图解析:
  reasoning: {intent_note.reasoning}
  action_type: {intent_note.structured.get('action_type', 'unknown')}
  action_summary: {intent_note.structured.get('action_summary', '')}

标签匹配:
  reasoning: {tag_note.reasoning}
  matched_power_tags: {json.dumps(tag_note.structured.get('matched_power_tags', []), ensure_ascii=False)}
  matched_weakness_tags: {json.dumps(tag_note.structured.get('matched_weakness_tags', []), ensure_ascii=False)}

挑战: {format_challenge_state(challenge)}

---
掷骰结果: {roll_info}
可用力量: {available_power} (你生成所有效果的tier之和 必须 ≤ {available_power}。每1级状态=1力量，每1标签=2力量)

请推演此行动在故事中实际产生什么效果。首先选择合适的效果类型，然后在可用力量预算内确定效果等级。"""
        return self.run_agent(AGENT_2_EFFECT_ACTUALIZATION, user_msg, "效果推演Agent")

    def run_consequence_agent(
        self,
        intent_note: AgentNote,
        effect_note: AgentNote,
        roll_result,
        context_block: str, narrative_block: str,
        challenge,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_3_CONSEQUENCE

        roll_info = f"power={roll_result.power}, dice={roll_result.dice}, total={roll_result.total}, outcome={roll_result.outcome}"

        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

{format_challenge_state(challenge)}

效果推演推理: {effect_note.reasoning}
已产生的效果: {json.dumps(effect_note.structured.get('effects', []), ensure_ascii=False)}

---
行动摘要: {intent_note.structured.get('action_summary', '')}
掷骰结果: {roll_info}

请从挑战的威胁列表中选择并兑现后果。{'(部分成功)' if roll_result.outcome == 'partial_success' else '(失败)'}"""
        return self.run_agent(AGENT_3_CONSEQUENCE, user_msg, "后果Agent")

    def run_narrator_agent(
        self,
        intent_note: AgentNote,
        effect_note: AgentNote,
        consequence_note: AgentNote | None,
        roll_result,
        context_block: str, narrative_block: str,
        character, challenge,
        player_input: str,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_4_NARRATOR

        roll_summary = f"{roll_result.dice[0]}+{roll_result.dice[1]}+{roll_result.power}={roll_result.total} ({roll_result.outcome})"

        cons_reasoning = ""
        cons_structured = {}
        if consequence_note:
            cons_reasoning = consequence_note.reasoning
            cons_structured = consequence_note.structured

        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

效果推演推理: {effect_note.reasoning}
效果: {json.dumps(effect_note.structured.get('effects', []), ensure_ascii=False)}
叙事提示: {effect_note.structured.get('narrative_hints', '')}

后果推理: {cons_reasoning}
后果: {json.dumps(cons_structured.get('consequences', []), ensure_ascii=False)}

---
玩家行动: {player_input}
掷骰: {roll_summary}

请将以上结构化的游戏结果翻译为沉浸式的叙事文本。"""
        return self.run_agent(AGENT_4_NARRATOR, user_msg, "叙述者Agent")

    def run_limit_break_agent(
        self,
        limit_names: list[str],
        challenge: Challenge,
        context_block: str, narrative_block: str,
    ) -> AgentNote:
        from src.agent_prompts import AGENT_5_LIMIT_BREAK

        limits_detail = []
        for name in limit_names:
            for limit in challenge.limits:
                if limit.name == name:
                    matching = challenge.get_matching_statuses(limit.name)
                    current = max((s.current_tier for s in matching), default=0)
                    limits_detail.append(f"  {limit.name}: {current}/{limit.max_tier} (极限突破!)")
                    break

        user_msg = f"""{context_block}

叙事历史:
{narrative_block}

{format_challenge_state(challenge)}

---
突破的极限:
{chr(10).join(limits_detail)}

请生成这个转折时刻的叙事。描述发生了什么——挑战方的某个防御被粉碎了。"""
