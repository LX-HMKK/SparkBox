import json
import re
import os
import yaml
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
        
        # 记忆功能：存储对话历史和当前方案
        self.conversation_history = []  # 存储对话记录
        self.current_solution = None    # 存储当前生成的方案

    # --------------------------------------------------
    # 公有接口
    # --------------------------------------------------
    def generate(self, vision_data: dict, user_message: str = None) -> dict:
        """
        核心生成函数（支持对话记忆）
        Args:
            vision_data: Step 1 输出的 JSON 字典
            user_message: 可选的用户对话内容（来自录音模块）
        Returns:
            dict: 包含方案详情 + image_prompt 的 JSON
        """
        # 1. 构建 Prompt (将视觉数据和对话历史注入)
        prompt = self._build_prompt_with_context(vision_data, user_message)

        try:
            if user_message:
                print(f" [Solution] 正在根据对话优化方案 (模型: {self.model})...")
            else:
                print(f" [Solution] 正在构思方案 (模型: {self.model})...")

            # 2. 调用 API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}]
            )

            # 3. 提取内容
            raw_text = completion.choices[0].message.content
            json_str = self._extract_json(raw_text)
            result = json.loads(json_str)
            
            # 4. 更新记忆
            if user_message:
                # 记录用户的对话
                self.conversation_history.append({
                    "role": "user",
                    "content": user_message
                })
                # 记录AI的优化建议
                self.conversation_history.append({
                    "role": "assistant",
                    "content": f"已根据您的反馈进行优化。{json_str}"
                })
            
            # 5. 保存当前方案
            self.current_solution = result

            return result

        except Exception as e:
            print(f" 方案生成失败: {e}")
            return None

    # --------------------------------------------------
    # 内部工具
    # --------------------------------------------------
    def _build_prompt_with_context(self, vision_data: dict, user_message: str = None) -> str:
        """
        将 Step 1 的数据格式化，并与 System Prompt 拼接（包含对话历史）
        """
        # 将字典转为易读的字符串
        context_str = json.dumps(vision_data, ensure_ascii=False, indent=2)

        # 读取 config 中的 Prompt
        system_prompt = self.cfg["prompt"]

        # 构建基础提示
        prompt = f"""
{system_prompt}

【当前学生的草图视觉分析数据】
{context_str}
"""
        
        # 如果有当前方案，添加到上下文
        if self.current_solution:
            solution_str = json.dumps(self.current_solution, ensure_ascii=False, indent=2)
            prompt += f"""

【当前已有的解决方案】
{solution_str}
"""
        
        # 如果有对话历史，添加到上下文
        if self.conversation_history:
            history_str = "\n".join([
                f"{msg['role']}: {msg['content']}" 
                for msg in self.conversation_history
            ])
            prompt += f"""

【对话历史】
{history_str}
"""
        
        # 如果有新的用户消息，添加优化指令
        if user_message:
            prompt += f"""

【用户新的反馈或建议】
{user_message}

请基于上述对话历史和当前方案，结合用户的新反馈，提出改进和优化的解决方案。
保持原有方案的优点，针对用户反馈的问题进行针对性改进。
"""
        
        return prompt

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
    
    def clear_memory(self):
        """
        清除对话历史和当前方案（开始新的对话时使用）
        """
        self.conversation_history = []
        self.current_solution = None
        print(" [Memory] 对话记忆已清除")
    
    def get_conversation_history(self) -> list:
        """
        获取当前对话历史
        Returns:
            list: 对话历史记录
        """
        return self.conversation_history.copy()


if __name__ == "__main__":
    # 1. 临时加载配置
    def load_test_config():
        try:
            # 向上回退两层,到达 d:\StudyWorks\3.1\item1\SparkBox
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            config_path = os.path.join(base_dir, 'config', "config.yaml")
            with open(config_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f" 无法读取配置文件: {e}")
            return None


    # 2. 模拟 Step 1 的数据
    mock_vision_data = {
        "project_title": "带集水槽的雨伞收纳筒",
        "visual_components": ["雨伞","硬质塑料伞套", "集水槽"],
        "user_intent_analysis": "学生旨在解决雨天进入室内后，湿雨伞无处放置并会滴湿地面的问题。他/她设计了一个带有集水槽的硬质塑料伞套，可以将收拢的湿雨伞直接插入，收集雨伞滴落的水，从而保持地面干燥整洁。"
    }

    print("===  开始测试 SolutionAgent  ===")

    config = load_test_config()

    if config:
        agent = SolutionAgent(config)
        
        # 第一次生成：初始方案
        print("\n【第1轮】生成初始方案...")
        result = agent.generate(mock_vision_data)

        if result:
            print("\n✓ 初始方案生成成功！")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
            # 模拟第一次对话：用户反馈
            print("\n" + "="*60)
            print("【第2轮】模拟用户对话反馈...")
            user_feedback_1 = "我觉得这个设计不错，但是能不能考虑加入一个可以挂钩的功能？这样可以挂在墙上节省空间。"
            print(f"用户说: {user_feedback_1}")
            
            result2 = agent.generate(mock_vision_data, user_feedback_1)
            if result2:
                print("\n✓ 优化方案1生成成功！")
                print(json.dumps(result2, ensure_ascii=False, indent=2))
                
                # 模拟第二次对话：进一步优化
                print("\n" + "="*60)
                print("【第3轮】模拟用户进一步反馈...")
                user_feedback_2 = "挂钩的想法很好！另外，能否设计成可以容纳不同尺寸雨伞的可调节版本？"
                print(f"用户说: {user_feedback_2}")
                
                result3 = agent.generate(mock_vision_data, user_feedback_2)
                if result3:
                    print("\n✓ 优化方案2生成成功！")
                    print(json.dumps(result3, ensure_ascii=False, indent=2))
                    
                    # 显示对话历史
                    print("\n" + "="*60)
                    print("【对话历史记录】")
                    history = agent.get_conversation_history()
                    for i, msg in enumerate(history, 1):
                        print(f"{i}. {msg['role']}: {msg['content'][:100]}...")
                    
                    # 清除记忆测试
                    print("\n" + "="*60)
                    print("【测试记忆清除功能】")
                    agent.clear_memory()
                    print(f"当前对话历史条数: {len(agent.get_conversation_history())}")
    else:
        print(" 未找到配置文件 config.yaml")