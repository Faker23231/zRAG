import dashscope
from http import HTTPStatus

from zzk.config.config import RerankConfig
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger

# 以下为华北2（北京）地域的配置，调用时请将{WorkspaceId}替换为真实的业务空间ID，各地域的配置不同。
dashscope.base_http_api_url = RerankConfig.rerank_base_url
dashscope.api_key = RerankConfig.rerank_api_key

def text_rerank(query,texts,limit=10):
    try:
        resp = dashscope.TextReRank.call(
            model="qwen3.7-text-rerank",
            query=query,
            documents=texts,
            # return_documents=True,
            top_n=limit,#这里我们最终要做断崖检测获取动态的topn，所以这里后期传递的是chunks的列表长度
            instruct="Given a web search query, retrieve relevant passages that answer the query."
        )
        if resp.status_code == HTTPStatus.OK:
            # print(resp,type(resp))
            # print(resp.output.results)
            return [{"index":item.index,"score":item.relevance_score} for item in resp.output.results]
        else:
            logger.error(f"重排序请求失败")
            raise Exception(f"重排序请求失败")

    except Exception as e:
        logger.error(f"重排序失败,{e}")
        raise e


if __name__ == '__main__':
    result = text_rerank(query="我是谁",texts=["人","狗"])
    print(json_format(result))