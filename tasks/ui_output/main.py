import time
import uuid
from flask import Flask, render_template, jsonify, request

app = Flask(__name__)

# --- 数据存储 ---
# 使用列表存储所有生成的历史记录
history = []


@app.route('/')
def index():
    return render_template('index.html')


# --- 获取数据的核心接口 ---
@app.route('/get_data')
def get_data():
    """
    前端通过此接口获取数据。
    参数: index (可选)
      - 不传或传 -1: 返回最新的一条
      - 传数字: 返回指定位置的历史记录
    """
    total_count = len(history)

    # 如果没有数据
    if total_count == 0:
        return jsonify({"empty": True, "total_count": 0})

    # 获取请求的索引
    req_index = request.args.get('index', type=int)

    # 逻辑：默认返回最新，或者返回指定索引
    if req_index is None or req_index < 0:
        target_index = total_count - 1  # 最新
    else:
        target_index = req_index

    # 越界保护
    if target_index >= total_count:
        target_index = total_count - 1
    if target_index < 0:
        target_index = 0

    return jsonify({
        "empty": False,
        "total_count": total_count,  # 总页数
        "current_index": target_index,  # 当前返回的是第几页
        "data": history[target_index]  # 实际数据
    })


# --- 模拟触发拍照 (生成新数据) ---
@app.route('/trigger_capture', methods=['POST'])
def trigger_capture():
    global history

    # 模拟生成新数据
    new_item = {
        "id": str(uuid.uuid4()),
        # 使用随机图模拟不同照片
        "image_url": f"https://picsum.photos/800/600?random={time.time()}",
        "text": f"【记录 #{len(history) + 1}】这是在 {time.strftime('%H:%M:%S')} 拍摄的画面。通过左右键可以翻阅历史记录。",
        "timestamp": time.strftime('%H:%M:%S')
    }

    history.append(new_item)

    # 限制历史记录长度（例如只保留最近50条，防止内存溢出）
    if len(history) > 50:
        history.pop(0)

    return jsonify({"status": "success", "new_index": len(history) - 1})


if __name__ == '__main__':
    app.run(debug=True, port=5000)