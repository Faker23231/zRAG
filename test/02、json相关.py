# 是什么
# json是一种数据格式，这种数据格式主要是用来做前后端交互的
# 在老早前，前后端进行请求交互的时候，如果要传递复杂数据，用的是xml，当时json还不流行
# xml是html的爹，它是用标签来描述表示数据的，最终是一个文件
# <star>
#     <name>杨幂</name>
#     <age>28</age>
#     <gender>female</gender>
#     <height>165</height>
# </star>
# 这样做完全可以达到交互的效果，但是问题很大。
# 1、xml传的是一个文件，文件比较大，传输效率比较低（占带宽）
# 2、xml的标签都是无用的东西，那么后端就得花费很大的精力去解析xml，效率也会低
# 所以xml是很早以前前后端用来传递的格式，现在几乎销声匿迹，只要现在看到xml都是用来做配置文件
#
# xml死的原因就是因为json的出现


# 为什么
# json这种数据格式本质上是一个字符串，俗称叫json串，它是一种轻量级的数据交换格式
# 对于字符串来说，它的体量就很小，传输效率很高（占带宽小）
# 字符串本身里面要的东西就是数据，不需要额外的标签去描述，前后端也不用费精力去解析，效率很高

# 怎么做
# json其实就相当于是前后端的一个月老
# 前端发请求给后端，前端传递的是前端js的数据类型，就算能传递到后端，后端java或者python也不认识前端传递过来的数据类型
#此时前端非要传递复杂数据，就必须把js的复杂数据类型转化成json(序列化json),然后把json字符串发给后端，后端就不能收到json认识这个字符串
# 后端拿到json串以后想要操作这个数据，就得借助后端java或者python当中给的json工具包，把json反序列化为对应语言的数据类型



# 前端当中有一个工具包 叫JSON    叫JSON.stringify() 序列化    JSON.parse() 反序列化
# python当中有一个工具包叫json  叫json.dumps() 序列化       json.loads()反序列化


# json包当中一共有两对4个方法：
import json
#专门把数据进行转化
# json.dumps()
# json.loads()
data = {
    "name":"yangmi",
    "age":28,
    "gender":"female",
    "height":165
}
# 先把字典序列化为json串,然后再返回给前端
data_json = json.dumps(data)

print(data,type(data))
print(data_json,type(data_json))



json_data = json.loads(data_json) # 把json串反序列化为字典
print(data_json,type(data_json))
print(json_data,type(json_data))

json_data["name"] = "杨幂"
print(json_data,type(json_data))



#把数据进行转化后，和文件进行操作
data2 = {
    "name":"赵丽颖",
    "age":28,
}

# json.dump() #先把python数据转化为json,然后再写入到json文件中
# json.load() #先从json文件中读取数据，然后再转化为python的数据类型
# with open("data.json","w",encoding="utf-8") as f:
#     json.dump(data2,f)


with open("data.json","r",encoding="utf-8") as f:
    python_dict = json.load(f)
    print(python_dict,type(python_dict))















