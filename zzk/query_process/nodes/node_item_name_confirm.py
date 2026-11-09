# zzk/query_process/nodes/node_item_name_confirm.py

from langchain.chat_models import init_chat_model

from zzk.config.config import LLMConfig, MilvusConfig
from zzk.config.prompt import ITEM_NAME_EXTRACT_SYSTEM_PROMPT, ITEM_NAME_EXTRACT_TEMPLATE
from zzk.query_process.base import NodeBase
from zzk.query_process.state import QueryGraphState
from zzk.tool.get_bge_embeddings import get_bge_embedding
from zzk.tool.json_format import json_format, parse_llm_json
from zzk.tool.logger import logger
from zzk.tool.milvus_client_tool import get_search_reqs, hybrid_search
from zzk.tool.mongo_tool import save_chat_message, get_recent_messages, update_history_item_names


class NodeItemNameConfirm(NodeBase):
    """
    节点功能：确认用户问题指向的知识主体（通用 RAG 场景下的主题条目）。
    - 未限定项目时：由大模型识别主体，并与 Milvus 中已入库的知识主体做名称对齐。
    - 已限定项目（scope_item_names）时：直接使用项目对应的知识主体，只做问题改写。
    """    # 覆盖基类的 name 属性，标识节点名称
    name: str = "node_item_name_confirm"

    def process(self, state: QueryGraphState):
        # todo 1 获取state给的初始化数据，查询mongo拿到历史记录整理成字符串
        history_str, message_id, original_query, session_id = self.get_history_str(state)
        # todo 2 根据历史记录和原始问题，调用大模型提取知识主体和重写的问题
        item_names, rewritten_query = self.get_item_names(history_str, original_query)
        #item_names是大模型根据问题和历史记录生成的主体名，目前并不是之前保存在milvus的名字
        #根据大模型生成的名字 向量化 从item_name表里面去找相似度
        scope_item_names = state.get("scope_item_names") or []
        final_item_names = []
        if scope_item_names:
            # 当前会话已经绑定到具体项目（用户自己上传的 PDF），检索范围天然确定，
            # 不需要再让大模型猜主体、也不需要去 item_name 表做名称对齐。
            final_item_names = list(scope_item_names)
            answer = ""
        else:
            answer = "没有在知识库里找到与这个问题相关的内容，换个说法试试，或先创建一个属于你的项目。"
            if item_names:
                #todo 3 向量化检索，遍历大模型给识别的主体名称，一个一个去混合检索milvus当中相似的主体条目
                search_item_name_list = self.hybrid_search_item_names(item_names)
                #todo 4 对齐主体名称，区分出确认的名字、可能的名字、噪音(最终的item_names保存在final_item_names中)
                answer, final_item_names = self.align_item_names(answer, final_item_names, search_item_name_list)

        # todo 5 处理历史记录，更新知识主体和重写问题到历史记录中
        message_id = self.handler_history(answer, final_item_names, message_id, rewritten_query, session_id)

        return {
            "message_id":message_id, #保存最新添加的历史记录id，
            "original_query":original_query,
            "answer":answer,
            "item_names":final_item_names,
            "rewritten_query":rewritten_query,
            "history":get_recent_messages(session_id), #这里必须重新获取历史记录，否则拿的还是回填前的
        }

    def handler_history(self, answer, final_item_names, message_id, rewritten_query, session_id):
        # 知识主体对齐完成后，这个节点的主要功能就结束了，但还需要把历史记录处理一下
        if answer:
            # 保存这个答案作为历史记录
            message_id = save_chat_message(
                session_id=session_id,
                role="assistant",
                text=answer,
            )
        #     history_list = get_recent_messages(session_id,n=12)
        # else:
        #     history_list = get_recent_messages(session_id, n=11)
        history_list = get_recent_messages(session_id)
        history_ids = [history.get("_id") for history in history_list]
        update_history_item_names(ids=history_ids, item_names=final_item_names, rewritten_query=rewritten_query)
        return message_id

    def align_item_names(self, answer, final_item_names, search_item_name_list):
        print(json_format(search_item_name_list))
        # 把检索整理的结果进行知识主体名称对齐：区分出确认的名字、可能的名字、噪音
        confirm_item_names = [
            search_item_name.get("search_item_name")
            for search_item_name in search_item_name_list if search_item_name["score"] >= 0.80
        ]
        option_item_names = [
            search_item_name.get("search_item_name")
            for search_item_name in search_item_name_list if search_item_name["score"] < 0.80
                                                             and search_item_name["score"] >= 0.6
        ]
        if confirm_item_names:
            # 有确定的名字
            final_item_names = confirm_item_names
            answer = ''
        elif option_item_names:
            final_item_names = []
            answer = f"我找到了几个相关的知识条目：{ '、'.join(option_item_names) }。你想了解哪一个？"
        else:
            # 全是噪音，没有任何名字
            final_item_names = []
            answer = "没有在知识库里找到与这个问题相关的内容，换个说法试试，或先创建一个属于你的项目。"
        return answer, final_item_names

    def hybrid_search_item_names(self, item_names):
        # 识别出来有名字，然后我们再去向量化检索，名称对齐，否则没必要走这两步
        embeddings = get_bge_embedding(item_names)
        search_item_name_list = []
        for idx, item_name in enumerate(item_names):
            dense_data = embeddings.get("dense")[idx]
            sparse_data = embeddings.get("sparse")[idx]

            # 混合检索
            reqs = get_search_reqs(
                dense_data=[dense_data],  # 需要的是列表，即使只有一个也要是列表的形式
                dense_anns_field="dense_vector",
                sparse_data=[sparse_data],
                sparse_anns_field="sparse_vector",
            )
            res = hybrid_search(
                collection_name=MilvusConfig.item_name_collection,
                reqs=reqs,
                ranker=(0.8, 0.2),
                output_fields=["item_name", "file_title"],
            )
            # print(res,type(res))
            # print(json_format(res))
            if not res:
                continue
            for search_item_name_dict in res[0]:
                search_item_name_list.append({
                    "original_item_name": item_name,
                    "search_item_name": search_item_name_dict.get("entity", {}).get("item_name"),
                    "score": search_item_name_dict.get("distance", 0),
                })
        return search_item_name_list

    def get_item_names(self, history_str, original_query):
        # 初始化大模型对象
        llm = init_chat_model(
            model=LLMConfig.llm_default_model,
            model_provider="openai",
            base_url=LLMConfig.openai_api_base,
            api_key=LLMConfig.openai_api_key,
            temperature=LLMConfig.llm_default_temperature,
        )
        messages = [
            {"role": "system", "content": ITEM_NAME_EXTRACT_SYSTEM_PROMPT},
            {"role": "user",
             "content": ITEM_NAME_EXTRACT_TEMPLATE.format(history_text=history_str, original_query=original_query)}
        ]
        res = llm.invoke(input=messages)
        res_json = res.content
        try:
            res_data = parse_llm_json(res_json)
        except ValueError as e:
            # 大模型没有返回合法JSON，降级为“没有识别到知识主体”，避免整个图直接崩掉
            logger.error(f"知识主体提取结果解析失败: {e}")
            return [], original_query
        if not isinstance(res_data, dict):
            logger.error(f"知识主体提取结果不是JSON对象: {res_data!r}")
            return [], original_query
        # print(res_data,type(res_data))
        item_names = res_data.get("item_names") or []
        if not isinstance(item_names, list):
            logger.error(f"item_names 不是列表: {item_names!r}")
            item_names = []
        # 模型可能返回非字符串元素，统一转成字符串并去掉空白字符
        item_names = [str(item).replace("\n", "").replace("\t", "").replace(" ", "") for item in item_names]
        item_names = [item for item in item_names if item]
        rewritten_query = res_data.get("rewritten_query") or original_query
        return item_names, rewritten_query

    def get_history_str(self, state):
        original_query = state.get("original_query")
        session_id = state.get("session_id")
        if not original_query:
            logger.error(f"原始问题不能为空")
            raise ValueError("原始问题不能为空")
        if not session_id:
            logger.error(f"会话ID不能为空")
            raise ValueError("会话ID不能为空")
        history_list = get_recent_messages(session_id)
        # 把当前这个用户的问题 立即保存历史记录
        message_id = save_chat_message(session_id, "user", original_query)
        # 把历史记录当中的role和text拼接起来，形成一个字符串，然后和原始问题一起交给大模型
        history_str = ''
        for history in history_list:
            role = history.get("role")
            text = history.get("text")
            history_str += f"{role}: {text}\n"
        return history_str, message_id, original_query, session_id



if __name__ == "__main__":

    # 模拟会话历史
    # session_id = "test_001"
    # save_chat_message(session_id, "user", "咨询下烫金机。")
    # save_chat_message(session_id, "assistant", "您好。请问是哪个型号")
    # save_chat_message(session_id, "user", "hak180")
    # save_chat_message(session_id, "assistant", "具体有什么问题呢？")

    # 初始化图状态
    init_state = {
        "session_id": "test_001",
        "original_query": "咋用？"
    }

    # 创建节点对象
    node_item_name_confirm = NodeItemNameConfirm()
    # 执行节点的单元测试
    result = node_item_name_confirm(init_state)
    # 将返回的图状态进行json序列化
    logger.info(json_format(result))