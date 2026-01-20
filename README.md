# 创意沙盒 SparkBox

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![OpenCV](https://img.shields.io/badge/Framework-OpenCV-orange.svg)](https://opencv.org/)
[![DashScope](https://img.shields.io/badge/AI-DashScope-brightgreen.svg)](https://help.aliyun.com/document_detail/2512468.html)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](https://opensource.org/licenses/MIT)

> 🎨 一个集成了图像处理与语音识别的 AI 交互系统原型。

</div>

## 项目简介

**创意沙盒 (SparkBox)** 是一个综合性的 AI 交互系统原型，旨在构建一个集图像采集、处理、语音识别与多模态模型交互于一体的开发平台。本项目当前实现了高质量的实时图像采集与预处理，并集成了语音转文字功能，为后续的 AI 应用提供了坚实的基础。

**目标用户**：计算机视觉开发者、AI 应用开发者、机器人系统工程师以及多模态交互研究者。

### ✨ 核心特性

- 📷 **实时图像采集**：支持从摄像头实时获取高清图像。
- 🔧 **图像预处理**：基于标定文件进行图像去畸变和仿射变换。
- 🗣️ **语音识别**：通过麦克风录音，调用阿里云 DashScope 服务将语音实时转写为文字。
- 🧩 **模块化设计**：各功能模块高度解耦，便于独立开发、测试和扩展。
- 📁 **配置驱动**：通过 YAML 文件管理相机参数、API密钥等配置，易于维护。

## 📁 项目结构

```txt
SparkBox/
├── README.md                    # 项目说明
├── .gitignore                   # Git 忽略配置
├── asset/                       # 资源文件目录
│   ├── camera.yaml              # 相机标定数据
│   ├── class.yaml               # 分类标签配置
│   └── recorder.wav             # (生成的)录音文件
├── config/                      # 配置文件目录
│   └── voice2text.yaml          # 语音识别配置
├── src/                         # 主函数目录 (待开发)
├── tasks/                       # 任务模块目录
│   ├── img_input/               # 图像采集与预处理模块
│   │   ├── ... (多个.py文件)
│   │   └── take_img.py          # 图像采集主脚本
│   ├── talk/                    # AI模型交互模块
│   │   ├── voice2text.py        # 语音识别模块
│   │   └── creative_demo.py     # (旧)创意演示
│   └── ui_output/               # UI输出模块
│       ├── ...
│       └── app.py               # Web应用入口
```

## 🛠️ 技术架构

### 技术选型

| 技术类别 | 技术栈 |
|:---|:---:|
| **后端语言** | Python 3.8+ |
| **图像处理** | opencv-python, numpy |
| **音频处理** | pyaudio |
| **AI 服务** | DashScope (阿里云) |
| **配置解析** | pyyaml |
| **Web 框架** | Flask |

## 🚀 快速开始

### 1. 环境要求

- Python >= 3.8
- Git

### 2. 环境配置

```bash
# 1. 克隆项目 (如果需要)
# git clone <your-repo-url>
# cd SparkBox

# 2. 创建并激活虚拟环境
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
# source venv/bin/activate

# 3. 安装依赖
pip install opencv-python numpy pyyaml flask dashscope pyaudio
```

> **Note:** 在 Windows 上安装 `pyaudio` 如果失败，可能需要先从 [Christoph Gohlke 的页面](https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio) 下载对应 Python 版本的 wheel 文件，然后使用 `pip install PyAudio‑0.2.11‑cp3x‑cp3x‑win_amd64.whl` 进行安装。

### 3. 服务配置

1.  **语音识别服务**
    -   前往[阿里云百炼控制台](https://help.aliyun.com/zh/model-studio/get-api-key)获取 API Key。
    -   将获取到的 Key 填入 `config/voice2text.yaml` 文件中的 `dashscope_api_key` 字段。

    ```yaml
    # config/voice2text.yaml
    dashscope_api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxx"
    # ... 其他配置
    ```

2.  **相机配置**
    -   确保相机设备已正确连接。
    -   根据需要修改 `asset/camera.yaml` 中的标定参数。默认使用索引为 `1` 的摄像头。

## 📖 运行与使用

### 语音识别模块

运行脚本后，会弹出一个控制窗口，请确保窗口处于激活状态。

```bash
python tasks/talk/voice2text.py
```

**交互指令:**
- **按 `r` 键**: 开始录音。
- **按 `s` 键**: 停止录音并开始转写。
- **按 `q` 键**: 退出程序。

录音文件会自动保存到 `asset/recorder.wav`，转写结果会打印在控制台。

### 图像采集模块

```bash
python tasks/img_input/take_img.py
```
此脚本会使用 `asset/camera.yaml` 中的配置来采集并处理图像。

---

## � Git 提交规范

为了保持项目提交历史清晰一致，请遵循以下规范：

### 提交消息格式

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 类型说明

| 类型 | 描述 |
|:---|:---|
| **feat** | 新功能（feature） |
| **fix** | 修复 Bug |
| **docs** | 文档更新 |
| **style** | 代码格式调整（不影响代码逻辑） |
| **refactor** | 代码重构（既不是新增功能，也不是修复 Bug） |
| **test** | 添加或修改测试 |
| **chore** | 构建过程或辅助工具的变动 |
| **perf** | 性能优化 |
| **ci** | 持续集成相关变动 |
| **build** | 影响构建系统或外部依赖的变动 |
| **revert** | 回滚到之前的提交 |

### 示例

```
feat(camera): 添加相机标定功能

- 实现了基于棋盘格的相机标定
- 支持自动保存标定参数到 YAML 文件
- 添加了标定结果的可视化展示

Closes #123
```

---

## �📋 开发计划

- [x] **模型交互模块**：集成语音识别 (DashScope)。
- [ ] **主程序集成**：在 `src/` 目录下开发主流程，整合图像和语音模块，实现协同工作。
- [ ] **多模态能力**：结合图像和语音输入，实现更复杂的 AI 交互，例如“看到什么说什么”。
- [ ] **增强UI功能**：使用 Flask 或其他框架提供更丰富的 Web 可视化和交互界面。
- [ ] **性能优化**：对图像和音频处理流程进行性能分析与优化，提升实时响应速度。

<div align="center">

Made with ❤️ by SparkBox Team

</div>
