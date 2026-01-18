import os
import yaml
import json
from openai import OpenAI


# ================= 工具：读取配置 =================
def load_config(config_path="config.yaml"):
    try:
        # 获取当前脚本所在目录，确保能找到同级目录下的 yaml
        base_dir = os.path.dirname(os.path.abspath(__file__))
        abs_path = os.path.join(base_dir, config_path)

        with open(abs_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 配置文件读取失败: {e}")
        return None


# ================= 核心：导师类 =================
class ProjectMentor:
    def __init__(self, config, analysis_result):
        """
        Args:
            config: 完整的配置字典 (从 yaml 读取)
            analysis_result: Step 1 的 JSON 数据
        """
        # 1. 直接从 config['mentor'] 读取所有参数
        mentor_cfg = config["mentor"]

        self.client = OpenAI(
            api_key=mentor_cfg["api_key"],
            base_url=mentor_cfg["base_url"],
            timeout=120
        )
        self.model = mentor_cfg["model_name"]

        # 2. 【关键】从 YAML 中获取 Prompt
        base_prompt = mentor_cfg["prompt"]

        # 3. 将视觉识别结果注入到 Prompt 中
        context_str = json.dumps(analysis_result, ensure_ascii=False, indent=2)

        full_system_prompt = f"""
        {base_prompt}

        【当前输入的视觉分析数据 (Context)】
        {context_str}
        """

        # 初始化对话历史
        self.history = [
            {"role": "system", "content": full_system_prompt}
        ]

    def chat(self, user_input=None):
        """
        发送对话请求
        """
        # 如果有输入，加入历史；如果是 None，说明是第一轮自动触发
        if user_input:
            self.history.append({"role": "user", "content": user_input})
        else:
            self.history.append({"role": "user", "content": "请根据分析数据，直接生成方案。"})

        try:
            print("🤖 导师正在思考...")
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.history,
                temperature=0.2  # 这里也可以从 config 读取，看你需求
            )

            reply = response.choices[0].message.content

            # 记住 AI 的回复
            self.history.append({"role": "assistant", "content": reply})

            return reply

        except Exception as e:
            return f"❌ 接口调用出错: {e}"


# ================= 本地测试入口 =================

if __name__ == "__main__":
    # 1. 读取真实的 config.yaml
    config = load_config()

    if config:
        # 2. 准备一份 Step 1 的假数据 (因为这里只测 Step 2)
        # 实际使用时，这个数据是上一个接口传过来的
        step1_result_mock = {
            "project_title": "智能避障小车",
            "visual_components": ["车轮", "超声波传感器", "底盘"],
            "user_intent_analysis": "做一个能自动躲避障碍物的小车"
        }

        print("=== ✅ 配置加载成功，开始测试导师模块 ===")

        # 3. 初始化
        mentor = ProjectMentor(config, step1_result_mock)

        # 4. 第一轮：自动生成方案
        initial_plan = mentor.chat()
        print(f"\n🎓 [初始方案]:\n{initial_plan}\n")

        # 5. 进入手动对话测试
        while True:
            user_input = input("👤 学生 (输入 q 退出): ")
            if user_input.lower() == 'q':
                break

            reply = mentor.chat(user_input)
            print(f"\n🎓 [导师回复]:\n{reply}\n")
    else:
        print("请检查目录下是否存在 config.yaml")