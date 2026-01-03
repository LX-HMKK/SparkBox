"""
相机实时Pose识别程序
使用YOLO11 pose模型进行实时矩形4角点检测
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from ultralytics import YOLO


class CanvasPoseDetection:
    def __init__(self, model_path, camera_yaml_path):
        """
        初始化Pose检测系统
        
        Args:
            model_path: YOLO pose模型文件路径
            camera_yaml_path: 相机标定参数文件路径
        """
        # 加载模型
        print(f"正在加载Pose模型: {model_path}")
        self.model = YOLO(model_path)
        
        # 加载相机标定参数
        print(f"正在加载相机参数: {camera_yaml_path}")
        with open(camera_yaml_path, 'r', encoding='utf-8') as f:
            camera_params = yaml.safe_load(f)
        
        self.camera_matrix = np.array(camera_params['camera_matrix'])
        self.dist_coeffs = np.array(camera_params['dist_coeffs'])
        self.image_width = camera_params['image_width']
        self.image_height = camera_params['image_height']
        
        # 存储角点信息
        self.corners_list = []
        
        print("初始化完成！")
    
    def process_frame(self, frame, confidence_threshold=0.25, undistort=True, draw=True):
        """
        处理单帧图像，进行分割识别并提取角点
        
        Args:
            frame: 输入的图像帧
            confidence_threshold: 置信度阈值
            undistort: 是否进行畸变矫正
            draw: 是否绘制可视化结果
        
        Returns:
            annotated_frame: 绘制了结果的帧（如果draw=True）
            corners_list: 角点列表，每个元素是一个对象的4个角点
            results: YOLO原始检测结果
        """
        # 畸变矫正（可选）
        if undistort:
            frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
        
        # 进行推理
        results = self.model(frame, conf=confidence_threshold, verbose=False)
        
        # 绘制结果并提取角点
        if draw:
            annotated_frame, corners_list = self.draw_results(frame, results[0])
        else:
            annotated_frame = frame
            corners_list = self.extract_corners_from_result(results[0])
        
        # 更新角点列表
        self.corners_list = corners_list
        
        return annotated_frame, corners_list, results
    
    def extract_corners_from_result(self, result):
        """
        从YOLO Pose结果中提取所有对象的4个角点
        
        Args:
            result: YOLO检测结果
        
        Returns:
            corners_list: 角点列表，每个元素是一个对象的4个角点坐标
        """
        corners_list = []
        
        if result.keypoints is not None and len(result.keypoints.xy) > 0:
            keypoints_array = result.keypoints.xy  # 形状: (num_objects, num_keypoints, 2)
            
            for keypoints in keypoints_array:
                # keypoints是4个点的坐标 [(x1,y1), (x2,y2), (x3,y3), (x4,y4)]
                corners = [(int(pt[0]), int(pt[1])) for pt in keypoints]
                corners_list.append(corners)
        
        return corners_list
    
    def run(self, camera_id=1, confidence_threshold=0.25):
        """
        运行实时识别（集成相机调用的便捷方法）
        
        Args:
            camera_id: 相机ID，默认为1
            confidence_threshold: 置信度阈值
        """
        # 打开相机
        cap = cv2.VideoCapture(camera_id)
        
        # 设置相机分辨率
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)
        
        if not cap.isOpened():
            print("错误: 无法打开相机")
            return
        
        print("相机已打开，按 'q' 退出")
        
        # 创建窗口
        cv2.namedWindow('Canvas Pose Detection', cv2.WINDOW_NORMAL)
        
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                print("错误: 无法读取帧")
                break
            
            # 处理帧
            annotated_frame, corners_list, results = self.process_frame(
                frame, confidence_threshold=confidence_threshold
            )
            
            # 显示FPS
            fps_text = f"FPS: {cap.get(cv2.CAP_PROP_FPS):.1f}"
            cv2.putText(annotated_frame, fps_text, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示检测数量
            num_detections = len(results[0].boxes) if results[0].boxes is not None else 0
            det_text = f"Detections: {num_detections}"
            cv2.putText(annotated_frame, det_text, (10, 70), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示角点数量
            total_corners = sum(len(corners) for corners in corners_list)
            corner_text = f"Corners: {total_corners}"
            cv2.putText(annotated_frame, corner_text, (10, 110), 
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            
            # 显示画面
            cv2.imshow('Canvas Pose Detection', annotated_frame)
            
            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("退出程序...")
                break
        
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
    
    def draw_results(self, frame, result):
        """
        在帧上绘制Pose检测结果（4个角点）
        
        Args:
            frame: 原始帧
            result: YOLO检测结果
        
        Returns:
            绘制了结果的帧，角点列表
        """
        annotated = frame.copy()
        corners_list = []
        
        # 定义4个角点的颜色和标签
        corner_colors = [
            (0, 255, 0),    # 角点0: 绿色
            (255, 0, 0),    # 角点1: 蓝色
            (0, 0, 255),    # 角点2: 红色
            (255, 255, 0)   # 角点3: 青色
        ]
        corner_labels = ['TL', 'TR', 'BR', 'BL']  # 左上、右上、右下、左下
        
        # 如果有检测结果
        if result.keypoints is not None and len(result.keypoints.xy) > 0:
            keypoints_array = result.keypoints.xy  # 形状: (num_objects, 4, 2)
            boxes = result.boxes.data.cpu().numpy()
            
            # 为每个检测对象绘制关键点
            for obj_idx, (keypoints, box) in enumerate(zip(keypoints_array, boxes)):
                # 获取置信度和类别
                conf = box[4]
                cls = int(box[5])
                
                # 转换为numpy数组以便处理
                kpts = keypoints.cpu().numpy() if hasattr(keypoints, 'cpu') else keypoints
                
                # 转换关键点为整数坐标
                corners = [(int(pt[0]), int(pt[1])) for pt in kpts]
                corners_list.append(corners)
                
                # 绘制边界框
                x1, y1, x2, y2 = map(int, box[:4])
                color = (0, 255, 0)
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                
                # 绘制标签
                label = f"Class {cls}: {conf:.2f}"
                (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                cv2.rectangle(annotated, (x1, y1 - 25), (x1 + w, y1), color, -1)
                cv2.putText(annotated, label, (x1, y1 - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # 绘制4个角点
                for corner_idx, corner in enumerate(corners):
                    # 绘制圆点
                    cv2.circle(annotated, corner, 8, corner_colors[corner_idx], -1)
                    cv2.circle(annotated, corner, 10, (255, 255, 255), 2)
                    
                    # 绘制角点标签
                    cv2.putText(annotated, corner_labels[corner_idx], 
                               (corner[0] + 15, corner[1] - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, corner_colors[corner_idx], 2)
                
                # 绘制矩形边框（连接4个角点）
                if len(corners) == 4:
                    pts = np.array(corners, np.int32)
                    pts = pts.reshape((-1, 1, 2))
                    cv2.polylines(annotated, [pts], True, (0, 255, 255), 2)
                
                # 打印角点坐标
                corner_names = ["左上", "右上", "右下", "左下"]
                print(f"\n对象 {obj_idx+1} (Class {cls}, Conf: {conf:.2f}) 的4个角点:")
                for idx, corner in enumerate(corners):
                    corner_name = corner_names[idx] if idx < 4 else f"角点{idx}"
                    print(f"  {corner_name} ({idx}): {corner}")
        
        return annotated, corners_list
    
    def get_corners(self):
        """
        获取最新的角点列表
        
        Returns:
            角点列表，每个元素是一个对象的角点坐标列表
        """
        return self.corners_list


def main():
    """主函数"""
    # 设置路径
    workspace_root = Path(__file__).parent.parent.parent
    
    # 使用pose模型（改为运行输出的最佳模型）
    model_path = workspace_root / "runs" / "pose" / "canvas_corners" / "weights" / "best.pt"
    
    # 如果没有trained model，使用预训练模型
    if not model_path.exists():
        print(f"警告: 训练模型不存在: {model_path}")
        print("将使用YOLO11n-pose预训练模型进行演示")
        model_path = "yolo11n-pose.pt"
    
    camera_yaml_path = workspace_root / "asset" / "camera.yaml"
    
    # 检查相机参数文件是否存在
    if not camera_yaml_path.exists():
        print(f"错误: 相机参数文件不存在: {camera_yaml_path}")
        return
    
    # 创建Pose检测系统
    pose_system = CanvasPoseDetection(str(model_path), str(camera_yaml_path))
    
    # 运行实时检测
    pose_system.run(camera_id=1, confidence_threshold=0.25)


if __name__ == "__main__":
    main()
