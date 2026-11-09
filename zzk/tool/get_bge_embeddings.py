#这个文件里面的工具就是用来专门对数据进行向量化的
from typing import List

from pymilvus.model.hybrid import BGEM3EmbeddingFunction

from zzk.config.config import BGEM3Config
from zzk.tool.json_format import json_format

# from FlagEmbedding import BGEM3FlagModel
#之前我们采用BGEM3FlagModel去初始化模型对象，现在使用pymilvus当中的BGEM3EmbeddingFunction去初始化模型对象
#因为我们后期数据是和milvus打交道，所以采用milvus封装的类去初始化兼容性会更好
bgem3_model = None
def get_bgem3_model():
    global bgem3_model
    if not bgem3_model:
        bgem3_model = BGEM3EmbeddingFunction(
            model_name=BGEM3Config.bge_m3_path,
            device=BGEM3Config.bge_device,
            use_fp16=BGEM3Config.bge_fp16,
        )
    return bgem3_model




def get_bge_embedding(texts: List[str]):
    model = get_bgem3_model()
    result = model.encode_documents(texts)

    #todo 整理稠密向量的过程 打印

    # print(result,type(result))  #result是一个字典，里面有dense和sparse两个键值对
    # print(result.get("dense"),type(result.get("dense"))) #获取稠密向量 是一个list
    # print(result.get("dense")[0],type(result.get("dense")[0])) #获取列表当中的第一个稠密向量，不是python的类型是numpy的类型 ndarray
    # print(result.get("dense")[0][0],type(result.get("dense")[0][0]))#获取第一个稠密向量当中的第一个元素，还是一个numpy的类型 numpy.float16
    #我们最终需要的稠密向量 必须是一个完全从外到内都是python数据类型的列表，因此我们需要把上面出现numpy的类型转换成python的类型

    # dense = [item.tolist() for item in result.get("dense")]
    # print(dense,type(dense))
    # print(dense[0],type(dense[0]))
    # print(dense[0][0],type(dense[0][0]))

    # 使用tolist把numpy的ndarray类型转化为python的list类型，它默认也会把内部的元素全部也转化为python的类型



    # todo 整理稀疏向量的过程 打印
    # print(result.get("sparse"),type(result.get("sparse")))

    #把稀疏向量打印的对象，尝试转化字典去打印，就可以看到内部的详细信息 主要关注三个列表
    # print(result.get("sparse").__dict__) #两个稀疏向量整体
    # for item in result.get("sparse"): #每个稀疏向量分别打印
    #     print(item.__dict__,type(item))
    #
    #
    # #为啥最终稀疏向量必须封装成字典？因为milvus存储的时候要求
    # print([dict(zip(item.indices.tolist(),item.data.tolist()))  for item in result.get("sparse")])


    return {
        "dense": [item.tolist() for item in result.get("dense")],
        "sparse":[dict(zip(item.indices.tolist(),item.data.tolist()))  for item in result.get("sparse")],
    }



if __name__ == '__main__':
    result = get_bge_embedding(["我爱杨幂","我爱赵丽颖"])
    print(json_format(result)) #result就是数据做完向量化的结果




