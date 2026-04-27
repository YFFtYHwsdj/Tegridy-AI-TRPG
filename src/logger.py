from __future__ import annotations

import os
import json
from datetime import datetime

_session_log_file = None
_call_index = 0


def init_log(project_root: str):
    global _session_log_file, _call_index
    _call_index = 0
    logs_dir = os.path.join(project_root, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    _session_log_file = os.path.join(logs_dir, f"{timestamp}_session.log")
    with open(_session_log_file, "w", encoding="utf-8") as f:
        f.write(f"╔══════════════════════════════════════════════════════════╗\n")
        f.write(f"║  Tegridy-AI-TRPG  API 调用日志                         ║\n")
        f.write(f"║  会话: {timestamp}                              ║\n")
        f.write(f"╚══════════════════════════════════════════════════════════╝\n\n")
    return _session_log_file


def log_call(agent_name: str, system_prompt: str, user_message: str, response: str, usage_info: dict | None = None):
    global _session_log_file, _call_index
    if _session_log_file is None:
        return

    _call_index += 1

    with open(_session_log_file, "a", encoding="utf-8") as f:
        f.write(f"{'─' * 70}\n")
        f.write(f"调用 #{_call_index} | Agent: {agent_name}\n")
        f.write(f"时间: {datetime.now().strftime('%H:%M:%S.%f')[:-3]}\n")

        if usage_info:
            prompt = usage_info.get("prompt_tokens", 0)
            completion = usage_info.get("completion_tokens", 0)
            total = usage_info.get("total_tokens", 0)
            cached = usage_info.get("cached_tokens")
            if cached is not None:
                uncached = prompt - cached
                f.write(f"Token: 提示 {prompt} (缓存 {cached} + 未缓存 {uncached}) | 生成 {completion} | 合计 {total}\n")
            else:
                f.write(f"Token: 提示 {prompt} (无缓存命中) | 生成 {completion} | 合计 {total}\n")

        f.write(f"{'─' * 70}\n\n")

        f.write(f"┌─── SYSTEM PROMPT ───────────────────────────────────────\n")
        for line in system_prompt.split("\n"):
            f.write(f"│ {line}\n")
        f.write(f"└──────────────────────────────────────────────────────────\n\n")

        f.write(f"┌─── USER MESSAGE ────────────────────────────────────────\n")
        for line in user_message.split("\n"):
            f.write(f"│ {line}\n")
        f.write(f"└──────────────────────────────────────────────────────────\n\n")

        f.write(f"┌─── RESPONSE ────────────────────────────────────────────\n")
        for line in response.split("\n"):
            f.write(f"│ {line}\n")
        f.write(f"└──────────────────────────────────────────────────────────\n\n\n")


def log_system(msg: str):
    global _session_log_file
    if _session_log_file is None:
        return
    with open(_session_log_file, "a", encoding="utf-8") as f:
        f.write(f"[系统] {msg}\n\n")


def log_roll(power: int, dice: tuple, total: int, outcome: str, power_tags: list, weakness_tags: list):
    global _session_log_file
    if _session_log_file is None:
        return
    with open(_session_log_file, "a", encoding="utf-8") as f:
        f.write(f"{'─' * 70}\n")
        f.write(f"[代码] 力量计算 & 掷骰\n")
        f.write(f"  匹配力量标签: {power_tags}\n")
        f.write(f"  匹配弱点标签: {weakness_tags}\n")
        f.write(f"  力量: {power}\n")
        f.write(f"  掷骰: {dice[0]} + {dice[1]} + {power} = {total} → {outcome}\n")
        f.write(f"{'─' * 70}\n\n")


def log_status_update(entity_name: str, statuses: dict):
    global _session_log_file
    if _session_log_file is None:
        return
    with open(_session_log_file, "a", encoding="utf-8") as f:
        if not statuses:
            f.write(f"[代码] 状态更新: {entity_name} → (无状态)\n\n")
        else:
            f.write(f"[代码] 状态更新: {entity_name}\n")
            for name, s in statuses.items():
                f.write(f"  {name}: 等级{s.current_tier} (格子: {sorted(s.ticked_boxes)})\n")
            f.write("\n")
