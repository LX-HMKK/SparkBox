# import json
# import re
# import random
# import urllib.parse
# from flask import Flask, render_template, request, jsonify
# from openai import OpenAI
#
# # ==========================================
# # 核心逻辑类
# # ==========================================
# class CreativeDemoAgent:
#     def __init__(self, api_key: str) -> None:
#         self.client = OpenAI(
#             api_key=api_key,
#             base_url="https://api.yixia.ai/v1",
#             # 【修复1】超时时间改为 120 秒，Gemini/GPT-4 有时响应很慢
#             timeout=120,
#             max_retries=3
#         )
#         self.model = "gemini-3-pro"
#
#     def generate(self, user_idea: str) -> dict:
#         prompt = self._build_prompt(user_idea)
#         try:
#             # 1. 调用 AI 生成文本方案
#             completion = self.client.chat.completions.create(
#                 model=self.model,
#                 messages=[{"role": "user", "content": prompt}]
#             )
#
#             content = completion.choices[0].message.content
#             json_str = self._extract_json(content)
#             result = json.loads(json_str)
#
#             # 【修复2】图片必须放在 static 文件夹下，通过 Web 路径访问
#             # 请确保你的项目目录下有 static/2.png 这个文件
#             result["preview_image"] = "/static/2.png"
#
#             return result
#
#         except Exception as e:
#             print(f"Server Error details: {e}")
#             return {
#                 "error": "生成超时或失败",
#                 "details": str(e),
#                 "project_name": "连接超时",
#                 "core_idea": "AI 响应时间过长，请重试",
#                 # 即使出错也显示这张图，保持界面完整
#                 "preview_image": "/static/2.png"
#             }
#
#     def _build_prompt(self, user_idea: str) -> str:
#         # 【修复3】精简 Prompt，去掉无关的图片描述要求，提高生成速度
#         return f"""
# 你是一个中小学创客教育助手。
# 用户想法：{user_idea}
#
# 请直接输出一个 JSON 格式的制作方案。
# 严格遵守 JSON 格式，不要输出任何 Markdown 标记或额外文字。
#
# {{
#   "project_name": "简短的作品名称",
#   "target_user": "适合年级",
#   "difficulty": "3星",
#   "core_idea": "一句话介绍核心功能",
#   "materials": ["材料A", "材料B", "材料C"],
#   "steps": ["第一步干什么", "第二步干什么", "第三步干什么"],
#   "learning_outcomes": ["学到什么知识1", "学到什么知识2"]
# }}
#         """
#
#     @staticmethod
#     def _extract_json(text: str) -> str:
#         try:
#             # 尝试提取 ```json ... ``` 或者是直接的 { ... }
#             match = re.search(r"\{[\s\S]*\}", text)
#             if match: return match.group()
#             return text
#         except:
#             return "{}"
#
#
# # ==========================================
# # Flask Web 服务
# # ==========================================
# app = Flask(__name__)
#
# # 建议：如果还是报错，可以尝试换一个更稳定的模型名，例如 "gpt-3.5-turbo" 测试一下
# API_KEY = "sk-kpQ9SDHDbDgpsIjNUsyQldJf5TJzPy3EHi58r5VjOmPbIiHW"
# agent = CreativeDemoAgent(api_key=API_KEY)
#
#
# @app.route('/')
# def index():
#     return render_template('index.html')
#
#
# @app.route('/static/<path:filename>')
# def serve_static(filename):
#     # 显式处理静态文件（通常 Flask 会自动处理，但加上这个保险）
#     return app.send_static_file(filename)
#
#
# @app.route('/api/create', methods=['POST'])
# def create_project():
#     data = request.json
#     idea = data.get('idea', '')
#     if not idea:
#         return jsonify({"error": "请输入想法"}), 400
#
#     print(f"收到请求: {idea}，开始请求 AI...") # 增加后台日志方便调试
#     result = agent.generate(idea)
#     print("AI 请求结束")
#     return jsonify(result)
#
#
# if __name__ == '__main__':
#     # threaded=True 可以防止一个请求卡死整个服务
#     app.run(debug=True, port=5000, threaded=True)
import time
from flask import Flask, render_template, request, jsonify


# ==========================================
# 核心逻辑类 (测试专用 - Mock模式)
# ==========================================
class CreativeDemoAgent:
    def __init__(self, api_key: str = None) -> None:
        # 测试模式下不需要连接 OpenAI
        pass

    def generate(self, user_idea: str) -> dict:
        # 1. 模拟 AI 思考的时间 (2秒)，方便你观察 Loading 动画
        time.sleep(2)

        # 2. 直接返回写死的测试数据
        # 无论用户输入什么，都会返回这个结果
        mock_result = {
            "project_name": "火星探测全向车 (UI测试)",
            "target_user": "初中一年级",
            "difficulty": "⭐⭐⭐⭐",
            "core_idea": "基于麦克纳姆轮的全向移动底盘，搭载机械臂进行模拟采样。",
            "materials": [
                "ESP32 主控板 x1",
                "麦克纳姆轮 x4",
                "N20 减速电机 x4",
                "SG90 舵机 (机械臂用) x2",
                "3D打印车架 x1",
                "锂电池组 7.4V x1"
            ],
            "steps": [
                "组装底盘：将四个麦克纳姆轮按照特定方向安装到电机上。",
                "电路连接：连接电机驱动板与 ESP32，注意正负极防止烧毁。",
                "机械臂调试：将舵机归零，安装机械臂爪子结构。",
                "程序编写：烧录全向运动算法 (前后左右+斜向移动)。",
                "整机测试：通过蓝牙手柄控制小车完成抓取任务。"
            ],
            "learning_outcomes": [
                "理解麦克纳姆轮的矢量运动原理",
                "掌握多路电机的协同控制算法",
                "学习 ESP32 的蓝牙通信功能"
            ],
            # 确保你的 /static/ 文件夹下有 2.png
            "preview_image": "/static/2.png"
        }

        return mock_result


# ==========================================
# Flask Web 服务
# ==========================================
app = Flask(__name__)

# 不需要 API KEY 了
agent = CreativeDemoAgent()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/static/<path:filename>')
def serve_static(filename):
    return app.send_static_file(filename)


@app.route('/api/create', methods=['POST'])
def create_project():
    data = request.json
    idea = data.get('idea', 'Default Idea')

    print(f"收到UI测试请求: {idea} (将返回固定数据)")

    result = agent.generate(idea)

    return jsonify(result)


if __name__ == '__main__':
    app.run(debug=True, port=5000)