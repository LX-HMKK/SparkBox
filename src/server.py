import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置你的日志目录路径
BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = str(BASE_DIR / "logs" / "ai_logs")

# 1. 核心接口：获取所有对话文件列表
@app.get("/api/list_files")
def list_files():
    # 扫描目录下所有 .json 文件
    files = [f for f in os.listdir(LOG_DIR) if f.endswith('.json')]
    # 按文件名排序（通常日期命名的话，倒序排列可以看到最新的）
    files.sort(reverse=True) 
    return {"files": files}

# 2. 挂载静态文件目录 (用于直接访问 json 内容和图片)
app.mount("/logs", StaticFiles(directory=LOG_DIR), name="logs")

if __name__ == "__main__":
    print(f"服务已启动，正在监听: {LOG_DIR}")
    uvicorn.run(app, host="0.0.0.0", port=8000)