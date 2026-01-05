import json
import re
import os
from openai import OpenAI

class CreativeDemoAgent:
    """面向中小学创客教育的 AI 作品设计助手"""

    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.yixia.ai/v1",  # 去掉尾部空格！
            timeout=60,
            max_retries=3
        )
        self.model = "gemini-3-pro"

    # --------------------------------------------------
    # 公有接口
    # --------------------------------------------------
    def generate(self, user_idea: str) -> dict:
        """根据用户一句话创意，返回完整创客方案（含预览图）"""
        prompt = self._build_prompt(user_idea)
        # ④ 用 chat.completions 接口
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}]
        )
        json_str = self._extract_json(completion.choices[0].message.content)
        return json.loads(json_str)

    # --------------------------------------------------
    # 内部工具
    # --------------------------------------------------
    def _build_prompt(self, user_idea: str) -> str:
        return f"""
你是一个【面向中小学生的 AI 创客作品设计助手】。

用户会描述一个想制作的作品或创作场景，
请你在【一次回复中】完成以下任务：

1. 给出一套【清晰、可教学、可落地】的作品制作方案
2. 同时生成一张【作品实物预览图】，帮助用户直观理解成品样子

请严格按照以下 JSON 格式输出，不要输出任何多余解释：
（preview_image 字段中请使用 markdown image 形式）

```json
{{
  "project_name": "",
  "target_user": "",
  "difficulty": "",
  "core_idea": "",
  "materials": [],
  "steps": [],
  "learning_outcomes": [],
  "preview_image": "![preview](IMAGE_URL_OR_BASE64)"
}}
用户需求：
{user_idea}
"""

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise ValueError("❌ 未能从模型回复中提取有效 JSON，原始回复：\n" + text)
        return match.group()


# --------------------------------------------------
# 脚本入口
# --------------------------------------------------
if __name__ == "__main__":
    # ===== 1. 填入你的 Gemini API Key =====
    API_KEY = "sk-Ye8XGQ9aZDxJwpTIaKc4rUGPS2Yma5G8lTsSIwO985DUescy"
    # ===== 2. 实例化代理 =====
    agent = CreativeDemoAgent(api_key=API_KEY)
    # ===== 3. 用户一句话需求 =====
    user_input = "我想制作一个智能小车，用来给10-12岁的学生学习编程和传感器"
    # ===== 4. 生成并打印 =====
    result = agent.generate(user_input)
    print("====== AI 生成结果 ======")
    print(json.dumps(result, ensure_ascii=False, indent=2))