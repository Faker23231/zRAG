# zzk/query_process/nodes/node_web_search_mcp.py
import asyncio
import json
import os



from agents import Agent, Runner
from agents.mcp import MCPServerStreamableHttp
from agents.model_settings import ModelSettings

from zzk.config.config import MCPConfig
from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger




class NodeWebSearchMcp(NodeBase):
    """
    节点功能，调用外部搜索引擎补充信息
    """

    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_web_search_mcp"

    def process(self, state: QueryGraphState):
        # 项目已限定知识范围时，不做联网检索，保证回答只来自用户自己的资料
        if state.get("scope_item_names"):
            return {"web_search_docs": []}

        rewritten_query = state.get("rewritten_query")
        result = asyncio.run(self.mcp_run(rewritten_query))
        # print(result.content[0].text,type(result.content[0].text))
        data = json.loads(result.content[0].text).get("pages")

        chunks = [
            {
                "title": item.get("title"),
                "content": item.get("snippet"),
                "url": item.get("url"),
                "source":"web"
            }
            for item in data
        ]

        return {
            "web_search_docs":chunks
        }


    async def mcp_run(self,query,limit=10):
        async with MCPServerStreamableHttp(
            name="网络搜索mcp工具",
            params={
                "url": MCPConfig.mcp_base_url,
                "headers": {"Authorization": f"Bearer {MCPConfig.mcp_api_key}"},
                "timeout": 10,
            },
            cache_tools_list=True,
            max_retry_attempts=3,
        ) as server:
            #原本用的是智能体的方式，现在我们没办法使用，只能使用调用服务器工具的方法传递工具名的方式去使用，异步操作
            result = await server.call_tool(
                tool_name="bailian_web_search",
                arguments={
                    "query": query,
                    "count":limit
                }
            )
            return result



if __name__ == "__main__":

    init_state = {
        "rewritten_query": "关于BrotherHAK180烫金机如何使用"
    }

    # 执行节点的业务调用
    node_web_search_mcp = NodeWebSearchMcp()
    result = node_web_search_mcp(init_state)
    logger.info(json_format(result))