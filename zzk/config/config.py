# import os
#
# from dotenv import load_dotenv
# load_dotenv(override=True) #覆盖系统环境变量当中配置的配置项吗，全部统一拿.env当中的配置
#


import os
from dotenv import load_dotenv
# 使用绝对路径加载 .env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.env"))
load_dotenv(dotenv_path=env_path, override=True)


#如果我们没有指定绝对路径，那么load_dotenv会默认从当前目录开始找.env,如果没有就往上爬楼，直到找到，找不到就炸
#我们指定了绝对路径，就会有两个好处
#1、效率高  直接去项目根目录下找.env 不用往上爬楼
#2、安全性高 如果我们在其它目录下也有同名的.env文件，此时不指定绝对路径，在爬楼的时候，第一次碰到.env就会直接拿这个.env作为
# 配置文件去使用，此时这个配置文件根本就不是我们项目的配置文件，这样就会造成安全问题


#mineru的配置信息
class MineruConfig:
    mineru_token=os.getenv('MINERU_TOKEN')



class LLMConfig:
    openai_api_key = os.getenv('OPENAI_API_KEY')
    openai_api_base = os.getenv('OPENAI_API_BASE')
    llm_default_model = os.getenv('LLM_DEFAULT_MODEL')
    #配置文件当中拿到的所有值，类型都是字符串，拿到代码当中需要强转
    llm_default_temperature = float(os.getenv('LLM_DEFAULT_TEMPERATURE'))
    vl_model = os.getenv('VL_MODEL')
    item_model = os.getenv('ITEM_MODEL')


class MinioConfig:
    minio_endpoint = os.getenv('MINIO_ENDPOINT')
    minio_access_key = os.getenv('MINIO_ACCESS_KEY')
    minio_secret_key = os.getenv('MINIO_SECRET_KEY')
    minio_bucket_name = os.getenv('MINIO_BUCKET_NAME')
    minio_img_dir = os.getenv('MINIO_IMG_DIR')


class BGEM3Config:
    bge_m3_path = os.getenv('BGE_M3_PATH')
    bge_device = os.getenv('BGE_DEVICE')
    bge_fp16 = os.getenv('BGE_FP16') in ("True","true","1")


class MilvusConfig:
    # Milvus 连接地址
    milvus_url = os.getenv('MILVUS_URL')
    chunks_collection = os.getenv('CHUNKS_COLLECTION')
    item_name_collection = os.getenv('ITEM_NAME_COLLECTION')

class MongoConfig:
    mongo_url = os.getenv('MONGO_URL')
    mongo_host = os.getenv('MONGO_HOST')
    mongo_port = int(os.getenv('MONGO_PORT'))
    mongo_db_name = os.getenv('MONGO_DB_NAME')


class MCPConfig:
    mcp_base_url = os.getenv('MCP_BASE_URL')
    mcp_api_key = os.getenv('MCP_API_KEY')

class RerankConfig:
    rerank_base_url = os.getenv('RERANK_BASE_URL')
    rerank_api_key = os.getenv('RERANK_API_KEY')