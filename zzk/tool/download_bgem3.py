"""
下载向量化模型 BAAI/bge-m3（ModelScope 源）

用法：
    python zzk/tool/download_bgem3.py

可通过环境变量 MODEL_LOCAL_DIR 指定模型落地目录，
默认：/home/ubuntu/ai_models/bge-m3（Linux）
     D:/ai_models/modelscope_cache/models/bge-m3（Windows）
下载完成后把该目录填到 .env 的 BGE_M3_PATH。
"""

import os
import sys

from modelscope.hub.snapshot_download import snapshot_download

# 模型落地目录：优先用环境变量，其次按操作系统给一个默认值
if os.getenv("MODEL_LOCAL_DIR"):
    local_dir = os.getenv("MODEL_LOCAL_DIR")
elif sys.platform.startswith("win"):
    local_dir = "D:/ai_models/modelscope_cache/models/bge-m3"
else:
    local_dir = "/home/ubuntu/ai_models/bge-m3"

# 这两个目录/文件跟向量化无关，跳过以节省下载体积
ignore_patterns = ["onnx*", "imgs*", "*.jpg", ".gitattributes"]

model_dir = snapshot_download(
    "BAAI/bge-m3",
    local_dir=local_dir,
    ignore_patterns=ignore_patterns,
)

print(f"模型已下载到: {model_dir}")
