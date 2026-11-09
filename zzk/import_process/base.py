import time
from abc import ABC,abstractmethod

from dotenv.main import rewrite

from zzk.import_process.state import ImportGraphState
from zzk.tool.logger import logger
from zzk.tool.task_utils import add_running_task, add_done_task, add_node_duration


class NodeBase(ABC):
    name = "node_base"

    def __init__(self):
        if self.name == "node_base":
            logger.error(f"节点类{self.__class__.__name__}必须配置name,代表节点名字")
            raise Exception(f"节点类{self.__class__.__name__}必须配置name,代表节点名字")

    # 这个call的提升就是为了统一干活
    def __call__(self, state: ImportGraphState):
        try:
            start_time = time.time()
            task_id = state.get("task_id")
            # 修改节点状态为开始运行
            add_running_task(task_id, self.name)

            logger.info(f"节点{self.name}开始执行")
            result = self.process(state)
            logger.info(f"节点{self.name}执行完成")

            # 修改节点状态为执行完成
            add_done_task(task_id, self.name)
            end_time = time.time()

            # 记录节点耗时
            add_node_duration(task_id,self.name,end_time - start_time)
            return result
        except Exception as e:
            logger.error(e)
            raise e


    @abstractmethod
    def process(self, state: ImportGraphState):
        pass
