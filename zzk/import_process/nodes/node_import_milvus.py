# zzk/import_process/nodes/node_import_milvus.py
import json

from pymilvus import DataType

from zzk.config.config import MilvusConfig
from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger
from zzk.tool.milvus_client_tool import get_milvus_client


class NodeImportMilvus(NodeBase):
    """
    导入向量库节点：数据持久化
    """

    name = "node_import_milvus"

    def process(self, state: ImportGraphState):
        # 从state当中获取chunks
        chunks = state.get("chunks")
        if not chunks:
            logger.error("没有获取到chunks数据，无法进行导入milvus处理")
            raise ValueError("没有获取到chunks数据，无法进行导入milvus处理")

        file_title = chunks[0].get("file_title")
        if not file_title:
            logger.error("chunks中没有file_title，无法进行幂等性删除和导入")
            raise ValueError("chunks中没有file_title，无法进行幂等性删除和导入")

        milvus_client = get_milvus_client()
        if not milvus_client.has_collection(MilvusConfig.chunks_collection):
            schema = milvus_client.create_schema(auto_id=True)
            schema.add_field(
                field_name="id",
                datatype=DataType.INT64,
                is_primary=True
            ).add_field(
                field_name="title",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="file_title",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="content",
                datatype=DataType.VARCHAR,
                max_length=3000
            ).add_field(
                field_name="part",
                datatype=DataType.INT64,
            ).add_field(
                field_name="item_name",
                datatype=DataType.VARCHAR,
                max_length=100
            ).add_field(
                field_name="dense_vector",
                datatype=DataType.FLOAT_VECTOR,
                dim=1024
            ).add_field(
                field_name="sparse_vector",
                datatype=DataType.SPARSE_FLOAT_VECTOR,
            )


            index_params = milvus_client.prepare_index_params()
            index_params.add_index(
                field_name="dense_vector",
                index_name="dense_vector_index",
                index_type="IVF_FLAT",
                metric_type="COSINE",
                params={"nlist": 128,"nprobe":10}
            )

            index_params.add_index(
                field_name="sparse_vector",
                index_name="sparse_vector_index",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                # params={"nlist": 128,"nprobe":10}
            )


            milvus_client.create_collection(
                collection_name=MilvusConfig.chunks_collection,
                schema=schema,
                index_params=index_params
            )


        # 导入数据
        #幂等性删除文件相同的所有chunk
        milvus_client.load_collection(collection_name=MilvusConfig.chunks_collection)
        # 转义后的值只用于拼filter，不能覆盖file_title，否则插入值和chunk里的file_title不一致
        escaped_file_title = file_title.replace("\\", "\\\\").replace("\'", "\\'").replace('\"', '\\"')
        filter = f"file_title == '{escaped_file_title}'"
        milvus_client.delete(
            collection_name=MilvusConfig.chunks_collection,
            filter=filter
        )

        #去添加chunks到milvus
        res = milvus_client.insert(
            collection_name=MilvusConfig.chunks_collection,
            data=chunks,
        )
        # print(res)

        #回填每个chunk在milvus当中的id到每个chunk,存储到state
        for idx,chunk in enumerate(chunks):
            # chunk["id"] = res.get("ids").pop(0)
            chunk["id"] = res.get("ids")[idx]

        return {
            "chunks": chunks,
        }



if __name__ == '__main__':
    node = NodeImportMilvus()
    with open(r"D:\study\p1\test_file\hak180产品安全手册_chunks_embedding.json","r",encoding="utf-8") as f:
        chunks = json.load(f)

    init_state = {
        "chunks": chunks,
    }
    result = node(init_state)
    logger.info(json_format(result))


