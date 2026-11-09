# zzk/import_process/nodes/node_bge_embedding.py
import json
from pathlib import Path

from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.get_bge_embeddings import get_bge_embedding
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger


class NodeBGEEmbedding(NodeBase):
    """
    混合向量化节点：使用 BGE-M3 模型将文本转换为向量
    """

    name = "node_bge_embedding"

    def process(self, state: ImportGraphState):
        # 从state当中获取chunks
        chunks = state.get("chunks")
        if not chunks:
            logger.error("没有获取到chunks数据，无法进行向量化处理")
            raise ValueError("没有获取到chunks数据，无法进行向量化处理")

        # 中间产物统一放到local_dir，文件名带上file_title，避免不同文档互相覆盖
        local_dir = state.get("local_dir")
        if not local_dir:
            logger.error("local_dir不能为空")
            raise ValueError("local_dir不能为空")
        local_dir_obj = Path(local_dir)
        local_dir_obj.mkdir(parents=True, exist_ok=True)
        file_title = chunks[0].get("file_title") or state.get("file_title") or "chunks"

        # 对chunks进行向量化
        # 按道理来讲下面一行就搞定了，而且bgem3在加载模型对象的时候有参数是可以做到批处理的
        # get_bge_embedding([f"{item.get("item_name")}\n{item.get("content")}" for item in chunks])

        # 自己手动实现批处理
        for i in range(0, len(chunks), 3):
            chunk_k_list = chunks[i : i + 3]
            #整理双向量化的字符串列表
            chunk_k_str_list = [f"{item.get('item_name') or ''}\n{item.get('content') or ''}" for item in chunk_k_list]
            embeddings = get_bge_embedding(chunk_k_str_list)

            #我们向量化结束主要就是把每个内容对应的向量回填到对应的chunk当中
            for idx,chunk in enumerate(chunk_k_list):
                chunk["dense_vector"] = embeddings.get("dense")[idx]
                chunk["sparse_vector"] = embeddings.get("sparse")[idx]

        with open(local_dir_obj / f"{file_title}_chunks_embedding.json", "w", encoding="utf-8") as f:
            f.write(json_format(chunks))

        return {
            "chunks":chunks
        }

if __name__ == '__main__':
    node = NodeBGEEmbedding()
    with open(r"D:\study\p1\test_file\hak180产品安全手册_chunks_item_name.json","r",encoding="utf-8") as f:
        data = f.read() #拿到的还是json串

    init_state = {
        "chunks":json.loads(data),
        "local_dir": r"D:\study\p1\test_file",
    }
    result = node(init_state)
    logger.info(json_format(result))