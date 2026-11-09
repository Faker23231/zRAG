import uvicorn
from fastapi import FastAPI
from starlette.responses import JSONResponse

app = FastAPI(
    title="FastAPI",
    description="这是一个测试的接口服务",
    version="0.1.0",
)
#这些参数后期再接口文档当中就可以看到，fastapi会给我们自动生成在线接口文档
#接口文档：接口说明，主要是后端人员把每个接口的使用说明给前端


@app.get("/")
def index():
    # return JSONResponse(
    #     status_code=200,
    #     content={
    #         "message": "我爱你杨幂",
    #     }
    # )
    return {"message": "我爱你杨幂"}  #这个其实是返回了一个json，只是它是简写


#fastapi既然玩的是后端，那么后端其实我们关注的就是两件事
# 1、接啥  参数（路径 查询 请求体） 请求头  请求方式
# 2、返啥  json数据  文件  流式。。。。


if __name__ == '__main__':
    uvicorn.run(
        app,
        host="0.0.0.0", #允许所有用户访问
        port=8000
    )


