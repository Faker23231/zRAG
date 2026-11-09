# zzk/query_process/nodes/node_answer_output.py
import re

from langchain.chat_models import init_chat_model

from zzk.config.config import LLMConfig
from zzk.config.prompt import ANSWER_PROMPT
from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.logger import logger
from zzk.tool.mongo_tool import save_chat_message
from zzk.tool.task_utils import put_data

# 参考资料最多拼进提示词的长度，避免超出上下文窗口
MAX_CONTEXT_CHARS = 9000


class NodeAnswerOutput(NodeBase):
    """
    节点功能：基于重排后的参考资料生成答案，并流式推送给前端。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_answer_output"

    def process(self, state: QueryGraphState):
        answer = state.get("answer", "")
        task_id = state.get("task_id")
        chunks = state.get("reranked_docs") or []
        history = state.get("history") or []
        item_names = state.get("item_names") or []
        rewritten_query = state.get("rewritten_query")
        session_id = state.get("session_id")

        if answer:
            # 意图识别阶段已经生成回答（例如请用户确认知识条目），直接推给用户
            put_data(task_id, event="final", data={
                "answer": answer,
                "image_urls": [],
                "sources": [],
            })
            return {"answer": answer}

        # 1 根据 chunks 整理 context（控制长度，保留提示词模板完整）
        context = ""
        for idx, chunk in enumerate(chunks, start=1):
            title = chunk.get("title")
            content = chunk.get("content")
            url = chunk.get("url")
            source = chunk.get("source")
            chunk_str = f"[切片:{idx}]\n[标题:{title}]\n[内容:{content}]\n[链接:{url}]\n[来源:{source}]\n\n"
            if len(context) + len(chunk_str) > MAX_CONTEXT_CHARS:
                break
            context += chunk_str

        # 2 整理历史记录
        history_str = "\n".join([f'{h.get("role")}:{h.get("text")}' for h in history])
        # 3 整理知识主体列表
        item_names_str = "、".join([str(name) for name in item_names])
        # 4 整理用户问题
        question = rewritten_query

        answer_prompt = ANSWER_PROMPT.format(
            context=context,
            history=history_str,
            item_names=item_names_str,
            question=question,
        )

        llm = init_chat_model(
            model=LLMConfig.llm_default_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )

        messages = [
            {"role": "user", "content": answer_prompt}
        ]

        res = llm.stream(input=messages)
        for chunk in res:
            delta = chunk.content or ""
            if not delta:
                continue
            put_data(task_id, event="delta", data={"delta": delta})
            answer += delta  # 后期历史记录需要保存

        # 推送完答案，手动把图片作为最后的推送：
        # 1、防止大模型没有把图片解析显示；2、作为这次推送的结束标志
        seen = set()  # 用于去重，避免同一张图片重复出现
        md_img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')
        for doc in chunks:
            text = doc.get("content") or ""
            for img_url in md_img_pattern.findall(text):
                img_url = img_url.strip()
                if img_url:
                    seen.add(img_url)
        images = list(seen)

        # 前端“引用来源”面板需要的最小字段
        sources = [
            {
                "index": idx,
                "title": chunk.get("title") or chunk.get("file_title") or "参考资料",
                "file_title": chunk.get("file_title"),
                "content": (chunk.get("content") or "")[:220],
                "url": chunk.get("url") or "",
                "source": chunk.get("source") or "local",
            }
            for idx, chunk in enumerate(chunks, start=1)
        ]

        put_data(task_id, event="final", data={
            "answer": answer,
            "image_urls": images,
            "sources": sources,
        })

        # 保存这次生成答案的历史记录，前端刷新后仍能看到对话
        if answer and session_id:
            try:
                save_chat_message(
                    session_id=session_id,
                    role="assistant",
                    text=answer,
                    rewritten_query=question,
                    item_names=item_names,
                )
            except Exception as e:
                logger.error(f"保存答案历史记录失败: {e}")

        return {
            "answer": answer,
        }
