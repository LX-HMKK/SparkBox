# 创意沙盒 SparkBox
综合项目一

## 项目结构

```txt
Sparkbox_ws/
├── README.md                    
├── .gitignore                  
├── asset/                       # 资源文件目录
│   └──camera.yaml              # 相机标定数据（内参矩阵、畸变系数）
├── img/                         # 图像保存目录（按时间戳命名）
│   └── YYYYMMDD_HHMMSS_mmm.png  # 去畸变后的相机图像
├── src/                         # 主函数目录
└── tasks/                       # 任务模块目录
    ├── img_input/               # 图像采集模块
    ├── talk/                    # 模型交互模块（待开发）
    └── ui_output/               # UI输出模块（待开发）
```

## 功能说明

 - 采集图像并去畸变（tasks/img_input/take_img.py）
- 模型交互功能（待开发）
- UI输出显示（待开发）

## 环境要求

```bash
python >= 3.8
opencv-python
numpy
pyyaml
```


## 相机配置

- 设备索引：1
- 分辨率：1280×720
- 帧率：30 FPS

