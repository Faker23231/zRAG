import json

from zzk.import_process.base import NodeBase
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger


class TestNode(NodeBase):
    name = "test_node"
    def process(self,state):
        print("执行测试节点")
        return state

if __name__ == '__main__':
    node = TestNode()
    init_state = {
        "local_file_path": r"D:\study\p1\test_file\hak180产品安全手册.pdf",
        "local_file_path1": r"D:\study\p1\test_file\hak180产品安全手册.pdf",
        "local_file_path2": r"D:\study\p1\test_file\hak180产品安全手册.pdf",
        "local_file_path3": r"D:\study\p1\test_file\hak180产品安全手册.pdf"
    }
    result = node(init_state)
    # logger.info(json.dumps(result,ensure_ascii=False,indent=4))
    logger.info(json_format(result))