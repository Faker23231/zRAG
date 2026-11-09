# zzk/import_process/nodes/node_entry.py
from pathlib import Path

from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.logger import logger


class NodeEntry(NodeBase):
    """
    入口节点：任务分发
    """

    name = "node_entry"

    def process(self, state: ImportGraphState):
        local_file_path = state.get("local_file_path")
        if not local_file_path:
            logger.error("未提供文件路径")
            raise Exception("未提供文件路径")

        local_file_path_obj = Path(local_file_path)
        if not local_file_path_obj.exists():
            logger.error("文件不存在")
            raise Exception("文件不存在")

        suffix = local_file_path_obj.suffix
        file_title = local_file_path_obj.stem  # 获取文件名（不包括后缀）
        # file_title = local_file_path_obj.name # 获取文件名（包括后缀）
        # print(file_title)
        if suffix.lower() == ".pdf":
            return {
                "is_pdf_read_enabled": True,
                "file_title": file_title,
                "pdf_path": str(local_file_path_obj)
            }
        elif suffix.lower() == ".md":
            return {
                "is_md_read_enabled": True,
                "file_title": file_title,
                "md_path": str(local_file_path_obj)
            }
        else:
            logger.error("不支持的文件类型")
            raise Exception(f"文件不是支持的格式，只支持 PDF 和 MD 文件。")


if __name__ == '__main__':
    node = NodeEntry()
    init_state = {
        "local_file_path": r"D:\study\p1\test_file\hak180产品安全手册.pdf"
    }
    result = node(init_state)
    logger.info(result)


