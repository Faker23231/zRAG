# zzk/web/service/chat_service.py
"""
对话服务：把「示例项目」和「用户项目」统一成一条 SSE 流。

- 示例项目：走内置资料检索（demo_service），不依赖 Milvus / MinerU。
- 用户项目：走完整查询图谱（HyDE + 混合检索 + RRF + 重排 + 生成），
  并通过 scope_item_names 把检索范围锁定在该项目对应的知识主体上。
"""
from __future__ import annotations

import json
import threading
import time
import uuid

from zzk.tool.logger import logger
from zzk.tool.task_utils import (
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    clear_queue,
    create_queue,
    get_data_timeout,
    get_task_info,
    get_task_status,
    put_data,
    reset_task,
    update_task_status,
)
from zzk.web.service import demo_service, project_service

# SSE 最长连接时间（秒），防止异常任务把连接挂死
MAX_STREAM_SECONDS = 900
# 没有新事件时发心跳的间隔（秒）
HEARTBEAT_SECONDS = 15


def default_session_id(project_id: str) -> str:
    return f"sess_{project_id}"


def _resolve_project(project_id: str) -> tuple[str, dict]:
    """返回 (kind, project)；kind ∈ {demo, upload}。"""
    demo = demo_service.get_demo(project_id)
    if demo:
        return "demo", demo
    project = project_service.get_project(project_id)
    if project:
        return "upload", project
    raise ValueError("项目不存在或已被删除")


def start_chat(project_id: str, message: str, session_id: str | None = None) -> dict:
    message = (message or "").strip()
    if not message:
        raise ValueError("问题不能为空")

    kind, project = _resolve_project(project_id)
    if kind == "upload" and project.get("status") != project_service.PROJECT_READY:
        if project.get("status") == project_service.PROJECT_FAILED:
            raise ValueError("这个项目导入失败了，请删除后重新上传 PDF")
        raise ValueError("项目还在解析中，请稍候再提问")

    session_id = session_id or default_session_id(project_id)
    task_id = f"chat_{uuid.uuid4().hex[:12]}"

    reset_task(task_id)
    create_queue(task_id)

    if kind == "demo":
        thread = threading.Thread(
            target=demo_service.stream_demo_answer,
            args=(task_id, session_id, project, message),
            name=f"demo-{task_id}",
            daemon=True,
        )
    else:
        item_name = project.get("item_name") or project.get("title")
        thread = threading.Thread(
            target=_run_upload_chat,
            args=(task_id, session_id, message, item_name),
            name=f"chat-{task_id}",
            daemon=True,
        )
    thread.start()

    return {
        "task_id": task_id,
        "session_id": session_id,
        "project_id": project_id,
        "project_title": project.get("title") or "",
    }


def _run_upload_chat(task_id: str, session_id: str, message: str, item_name: str) -> None:
    from zzk.query_process.main_graph import QueryMainGraphRunner

    try:
        update_task_status(task_id, TASK_STATUS_PROCESSING)
        QueryMainGraphRunner.create_and_run({
            "task_id": task_id,
            "session_id": session_id,
            "original_query": message,
            "scope_item_names": [item_name] if item_name else [],
        })
        update_task_status(task_id, TASK_STATUS_COMPLETED)
        put_data(task_id, event="progress", data=get_task_info(task_id))
    except Exception as e:
        logger.error(f"项目问答执行失败: {e}")
        put_data(task_id, event="error", data={"message": f"问答执行失败：{e}"})
        update_task_status(task_id, TASK_STATUS_FAILED)


def _schedule_cleanup(task_id: str, delay: float = 120) -> None:
    """延迟释放队列：图节点在 final 之后还可能补一条 progress，立即清空会让它空等。"""
    timer = threading.Timer(delay, clear_queue, args=(task_id,))
    timer.daemon = True
    timer.start()


def sse_stream(task_id: str):
    """生成 SSE 事件流；收到 final / error 后主动结束，避免连接永久悬挂。"""
    started = time.time()
    last_beat = time.time()
    finished = False

    try:
        while True:
            if time.time() - started > MAX_STREAM_SECONDS:
                yield f"event: error\ndata: {json.dumps({'message': '处理超时，请重试'}, ensure_ascii=False)}\n\n"
                finished = True
                break

            item = get_data_timeout(task_id, timeout=1)
            if item is None:
                status = get_task_status(task_id)
                if status == TASK_STATUS_FAILED:
                    yield f"event: error\ndata: {json.dumps({'message': '任务执行失败'}, ensure_ascii=False)}\n\n"
                    finished = True
                    break
                if time.time() - last_beat >= HEARTBEAT_SECONDS:
                    last_beat = time.time()
                    yield ": ping\n\n"
                time.sleep(0.2)
                continue

            event = item.get("event") or "message"
            data = item.get("data")
            if not isinstance(data, str):
                data = json.dumps(data, ensure_ascii=False)
            yield f"event: {event}\ndata: {data}\n\n"

            if event in ("final", "error"):
                finished = True
                break
    finally:
        # 正常结束给图节点留出补发事件的时间；客户端断开时也保留一段时间，
        # 避免后台任务写入队列时长时间阻塞。
        _schedule_cleanup(task_id, 30 if finished else 300)
