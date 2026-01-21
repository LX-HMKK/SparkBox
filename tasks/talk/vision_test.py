import os
import json
import yaml
import base64
import re  # 引入正则库
from io import BytesIO
from PIL import Image
from openai import OpenAI


# 加载配置
def load_config(config_path="config.yaml"):
    # 向上回退两层,到达 d:\StudyWorks\3.1\item1\SparkBox
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    abs_path = os.path.join(base_dir, 'config', config_path)
    try:
        with open(abs_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 配置加载失败: {e}")
        return None


# JSON 清洗
def extract_json_from_text(text):
    """
    不管模型返回的是纯 JSON，还是带 Markdown 的 ```json，
    还是混杂了废话，都尝试提取出真正的 JSON 部分。
    """
    if not text:
        return None

    # 1. 尝试移除 Markdown 代码块标记
    cleaned_text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r"```", "", cleaned_text)

    # 2. 如果首尾有空白字符，去除
    cleaned_text = cleaned_text.strip()

    # 3. 尝试直接解析
    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        pass  # 解析失败，继续尝试正则提取

    # 4. 正则暴力提取 {} 包裹的内容
    try:
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            return json.loads(match.group(1))
    except:
        pass

    return None


# 图片预处理
def process_image_to_base64(image_path, target_min_size):
    try:
        img = Image.open(image_path).convert("RGB")
        w, h = img.size

        # 放大逻辑
        if min(w, h) < target_min_size:
            scale = target_min_size / min(w, h)
            new_size = (int(w * scale), int(h * scale))
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            print(f"🔄 图片已放大: {w}x{h} → {new_size[0]}x{new_size[1]}")

        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as e:
        print(f"❌ 图片处理失败: {e}")
        return None


# 模型分析函数
def analyze_student_idea(image_path, config):
    try:
        # 读取配置
        vision_cfg = config["vision"]
        prompt_text = vision_cfg["prompt"]
        target_size = vision_cfg["target_min_size"]

        # 初始化客户端
        client = OpenAI(
            api_key=vision_cfg["api_key"],
            base_url=vision_cfg["base_url"],
            timeout=60
        )

        # 图片处理
        base64_image = process_image_to_base64(image_path, target_size)
        if not base64_image:
            return None

        print(f"🤖 正在调用模型: {vision_cfg['model_name']}...")

        # 发送请求，依靠 Prompt 和 clean 函数来处理
        response = client.chat.completions.create(
            model=vision_cfg["model_name"],
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt_text + "\n\n请务必只输出纯 JSON，不要包含 Markdown 标记。"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
        )

        # 获取原始文本
        raw_content = response.choices[0].message.content

        # 🐛 DEBUG: 打印出来看看模型到底回了什么！
        #print(f"\n🐛 [调试] 模型原始返回内容:\n{raw_content}\n")

        # 数据清洗并解析
        json_data = extract_json_from_text(raw_content)

        if json_data:
            return json_data
        else:
            print("❌ 无法从返回内容中提取 JSON，请debug检查上方调试信息。")
            return None

    except Exception as e:
        print(f"❌ 请求过程发生错误: {e}")
        return None


if __name__ == "__main__":
    config = load_config()
    if config:
        image_file = "warped_20260115_201920.jpg"
        if os.path.exists(image_file):
            result = analyze_student_idea(image_file, config)
            if result:
                print("\n✅ 分析成功")
                print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"⚠️ 图片不存在: {image_file}")

