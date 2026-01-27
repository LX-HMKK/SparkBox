<div align="center">

# ✨ SparkBox
### AI驱动的创意工程助手

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
<!-- ![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg) -->
![Windows Build](https://img.shields.io/badge/Windows_x64-passing-brightgreen?logo=windows)
![Ubuntu Build](https://img.shields.io/badge/Ubuntu_Arm64-passing-brightgreen?logo=ubuntu)

<br/>

**SparkBox** 是一个基于分布式管理器架构的智能硬件项目<br/>
它能将学生天马行空的 **手绘草图** 转化为结构完整的 **工程解决方案**<br/>
并通过多模态AI交互系统提供实时指导，点燃从创意到现实的火花。

[功能特性](#-核心功能) • [系统架构](#-系统架构) • [快速开始](#-快速开始) • [开发计划](#-开发路线图)

</div>

---

## 🚀 项目概述

SparkBox 专为中小学生设计，是一个集成了 **计算机视觉**、**自然语言处理** 和 **生成式AI** 技术的创客教育平台。旨在消除创意与实现之间的技术鸿沟，将孩子们的创意草图无缝转化为可动手实践的工程项目。

### 🌟 核心功能

| 功能 | 描述 |
| :--- | :--- |
| 🎨 **智能草图识别** | 自动识别手绘草图、符号和潦草文字，理解创意原点。 |
| 🛠️ **工程方案生成** | 基于识别内容，生成包含材料、步骤和原理的完整制作方案。 |
| 🖼️ **真实感可视化** | 集成 NanoBanana 生成式AI (RealVisXL)，生成照片级逼真的作品预览图。 |
| 🗣️ **上下文对话** | 支持多轮对话记忆，可针对当前生成的方案进行深入探讨和优化。 |
| 💻 **双平台支持** | 提供 Windows 调试版和 ARM64 部署版，兼顾开发便利与实际应用。 |
| 📱 **移动端配套** | 配套移动App，提供历史记录回顾和方案下载。 |
---

## 🏗️ 系统架构

### 分布式管理器框架

SparkBox 采用高度模块化的设计，其核心功能被分解为一系列独立的管理器，协同工作，确保系统稳定高效。

```mermaid
graph TD
    subgraph A[应用入口层]
        A1["main_win.py<br>(Windows调试)"]
        A2["main_arm.py<br>(ARM64部署)"]
    end

    subgraph B[分布式管理器框架]
        B1["CameraManager<br>(摄像头管理)"]
        B2["AIManager<br>(AI协调)"]
        B3["WebManager<br>(Web界面)"]
        B4["GPIO Manager<br>(硬件交互)"]
        B5["Voice Handler<br>(语音处理)"]
        B6["Detection Module<br>(图像检测)"]
    end

    subgraph C[AI能力层]
        C1["Vision Agent<br>(Gemini视觉)"]
        C2["Solution Agent<br>(Gemini推理)"]
        C3["Image Gen Agent<br>(NanoBanana生成)"]
        C4["Voice2Text<br>(DashScope ASR)"]
    end

    A --> B --> C
```

### 🧩 管理器职责

| 管理器 | 主要职责 |
| :--- | :--- |
| **CameraManager** | 摄像头初始化、图像采集、帧处理与优化。 |
| **AIManager** | 协调AI工作流、管理状态、整合多模态结果。 |
| **WebManager** | 运行Flask服务器、通过SSE推送实时事件、管理浏览器界面。 |
| **GPIO Manager** | (ARM64专用) 处理硬件按键输入、控制LED状态指示灯。 |

---

## 🧠 AI技术栈

### 多模型协作架构

SparkBox 采用“分工协作”的AI模型组合，每个模型专注于其最擅长的领域，共同完成从理解到创造的全过程。

```mermaid
graph LR
    A["用户输入<br>(语音/图像)"] --> B{多模型协调处理};
    B --> C[综合输出];

    subgraph D[AI模型矩阵]
        D1["Gemini (主脑)<br>• 视觉分析<br>• 逻辑推理<br>• 方案生成"]
        D2["DashScope (ASR)<br>• 语音转文字<br>• 实时识别"]
        D3["NanoBanana (图像)<br>• 预览图生成<br>• 高质量渲染"]
    end
```

| AI任务 | 模型 | 核心职责 |
| :--- | :--- | :--- |
| **视觉分析** | Gemini 2.5 Pro | 图像理解、手写文字识别。 |
| **方案生成** | Gemini 3 Pro | STEM教育方案、安全制作流程。 |
| **语音转文字** | DashScope ASR | 实时语音识别，支持多种语言。 |
| **图像生成** | NanoBanana RealVisXL | 生成照片级真实感的作品预览图。 |

---

## ⚙️ 平台特性

<details>
<summary><strong>💻 Windows调试版本 (main_win.py)</strong></summary>

- **⌨️ 键盘控制**: 使用 `空格键` 触发识别，`ESC` 键退出程序。
- **🐛 调试友好**: 提供完整的错误日志和调试信息，方便快速定位问题。
- **🔥 开发模式**: 支持代码热重载和集成开发环境（IDE）的调试工具。
</details>

<details>
<summary><strong>🤖 ARM64部署版本 (main_arm.py)</strong></summary>

- **🕹️ GPIO硬件控制**: 通过物理按键进行输入，使用LED灯指示系统状态。
- **🔒 Chromium Kiosk模式**: 强制全屏显示，禁用退出选项，提供沉浸式体验。
- **🚀 优化性能**: 针对ARM架构进行深度性能调优，确保流畅运行。
- **🔄 自动启动**: 支持设置为系统服务，实现开机自运行。

#### ARM64 Kiosk模式技术实现
```python
# Chromium Kiosk模式配置
subprocess.Popen([
    "chromium-browser", 
    "--kiosk",              # 强制全屏模式
    "--noerrdialogs",       # 禁用错误对话框
    "--disable-infobars",   # 隐藏信息栏
    "--app=http://localhost:5000"  # 指定应用URL
], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
```
</details>

<details>
<summary><strong>📱 移动端配套服务 (server.py)</strong></summary>

- **📡 本地记忆转发**: 运行轻量级FastAPI服务，将本地生成的AI日志和方案文件转发至局域网。
- **📱 手机App对接**: 专为Flutter开发的手机配套App设计，支持从移动端回顾历史创意和方案。
- **📂 静态资源挂载**: 自动挂载日志目录，允许外部设备直接访问生成的JSON数据和图片资源。

#### 核心接口说明
- `GET /api/list_files`: 获取所有历史对话/方案列表（按时间倒序）。
- `GET /logs/{filename}`: 访问具体的方案内容或生成的图片。
</details>

---

## 🛠️ 安装配置

<details>
<summary><strong>📋 点击展开安装指南</strong></summary>

### 系统要求
- Python 3.8+
- OpenCV 4.5+
- Flask 2.0+
- 一个可用的摄像头设备

### 依赖安装
```bash
# 核心依赖
pip install opencv-python flask pyyaml openai pillow dashscope pyaudio numpy

# 可选依赖（硬件支持）
pip install Hobot.GPIO  # ARM64 GPIO支持

# 开发依赖
pip install pytest black flake8  # 代码质量工具
```

### 完整安装命令
```bash
pip install opencv-python flask pyyaml openai pillow dashscope pyaudio numpy \
            opencv-contrib-python flask-cors requests urllib3

# ARM64平台额外安装
pip install Hobot.GPIO
```

### 配置文件
项目使用YAML文件进行参数管理，清晰易懂：
- `config/config.yaml`: 主配置文件（AI模型密钥、视觉参数等）。
- `config/voice2text.yaml`: 语音识别相关配置。
- `config/io.yaml`: GPIO硬件配置（ARM64平台）。
</details>

---

## 📂 项目结构

<details>
<summary><strong>📁 点击查看目录树</strong></summary>

```text
SparkBox/
├── asset/              # 资源文件 (图片、模型、配置示例)
├── config/             # 配置文件 (YAML)
├── src/                # 应用程序入口
│   ├── main_arm.py     # ARM/Linux 部署入口 (Kiosk模式)
│   ├── main_win.py     # Windows 调试入口
│   └── server.py       # 移动端配套服务 (FastAPI)
├── tasks/              # 核心业务逻辑模块
│   ├── img_input/      # 图像输入与处理
│   │   ├── camera_manager.py # 摄像头管理
│   │   └── detect.py         # 目标检测
│   ├── talk/           # AI 交互核心
│   │   ├── ai_manager.py     # AI 流程总管
│   │   ├── vision_module.py  # 视觉分析
│   │   ├── mentor_module.py  # 方案生成
│   │   ├── image_module.py   # 图像生成
│   │   └── voice2text.py     # 语音识别
│   └── ui_output/      # Web 前端界面
│       ├── web_manager.py    # Web 服务管理
│       ├── templates/        # HTML 模板
│       └── static/           # 静态资源 (JS/CSS)
├── tools/              # 实用工具脚本
└── README.md           # 项目文档
```

</details>

---

## 🚀 快速开始

<details>
<summary><strong>▶️ 点击展开启动说明</strong></summary>

### Windows调试模式
```bash
cd d:\StudyWorks\3.1\item1\SparkBox
python src/main_win.py
```

### ARM64部署模式
```bash
cd /opt/sparkbox
python src/main_arm.py
```

### 访问Web界面
启动后，系统将自动打开浏览器并访问：`http://localhost:5000`
</details>

---

## 📝 使用流程

1.  **准备阶段**: 打开摄像头，确保光线充足，调整好拍摄角度。
2.  **草图绘制**: 在白纸上清晰地绘制你的创意草图和文字说明。
3.  **触发识别**: 按下 `空格键` (Windows) 或 `GPIO按键` (ARM64) 启动AI分析。
4.  **AI分析**: 系统自动进行视觉识别、方案生成和图像渲染。
5.  **结果展示**: 在Web界面查看详细的分析结果和精美的作品预览图。
6.  **交互优化**: 通过语音与AI对话，进行追问、调整或获取更多灵感。

---

## ✨ 技术亮点

<details>
<summary><strong>👁️ 视觉识别优化</strong></summary>

- **潦草文字识别**: 针对学生手写体进行深度优化，识别率更高。
- **图形符号理解**: 能够准确识别抽象图形、流程图和电路符号。
- **上下文推理**: 结合文字和图形进行智能分析，理解更深层意图。
</details>

<details>
<summary><strong>🎓 工程教育适配</strong></summary>

- **年龄段适配**: 根据中小学生的认知水平，动态调整输出内容的深度和广度。
- **STEM知识整合**: 在方案中巧妙融入科学、技术、工程和数学知识点。
- **安全第一**: 在材料和工具的选择上，优先考虑学生操作的安全性。
</details>

<details>
<summary><strong>⚡ 实时性能优化</strong></summary>

- **异步处理**: 采用多线程处理耗时任务，避免界面卡顿。
- **流式传输 (SSE)**: 实时向前端推送处理状态和结果，提供即时反馈。
- **智能缓存**: 对重复计算进行缓存，减少不必要的AI调用，提升响应速度。
</details>

---

## 🗺️ 开发路线图

<details>
<summary><strong>✅ 已实现功能</strong></summary>

- [x] **代码架构统一**: 完成 `main_win.py` 和 `main_arm.py` 的架构重构，统一使用管理器模式。
- [x] **Web交互界面**: 基于Flask和SSE实现的实时交互Web UI，支持状态推送和视频流。
- [x] **移动端数据服务**: 实现 `server.py` 本地记忆转发服务，支持Flutter App接入访问。
- [x] **视觉/语音/生成全链路**: 打通从摄像头输入、语音交互到AI方案生成的完整闭环。
</details>

<details>
<summary><strong>📅 近期优化目标</strong></summary>

- [ ] **UI模式自适应**: 根据运行平台自动调整界面布局和交互方式。
- [ ] **GPIO响应优化**: 降低按键复位延迟，提升硬件交互的灵敏度和体验。
</details>

<details>
<summary><strong>📷 硬件升级计划</strong></summary>

- [ ] **高分辨率相机**: 适配更高像素的专业摄像头，提升输入精度。
- [ ] **工业级CMOS传感器**: 采用工业级CMOS相机，增强在复杂光照下的图像质量。
- [ ] **多点触控支持**: 为系统增加触摸屏交互界面，提供更多操作可能。
</details>

<details>
<summary><strong>🔮 未来功能扩展</strong></summary>

- [ ] **多语言支持**: 扩展支持更多语言的语音识别和自然语言处理。
- [ ] **云端同步**: 实现项目数据的云端存储和跨设备同步。
- [ ] **协作功能**: 支持多用户在线协作，共同完成一个创意项目。
</details>

---

### Git提交规范

我们遵循 [Angular提交约定](https://github.com/angular/angular/blob/main/CONTRIBUTING.md#commit)，这有助于保持提交历史的清晰和可读性。

`type` 必须是以下之一:
- **feat**: 新功能
- **fix**: Bug修复
- **docs**: 文档变更
- **style**: 代码风格（不影响代码含义的更改）
- **refactor**: 重构（既不修复错误也不添加功能）
- **perf**: 性能优化
- **test**: 添加或修改测试
- **chore**: 构建过程或辅助工具的变动

---

## 📞 技术支持

如有任何技术问题或建议，请通过以下方式联系我们：

- **提交GitHub Issue**: 这是最推荐的方式，便于跟踪和管理。
- **提供详细报告**: 请附上详细的技术报告、错误信息和复现步骤。

---

<div align="center">
<b>SparkBox</b> - 让每个创意都闪闪发光 ✨
</div>
