import json
import re
from openai import OpenAI

class SolutionAgent:
    """
    接收视觉分析数据 -> 生成方案 & 绘图描述词
    """

    def __init__(self, config):
        """
        初始化：从 config 中加载配置
        """
        self.cfg = config["solution_generator"]

        self.client = OpenAI(
            api_key=self.cfg["api_key"],
            base_url=self.cfg["base_url"],
            timeout=120,
            max_retries=3
        )
        self.model = self.cfg["model_name"]

    # --------------------------------------------------
    # 公有接口
    # --------------------------------------------------
    def generate(self, vision_data: dict) -> dict:
        """
        核心生成函数
        Args:
            vision_data: Step 1 输出的 JSON 字典
        Returns:
            dict: 包含方案详情 + image_prompt 的 JSON
        """
        # 1. 构建 Prompt (将视觉数据注入)
        prompt = self._build_prompt_with_context(vision_data)

        try:
            print(f"🧠 [Solution] 正在构思方案 (模型: {self.model})...")

            # 2. 调用 API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )

            # 3. 提取内容
            raw_text = completion.choices[0].message.content
            json_str = self._extract_json(raw_text)

            return json.loads(json_str)

        except Exception as e:
            print(f"❌ 方案生成失败: {e}")
            return None

    # --------------------------------------------------
    # 内部工具
    # --------------------------------------------------
    def _build_prompt_with_context(self, vision_data: dict) -> str:
        """
        将 Step 1 的数据格式化，并与 System Prompt 拼接
        """
        # 将字典转为易读的字符串
        context_str = json.dumps(vision_data, ensure_ascii=False, indent=2)

        # 读取 config 中的 Prompt
        system_prompt = self.cfg["prompt"]

        # 组合
        return f"""
        {system_prompt}

        【当前学生的草图视觉分析数据】
        {context_str}
        """

    @staticmethod
    def _extract_json(text: str) -> str:
        """
        稳健的 JSON 提取逻辑
        """
        try:
            # 移除 Markdown 代码块标记
            text = re.sub(r"```json\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"```", "", text).strip()

            # 正则提取 {}
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return match.group()
            return text
        except:
            return text


# --------------------------------------------------
# 独立测试入口 (模拟数据)
# --------------------------------------------------
if __name__ == "__main__":
    import os
    import yaml


    # 1. 临时加载配置
    def load_test_config():
        try:
            # 确保 config.yaml 在同级目录
            base_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(base_dir, "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"❌ 无法读取配置文件: {e}")
            return None


    # 2. 模拟 Step 1 的数据
    mock_vision_data = {
        "project_title": "减负文具盒",
        "visual_components": ["笔帽", "笔身模块", "笔尖", "连接螺纹"],
        "user_intent_analysis": "学生希望设计一款模块化的多功能笔，通过将不同颜色/类型的笔芯（如红、蓝、黑、荧光、铅笔）做成可自由组合的模块，从而用一支笔替代多支笔。其核心意图是减少学生需要携带的文具数量和重量，实现“减负”和便携。"
    }

    print("=== 🚀 开始测试 SolutionAgent (独立模式) ===")

    config = load_test_config()

    if config:
        agent = SolutionAgent(config)
        result = agent.generate(mock_vision_data)

        if result:
            print("\n✅ 生成成功！返回数据如下：")
            print(json.dumps(result, ensure_ascii=False, indent=2))

            print(f"\n🔒 [预留给 Step 3 的接口] image_prompt: \n{result.get('image_prompt')}")
    else:
        print("❌ 未找到配置文件 config.yaml")