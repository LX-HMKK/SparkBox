import json
import re
import random
import urllib.parse
from openai import OpenAI

class CreativeDemoAgent:
    """面向中小学创客教育的 AI 作品设计助手"""
    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.yixia.ai/v1",  # 去掉尾部空格！
            timeout=120,
            max_retries=3
        )
        self.model = "gemini-3-pro"

    def build_pollinations_url(self, image_prompt: str) -> str:
        """
        构建高保真绘图链接
        使用 Flux 模型 + 随机种子 + 增强画质参数
        """
        encoded_prompt = urllib.parse.quote(image_prompt)
        seed = random.randint(0, 1000000)

        # model=flux 是关键，它对机械结构的理解远超默认模型
        # aspect=4:3 这种比例更像专业相机拍摄
        url = (
            f"https://image.pollinations.ai/prompt/{encoded_prompt}"
            f"?model=flux&width=1280&height=960&seed={seed}&nologo=true&enhance=true"
        )
        return url

    # --------------------------------------------------
    # 公有接口
    # --------------------------------------------------
    def generate(self, user_idea: str) -> dict:
        prompt = self._build_prompt(user_idea)

        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            json_str = self._extract_json(completion.choices[0].message.content)
            result = json.loads(json_str)

            # 优化提示词后缀：增加具体的渲染风格词汇
            EDU_IMAGE_SUFFIX = (
                ", hyper-realistic educational robot kit, "
                "isometric view, exploded view style, "  # 爆炸图或等轴图适合展示零件
                "electronic components, arduino, wires, sensors, "
                "clean white background, studio lighting, 4k resolution, 3d blender render"
            )

            # 组合提示词
            full_image_prompt = result["image_prompt"] + EDU_IMAGE_SUFFIX

            # 生成链接
            result["preview_image"] = self.build_pollinations_url(full_image_prompt)

            # 移除 raw image_prompt，前端不需要显示这个
            if "image_prompt" in result:
                del result["image_prompt"]

            return result

        except Exception as e:
            print(f"Error: {e}")
            return {"error": "生成失败，请重试"}

    # --------------------------------------------------
    # 内部工具
    # --------------------------------------------------
    def _build_prompt(self, user_idea: str) -> str:
        return f"""
你是一个【面向中小学生的 AI 创客作品设计助手】。
用户需求：{user_idea}
用户会描述一个想制作的作品或创作场景，
请你在【一次回复中】完成以下任务：

1. 给出一套【清晰、可教学、可落地】的作品制作方案
2. 同时生成一张【作品实物预览图】，帮助用户直观理解成品样子

⚠️ 非常重要的规则：
- 你必须【只输出 JSON】
- 不要输出任何解释性文字
关于 image_prompt 的特别要求：
请用英文详细描述该作品的【外观视觉特征】。包括形状、颜色、主要材质（如木板、亚克力、电线）、核心传感器组件。不要描述抽象功能，只描述在这个作品的照片里能看到什么。
请严格按照以下 JSON 格式输出，不要输出任何多余解释：

{{
  "project_name": "",
  "target_user": "",
  "difficulty": "",
  "core_idea": "",
  "materials": [],
  "steps": [],
  "learning_outcomes": [],
  "preview_image": "https://example.com/preview.png"
}}

"""

    @staticmethod
    def _extract_json(text: str) -> str:
        # 增加更稳健的 JSON 提取逻辑
        try:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return match.group()
            # 如果没有找到花括号，尝试直接解析（防止模型只返回了 json 内容没有 markdown 标记）
            return text
        except:
            raise ValueError("无法解析模型返回的数据")


# --------------------------------------------------
# 脚本入口
# --------------------------------------------------
if __name__ == "__main__":
    API_KEY = "sk-kpQ9SDHDbDgpsIjNUsyQldJf5TJzPy3EHi58r5VjOmPbIiHW"
    #实例化代理
    agent = CreativeDemoAgent(api_key=API_KEY)
    #用户一句话需求
    user_input = "我想制作一个智能垃圾桶，可以自动感应开盖"
    result = agent.generate(user_input)
    print("====== 生成结果 ======")
    print(json.dumps(result, ensure_ascii=False, indent=2))