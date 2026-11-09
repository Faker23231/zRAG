# zzk/import_process/nodes/node_item_name_recognition.py
import json
from pathlib import Path

from langchain.chat_models import init_chat_model
from pymilvus import MilvusClient, DataType

from zzk.config.config import LLMConfig, MilvusConfig
from zzk.config.prompt import ITEM_NAME_SYSTEM_PROMPT, ITEM_NAME_USER_PROMPT_TEMPLATE
from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.get_bge_embeddings import get_bge_embedding
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger
from zzk.tool.milvus_client_tool import get_milvus_client


class NodeItemNameRecognition(NodeBase):
    """
    主体识别节点：主体识别与标签提取
    """

    name = "node_item_name_recognition"

    def process(self, state: ImportGraphState):
        #0、获取数据
        chunks, file_title = self.get_chunks(state)
        local_dir = state.get("local_dir")
        if not local_dir:
            logger.error("local_dir不能为空")
            raise ValueError("local_dir不能为空")

        #1、拿到部分的chunk 把这些chunk的内容拼接起来变成一个字符串
        chunks_str = self.get_chunks_str(chunks, file_title)

        #2、调用大模型把拼接的字符串作为prompt，整理总结知识主体（文档整体讲述的主题）
        item_name = self.get_item_name(chunks_str, file_title)

        #3、创建milvus连接，并创建表collection
        milvus_client = self.create_milvus_collection()

        # 4、幂等性删除后，把整理的知识主体向量化存储到milvus，并把主体名回填到每个chunk
        self.insert_data(chunks, file_title, item_name, milvus_client, local_dir)

        return {
            "chunks": chunks,
            "item_name": item_name,
        }


    def insert_data(self, chunks, file_title, item_name, milvus_client, local_dir):
        # 5、把整理的知识主体向量化存储到milvus
        # 5-1 幂等性删除 先删除再插入，删除的时候其实可以是item_name作为过滤条件 也可以file_title作为过滤条件，file_title作为过滤条件更精准
        # 大模型识别出来的item_name不是很稳定
        milvus_client.load_collection(MilvusConfig.item_name_collection)  # milvus删除数据要先加载某个表才能执行删除操作
        # 为了让过滤条件字符串不出现语法错误，我们需要把一些特殊的字符进行转换
        # 只用于拼接filter，不能覆盖原file_title，否则入库值和备份文件名都会被转义字符污染
        escaped_file_title = file_title.replace("\\", "\\\\").replace("\'", "\\'").replace('\"', '\\"')
        fiilter = f"file_title == '{escaped_file_title}'"
        milvus_client.delete(
            collection_name=MilvusConfig.item_name_collection,
            filter=fiilter
        )
        # 5-2把item_name向量化添加到milvus
        embeddings = get_bge_embedding([item_name])
        data = {
            "item_name": item_name,
            "file_title": file_title,
            "dense_vector": embeddings.get("dense")[0],
            "sparse_vector": embeddings.get("sparse")[0],
        }
        res = milvus_client.insert(
            collection_name=MilvusConfig.item_name_collection,
            data=data,
        )
        # print(res) res结果是{'insert_count': 1, 'ids': [469793409471431925]}
        # 回填item_name到每个chunk，并且把chunks备份下个节点去使用
        for chunk in chunks:
            chunk["item_name"] = item_name


        # 备份最新的chunks也就是回填完item_name的chunks到本地文件，方便下个节点读取使用
        local_dir_obj = Path(local_dir)
        local_dir_obj.mkdir(parents=True, exist_ok=True)
        with open(local_dir_obj / f"{file_title}_chunks_item_name.json", "w", encoding="utf-8") as f:
            f.write(json_format(chunks))

    def create_milvus_collection(self):
        milvus_client = get_milvus_client()
        # 判断有没有当前要准备创建的表
        if not milvus_client.has_collection(collection_name=MilvusConfig.item_name_collection):
            # 创建表
            # 1、创建结构schema  2、创建索引index  3、创建表
            # 创建结构schema
            schema = milvus_client.create_schema(
                auto_id=True
            )

            schema.add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True,

            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100,

            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100,
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            )

            # 创建索引
            index_params = milvus_client.prepare_index_params()
            # 稠密向量的索引
            index_params.add_index(
                field_name="dense_vector",  # 给表哪个字段创建索引
                index_name="dense_vector_index",
                index_type="IVF_FLAT",
                metric_type="COSINE",  # 计算相似度的指标算法
                params={"nlist": 128, "nprobe": 10},  # 分簇查找
            )

            index_params.add_index(
                field_name="sparse_vector",
                index_name="sparse_vector_index",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                # params={"inverted_index_algo": "DAAT_MAXSCORE"}, #主要就是想让我们了解这个参数是可以优化查询的
            )

            # 创建表
            milvus_client.create_collection(
                collection_name=MilvusConfig.item_name_collection,
                schema=schema,
                index_params=index_params
            )
        return milvus_client

    def get_item_name(self, chunks_str, file_title):
        llm = init_chat_model(
            model=LLMConfig.item_model,
            model_provider="openai",
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature,
        )
        messages = [
            {"role": "system", "content": ITEM_NAME_SYSTEM_PROMPT},
            {"role": "user",
             "content": ITEM_NAME_USER_PROMPT_TEMPLATE.format(file_title=file_title, context=chunks_str)},
        ]
        res = llm.invoke(input=messages)
        # print(res.content)
        # 大模型识别出来的主体名字可能有空格，去除
        item_name = res.content.replace("\n", "").replace("\t", "").replace(" ", "")
        if not item_name:
            item_name = file_title
        # print(item_name)
        return item_name

    def get_chunks_str(self, chunks, file_title):
        chunk_k_list = chunks[:15]
        max_length = 10000
        chunks_str = ""
        for idx, chunk in enumerate(chunk_k_list, start=1):
            title = chunk.get("title")
            content = chunk.get("content")
            chunk_text = f"[切片{idx}]\n文件名:{file_title}\n标题:{title}\n内容:{content}\n\n"
            chunks_str += chunk_text
            if len(chunks_str) > max_length:
                break
        chunks_str = chunks_str[:max_length]
        return chunks_str

    def get_chunks(self, state):
        chunks = state.get("chunks")
        file_title = state.get("file_title")
        if not chunks:
            logger.error("chunks不能为空")
            raise ValueError("chunks不能为空")
        if not file_title:
            logger.error("file_title不能为空")
            raise ValueError("file_title不能为空")
        return chunks, file_title


if __name__ == '__main__':
    node = NodeItemNameRecognition()
    with open(r"D:\study\p1\test_file\hak180产品安全手册_chunks.json","r",encoding="utf-8") as f:
        # chunks = f.read()
        chunks = json.load(f)

    init_state = {
        # "chunks": json.loads(chunks),
        "chunks": chunks,
        "file_title": "hak180产品安全手册",
        "local_dir": r"D:\study\p1\test_file",
    }

    result = node(init_state)
    logger.info(json_format(result))










