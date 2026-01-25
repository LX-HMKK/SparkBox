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
        self.history = []
        
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

    def chat(self, text: str) -> str:
        """
        与AI进行对话（不涉及图像）
        """
        if not self.current_solution:
            return "请先分析一张图片，然后再开始对话。"

        # 将用户输入添加到历史记录
        self.history.append({"role": "user", "content": text})

        try:
            print(f" [Chat] 正在与AI对话 (模型: {self.model})...")

            # 调用 API
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.history
            )

            # 提取内容
            response = completion.choices[0].message.content
            
            # 将AI响应添加到历史记录
            self.history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            print(f" 对话失败: {e}")
            return "抱歉，我暂时无法回答。"

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
