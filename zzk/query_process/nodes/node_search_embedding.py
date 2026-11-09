# zzk/query_process/nodes/node_search_embedding.py
from zzk.config.config import MilvusConfig
from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.get_bge_embeddings import get_bge_embedding
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger
from zzk.tool.milvus_client_tool import get_search_reqs, hybrid_search


class NodeSearchEmbedding(NodeBase):
     """
    节点功能：基于已确认的知识主体 + 改写后的用户问题，执行 Milvus 混合检索。
     """

     # 覆盖基类的 name 属性，标识节点名称
     name: str = "node_search_embedding"

     def process(self, state: QueryGraphState):
         rewritten_query = state.get("rewritten_query") #让我们检索用的
         item_names = state.get("item_names") #让我们在检索的时候过滤用的条件


         #把重写的问题进行向量化
         embeddings = get_bge_embedding([rewritten_query])
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
             output_fields=["id", "title",'file_title',"content","part","item_name"],
             ranker=(0.6, 0.4),
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
             "embedding_chunks":chunks
         }



if __name__ == "__main__":
    init_state = {
        "rewritten_query": "关于BrotherHAK180烫金机如何使用",
        "item_names": ["兄弟HAK180烫金机"] #一定要和你自己的milvus存储的名字一致
    }
    node_search_embedding = NodeSearchEmbedding()
    result = node_search_embedding(init_state)
    logger.info(json_format(result))