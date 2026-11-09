import pathlib

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

app = FastAPI()







# todo 配置静态文件夹
# 当前文件目录
BASE_DIR = pathlib.Path(__file__).parent
print("当前文件目录：", BASE_DIR)
static_dir = BASE_DIR / "static"

# 挂载静态文件
# 第一个参数：所有以 /static 开头的请求都交给这个模块处理
# 第二个参数：指定静态文件的存放目录
# 第三个参数：给挂载点起个名字（路由的名字）
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
# 用户访问：http://127.0.0.1:8000/static/image.png
#      ↓
# FastAPI 看到 "/static" 开头
#      ↓
# 交给 StaticFiles 处理
#      ↓
# StaticFiles 去 {static_dir} 找文件
#      ↓
# 返回给用户



#跨域
#跨域其实是浏览器的一个安全策略，也叫同源策略验证
#浏览器目前访问的协议  ip  端口 如果和服务器一模一样，那么代表同源，此时浏览器认为你发请求拿数据是安全的
#如果三者有一个不一样，那么浏览器就会报错，不同源就代表跨域，拿不到数据


# todo配置跨域解决的中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)




@app.get("/hello")
def hello():
    return {"msg": "我爱你杨幂"}




if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)





















