import base64
import json
import re
from io import BytesIO
from PIL import Image
from openai import OpenAI

class VisionAgent:
    def __init__(self, config):
        """
        初始化：接收配置，建立连接
        """
        #预留全局配置
        self.full_config = config
        # 根据 yaml 结构提取视觉配置
        self.vision_cfg = config["vision"]

        self.client = OpenAI(
            api_key=self.vision_cfg["api_key"],
            base_url=self.vision_cfg["base_url"],
            timeout=60
        )

    def _extract_json_from_text(self, text):
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

    def _process_image_to_base64(self, image_path):
        try:
            target_min_size = self.full_config["vision"]["target_min_size"]

            img = Image.open(image_path).convert("RGB")
            w, h = img.size

            # 放大逻辑
            if min(w, h) < target_min_size:
                scale = target_min_size / min(w, h)
                new_size = (int(w * scale), int(h * scale))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                print(f" [Vision] 图片已放大: {w}x{h} -> {new_size[0]}x{new_size[1]}")

            buffered = BytesIO()
            img.save(buffered, format="JPEG")
            return base64.b64encode(buffered.getvalue()).decode("utf-8")
        except Exception as e:
            print(f" 图片处理失败: {e}")
            return None

    def analyze(self, image_path):
        """对外接口"""
        # 1. 图片处理
        base64_image = self._process_image_to_base64(image_path)
        if not base64_image:
            return None

        # 2. 准备 Prompt
        prompt_text = self.full_config["vision"]["prompt"]

        # prompt 后缀
        final_prompt = prompt_text + "\n\n请务必只输出纯 JSON，不要包含 Markdown 标记。"

        print(f" [Vision] 正在调用模型: {self.vision_cfg['model_name']}...")

        try:
            response = self.client.chat.completions.create(
                model=self.vision_cfg["model_name"],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": final_prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        ]
                    }
                ]
            )

            # 获取原始文本
            raw_content = response.choices[0].message.content

            # 🐛 DEBUG: 打印出来看看模型到底回了什么！
            # print(f" [调试] 原始返回: {raw_content}")

            return self._extract_json_from_text(raw_content)

        except Exception as e:
            print(f" 视觉请求错误: {e}")
            return None
