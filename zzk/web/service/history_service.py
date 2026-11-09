# zzk/web/service/history_service.py
"""
会话历史读写。

MongoDB 是首选存储（与查询图共用 chat_message 集合）；
当 Mongo 不可用时退化为进程内存储，保证示例演示仍能正常对话。
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Any

from zzk.tool.logger import logger
from zzk.tool.mongo_tool import clear_history, get_recent_messages, save_chat_message

_LOCK = threading.Lock()
_MEMORY: dict[str, list[dict]] = defaultdict(list)


def append_message(session_id: str, role: str, text: str, **extra: Any) -> None:
    if not session_id or not text:
        return
    ts = time.time()
    with _LOCK:
        _MEMORY[session_id].append({"role": role, "text": text, "ts": ts, **extra})
        # 本地兜底只保留最近 200 条
        _MEMORY[session_id] = _MEMORY[session_id][-200:]
    try:
        save_chat_message(session_id, role, text)
    except Exception as e:
        logger.warning(f"写入 Mongo 会话历史失败，已使用本地兜底: {e}")


def recent_messages(session_id: str, n: int = 50) -> list[dict]:
    """按时间正序返回最近 n 条消息。"""
    if not session_id:
        return []
    try:
        messages = get_recent_messages(session_id, n=n)
        if messages:
            result = []
            for item in messages:
                result.append({
                    "id": str(item.get("_id")),
                    "role": item.get("role") or "",
                    "text": item.get("text") or "",
                    "ts": item.get("ts"),
                    "item_names": item.get("item_names") or [],
                })
            result.sort(key=lambda item: item.get("ts") or 0)
            return result
    except Exception as e:
        logger.warning(f"读取 Mongo 会话历史失败，已使用本地兜底: {e}")

    with _LOCK:
        messages = list(_MEMORY.get(session_id, []))
    return [
        {
            "id": f"local-{idx}",
            "role": item.get("role") or "",
            "text": item.get("text") or "",
            "ts": item.get("ts"),
            "item_names": [],
        }
        for idx, item in enumerate(messages[-n:])
    ]


def clear_messages(session_id: str) -> None:
    with _LOCK:
        _MEMORY.pop(session_id, None)
    try:
        clear_history(session_id)
    except Exception as e:
        logger.warning(f"清空 Mongo 会话历史失败: {e}")
