# zzk/web/service/project_service.py
"""
用户项目服务：PDF 落盘、导入图谱执行、项目注册表读写。

项目是「一次上传 + 一个知识主体」的组合，对话时只在这份文档的范围内检索。
"""
from __future__ import annotations

import json
import os
import shutil
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path

from zzk.config.config import MinioConfig
from zzk.tool.logger import logger
from zzk.tool.task_utils import (
    TASK_STATUS_FAILED,
    TASK_STATUS_PROCESSING,
    add_done_task,
    add_node_duration,
    add_running_task,
    get_task_info,
    update_task_status,
)

# 仓库根目录：zzk/web/service -> zzk/web -> zzk -> 项目根
BASE_DIR = Path(__file__).resolve().parents[3]
DATA_DIR = Path(os.getenv("RAG_DATA_DIR", BASE_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"
REGISTRY_FILE = DATA_DIR / "projects.json"

_LOCK = threading.RLock()

PROJECT_QUEUED = "processing"
PROJECT_READY = "ready"
PROJECT_FAILED = "failed"


# ---------------------------------------------------------------------------
# 注册表
# ---------------------------------------------------------------------------

def _ensure_dirs() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _load_registry() -> dict:
    _ensure_dirs()
    if not REGISTRY_FILE.exists():
        return {"projects": []}
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"projects": []}
        data.setdefault("projects", [])
        return data
    except Exception as e:
        logger.error(f"读取项目注册表失败: {e}")
        return {"projects": []}


def _save_registry(data: dict) -> None:
    _ensure_dirs()
    tmp = REGISTRY_FILE.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(REGISTRY_FILE)


def _public(project: dict) -> dict:
    return {
        "id": project["id"],
        "kind": "upload",
        "title": project.get("title") or project.get("file_name") or "未命名项目",
        "subtitle": project.get("file_name") or "",
        "status": project.get("status") or PROJECT_FAILED,
        "item_name": project.get("item_name"),
        "file_name": project.get("file_name"),
        "file_size": project.get("file_size") or 0,
        "created_at": project.get("created_at"),
        "error": project.get("error"),
        "doc_count": project.get("chunk_count") or 0,
    }


def list_projects() -> list[dict]:
    with _LOCK:
        data = _load_registry()
        projects = sorted(data["projects"], key=lambda p: p.get("created_at") or 0, reverse=True)
        return [_public(p) for p in projects]


def get_project(project_id: str) -> dict | None:
    with _LOCK:
        data = _load_registry()
        for project in data["projects"]:
            if project.get("id") == project_id:
                return dict(project)
    return None


def _update_project(project_id: str, **fields) -> None:
    with _LOCK:
        data = _load_registry()
        for project in data["projects"]:
            if project.get("id") == project_id:
                project.update(fields)
                project["updated_at"] = time.time()
                break
        _save_registry(data)


def project_snapshot(project_id: str) -> dict | None:
    project = get_project(project_id)
    if not project:
        return None
    snapshot = _public(project)
    task_id = project.get("task_id")
    snapshot["progress"] = get_task_info(task_id) if task_id else {
        "status": "", "running_list": [], "done_list": [], "durations": {}
    }
    return snapshot


# ---------------------------------------------------------------------------
# 上传与导入
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    name = Path(name or "document.pdf").name
    name = name.replace("/", "_").replace("\\", "_").strip()
    return name or "document.pdf"


def create_project(filename: str, file_bytes: bytes) -> dict:
    """保存 PDF 并登记项目，返回项目快照。导入在后台线程执行。"""
    safe_name = _safe_filename(filename)
    if not safe_name.lower().endswith(".pdf"):
        raise ValueError("目前只支持上传 PDF 文件")

    project_id = f"prj_{uuid.uuid4().hex[:10]}"
    task_id = f"imp_{uuid.uuid4().hex[:10]}"
    project_dir = UPLOAD_DIR / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    file_path = project_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    title = Path(safe_name).stem
    project = {
        "id": project_id,
        "kind": "upload",
        "title": title,
        "file_name": safe_name,
        "file_size": len(file_bytes),
        "file_path": str(file_path),
        "local_dir": str(project_dir),
        "status": PROJECT_QUEUED,
        "task_id": task_id,
        "item_name": None,
        "chunk_count": 0,
        "error": None,
        "created_at": time.time(),
        "updated_at": time.time(),
    }
    with _LOCK:
        data = _load_registry()
        data["projects"].append(project)
        _save_registry(data)

    thread = threading.Thread(
        target=_run_import,
        args=(project_id, task_id, str(file_path), str(project_dir), safe_name),
        name=f"import-{project_id}",
        daemon=True,
    )
    thread.start()
    return project_snapshot(project_id)


def _archive_to_minio(file_path: str, file_name: str) -> None:
    """原文件归档，失败不影响导入主流程。"""
    try:
        from zzk.tool.minio_client_tool import get_minio_client

        client = get_minio_client()
        client.fput_object(
            bucket_name=MinioConfig.minio_bucket_name,
            object_name=f"upload_file/{datetime.now().strftime('%Y%m%d')}/{file_name}",
            file_path=file_path,
        )
    except Exception as e:
        logger.warning(f"原始文件归档到 MinIO 失败（不影响导入）: {e}")


def _run_import(project_id: str, task_id: str, file_path: str, local_dir: str, file_name: str) -> None:
    from zzk.import_process.main_graph import MainGraphRunner

    try:
        update_task_status(task_id, TASK_STATUS_PROCESSING)

        # 上传步骤也展示在前端的进度时间线上
        add_running_task(task_id, "upload_file")
        started = time.time()
        _archive_to_minio(file_path, file_name)
        add_done_task(task_id, "upload_file")
        add_node_duration(task_id, "upload_file", time.time() - started)

        result = MainGraphRunner.create_and_run({
            "task_id": task_id,
            "local_file_path": file_path,
            "local_dir": local_dir,
        })
        item_name = (result or {}).get("item_name") or Path(file_name).stem
        chunks = (result or {}).get("chunks") or []
        _update_project(
            project_id,
            status=PROJECT_READY,
            item_name=item_name,
            chunk_count=len(chunks),
            error=None,
        )
        logger.info(f"项目导入完成: {project_id} -> {item_name} ({len(chunks)} 个切片)")
    except Exception as e:
        logger.error(f"项目导入失败 {project_id}: {e}")
        update_task_status(task_id, TASK_STATUS_FAILED)
        _update_project(project_id, status=PROJECT_FAILED, error=str(e))


def recover_stuck_projects() -> int:
    """服务重启后，把上次没跑完的导入任务标记为失败，避免前端无限等待。"""
    with _LOCK:
        data = _load_registry()
        changed = 0
        for project in data["projects"]:
            if project.get("status") == PROJECT_QUEUED:
                project["status"] = PROJECT_FAILED
                project["error"] = "服务重启导致解析中断，请重新上传"
                project["updated_at"] = time.time()
                changed += 1
        if changed:
            _save_registry(data)
    return changed


def delete_project(project_id: str) -> bool:
    with _LOCK:
        data = _load_registry()
        target = None
        remaining = []
        for project in data["projects"]:
            if project.get("id") == project_id:
                target = project
            else:
                remaining.append(project)
        if not target:
            return False
        data["projects"] = remaining
        _save_registry(data)

    project_dir = target.get("local_dir")
    if project_dir:
        try:
            shutil.rmtree(project_dir, ignore_errors=True)
        except Exception:
            pass
    return True
