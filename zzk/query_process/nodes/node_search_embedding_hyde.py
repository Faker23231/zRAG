# zzk/query_process/nodes/node_search_embedding_hyde.py
from langchain.chat_models import init_chat_model

from zzk.config.config import LLMConfig, MilvusConfig
from zzk.config.prompt import HYDE_PROMPT
from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.get_bge_embeddings import get_bge_embedding
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger
from zzk.tool.milvus_client_tool import get_search_reqs, hybrid_search


class NodeSearchEmbeddingHyde(NodeBase):
    """
    节点功能：HyDE (Hypothetical Document Embedding)
    先让 LLM 生成假设性答案，再对答案进行向量检索，提高召回率。
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_search_embedding_hyde"

    def process(self, state: QueryGraphState):
        rewritten_query = state.get("rewritten_query")
        item_names = state.get("item_names")

        #先把重写的问题丢给大模型，让大模型生成假设性答案
        llm = init_chat_model(
            model=LLMConfig.llm_default_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )
        messages = [
            {"role":"user", "content": HYDE_PROMPT.format(rewritten_query=rewritten_query)},
        ]

        res = llm.invoke(input=messages)
        hyde_answer = res.content
        print(hyde_answer)

        # 把重写的问题进行向量化
        embeddings = get_bge_embedding([rewritten_query + "\n" + hyde_answer])
        dense_data = embeddings.get("dense")[0]
        sparse_data = embeddings.get("sparse")[0]

        # 混合检索
        # 导入模块已经识别出每份文档的知识主体并回填到每个 chunk，这里用主体做过滤：
        # 只有 chunk 的 item_name 命中本次确认的主体集合，才参与召回。
        # 没有限定主体时不做过滤，直接全库召回（通用 RAG 的兜底策略）。

        item_names = [
            item_name.replace("\\", "\\\\").replace('\"', '\\"').replace("\'", "\\'")
            for item_name in item_names
        ]
        expr = f"item_name in {item_names}" if item_names else None

        reqs = get_search_reqs(
            dense_data=[dense_data],
            sparse_data=[sparse_data],
            dense_anns_field="dense_vector",
            sparse_anns_field="sparse_vector",
            expr=expr,
        )

        res = hybrid_search(
            collection_name=MilvusConfig.chunks_collection,
            reqs=reqs,
            output_fields=["id", "title", 'file_title', "content", "part", "item_name"],
            ranker=(0.7, 0.3),
        )
        print(json_format(res))

        # chunks = []
        # for item in res[0]:
        #     chunks.append({
        #         **item.get("entity"),
        #         "score": item.get("distance"),
        #         "source":"local"
        #     })

        rows = res[0] if res else []
        chunks = [
            {
                **item.get("entity"),
                "score": item.get("distance"),
                "source": "local"
            }
            for item in rows
        ]

        return {
            "hyde_embedding_chunks": chunks
        }


















# zzk/query_process/node_search_embedding_hyde.py

if __name__ == "__main__":
    init_state = {
        "rewritten_query": "关于BrotherHAK180烫金机如何使用",
        "item_names": ["兄弟HAK180烫金机"]
    }
    node_search_embedding_hyde = NodeSearchEmbeddingHyde()
    result = node_search_embedding_hyde(init_state)
    logger.info(json_format(result))