"""
相机实时Pose识别程序（GPU加速版）
使用YOLO11 pose模型进行实时矩形4角点检测
"""

import cv2
import numpy as np
import yaml
from pathlib import Path
from ultralytics import YOLO
import torch  # 新增：导入torch用于GPU管理


class CanvasPoseDetection:
    def __init__(self, model_path, camera_yaml_path, class_yaml_path=None, device=None, target_size_mm=140):
        """
        初始化Pose检测系统（支持GPU加速）
        
        Args:
            model_path: YOLO pose模型文件路径
            camera_yaml_path: 相机标定参数文件路径
            class_yaml_path: 类别配置文件路径（可选）
            device: 运行设备 (None=自动选择, 'cpu', 'cuda', 'cuda:0'等)
            target_size_mm: 目标正方形边长（毫米）
        """
        # 自动选择设备（优先GPU）
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device
        
        print(f"使用设备: {self.device}")
        if self.device.startswith('cuda'):
            print(f"GPU名称: {torch.cuda.get_device_name(0)}")
        
        # 加载模型（指定设备）
        print(f"正在加载Pose模型: {model_path}")
        self.model = YOLO(model_path).to(self.device)
        
        # 加载相机标定参数
        print(f"正在加载相机参数: {camera_yaml_path}")
        with open(camera_yaml_path, 'r', encoding='utf-8') as f:
            camera_params = yaml.safe_load(f)
        
        self.camera_matrix = np.array(camera_params['camera_matrix'])
        self.dist_coeffs = np.array(camera_params['dist_coeffs'])
        self.image_width = camera_params['image_width']
        self.image_height = camera_params['image_height']
        
        # 设置目标尺寸（像素）
        self.target_size_mm = target_size_mm
        # 假设每毫米对应的像素数为一个估算值，实际应用中可能需要更精确的计算
        # 这里我们先设定一个目标尺寸（像素），后续会根据相机参数进行调整
        self.target_size_px = 400  # 可以根据实际需要调整
        
        # 加载类别配置文件（如果有）
        self.class_config = None
        if class_yaml_path and Path(class_yaml_path).exists():
            with open(class_yaml_path, 'r', encoding='utf-8') as f:
                self.class_config = yaml.safe_load(f)
            print(f"已加载类别配置: {self.class_config}")
        else:
            print("未找到类别配置文件，使用默认配置")
        
        # 存储角点信息
        self.corners_list = []
        self.current_corners = []  # 存储当前检测到的角点
        
        # 可选：启用OpenCV CUDA加速（如果需要）
        self.use_cv2_cuda = False
        if self.device.startswith('cuda') and cv2.cuda.getCudaEnabledDeviceCount() > 0:
            self.use_cv2_cuda = True
            print("OpenCV CUDA加速已启用")
            # 预创建畸变矫正的映射表（GPU版）
            self.map1, self.map2 = cv2.cuda.convertMaps(
                cv2.initUndistortRectifyMap(self.camera_matrix, self.dist_coeffs, None,
                                           self.camera_matrix, (self.image_width, self.image_height),
                                           cv2.CV_16SC2),
                dstmap1type=cv2.CV_16SC2,
                dstmap2type=cv2.CV_16UC1
            )
        
        print("初始化完成！")
    
    def process_frame(self, frame, confidence_threshold=0.25, undistort=True, draw=True):
        """
        处理单帧图像（GPU加速版），进行分割识别并提取角点
        """
        # 畸变矫正（GPU加速版）
        if undistort:
            if self.use_cv2_cuda:
                # OpenCV CUDA畸变矫正
                gpu_frame = cv2.cuda_GpuMat()
                gpu_frame.upload(frame)
                frame = cv2.cuda.remap(gpu_frame, self.map1, self.map2, cv2.INTER_LINEAR).download()
            else:
                # CPU版畸变矫正（备用）
                frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
        
        # 进行推理（GPU加速，禁用自动CPU拷贝）
        results = self.model(
            frame, 
            conf=confidence_threshold, 
            verbose=False,
            device=self.device,  # 显式指定设备
            stream=False,        # 非流式推理（实时场景）
            augment=False        # 关闭数据增强提升速度
        )
        
        # 绘制结果并提取角点
        if draw:
            annotated_frame, corners_list = self.draw_results(frame, results[0])
        else:
            annotated_frame = frame
            corners_list = self.extract_corners_from_result(results[0])
        
        # 更新角点列表
        self.corners_list = corners_list
        # 更新当前角点
        if corners_list:
            self.current_corners = corners_list[0]  # 使用检测到的第一个对象的角点作为当前角点
        else:
            self.current_corners = []
        
        return annotated_frame, corners_list, results

    def get_current_corners(self):
        """
        获取当前检测到的四个角点坐标
        返回当前检测到的矩形的四个角点坐标，按顺序为：左上、右上、右下、左下
        如果没有检测到任何对象，则返回空列表
        """
        return self.current_corners

    def get_corners(self):
        """获取最新的角点列表（所有检测到的对象）"""
        return self.corners_list

    def apply_perspective_transform(self, frame, target_size=None):
        """
        对输入帧应用透视变换，将检测到的四个角点变换为正方形
        Args:
            frame: 输入图像帧
            target_size: 目标正方形尺寸（像素），默认使用初始化时的尺寸
        Returns:
            warped: 透视变换后的图像
        """
        if target_size is None:
            target_size = self.target_size_px
        
        # 获取当前角点
        corners = self.get_current_corners()
        
        if len(corners) != 4:
            print("检测到的角点数量不是4个，无法进行透视变换")
            return frame  # 如果角点数量不是4个，返回原图
        
        # 确保角点顺序为：左上、右上、右下、左下
        pts = np.float32(corners)
        
        # 定义目标正方形的四个角点
        target_square = np.float32([
            [0, 0],                    # 左上
            [target_size - 1, 0],      # 右上
            [target_size - 1, target_size - 1],  # 右下
            [0, target_size - 1]       # 左下
        ])
        
        # 计算透视变换矩阵
        matrix = cv2.getPerspectiveTransform(pts, target_square)
        
        # 应用透视变换
        warped = cv2.warpPerspective(frame, matrix, (target_size, target_size))
        
        return warped

    def extract_corners_from_result(self, result):
        """
        从YOLO Pose结果中提取角点（优化GPU->CPU数据传输）
        """
        corners_list = []
        
        if result.keypoints is not None and len(result.keypoints) > 0:
            # 批量处理关键点，减少CPU/GPU拷贝次数
            all_keypoints = result.keypoints.xy  # 直接在GPU上获取（如果可用）
            # 只拷贝一次到CPU（而非逐次拷贝）
            all_keypoints_cpu = all_keypoints.cpu().numpy() if self.device.startswith('cuda') else all_keypoints.numpy()
            
            if self.class_config and 'classes' in self.class_config:
                canvas_points = self.class_config['classes']['canvas']
                
                for kpts in all_keypoints_cpu:
                    corners = []
                    for i in range(kpts.shape[0]):
                        x_val, y_val = kpts[i][0], kpts[i][1]
                        if np.isfinite(x_val) and np.isfinite(y_val):
                            x = int(np.round(x_val))
                            y = int(np.round(y_val))
                            corners.append((x, y))
                        else:
                            corners.append((0, 0))
                    corners_list.append(corners)
            else:
                # 默认处理逻辑
                for kpts in all_keypoints_cpu:
                    corners = []
                    for i in range(kpts.shape[0]):
                        x_val, y_val = kpts[i][0], kpts[i][1]
                        if np.isfinite(x_val) and np.isfinite(y_val):
                            x = int(np.round(x_val))
                            y = int(np.round(y_val))
                            corners.append((x, y))
                        else:
                            corners.append((0, 0))
                    corners_list.append(corners)
        
        return corners_list
    
    def run(self, camera_id=1, confidence_threshold=0.25):
        """
        运行实时识别（GPU加速版）
        """
        # 打开相机
        cap = cv2.VideoCapture(camera_id)
        
        # 设置相机参数（优化实时性能）
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区，降低延迟
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))  # 加速相机读取
        
        if not cap.isOpened():
            print("错误: 无法打开相机")
            return
        
        print("相机已打开，按 'q' 退出")
        
        # 创建窗口
        cv2.namedWindow('Canvas Pose Detection', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Warped Output', cv2.WINDOW_NORMAL)
        
        # 帧率计算（更准确）
        fps_counter = 0
        fps_start_time = cv2.getTickCount()
        
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
            
            # 应用透视变换
            warped_frame = self.apply_perspective_transform(frame)
            
            # 计算并显示FPS
            fps_counter += 1
            if fps_counter >= 10:  # 每10帧更新一次FPS
                current_time = cv2.getTickCount()
                fps = fps_counter / ((current_time - fps_start_time) / cv2.getTickFrequency())
                fps_start_time = current_time
                fps_counter = 0
            else:
                fps = cap.get(cv2.CAP_PROP_FPS)
            
            cv2.putText(annotated_frame, f"FPS: {fps:.1f} (GPU: {self.device})", (10, 30), 
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
            cv2.imshow('Warped Output', warped_frame)
            
            # 按 'q' 退出
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("退出程序...")
                break
        
        # 释放资源
        cap.release()
        cv2.destroyAllWindows()
        
        # 清理GPU缓存（可选）
        if self.device.startswith('cuda'):
            torch.cuda.empty_cache()
    
    def draw_results(self, frame, result):
        """
        在帧上绘制Pose检测结果（优化GPU数据处理）
        """
        annotated = frame.copy()
        corners_list = []
        
        # 角点标签和颜色配置
        if self.class_config and 'classes' in self.class_config:
            canvas_points = self.class_config['classes']['canvas']
            corner_labels = [pt.split('_')[1].upper() for pt in canvas_points]
        else:
            corner_labels = ['TL', 'TR', 'BR', 'BL']
        
        corner_colors = [(0, 255, 0), (255, 0, 0), (0, 0, 255), (255, 255, 0)]
        
        # 处理检测结果
        if result.keypoints is not None and len(result.keypoints) > 0:
            # 批量拷贝关键点到CPU（减少拷贝次数）
            keypoints_cpu = result.keypoints.xy.cpu().numpy() if self.device.startswith('cuda') else result.keypoints.xy.numpy()
            boxes_cpu = result.boxes.data.cpu().numpy() if (result.boxes is not None and self.device.startswith('cuda')) else (result.boxes.data.numpy() if result.boxes is not None else [])
            
            # 遍历每个检测对象
            for obj_idx, kpts in enumerate(keypoints_cpu):
                # 处理边界框
                box_idx = obj_idx if obj_idx < len(boxes_cpu) else 0
                if len(boxes_cpu) > 0 and box_idx < len(boxes_cpu):
                    box = boxes_cpu[box_idx]
                    conf = box[4]
                    cls = int(box[5])
                else:
                    conf = 0.9
                    cls = 0
                
                # 提取角点坐标
                corners = []
                for i in range(kpts.shape[0]):
                    x_val, y_val = kpts[i][0], kpts[i][1]
                    if np.isfinite(x_val) and np.isfinite(y_val):
                        x = int(np.round(x_val))
                        y = int(np.round(y_val))
                        corners.append((x, y))
                    else:
                        corners.append((0, 0))
                corners_list.append(corners)
                
                # 绘制边界框
                if len(boxes_cpu) > 0 and box_idx < len(boxes_cpu):
                    x1, y1, x2, y2 = map(int, box[:4])
                    color = (0, 255, 0)
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
                    
                    # 绘制标签
                    label = f"Class {cls}: {conf:.2f}"
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(annotated, (x1, y1 - 25), (x1 + w, y1), color, -1)
                    cv2.putText(annotated, label, (x1, y1 - 5),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)
                
                # 绘制角点
                for corner_idx, corner in enumerate(corners):
                    if corner_idx < len(corner_colors):
                        cv2.circle(annotated, corner, 8, corner_colors[corner_idx], -1)
                        cv2.circle(annotated, corner, 10, (255, 255, 255), 2)
                        
                        if corner_idx < len(corner_labels):
                            cv2.putText(annotated, corner_labels[corner_idx], 
                                       (corner[0] + 15, corner[1] - 5),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, corner_colors[corner_idx], 2)
                
                # 绘制矩形边框
                if len(corners) == 4:
                    pts = np.array(corners, np.int32).reshape((-1, 1, 2))
                    cv2.polylines(annotated, [pts], True, (0, 255, 255), 2)
                
                # 打印角点信息（可选）
                if self.class_config and 'classes' in self.class_config:
                    point_names = self.class_config['classes']['canvas']
                else:
                    point_names = ["左上", "右上", "右下", "左下"]
                
                print(f"\n对象 {obj_idx+1} (Class {cls}, Conf: {conf:.2f}) 的4个角点:")
                for idx, corner in enumerate(corners):
                    point_name = point_names[idx] if idx < len(point_names) else f"角点{idx}"
                    print(f"  {point_name} ({idx}): {corner}")
        
        return annotated, corners_list

    def get_corners(self):
        """获取最新的角点列表"""
        return self.corners_list


def main():
    """主函数（GPU加速版）"""
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
    
    # 创建Pose检测系统（自动选择GPU/CPU）
    pose_system = CanvasPoseDetection(
        str(model_path), 
        str(camera_yaml_path), 
        str(class_yaml_path),
        device=None,  # None=自动选择，也可以手动指定：'cuda:0'/'cpu'
        target_size_mm=140  # 目标正方形边长为140mm
    )
    
    # 运行实时检测
    pose_system.run(camera_id=1, confidence_threshold=0.75)


if __name__ == "__main__":
    # 验证CUDA可用性
    print("="*50)
    print(f"PyTorch CUDA可用: {torch.cuda.is_available()}")
    print(f"OpenCV CUDA可用: {cv2.cuda.getCudaEnabledDeviceCount() > 0}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"CUDA版本: {torch.version.cuda}")
    print("="*50)
    
    main()