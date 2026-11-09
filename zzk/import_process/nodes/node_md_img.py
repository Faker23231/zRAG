# zzk/import_process/nodes/node_md_img.py
import base64
import os
import re
import time
from collections import deque
from pathlib import Path
from datetime import datetime, timedelta

from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from minio.deleteobjects import DeleteObject
from openai import api_key

from zzk.config.config import LLMConfig, MinioConfig
from zzk.import_process.base import NodeBase
from zzk.import_process.state import ImportGraphState
from zzk.tool.json_format import json_format
from zzk.tool.logger import logger
from zzk.tool.minio_client_tool import get_minio_client


class NodeMDImg(NodeBase):
    """
    MarkDown图片处理节点：多模态图片理解
    """
    name = "node_md_img"

    # 图片之间的错峰间隔（秒）：视觉大模型有 RPM/TPM 限流，
    # 连续请求容易被网关挂起或直接 429，所以每张图片之间固定等待一段时间
    IMAGE_INTERVAL_SECONDS = 10

    # 图片后缀名 -> MIME 媒体类型，拼接 Data URI 时按图片真实格式声明
    MIME_TYPES = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        ".webp": "image/webp",
    }

    def process(self, state: ImportGraphState):
        #第一大步：防御性校验并且获取到md_content
        md_content, md_path_obj = self.get_md_content(state)

        #拿到内容，接着我需要找到每张图片名字，通过正则从内容当中去拿到图片的位置
        # 获取本地图片的目录，如果不存在，就直接返回原来的内容，因为没有图片需要处理
        image_dir = md_path_obj.parent / "images"
        if not image_dir.exists():
            logger.warning("本地图片目录不存在")
            return {
                "md_content":md_content
            }

        image_names = os.listdir(image_dir) #把一个目录当中所有的文件名字组成列表，包括目录名
        # print(image_names)
        if not image_names:
            logger.warning("本地图片目录中没有图片")
            return {
                "md_content": md_content
            }

        # 第二大步：拿到图片的名字，接着我需要把每张图片的路径和它的上下文组装到一起
        image_with_context_list = self.get_image_with_context_list(image_dir, image_names, md_content)

        # 第三大步：拿到图片的上下文，接着我需要把每张图片的内容和它的上下文交给大模型去整理摘要,最终整理成字典暂存到列表
        image_with_summary_list = self.get_image_with_summary_list(image_with_context_list)

        # 第四大步：minio幂等性删除并且上传图片获取到在线的图片url暂存到列表
        image_with_summary_url_list = self.get_image_with_summary_url_list(image_with_summary_list, md_path_obj)

        # 第五大步：替换md_content当中的图片路径为在线的图片url,还有摘要，并且把新的内容写到最新的文件
        md_content, new_md_path_obj = self.replace_md_content(image_with_summary_url_list, md_content, md_path_obj)

        return {
            "md_path": str(new_md_path_obj),
            "md_content": md_content,
        }

    def replace_md_content(self, image_with_summary_url_list, md_content, md_path_obj):
        # 把md_content当中的图片路径替换成在线的图片url 摘要也要做替换
        for image_with_summary_url in image_with_summary_url_list:
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_with_summary_url.get("image_name")) + r"\)")
            # 使用自己给定的字符串替换 md_content当中符合正则的子串
            # md_content = pattern.sub(
            #     f"![{image_with_summary_url.get('summary')}]({image_with_summary_url.get('url')})",
            #     md_content,
            # )

            #替换的时候字符串采用lambda表达式返回的方式去做。好处是这样的写法如果碰到字符串当中有特殊字符也可以处理
            #上面的写法，如果碰到字符串当中有特殊字符就会炸
            md_content = pattern.sub(
                lambda _:f"![{image_with_summary_url.get('summary')}]({image_with_summary_url.get('url')})",
                md_content,
            )



        #   构造最新的md文件路径，把替换完成的内容写到最新的文件
        new_md_path_obj = md_path_obj.parent / f"{md_path_obj.stem}_new.md"
        with open(new_md_path_obj, "w", encoding="utf-8") as f:
            f.write(md_content)
        return md_content, new_md_path_obj

    def get_image_with_summary_url_list(self, image_with_summary_list, md_path_obj):
        # 后面接着上面的继续搞url
        # 上传图片获取图片的在线url
        minio_client = get_minio_client()
        # 构造上传图片在桶里面的目录(除了桶和文件名字，中间的就是目录)
        upload_dir = f"{MinioConfig.minio_img_dir}/{datetime.now().strftime('%Y%m%d')}/{md_path_obj.stem}"
        # 本来我们准备好上传的目录之后就可以调用工具进行上传，但是在上传之前我们都要去做一个幂等性删除，图片如果存在了就删除
        # 幂等性删除图片
        # 1、根据工具从minio当中获取到老文件
        bucket_name = MinioConfig.minio_bucket_name
        old_image_generator = minio_client.list_objects(
            bucket_name=bucket_name,
            prefix=upload_dir,
            recursive=True,
        )
        # print("1111111111", old_image_generator)
        # 2、把老文件转化为delete_object_list
        delete_object_list = [DeleteObject(obj.object_name) for obj in old_image_generator]
        # 3、调用工具删除minio当中的老文件
        errors = minio_client.remove_objects(
            bucket_name=bucket_name,
            delete_object_list=delete_object_list
        )
        # print("2222222222", errors)
        # 我想打印想知道errors生成器的错误消息的生成器，还是真正删除图片的生成器
        # 如果我们没有遍历它，图片删除了，代表这个生成器就是错误消息的生成器
        for error in errors:
            logger.warning("error occurred when deleting object", error)



        image_with_summary_url_list = []
        for image_with_summary in image_with_summary_list:
            minio_client.fput_object(
                bucket_name=bucket_name,
                object_name=f"{upload_dir}/{image_with_summary.get("image_name")}",  # 目录名 + 文件名
                file_path=image_with_summary.get("image_path"),
            )

            # url = minio_client.get_presigned_url(
            #     method="GET",
            #     bucket_name=bucket_name,
            #     object_name=f"{upload_dir}/{image_with_summary.get("image_name")}",
            #     expires=timedelta(hours=2),
            # )
            # print(url)

            url = f"http://{MinioConfig.minio_endpoint}/{bucket_name}/{upload_dir}/{image_with_summary.get("image_name")}"
            image_with_summary_url_list.append({
                **image_with_summary,
                "url": url
            })
        return image_with_summary_url_list

    def get_image_with_summary_list(self, image_with_context_list):
        # 我们就可以把图片的上下文 图片的内容 我们自己写的提示词 交给大模型去帮我们整理摘要（视觉大模型）
        llm = init_chat_model(
            model=LLMConfig.vl_model,
            model_provider="openai",
            api_key=LLMConfig.openai_api_key,
            base_url=LLMConfig.openai_api_base,
            temperature=LLMConfig.llm_default_temperature
        )
        dq = deque(maxlen=30)
        # 把摘要总结完成暂存到列表
        image_with_summary_list = []
        for index, image_with_context in enumerate(image_with_context_list):
            # 错峰：第一张立即处理，之后每张先等固定间隔，把请求摊开，避开限流窗口
            if index > 0:
                logger.info(f"错峰等待 {self.IMAGE_INTERVAL_SECONDS} 秒后处理第 {index + 1} 张图片")
                time.sleep(self.IMAGE_INTERVAL_SECONDS)

            current_time = time.time()
            # 拿到每张图片的字典，按道理来说就得调用大模型，但是大模型有频率限制，得先做大模型的限频操作
            # 令牌桶 滑动门实现限频操作
            # 1、设计一个队列，这个队列的长度就是你要限定的频率的上限 一般是模型频率上限 * 80%
            # 2、这个队列当中保存的是每个图片调用大模型发请求的时间
            # 3、队列当中每个请求的时间最多能待一分钟
            # 4、队列当中最多能放2400个时间，如果第2401个请求来了，第一个时间还没有超过一分钟，就得等待
            # 5、只有队列当中有位置了，才能继续发请求。

            # 第一步：盲清一波
            while dq and current_time - dq[0] > 60:
                dq.popleft()  # 清除队列的第一个人

            # 第二步：队列只有两种状态 要么满了，要么有空位
            if len(dq) == dq.maxlen:
                # 满了就得等待，计算等待的时间
                need_wait_time = 60 - (current_time - dq[0])

                if need_wait_time > 0:
                    time.sleep(need_wait_time)

                current_time = time.time()

                while dq and current_time - dq[0] > 60:
                    dq.popleft()  # 清除队列的第一个人

            dq.append(current_time)  # 令牌分发

            # 整理图片的内容交给大模型有两种方式，一种是把图片的二进制数据发给大模型，一种是把图片的URL发给大模型

            image_path = image_with_context.get("image_path")
            with open(image_path, "rb") as f:
                image_data = f.read()
                base64_data = base64.b64encode(image_data).decode("utf-8")
            # 根据图片真实后缀取 MIME 类型，取不到时兜底为 jpeg
            mime = self.MIME_TYPES.get(Path(image_path).suffix.lower(), "image/jpeg")

            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime};base64,{base64_data}"
                            },
                        },
                        {"type": "text", "text": f"""
                            这是一张图片，图片上文部分为"{image_with_context.get("pre_text")}"，
                            下文部分为"{image_with_context.get("post_text")}"，请用中文简要总结这张图片的摘要,字数在50字以内。"""
                        },
                    ],
                },
            ]

            res = llm.invoke(input=messages)
            # print(res.content)

            image_with_summary_list.append({
                "image_name": image_with_context.get("image_name"),
                "summary": res.content,
                "image_path": image_with_context.get("image_path")
            })
        return image_with_summary_list

    def get_image_with_context_list(self, image_dir, image_names, md_content):
        IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
        image_with_context_list = []  # 找到每张图片的上下文后先暂存一下，后面要用到就从这个列表当中再去拿
        for image_name in image_names:
            suffix = Path(image_name).suffix
            if suffix.lower() not in IMAGE_EXTENSIONS:
                logger.warning(f"图片后缀名不正确")
                continue
            pattern = re.compile(r"!\[.*?\]\(.*?" + re.escape(image_name) + r"\)")

            match = pattern.search(md_content)  # 从内容当中查找正则相关的子串，找到第一个就结束，如果没有找到，就返回None
            if not match:
                logger.warning(f"没有找到图片的引用")
                continue

            start, end = match.span()  # 拿到每张图片在内容当中的起始位置和结束位置
            pre_text = md_content[max(start - 300, 0):start]
            post_text = md_content[end:min(end + 300, len(md_content))]



            image_with_context_list.append({
                "image_name": image_name,
                "pre_text": pre_text,
                "post_text": post_text,
                "image_path": str(image_dir / image_name)
            })
        return image_with_context_list

    def get_md_content(self, state):
        md_path = state.get("md_path")
        if not md_path:
            logger.error("md_path不能为空")
            raise ValueError("md_path不能为空")
        md_path_obj = Path(md_path)
        if not md_path_obj.exists():
            logger.error("md_path文件不存在")
            raise ValueError("md_path文件不存在")
        # utf-8-sig：兼容带BOM的md
        with open(md_path_obj, "r", encoding="utf-8-sig") as f:
            md_content = f.read()
        return md_content, md_path_obj


if __name__ == '__main__':
    node = NodeMDImg()
    init_state = {
        "md_path": r"D:\study\p1\test_file\hak180产品安全手册\hak180产品安全手册.md"
    }
    result = node(init_state)
    logger.info(json_format(result))




