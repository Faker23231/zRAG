# zzk/web/service/demo_service.py
"""
内置示例知识库服务。

示例项目不依赖 Milvus / MinerU：资料随项目内置，检索用轻量的中文词元匹配完成，
回答仍然走同一套通用 RAG 提示词与大模型流式输出，保证「打开就能体验」。
"""
from __future__ import annotations

import json
import re
import threading
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from langchain.chat_models import init_chat_model

from zzk.config.config import LLMConfig
from zzk.config.prompt import ANSWER_PROMPT
from zzk.tool.logger import logger
from zzk.tool.task_utils import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    add_done_task,
    add_running_task,
    get_task_info,
    put_data,
    update_task_status,
)
from zzk.web.service.history_service import append_message, recent_messages

DEMO_FILE = Path(__file__).resolve().parent.parent / "data" / "demos.json"

_ZH_RE = re.compile(r"[\u4e00-\u9fff]+")
_EN_RE = re.compile(r"[a-z0-9]+")


@lru_cache(maxsize=1)
def _load_all() -> tuple[dict, ...]:
    with open(DEMO_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    demos = data.get("demos") or []
    for demo in demos:
        demo["id"] = str(demo.get("id") or "").strip()
        demo["docs"] = [
            {
                "title": str(doc.get("title") or "未命名资料"),
                "content": str(doc.get("content") or ""),
                "category": str(doc.get("category") or ""),
                "image": str(doc.get("image") or ""),
            }
            for doc in (demo.get("docs") or [])
        ]
    return tuple(demos)


def list_demos() -> list[dict]:
    """给前端用的示例列表：不返回正文，避免首页体积过大。"""
    result = []
    for demo in _load_all():
        result.append({
            "id": demo["id"],
            "title": demo.get("title") or "",
            "subtitle": demo.get("subtitle") or "",
            "tagline": demo.get("tagline") or "",
            "description": demo.get("description") or "",
            "tags": demo.get("tags") or [],
            "accent": demo.get("accent") or "blue",
            "featured": bool(demo.get("featured")),
            "cover": demo.get("cover") or "",
            "hero_images": demo.get("hero_images") or [],
            "stats": demo.get("stats") or {},
            "sections": demo.get("sections") or [],
            "index_terms": demo.get("index_terms") or [],
            "questions": demo.get("questions") or [],
            "doc_count": len(demo.get("docs") or []),
        })
    return result


def get_demo(demo_id: str) -> dict | None:
    for demo in _load_all():
        if demo["id"] == demo_id:
            return demo
    return None


# ---------------------------------------------------------------------------
# 轻量检索：中文二元词 + 英文/数字词元，标题加权
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    text = (text or "").lower()
    tokens: set[str] = set(_EN_RE.findall(text))
    for seg in _ZH_RE.findall(text):
        if len(seg) == 1:
            tokens.add(seg)
        else:
            tokens.update(seg[i:i + 2] for i in range(len(seg) - 1))
    return tokens


def _doc_score(query: str, query_tokens: set[str], doc: dict) -> float:
    title_tokens = _tokens(doc.get("title", ""))
    body_tokens = _tokens(f"{doc.get('category', '')} {doc.get('content', '')}")
    score = 3.0 * len(query_tokens & title_tokens) + 1.0 * len(query_tokens & body_tokens)
    # 问题里出现标题原文时额外加权，命中更稳定
    title = doc.get("title", "")
    if title and title in query:
        score += 6.0
    # 问题点名了条目（如「虎先锋」）时，条目本身必须排在通用机制之上
    entity = _entity_name(doc)
    if len(entity) >= 2 and entity in query:
        score += 10.0
    return score


def _entity_name(doc: dict) -> str:
    title = str(doc.get("title") or "")
    return re.split(r"[：:｜|]", title, maxsplit=1)[0].strip() or title


def _entity_hint(doc: dict) -> str:
    title = str(doc.get("title") or "")
    parts = re.split(r"[：:｜|]", title, maxsplit=1)
    detail = parts[1].strip() if len(parts) > 1 else ""
    category = str(doc.get("category") or "").strip()
    return " · ".join(item for item in (category, detail) if item)


def retrieve(demo: dict, query: str, top_k: int = 4) -> list[dict]:
    query_tokens = _tokens(query)
    scored: list[tuple[float, dict]] = []
    for doc in demo.get("docs") or []:
        scored.append((_doc_score(query, query_tokens, doc), doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    hits = [doc for score, doc in scored if score > 0][:top_k]
    if not hits:
        # 没有明显命中时给出该示例的通用资料，让模型据此说明“资料不足”
        hits = [doc for _, doc in scored[:2]]
    return hits


def _history_text(session_id: str) -> str:
    messages = recent_messages(session_id, n=10)
    return "\n".join(f'{m.get("role")}: {m.get("text")}' for m in messages)


def _build_context(docs: Iterable[dict], max_chars: int = 9000) -> str:
    context = ""
    for idx, doc in enumerate(docs, start=1):
        chunk = (
            f"[切片:{idx}]\n[标题:{doc.get('title')}]\n[内容:{doc.get('content')}]\n"
            f"[链接:]\n[来源:demo]\n\n"
        )
        if len(context) + len(chunk) > max_chars:
            break
        context += chunk
    return context


def _sources(pairs: Iterable[tuple[int, dict]]) -> list[dict]:
    return [
        {
            "index": idx,
            "title": doc.get("title") or "示例资料",
            "file_title": "内置示例知识库",
            "content": (doc.get("content") or "")[:220],
            "url": "",
            "image": doc.get("image") or "",
            "category": doc.get("category") or "",
            "source": "demo",
        }
        for idx, doc in pairs
    ]


# ---------------------------------------------------------------------------
# 追问澄清：问题太宽泛 / 只给了名字时，先确认玩家到底想了解什么
# ---------------------------------------------------------------------------

CLARIFY_INTENTS: tuple[dict, ...] = (
    {
        "label": "招式与打法",
        "value": "招式怎么应对，输出窗口在哪里",
        "keywords": ("怎么打", "打法", "招式", "弱点", "躲", "应对", "输出", "打不过", "难打"),
    },
    {
        "label": "位置与前置",
        "value": "在哪里，需要什么前置条件",
        "keywords": ("在哪", "位置", "哪里", "怎么去", "前置", "条件", "解锁", "入口", "进入"),
    },
    {
        "label": "掉落与奖励",
        "value": "击败或完成后能获得什么",
        "keywords": ("掉落", "奖励", "获得", "给什么", "材料", "有什么用", "值得"),
    },
    {
        "label": "配装与准备",
        "value": "推荐用什么装备、法宝和葫芦",
        "keywords": ("配装", "装备", "准备", "等级", "推荐", "法宝", "葫芦", "加点"),
    },
)


def clarify(demo: dict, query: str) -> dict:
    """返回是否需要追问，以及可供玩家点选的条目 / 意图。

    纯启发式，不调用大模型：只要问题里没有明确条目、或只有条目没有意图，
    前端就弹出确认框，让玩家两步选完再提问。
    """
    text = (query or "").strip()
    # 去掉「怎么打 / 在哪 / 有什么用」这类意图词，只用来找条目，避免误命中标题里的单字
    entity_text = text
    for item in CLARIFY_INTENTS:
        for word in item["keywords"]:
            entity_text = entity_text.replace(word, " ")
    entity_tokens = _tokens(entity_text)
    ranked = sorted(
        ((_doc_score(text, entity_tokens, doc), doc) for doc in (demo.get("docs") or [])),
        key=lambda item: item[0],
        reverse=True,
    )
    scored = ranked
    entities: list[dict] = []
    seen: set[str] = set()
    for score, doc in scored:
        name = _entity_name(doc)
        if not name or name in seen:
            continue
        seen.add(name)
        entities.append({"name": name, "hint": _entity_hint(doc), "value": name})
        if len(entities) >= 4:
            break

    matched_entities = [item for item in entities if len(item["name"]) >= 2 and item["name"] in text]
    matched_intents = [
        {"label": item["label"], "value": item["value"]}
        for item in CLARIFY_INTENTS
        if any(word in text for word in item["keywords"])
    ]

    compact = re.sub(r"[\s，。！？、,.!?~～…]+", "", text)
    too_short = len(compact) <= 4 and not matched_entities
    entity_only = bool(matched_entities) and len(compact) <= len(matched_entities[0]["name"]) + 1
    entity_without_intent = bool(matched_entities) and not matched_intents and entity_only
    intent_without_entity = bool(matched_intents) and not matched_entities
    # 完全没命中时不追问，交给正常回答说明资料未覆盖；只有“太模糊”或“少了主语/意图”才弹窗
    needed = too_short or entity_without_intent or intent_without_entity

    intents = [{"label": item["label"], "value": item["value"]} for item in CLARIFY_INTENTS]
    if matched_entities:
        hint = f"在《{demo.get('title', '知识库')}》里找到 {len(matched_entities)} 个直接相关的条目"
    else:
        hint = f"《{demo.get('title', '知识库')}》里有 {len(entities)} 个可能相关的条目，先确认一下方向"

    return {
        "needed": needed,
        "question": "再确认一下，你想了解哪一块？",
        "hint": hint,
        "entities": entities,
        "intents": intents,
        "matched_entities": [item["name"] for item in matched_entities],
        "matched_intents": [item["label"] for item in matched_intents],
        "suggestion": text,
    }


def _fallback_answer(query: str, docs: list[dict]) -> str:
    """大模型不可用时的兜底：直接摘录最相关的段落。"""
    if not docs:
        return "示例资料里没有找到与这个问题相关的内容。可以换个问法，或试着问示例问题。"
    best = docs[0]
    return (
        f"（示例资料摘要）{best.get('title')}：\n\n{best.get('content')}\n\n"
        f"当前未能连接到大模型，以上是与「{query}」最相关的示例资料原文。"
    )


def stream_demo_answer(task_id: str, session_id: str, demo: dict, query: str) -> None:
    """在后台线程中执行：检索示例资料 → 流式生成回答 → 落库。"""
    try:
        update_task_status(task_id, TASK_STATUS_PROCESSING)
        history_text = _history_text(session_id)
        append_message(session_id, "user", query)
        put_data(task_id, event="progress", data=get_task_info(task_id))

        add_running_task(task_id, "demo_analyze")
        put_data(task_id, event="progress", data=get_task_info(task_id))
        add_done_task(task_id, "demo_analyze")

        add_running_task(task_id, "demo_retrieve")
        put_data(task_id, event="progress", data=get_task_info(task_id))
        docs = retrieve(demo, query)
        add_done_task(task_id, "demo_retrieve")
        put_data(task_id, event="progress", data=get_task_info(task_id))

        add_running_task(task_id, "demo_answer")
        put_data(task_id, event="progress", data=get_task_info(task_id))

        answer = ""
        prompt = ANSWER_PROMPT.format(
            context=_build_context(docs),
            history=history_text,
            item_names=demo.get("title", ""),
            question=query,
        )

        try:
            llm = init_chat_model(
                model=LLMConfig.llm_default_model,
                model_provider="openai",
                base_url=LLMConfig.openai_api_base,
                api_key=LLMConfig.openai_api_key,
                temperature=LLMConfig.llm_default_temperature,
            )
            for chunk in llm.stream(input=[{"role": "user", "content": prompt}]):
                delta = chunk.content or ""
                if not delta:
                    continue
                answer += delta
                put_data(task_id, event="delta", data={"delta": delta})
        except Exception as e:
            logger.error(f"示例问答调用大模型失败: {e}")
            answer = _fallback_answer(query, docs)
            put_data(task_id, event="delta", data={"delta": answer})

        add_done_task(task_id, "demo_answer")
        update_task_status(task_id, TASK_STATUS_COMPLETED)

        append_message(session_id, "assistant", answer)

        # 只回传答案真正引用到的切片，避免把检索噪声也算作“引用”
        cited = sorted({
            int(num) for num in re.findall(r"\[(?:切片\s*[:：]\s*)?(\d{1,2})\]", answer)
            if 1 <= int(num) <= len(docs)
        })
        cited_pairs = [(idx, docs[idx - 1]) for idx in cited]
        if not cited_pairs:
            cited_pairs = list(enumerate(docs[:3], start=1))

        # 优先展示问题点名条目自己的图；没有问题条目时才退回引用切片的配图
        named = [doc for _, doc in cited_pairs if doc.get("image") and _entity_name(doc) in query]
        picked = named or [doc for _, doc in cited_pairs if doc.get("image")]
        image_urls: list[str] = []
        for doc in picked:
            image = doc.get("image") or ""
            if image and image not in image_urls:
                image_urls.append(image)

        put_data(task_id, event="final", data={
            "answer": answer,
            "image_urls": image_urls[:2],
            "sources": _sources(cited_pairs),
        })
        put_data(task_id, event="progress", data=get_task_info(task_id))
    except Exception as e:
        logger.error(f"示例问答执行失败: {e}")
        put_data(task_id, event="error", data={"message": f"示例问答执行失败: {e}"})
        update_task_status(task_id, TASK_STATUS_FAILED)
