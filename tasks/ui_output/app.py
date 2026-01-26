
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