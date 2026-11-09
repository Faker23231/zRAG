# src/kb_0716/schemas.py

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """非流式/流式问答的请求体"""

    session_id: str | None = Field(
        default=None, description="会话ID，不传则由服务端生成并返回"
    )
    query: str = Field(..., min_length=1, description="用户原始问题")


class ChatResponse(BaseModel):
    """非流式问答的响应体"""

    session_id: str
    message_id: str | None = None
    answer: str
    item_names: list[str] = Field(default_factory=list)
    rewritten_query: str | None = None


class HistoryMessage(BaseModel):
    """一条历史会话记录"""

    id: str
    role: str
    text: str
    item_names: list[str] = Field(default_factory=list)
    rewritten_query: str | None = None
    ts: float | None = None


class HealthResponse(BaseModel):
    """健康检查结果"""

    status: str
    services: dict[str, bool]


class ErrorResponse(BaseModel):
    """统一错误响应"""

    code: int
    message: str
