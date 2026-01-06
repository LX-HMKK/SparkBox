# agent.py
import json
import re
from openai import OpenAI


class CreativeDemoAgent:
    """面向中小学创客教育的 AI 作品设计助手"""

    def __init__(self, api_key: str) -> None:
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.yixia.ai/v1",
            timeout=60,
            max_retries=3
        )
        self.model = "gemini-3-pro"

    def generate(self, user_idea: str) -> dict:
        """根据用户一句话创意，返回完整创客方案（含预览图）"""
        try:
            prompt = self._build_prompt(user_idea)
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )
            content = completion.choices[0].message.content
            # 增加一些容错处理，防止模型返回Markdown代码块包裹
            json_str = self._extract_json(content)
            return json.loads(json_str)
        except Exception as e:
            # 返回错误信息结构，避免前端崩溃
            return {"error": str(e)}

    def _build_prompt(self, user_idea: str) -> str:
        return f"""
你是一个【面向中小学生的 AI 创客作品设计助手】。

用户会描述一个想制作的作品或创作场景，
请你在【一次回复中】完成以下任务：

1. 给出一套【清晰、可教学、可落地】的作品制作方案
2. 如果你有绘画能力，请生成一张作品示意图的URL；如果没有，请提供一个相关的 Unsplash 图片 URL 或者 占位符图片 URL。

请严格按照以下 JSON 格式输出，不要输出任何多余解释：
(preview_image 字段请只填写 URL 字符串，不要使用 markdown 格式)

```json
{{
  "project_name": "作品名称",
  "target_user": "适用人群",
  "difficulty": "难度等级 (1-5星)",
  "core_idea": "核心创意简述",
  "materials": ["材料1", "材料2"],
  "steps": ["步骤1", "步骤2"],
  "learning_outcomes": ["收获1", "收获2"],
  "preview_image": "IMAGE_URL"
}}
用户需求：
{user_idea}
"""

    @staticmethod
    def _extract_json(text: str) -> str:
        # 清理可能存在的 markdown 代码块标记
        text = re.sub(r"^```json\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^```\s*$", "", text, flags=re.MULTILINE)

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            # 如果找不到，尝试返回原始文本以便调试
            raise ValueError(f"无法提取JSON，模型返回内容：{text[:100]}...")
        return match.group()