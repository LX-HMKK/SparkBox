"""
CanvasPoseDetection外部调用示例
此脚本演示如何创建CanvasPoseDetection对象，输入frame并获取四个角点坐标
"""

import cv2
import numpy as np
from pathlib import Path
from model_test import CanvasPoseDetection


def main():
    # 设置路径
    workspace_root = Path(__file__).parent.parent.parent
    
    # 模型路径
    model_path = workspace_root / "asset" / "best.pt"
    if not model_path.exists():
        print(f"警告: 训练模型不存在: {model_path}")
        print("将使用YOLO11n-pose预训练模型进行演示")
        model_path = "yolo11n-pose.pt"
    
    # 配置文件路径
    camera_yaml_path = workspace_root / "asset" / "camera.yaml"
    class_yaml_path = workspace_root / "asset" / "class.yaml"
    
    # 检查相机参数文件
    if not camera_yaml_path.exists():
        print(f"错误: 相机参数文件不存在: {camera_yaml_path}")
        return
    
    # 创建Pose检测系统
    pose_system = CanvasPoseDetection(
        str(model_path), 
        str(camera_yaml_path), 
        str(class_yaml_path),
        device=None,  # None=自动选择，也可以手动指定：'cuda:0'/'cpu'
        target_size_mm=140  # 目标正方形边长为140mm
    )
    
    # 打开摄像头
    cap = cv2.VideoCapture(1)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)
    
    if not cap.isOpened():
        print("错误: 无法打开摄像头")
        return
    
    print("摄像头已打开，按 'q' 退出")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("错误: 无法读取帧")
            break
        
        # 处理当前帧，获取角点
        annotated_frame, all_corners_list, results = pose_system.process_frame(
            frame, 
            confidence_threshold=0.25, 
            undistort=True, 
            draw=True
        )
        
        # 获取当前检测到的四个角点坐标
        current_corners = pose_system.get_current_corners()
        
        # 应用透视变换，将四个角点变换为边长为140mm的正方形
        warped_frame = pose_system.apply_perspective_transform(frame)
        
        # 显示角点信息
        if current_corners:
            print(f"当前检测到的四个角点坐标: {current_corners}")
            # 可以在这里对角点进行进一步处理
            for i, corner in enumerate(current_corners):
                print(f"  角点 {i+1}: ({corner[0]}, {corner[1]})")
        else:
            print("当前帧未检测到任何对象")
        
        # 显示处理后的帧
        cv2.imshow('Canvas Pose Detection', annotated_frame)
        cv2.imshow('Warped Output (140mm square)', warped_frame)
        
        # 按 'q' 退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("退出程序...")
            break
    
    # 释放资源
    cap.release()
    cv2.destroyAllWindows()


def get_corners_and_warped_frame(pose_system, frame):
    """
    从单个帧中获取角点坐标并应用透视变换的辅助函数
    
    Args:
        pose_system: CanvasPoseDetection对象
        frame: 输入的图像帧
    
    Returns:
        current_corners: 当前检测到的四个角点坐标
        warped_frame: 透视变换后的图像
    """
    # 处理当前帧
    annotated_frame, all_corners_list, results = pose_system.process_frame(
        frame, 
        confidence_threshold=0.25, 
        undistort=True, 
        draw=False  # 不需要绘制，仅提取角点
    )
    
    # 获取当前检测到的四个角点坐标
    current_corners = pose_system.get_current_corners()
    
    # 应用透视变换
    warped_frame = pose_system.apply_perspective_transform(frame)
    
    return current_corners, warped_frame


if __name__ == "__main__":
    main()