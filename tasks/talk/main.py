import yaml
import os
import json
from vision_module import VisionAgent
from mentor_module import SolutionAgent
from image_module import ImageGenAgent


def load_config():
    """加载配置文件"""
    try:
        # 向上回退两层,到达 d:\StudyWorks\3.1\item1\SparkBox
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        config_path = os.path.join(base_dir, 'config', "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f" 配置加载失败: {e}")
        return None


def main():
    """完整流程：图像识别 -> 方案生成 -> 预览图生成"""

    print(" SparkBox 创客作品助手 - 完整流程")
    print("\n")
    
    # 加载配置
    config = load_config()
    if not config:
        return

    # === Step 1: 视觉识别 ===
    print(" Step 1: 视觉识别")
    print("-" * 60)
    
    vision_agent = VisionAgent(config)
    # 假设你目录下有这张图
    image_file = "perspective_20260118_142415_965.jpg"
    
    if not os.path.exists(image_file):
        print(f" 图片文件不存在: {image_file}")
        print(" 提示: 请将图片放在 tasks/talk/ 目录下")
        return
    
    vision_result = vision_agent.analyze(image_file)

    if not vision_result:
        print(" 视觉识别失败，流程终止")
        return

    print(f" 识别成功: {vision_result.get('project_title')}\n")

    # === Step 2: 方案生成 ===
    print(" Step 2: 方案生成")
    print("-" * 60)
    
    solution_agent = SolutionAgent(config)
    solution_result = solution_agent.generate(vision_result)

    if not solution_result:
        print(" 方案生成失败，流程终止")
        return

    # debug打印方案信息
    print(f" 方案生成成功: {solution_result.get('project_name', '未命名')}")
    print(f" 核心创意: {solution_result.get('core_idea', 'N/A')}\n")

    # === Step 3: 预览图生成 ===
    print(" Step 3: 预览图生成")
    print("-" * 60)
    
    image_agent = ImageGenAgent(config)
    image_prompt = solution_result.get("image_prompt", "")
    
    if not image_prompt:
        print("️ 未找到绘图提示词，跳过预览图生成")
    else:
        image_url = image_agent.generate_image(image_prompt)
        
        if image_url:
            print(f" 预览图生成成功！\n")
            print(f" 预览图地址:\n{image_url}\n")
        else:
            print(" 预览图生成失败")

    # === 最终结果输出 ===
    print("\n" + "=" * 60)
    print(" 完整结果")
    print("=" * 60 + "\n")
    
    # 组装完整数据
    complete_result = {
        "vision_analysis": vision_result,
        "solution": solution_result,
        "preview_image_url": image_url if 'image_url' in locals() and image_url else None
    }
    
    # 打印 JSON 格式结果
    print(json.dumps(complete_result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()