# src/kb_0716/app.py
"""
兼容入口。

原先这里是一套独立的查询接口（/api/chat、/api/history），现已统一收敛到
`zzk.web.app`：同一个进程提供首页、示例项目、PDF 导入、对话 SSE 与历史记录。

启动：
    uv run uvicorn kb_0716.app:app --host 0.0.0.0 --port 8000
或：
    uv run kb-0716
"""
from zzk.web.app import app, main

__all__ = ["app", "main"]


if __name__ == "__main__":
    main()
