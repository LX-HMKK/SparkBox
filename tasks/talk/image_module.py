import urllib.parse
import random


class ImageGenAgent:
    """
    预览图生成助手 (RealVisXL 照片特调版)
    功能：使用专攻真实感的模型，配合负向约束，强制输出照片。
    """

    def __init__(self, config):
        self.cfg = config["image_generator"]
        # 读取配置里的模型名称，默认用 realvisxl
        self.model_name = self.cfg.get("model_name", "realvisxl")

    def generate_image(self, prompt: str) -> str:
        """
        核心绘图函数
        Args:
            prompt: 英文绘图提示词
        Returns:
            str: 生成的图片 URL
        """
        if not prompt:
            print(" [ImageGen] 未收到提示词")
            return None

        print(f" [ImageGen] 正在生成照片级预览图 (模型: {self.model_name})...")

        try:
            # --- 提示词工程 (Prompt Engineering) ---

            # 1. 【正向增强】强调摄影感、瑕疵和环境
            # 使用 "documentary photograph"(纪实摄影) 比单纯 "photograph" 更真实
            # "tangible textures"(可触摸的纹理), "messy wiring"(杂乱的线) 增加手工感
            # "natural workshop lighting"(自然车间光) 避免完美的棚拍光
            photorealistic_suffix = (
                ", documentary photograph shot on dslr, macro lens close-up, "
                "tangible textures, rough materials, messy wiring, "
                "natural workshop lighting, film grain, sharp focus"
            )

            # 2. 【负向约束】明确禁止卡通和渲染风格
            # Pollinations 常常把 prompt 后半部分作为负向参考
            negative_constraints = (
                ", NOT cartoon, NOT 3d render, NOT cgi, NOT anime, "
                "NOT blender, no smooth plastic, no perfect shapes"
            )

            # 3. 组合提示词
            # 原始描述 + 摄影风格 + 负向约束
            full_prompt = f"{prompt}{photorealistic_suffix}{negative_constraints}"

            # --- URL 构建 ---

            # 4. URL 编码
            encoded_prompt = urllib.parse.quote(full_prompt)

            # 5. 随机种子和尺寸
            seed = random.randint(0, 1000000)
            width = self.cfg.get("width", 1280)
            height = self.cfg.get("height", 960)

            # 6. 拼接 URL
            # enhance=false: 必须关闭，防止它自作聪明加回 artistic 风格
            image_url = (
                f"https://image.pollinations.ai/prompt/{encoded_prompt}"
                f"?model={self.model_name}&width={width}&height={height}&seed={seed}&nologo=true&enhance=false"
            )

            return image_url

        except Exception as e:
            print(f" URL 生成失败: {e}")
            return None
