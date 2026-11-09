import json
import re

from bson import ObjectId


class MongoJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)


def json_format(data):
    return json.dumps(data,ensure_ascii=False,indent=4,cls=MongoJSONEncoder)
    # return json.dumps(data,ensure_ascii=False,indent=4,default=str)


# 匹配 ```json ... ``` 或 ``` ... ``` 包裹的内容
_MD_FENCE = re.compile(r"^\s*```[a-zA-Z]*\s*(.*?)\s*```\s*$", re.S)


def parse_llm_json(text):
    """
    尽量从大模型返回的文本中解析出JSON对象。
    兼容三种脏数据：markdown代码块包裹、JSON前后夹带解释性文字、纯空内容。
    :raises ValueError: 完全解析不出来时抛出，调用方决定降级还是中断
    """
    if isinstance(text, (dict, list)):
        return text
    if text is None or not str(text).strip():
        raise ValueError("大模型返回内容为空，无法解析JSON")

    content = str(text).strip()

    # 1 去掉 markdown 代码块
    matched = _MD_FENCE.match(content)
    if matched:
        content = matched.group(1).strip()

    # 2 直接解析
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass

    # 3 兜底：截取第一个 { 到最后一个 }（兼容前后夹带解释文字）
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            pass

    raise ValueError(f"大模型返回内容不是合法JSON，前200个字符: {content[:200]!r}")
