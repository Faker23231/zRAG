# 目标：后端先接收查询请求，后台处理，SSE 推送处理结果
#
# 案例2 使用post请求加异步操作
# 	1、前端发请求传递一个query，再传递一个session_id  两个参数到后端进行请求体接收
# 	2、后端写一个接口获取这两个参数，并返回给前端收到的消息，并启动task造消息
import asyncio
import time

# 	3、前端订阅sse请求
# 	4、服务端需要写sse回复接口，从task当中获取自己的队列，从队列当中一个一个yield答案


import uvicorn
from fastapi import FastAPI, Body, BackgroundTasks, Query
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from asyncio import Queue

from starlette.responses import StreamingResponse

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class BodyParams(BaseModel):
    query: str = Field(..., description="查询内容")
    session_id: str = Field(..., description="会话id")


q_dict = {}
async def make_data(query, session_id):
    if q_dict.get(session_id) is None:
        q_dict[session_id] = Queue()

    q = q_dict.get(session_id)
    await q.put("我爱杨幂01")
    await q.put("我爱杨幂02")
    await q.put("我爱杨幂03")
    await q.put("我爱杨幂04")
    await q.put("我爱杨幂05")
    await q.put(None)

#后台任务当中其实是可以跑异步操作的，但是不建议，一旦后台任务当中是异步操作，那么后台任务里面从高到低必须都是异步


@app.post("/sse02")
def sse02(
    background_tasks: BackgroundTasks,
    body_params: BodyParams = Body(...,description="请求体参数"),

):
    query = body_params.query
    session_id = body_params.session_id
    background_tasks.add_task(make_data, query, session_id)

    return {"msg": "收到"}


@app.get("/handlersse02")
async def handlersse02(
    session_id: str = Query(..., description="会话id")
):

    async def generate_data():
        while q_dict.get(session_id) is None:
            # time.sleep(1)
            await asyncio.sleep(1)
        q = q_dict.get(session_id)
        while True:
            data = await q.get()
            await asyncio.sleep(1)
            yield f"data: {data}\n\n"
            if data is None:
                break


    return StreamingResponse(generate_data(), media_type="text/event-stream")



if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)