from pymilvus import MilvusClient, AnnSearchRequest, WeightedRanker
from scipy.cluster.hierarchy import weighted

from zzk.config.config import MilvusConfig
#获取milvus的客户端连接工具
milvus_client = None
def get_milvus_client():
    global milvus_client  # 引用全局客户端变量，实现单例复用
    if not milvus_client:  # 仅在未初始化时创建连接
        milvus_client = MilvusClient(
            uri=MilvusConfig.milvus_url,  # 从配置读取 milvus 服务地址
        )
    return milvus_client  # 返回客户端实例




def get_search_reqs(
        dense_data,
        dense_anns_field,
        sparse_data,
        sparse_anns_field,
        dense_param=None,
        sparse_param=None,
        limit=10,
        expr=None
):
    if not dense_param:
        dense_param = {
            "metric_type": "COSINE",
        }
    if not sparse_param:
        sparse_param = {
            "metric_type": "IP",
        }

    """
    把稠密向量和稀疏向量分别创建自己的检索请求，实例化AnnSearchRequest,拿到实例
    :return: 返回的是两个检索请求的实例组成的列表
    """
    dense_req = AnnSearchRequest(
        data=dense_data,
        anns_field=dense_anns_field,
        param=dense_param,
        limit=limit,
        expr=expr,
    )


    sparse_req = AnnSearchRequest(
        data=sparse_data,
        anns_field=sparse_anns_field,
        param=sparse_param,
        limit=limit,
        expr=expr,
    )


    return [dense_req,sparse_req]


def hybrid_search(collection_name,reqs,limit=10,output_fields=None,ranker=(0.5,0.5)):
    """
    混合检索，稠密向量和稀疏向量的混合检索,需要传递上面那个工具函数返回的请求列表
    :return:
    """
    weighted_ranker = WeightedRanker(*ranker) #加权排名 前面的值对应是稠密 后面的值对应稀疏

    milvus_client = get_milvus_client()

    res = milvus_client.hybrid_search(
        collection_name=collection_name,
        reqs=reqs,
        ranker=weighted_ranker,
        limit=limit,
        output_fields=output_fields
    )

    return res
