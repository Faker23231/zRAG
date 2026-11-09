import time

import uvicorn
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()


#后台任务说的情况结果是： 前端发一个请求，后端接口接受到请求后立即返回响应
#但是接口当中调用了后台任务，后台任务可以在后台继续执行。
#接口返回已经结束了，后台任务还在运行

def print_love(n,seconds=1):
    while n > 0:
        print("我爱你杨幂")
        time.sleep(seconds)
        n -= 1



@app.get("/backgroundtask")
def background_task(background_tasks: BackgroundTasks):

    background_tasks.add_task(print_love,10,seconds=2)

    return {"message": "后台任务正在执行"}




if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)

