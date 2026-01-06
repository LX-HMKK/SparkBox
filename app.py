import streamlit as st
from agent import CreativeDemoAgent
import time

# --- 1. 页面基础配置 ---
st.set_page_config(
    page_title="AI 创客向导",
    page_icon="🤖",
    layout="centered"  # 改为居中布局，更像手机/卡片应用
)

# 硬编码 API Key (隐藏了设置栏)
API_KEY = "sk-Ye8XGQ9aZDxJwpTIaKc4rUGPS2Yma5G8lTsSIwO985DUescy"

# --- 2. 初始化 Session State (状态管理) ---
# 用于记住生成的结果和当前页码
if 'result' not in st.session_state:
    st.session_state.result = None
if 'page' not in st.session_state:
    st.session_state.page = 1


# --- 3. 辅助函数：翻页逻辑 ---
def next_page():
    st.session_state.page += 1


def prev_page():
    st.session_state.page -= 1


def reset_app():
    st.session_state.result = None
    st.session_state.page = 1


# --- 4. 主逻辑 ---

# 场景 A: 还没有生成结果 -> 显示输入框
if st.session_state.result is None:
    st.title("🤖 AI 创客设计助手")
    st.markdown("### 告诉我你想做什么？")

    user_input = st.text_area(
        label="用户创意描述",  # <--- 给它一个名字
        label_visibility="collapsed",  # <--- 告诉 Streamlit 在界面上隐藏这个名字
        placeholder="例如：我想做一个能自动避开障碍物的智能小车...",
        height=150
    )

    if st.button("🚀 开始设计", type="primary", use_container_width=True):
        if not user_input:
            st.warning("请先输入你的想法")
        else:
            agent = CreativeDemoAgent(api_key=API_KEY)
            with st.spinner('AI 正在大脑风暴...绘制图纸...编写步骤...'):
                try:
                    # 获取结果并存入 session_state
                    data = agent.generate(user_input)
                    if "error" in data:
                        st.error(f"出错啦: {data['error']}")
                    else:
                        st.session_state.result = data
                        st.rerun()  # 强制刷新页面以显示结果
                except Exception as e:
                    st.error(f"发生错误: {e}")

# 场景 B: 已经有结果了 -> 显示分页内容
else:
    data = st.session_state.result
    current_page = st.session_state.page

    # 顶部进度条
    progress = (current_page / 3)
    st.progress(progress)

    # --- 第一页：封面与创意 ---
    if current_page == 1:
        st.subheader(f"📂 {data.get('project_name', '未命名项目')}")

        # 1. 显示图片 (使用 Markdown 修复版)
        img_str = data.get("preview_image", "")
        if img_str:
            if "![" in img_str and "](" in img_str:
                start = img_str.find("](") + 2
                end = img_str.find(")", start)
                img_url = img_str[start:end]
            else:
                img_url = img_str
            st.markdown(f"![preview]({img_url})")

        # 2. 核心信息
        st.info(f"💡 **核心创意**: {data.get('core_idea', '')}")

        c1, c2 = st.columns(2)
        with c1:
            st.metric("适用人群", data.get('target_user', 'N/A'))
        with c2:
            st.metric("难度等级", data.get('difficulty', '⭐⭐⭐'))

        st.markdown("---")

        # 按钮区
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.button("🔄 重新提问", on_click=reset_app)
        with col_r:
            st.button("准备材料 👉", type="primary", on_click=next_page, use_container_width=True)

    # --- 第二页：所需材料 ---
    elif current_page == 2:
        st.header("🛠️ 准备材料")
        st.markdown("在开始之前，请检查你是否拥有以下物品：")

        materials = data.get('materials', [])
        for mat in materials:
            st.markdown(f"#### ▫️ {mat}")

        st.markdown("---")

        # 按钮区
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.button("👈 返回封面", on_click=prev_page)
        with col_r:
            st.button("开始制作 👉", type="primary", on_click=next_page, use_container_width=True)

    # --- 第三页：制作步骤 ---
    elif current_page == 3:
        st.header("📝 制作步骤")

        steps = data.get('steps', [])
        for i, step in enumerate(steps, 1):
            with st.expander(f"第 {i} 步", expanded=True):
                st.write(step)

        # 学习收获
        st.success(f"🎓 **完成这个项目，你将学会：** {', '.join(data.get('learning_outcomes', []))}")

        st.markdown("---")

        # 按钮区
        col_l, col_r = st.columns([1, 1])
        with col_l:
            st.button("👈 查看材料", on_click=prev_page)
        with col_r:
            st.button("🎉 完成/新项目", type="primary", on_click=reset_app, use_container_width=True)