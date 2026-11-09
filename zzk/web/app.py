# zzk/web/app.py
"""
zRAG —— 统一 Web 服务。

同一个进程里提供：
- 静态前端（首页 / 资料库 / 创建项目 / 多窗口工作台）
- 项目接口（PDF 上传、导入进度、删除）
- 对话接口（POST 建任务 + SSE 流式输出）
- 会话历史接口
- 追问澄清接口

启动：
    uv run uvicorn zzk.web.app:app --host 0.0.0.0 --port 8000
或：
    uv run zrag
"""
from __future__ import annotations

import os
import socket
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from zzk.config.config import LLMConfig, MilvusConfig, MinioConfig, MongoConfig
from zzk.tool.logger import logger
from zzk.web.service import chat_service, demo_service, history_service, project_service

WEB_DIR = Path(__file__).resolve().parent
PAGES_DIR = WEB_DIR / "pages"
ASSETS_DIR = PAGES_DIR / "assets"

MAX_UPLOAD_BYTES = 50 * 1024 * 1024  # 50MB

@asynccontextmanager
async def lifespan(_: FastAPI):
    stuck = project_service.recover_stuck_projects()
    if stuck:
        logger.warning(f"已将 {stuck} 个中断的导入任务标记为失败")
    yield


app = FastAPI(title="zRAG", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


# ---------------------------------------------------------------------------
# 请求体
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    project_id: str = Field(..., description="示例项目或用户项目 id")
    message: str = Field(..., min_length=1, description="用户问题")
    session_id: str | None = Field(default=None, description="会话 id，不传则使用项目默认会话")


class ClarifyRequest(BaseModel):
    project_id: str = Field(..., description="示例项目或用户项目 id")
    message: str = Field(..., min_length=1, description="用户原始问题")


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

def _host_port(url: str | None) -> tuple[str | None, int | None]:
    if not url:
        return None, None
    parsed = urlparse(url if "//" in url else f"//{url}")
    return parsed.hostname, parsed.port


def _tcp_alive(host: str | None, port: int | None, timeout: float = 0.6) -> bool:
    if not host or not port:
        return False
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# 页面
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def index():
    return FileResponse(
        PAGES_DIR / "index.html",
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    icon = ASSETS_DIR / "favicon.svg"
    if icon.exists():
        return FileResponse(icon, media_type="image/svg+xml")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# 基础接口
# ---------------------------------------------------------------------------

@app.get("/api/health")
def health():
    milvus_host, milvus_port = _host_port(MilvusConfig.milvus_url)
    minio_host, minio_port = _host_port(MinioConfig.minio_endpoint)
    services = {
        "milvus": _tcp_alive(milvus_host, milvus_port),
        "minio": _tcp_alive(minio_host, minio_port),
        "mongo": _tcp_alive(MongoConfig.mongo_host, MongoConfig.mongo_port),
    }
    return {
        "status": "ok" if all(services.values()) else "degraded",
        "services": services,
        "llm": bool(LLMConfig.openai_api_key and LLMConfig.openai_api_base),
        "demos": len(demo_service.list_demos()),
    }


@app.get("/api/examples")
def examples():
    return {"items": demo_service.list_demos()}


@app.post("/api/clarify")
def clarify(body: ClarifyRequest):
    """只对内置示例做启发式澄清：判断问题是否宽泛，并给出可点选的方向。"""
    demo = demo_service.get_demo(body.project_id)
    if not demo:
        return {"needed": False}
    return demo_service.clarify(demo, body.message)


# ---------------------------------------------------------------------------
# 项目
# ---------------------------------------------------------------------------

@app.get("/api/projects")
def projects():
    return {"items": project_service.list_projects()}


@app.post("/api/projects")
async def create_project(file: UploadFile = File(...)):
    filename = file.filename or "document.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="目前只支持上传 PDF 文件")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="文件内容为空")
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="PDF 不能超过 50MB")

    try:
        project = project_service.create_project(filename, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建项目失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建项目失败：{e}")

    return {"project": project}


@app.get("/api/projects/{project_id}/status")
def project_status(project_id: str):
    snapshot = project_service.project_snapshot(project_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail="项目不存在")
    return snapshot


@app.delete("/api/projects/{project_id}")
def remove_project(project_id: str):
    if demo_service.get_demo(project_id):
        raise HTTPException(status_code=400, detail="示例项目不能删除")
    if not project_service.delete_project(project_id):
        raise HTTPException(status_code=404, detail="项目不存在")
    return {"deleted": True, "project_id": project_id}


# ---------------------------------------------------------------------------
# 对话
# ---------------------------------------------------------------------------

@app.post("/api/chat")
def chat(body: ChatRequest):
    try:
        return chat_service.start_chat(body.project_id, body.message, body.session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建对话任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建对话任务失败：{e}")


@app.get("/api/stream/{task_id}")
def stream(task_id: str):
    return StreamingResponse(
        chat_service.sse_stream(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/history/{session_id}")
def history(session_id: str):
    messages = history_service.recent_messages(session_id)
    return {"items": messages}


@app.delete("/api/history/{session_id}")
def clear_history(session_id: str):
    history_service.clear_messages(session_id)
    return {"cleared": True, "session_id": session_id}


# ---------------------------------------------------------------------------
# 异常出口
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(f"{request.method} {request.url.path} 执行失败: {exc}")
    return JSONResponse(status_code=500, content={"message": f"服务异常：{exc}"})


def main() -> None:
    import uvicorn

    uvicorn.run(
        "zzk.web.app:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("API_RELOAD", "false").lower() == "true",
        workers=1,
    )


if __name__ == "__main__":
    main()
