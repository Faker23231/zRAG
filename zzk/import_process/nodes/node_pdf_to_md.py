# zzk/import_process/nodes/node_pdf_to_md.py
import shutil
import time
from pathlib import Path

from zzk.config.config import MineruConfig
from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.logger import logger


class NodePDFToMD(NodeBase):
    """
    PDF 转 Markdown 节点：PDF结构化解析
    """

    name = "node_pdf_to_md"

    def process(self, state: ImportGraphState):
        #第一大步：检查文件pdf和local_dir的存在
        local_dir_obj, local_file_path, local_file_path_obj = self.check_pdf_path(state)

        #第二大步：上传pdf文件到mineru
        batch_id = self.upload_pdf_file(local_file_path, local_file_path_obj)

        #第三大步：轮询获取mineru转化md的zip压缩包url地址
        url = self.get_zip_url(batch_id)

        #第四大步：下载zip 解压压缩包获取md文件，对md文件进行改名，读取文件内容
        md_content, new_md_file_path_obj = self.handler_md_file(local_dir_obj, local_file_path_obj, url)

        return {
            "md_path":str(new_md_file_path_obj),
            "md_content":md_content
        }

    def handler_md_file(self, local_dir_obj, local_file_path_obj, url):
        # 下载压缩包的内容并保存到本地的zip文件当中
        import requests
        zip_res = requests.get(url)
        if zip_res.status_code != 200:
            logger.error("下载压缩包的内容请求失败")
            raise ValueError("下载压缩包的内容请求失败")
        zip_content = zip_res.content  # 获取压缩包的内容
        # 把压缩包的内容写入到本地的一个zip文件当中，保存到本地
        zip_file_path_obj = local_dir_obj / f"{local_file_path_obj.stem}.zip"
        with open(zip_file_path_obj, 'wb') as f:
            f.write(zip_content)
        # 把下载的zip文件解压到本地
        import zipfile
        unzip_dir_obj = local_dir_obj / f"{local_file_path_obj.stem}"
        # 幂等性删除
        if unzip_dir_obj.exists():
            shutil.rmtree(unzip_dir_obj)  # 递归删除 有没有内容都删
        unzip_dir_obj.mkdir(parents=True, exist_ok=True)
        # 打开zip压缩文件，把文件当中的内容解压到指定的目录当中
        with zipfile.ZipFile(zip_file_path_obj) as unzip_content_handler:
            unzip_content_handler.extractall(unzip_dir_obj)
        # 把解压出来的文件进行改名处理
        # 第一步找到老文件的位置
        old_md_file_path_obj = unzip_dir_obj / "full.md"
        # 第二步改名处理，但是没有落盘，返回的新的文件路径对象
        new_md_file_path_obj = old_md_file_path_obj.with_name(f"{local_file_path_obj.stem}.md")
        # 第三步真正的改名处理，落盘
        old_md_file_path_obj.rename(new_md_file_path_obj)
        with open(new_md_file_path_obj, 'r', encoding='utf-8') as f:
            md_content = f.read()
        return md_content, new_md_file_path_obj

    def get_zip_url(self, batch_id):
        # 拿着上传得到的batch_id去轮询获取mineru转化的md的压缩包路径
        import requests
        token = MineruConfig.mineru_token
        url = f"https://mineru.net/api/v4/extract-results/batch/{batch_id}"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        # 解析是异步任务：先排队（pending），再逐页解析（running），实测2MB/15页约需1分钟左右，
        # 高峰期排队可能更久，所以预算给到10分钟
        total_time = 600
        start_time = time.time()
        # 轮询获取 隔2秒发一次请求 直到拿到需要的结果
        while True:
            # 先判超时：必须用真实流逝的时间，不能让sleep的时间"逃过"计时
            if time.time() - start_time > total_time:
                logger.error("获取mineru转化的md的压缩包路径请求超时")
                raise ValueError("获取mineru转化的md的压缩包路径请求超时")

            try:
                res = requests.get(url, headers=header, timeout=30)
            except requests.RequestException as e:
                # 只有网络抖动这类临时故障才重试，其余错误直接抛出
                logger.warning(f"轮询mineru结果请求异常，稍后重试：{e}")
                time.sleep(2)
                continue

            # 判断请求成功不成功
            if res.status_code != 200:
                logger.error("获取mineru转化的md的压缩包路径请求失败")
                raise ValueError("获取mineru转化的md的压缩包路径请求失败")
            # 请求成功拿请求体内容
            result = res.json()
            if result.get("code") != 0:
                logger.error(f"获取mineru转化的md的压缩包路径请求数据获取失败：{result.get('msg')}")
                raise ValueError("获取mineru转化的md的压缩包路径请求数据获取失败")

            extract_result = (result.get("data") or {}).get("extract_result") or []
            if not extract_result:
                logger.warning("mineru返回的extract_result为空，稍后重试")
                time.sleep(2)
                continue

            extract_item = extract_result[0]
            state = extract_item.get("state")
            # 解析完成，拿压缩包地址走人
            if state == "done":
                return extract_item.get("full_zip_url")
            # 解析失败：必须立刻抛，否则真实原因会被"正在解析中"一直掩盖
            if state == "failed":
                logger.error(f"mineru解析失败：{extract_item.get('err_msg')}")
                raise ValueError(f"mineru解析失败：{extract_item.get('err_msg')}")

            # waiting-file(等待文件上传)/pending(排队)/running(解析中)/converting(格式转换) 都是中间态
            progress = extract_item.get("extract_progress") or {}
            logger.info(
                f"mineru解析中：state={state} "
                f"进度={progress.get('extracted_pages')}/{progress.get('total_pages')}页"
            )
            time.sleep(2)

    def upload_pdf_file(self, local_file_path, local_file_path_obj):
        # 使用minerU把pdf进行md的转换
        # 上传
        import requests
        token = MineruConfig.mineru_token
        url = "https://mineru.net/api/v4/file-urls/batch"
        header = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        data = {
            "files": [
                {"name": f"{local_file_path_obj.name}", "data_id": "abcd"}
            ],
            "model_version": "vlm"
        }
        file_path = [local_file_path]
        # 判断请求成功不成功
        response = requests.post(url, headers=header, json=data)
        if response.status_code != 200:
            logger.error("上传文件请求失败")
            raise ValueError("上传文件请求失败")
        # 到这代表请求成功，然后拿响应报文当中的数据内容，接着要判断数据获取成功不成功
        result = response.json()
        if result["code"] != 0:
            logger.error("上传文件请求数据获取失败")
            raise ValueError("上传文件请求数据获取失败")
        # 如果后期数据还有对错之分，其实我们还要再去考虑一层判断，判断数据拿的对不对
        # 这个请求是没有数据对错的判断，因为这个数据不是实时数据，一般实时数据才会有对错判断
        batch_id = result["data"]["batch_id"]
        urls = result["data"]["file_urls"]
        for i in range(0, len(urls)):
            with open(file_path[i], 'rb') as f:
                res_upload = requests.put(urls[i], data=f, timeout=300)
                # 上传失败必须抛异常：否则任务被建出来了但文件没到位，
                # mineru 会一直停在 waiting-file/pending，表现为"一直正在解析中"
                if res_upload.status_code != 200:
                    logger.error(f"{urls[i]}上传失败")
                    raise ValueError(f"文件上传到mineru失败，HTTP状态码：{res_upload.status_code}")
                logger.info(f"{urls[i]}上传成功")
        # print(batch_id)
        return batch_id

    def check_pdf_path(self, state):
        local_file_path = state.get("local_file_path")
        local_dir = state.get("local_dir")
        if not local_file_path:
            logger.error("local_file_path不能为空")
            raise ValueError("local_file_path不能为空")
        local_file_path_obj = Path(local_file_path)
        if not local_file_path_obj.exists():
            logger.error("local_file_path文件不存在")
            raise ValueError("local_file_path文件不存在")
        # 判断输出的文件目录
        if not local_dir:
            logger.error("local_dir不能为空")
            raise ValueError("local_dir不能为空")
        local_dir_obj = Path(local_dir)
        if not local_dir_obj.exists():
            # parents = True,递归创建
            # exist_ok=True 如果这个目录存在 不报错
            local_dir_obj.mkdir(parents=True, exist_ok=True)
        return local_dir_obj, local_file_path, local_file_path_obj


if __name__ == '__main__':
    node = NodePDFToMD()
    init_state = {
        "local_file_path":r"D:\study\p1\test_file\hak180产品安全手册.pdf",
        "local_dir":r"D:\study\p1\test_file"
    }

    result = node(init_state)
    logger.info(result)
