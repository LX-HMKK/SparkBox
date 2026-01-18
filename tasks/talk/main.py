import yaml
import os
# 导入两个模块
from vision_module import VisionAgent
from mentor_test import SolutionAgent


def load_config():
    # ... (你的加载配置代码) ...
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    config = load_config()
    if not config: return

    # === Step 1: 视觉识别 ===
    vision_agent = VisionAgent(config)
    # 假设你目录下有这张图
    vision_result = vision_agent.analyze("warped_20260107_203757.jpg")

    if not vision_result:
        print("❌ 第一步失败，流程终止")
        return

    print(f"✅ 识别成功: {vision_result.get('project_title')}")

    # === Step 2: 方案生成 (核心变化) ===
    solution_agent = SolutionAgent(config)
    final_result = solution_agent.generate(vision_result)

    if final_result:
        # 1. 提取方案 (打印给用户看)
        solution_text = final_result.get("solution_content", "生成为空")

        print("\n" + "=" * 20 + " 💡 解决方案 " + "=" * 20)
        print(solution_text)
        print("=" * 50)

        # 2. 提取绘图词 (悄悄保存，不打印，留给 Step 3 用)
        image_prompt_en = final_result.get("image_prompt", "")

        print(f"\n🔒 [后台] 已生成绘图提示词 ({len(image_prompt_en)} chars)，准备传给 Step 3...")
        print(image_prompt_en) # 调试时可以打印看看

        # TODO: 这里调用你的第三个接口
        # draw_agent.draw(image_prompt_en)


if __name__ == "__main__":
    main()