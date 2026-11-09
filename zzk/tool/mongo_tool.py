#这个文件是专门给mongodb的操作做了封装，后期操作mongo的增删改查全部都对应这个文件当中的一个函数
#1、获取单例的mongo链接对象
import time

from bson import ObjectId
from pymongo import MongoClient,ASCENDING

from zzk.config.config import MongoConfig

mongo_client = None
def get_mongo_client():
    global mongo_client
    if not mongo_client:
        mongo_client = MongoClient(
            host=MongoConfig.mongo_host,
            port=MongoConfig.mongo_port,
        )
        print(mongo_client)
    return mongo_client

# db = client[""]

mongo_tool = None
def get_mongo_tool():
    global mongo_tool #声明使用全局变量，保证单例复用
    if mongo_tool is None: #首次调用时才初始化（懒加载）
        mongo_client = get_mongo_client() #获取连接对象，目的是为了创建数据库
        db = mongo_client[MongoConfig.mongo_db_name] #创建数据获取数据库对象
        mongo_tool = db["chat_message"] #创建集合对象 获取集合对象
        # mongo_tool.create_index([("session_id", 1),("ts",-1)]) #创建索引
    return mongo_tool #返回集合对象


#表的增删改查
# clear_history清空某个session_id的所有消息
def clear_history(session_id):
    mongo_tool = get_mongo_tool()
    mongo_tool.delete_many({"session_id": session_id})

# get_recent_messages 根据session_id获取最近的n条消息
def get_recent_messages(session_id,n=10):
    mongo_tool = get_mongo_tool()
    result = mongo_tool.find({"session_id":session_id}).sort({"ts":-1}).limit(n)
    return list(result) #必须强转传入游标对象才能获取到字典的列表数据


# 增改一体，一个函数可以增也可以改，增和改在这里都是全量
# save_chat_message保存历史记录（根据id决定是添加还是修改）
# 一条数据如果是新增，那么它还没进入到数据库，此时不可能有id
# 一条数据如果是修改，那么代表这条数据是从数据库里面取出来的，所以一定有id


def save_chat_message(session_id,role,text,rewritten_query=None,item_names=None,ts=None,message_id=None):
    mongo_tool = get_mongo_tool()
    if message_id:
        # 修改
        mongo_tool.update_one({"_id":message_id},{
            "$set":{
                "session_id":session_id,
                "role":role,
                "text":text,
                "rewritten_query":rewritten_query,
                "item_names":item_names,
                "ts":ts or time.time(),
            }
        })
    else:
        result = mongo_tool.insert_one({
            "session_id":session_id,
            "role":role,
            "text":text,
            "rewritten_query":rewritten_query,
            "item_names":item_names,
            "ts":ts or time.time(),
        })
        return result.inserted_id #添加成功返回新增的数据id，注意打印的时候看不出来,要返回就得inserted_id，而且是一个ObjectId类型


def update_history_item_names(ids,item_names,rewritten_query):
    mongo_tool = get_mongo_tool()
    mongo_tool.update_many({"_id":{"$in":ids}},{
        "$set":{
            "item_names":item_names,
            "rewritten_query":rewritten_query
        }
    })




if __name__ == '__main__':
    session_id = "test_001"

    #todo 测试增
    # result = save_chat_message(session_id, "user", "咨询下烫金机。")
    # print(result,type(result))



    #todo 测试查
    # result = get_recent_messages(session_id)
    # print(result)


    #todo 测试改
    # save_chat_message("hahaha", "user", "hehehehe。",message_id=ObjectId('6ad336ee658b92404e63f9d5'))



    #todo 测试删
    clear_history(session_id)


