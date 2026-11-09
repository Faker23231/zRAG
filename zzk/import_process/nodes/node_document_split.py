# zzk/import_process/nodes/node_document_split.py
import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from zzk.config.config import MineruConfig
from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger


class NodeDocumentSplit(NodeBase):
    """
    文档切分节点：智能文档切片
    """

    name = "node_document_split"

    def process(self, state: ImportGraphState):
        #第一大步：获取整理完的md文档内容和文件标题
        file_title, md_content = self.get_md_content(state)
        #第二大步：粗切：根据标题和内容，切分成多个区块
        split_section_list = self.get_split_section_list(file_title, md_content)
        #第三大步：细切：长切短合，并把区块的标题和内容组装到一起
        final_chunk_list = self.get_final_chunk_list(file_title, split_section_list)

        #把切好的chunks变成json 存储到json文件，目的是为了下个节点要用的时候，直接从json文档当中去读
        #中间产物统一放到local_dir，文件名带上file_title，避免不同文档互相覆盖
        local_dir = state.get("local_dir")
        if not local_dir:
            logger.error("local_dir不能为空")
            raise ValueError("local_dir不能为空")
        local_dir_obj = Path(local_dir)
        local_dir_obj.mkdir(parents=True, exist_ok=True)
        chunks_file_path_obj = local_dir_obj / f"{file_title}_chunks.json"
        with open(chunks_file_path_obj, "w", encoding="utf-8") as f:
            f.write(json_format(final_chunk_list))

            # json.dump(final_chunk_list, f, ensure_ascii=False, indent=4)

        return {
            "chunks":final_chunk_list
        }

    def get_final_chunk_list(self, file_title, split_section_list):
        # 细切：长切短合
        splitter = RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n", "。", "！", "？", "；", "!", "?", ";", " "],
            chunk_size=300,
            chunk_overlap=50
        )
        final_chunk_list = []
        for split_section in split_section_list:
            # 获取每个区块的内容，根据内容判断长度是不是超过指定的长度，如果超过就再去切分，如果不超过就不切
            title = split_section.get("title")
            content = split_section.get("content")
            if content.startswith("#"):
                # 剥掉标题行，按行切分更稳：原来用len(title)+2，标题后没有空行时会多吞一个字符
                content_lines = content.split("\n", 1)
                real_content = content_lines[1].strip() if len(content_lines) > 1 else ""
            else:
                real_content = content

            if len(real_content) < 300:
                final_chunk_list.append({
                    **split_section,
                    "part": 0  # 这个数据目的是为了溯源，没有被切的人我们编号为0，如果一旦被切，被切的几个编号从1开始
                })
                continue



            if "<table" in real_content:
                final_chunk_list.append({
                    **split_section,
                    "part": 0  # 这个数据目的是为了溯源，没有被切的人我们编号为0，如果一旦被切，被切的几个编号从1开始
                })
                continue



            for idx, splite_text in enumerate(splitter.split_text(real_content), start=1):
                # 把切成每个小块文本，也得组装成一个chunk字典，存入final_chunk_list
                final_chunk_list.append({
                    "title": title,
                    "content": title + "\n\n" + splite_text,
                    "file_title": file_title,
                    "part": idx
                })
        return final_chunk_list

    def get_split_section_list(self, file_title, md_content):
        split_line_list = md_content.split("\n")
        is_block = False  # False代表不在代码围栏里面，True代表在代码围栏里面
        code_pattern = r"^(`{3,}|~{3,})"  # 如果后期正则只用写一次，那么编译不编译成对象都行
        title_pattern = r'^\s*#{1,6}\s+.+'
        # code_pattern = re.compile(r"^(`{3,}|~{3,})")  #后期如果一个正则字符串要写多次，我们可以编译成一个正则对象，后期用对象即可
        marker = None
        start_index = 0
        temp_section_list = []
        for idx, splite_line in enumerate(split_line_list):
            splite_line = splite_line.strip()
            # 判断这个行是不是标题
            # 1、得先保证这行不在代码围栏里面
            # 2、再去保证这行符合标题的正则
            match = re.match(code_pattern, splite_line)
            if match:
                # 拿到了~~~或者```,是代码
                if not is_block:
                    # 说明不在代码围栏里面，第一次碰到代码围栏的开始，准备进入
                    is_block = True
                    marker = match.group(1)
                else:
                    #第二次碰到代码围栏，说明代码结束了
                    if marker == match.group(1):
                        is_block = False
                        marker = None

            if not is_block and re.match(title_pattern, splite_line):
                # 一定是标题
                temp_section_list.append(split_line_list[start_index:idx])
                start_index = idx

        temp_section_list.append(split_line_list[start_index:])
        # 把切分出来的每个小列表对应整理成字典,就是我们粗切出来的每个section
        split_section_list = []
        for temp_section in temp_section_list:
            content = "\n".join(temp_section).strip()
            if not content:
                # 文档第一行就是标题时，前面会切出一个空section，跳过它避免生成空chunk
                continue
            # 用content的首行取标题：temp_section[0]可能是空行，会得到空标题
            title = content.split("\n", 1)[0] if content.startswith("#") else "无标题"
            split_section_list.append({
                "title": title,
                "content": content,
                "file_title": file_title,
            })
        # logger.info(json_format(split_section_list))
        return split_section_list

    def get_md_content(self, state):
        md_path = state.get("md_path")
        file_title = state.get("file_title")
        if not md_path:
            logger.error("未提供文件路径")
            raise Exception("未提供文件路径")
        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("文件不存在")
            raise Exception("文件不存在")
        if not file_title:
            logger.error("文件名不存在")
            raise Exception("文件名不存在")
        # utf-8-sig：兼容带BOM的md，否则首行标题会以"\ufeff#"开头，识别不出标题
        with open(md_path_obj, "r", encoding="utf-8-sig") as f:
            md_content = f.read()
        # 拿到md的内容，我们要按行切分，所以选择字符串的split方法去按照换行符切分为列表
        # 换行符我们得去统一一下
        md_content = md_content.replace("\r\n", "\n").replace("\r", "\n")
        return file_title, md_content


if __name__ == '__main__':
    node = NodeDocumentSplit()
    init_state = {
        "md_path":r"D:\study\p1\test_file\hak180产品安全手册\hak180产品安全手册_new.md",
        "file_title":"hak180产品安全手册",
        "local_dir":r"D:\study\p1\test_file",
    }
    result = node(init_state)
    logger.info(json_format(result))


