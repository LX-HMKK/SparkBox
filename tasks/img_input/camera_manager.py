"""
摄像头管理器 - 负责摄像头处理、图像采集和快照功能
"""
import cv2
import time
import threading
from datetime import datetime
from pathlib import Path


class CameraManager:
    def __init__(self, camera_id=0, width=1280, height=720):
        """
        初始化摄像头管理器
        
        Args:
            camera_id: 摄像头ID
            width: 摄像头宽度
            height: 摄像头高度
        """
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.cap = None
        self.running = False
        
        # Frame state
        self.latest_frame = None
        self.latest_raw_frame = None
        self.frame_lock = threading.Lock()
        
        # Status overlay settings
        self.status_message = "Ready"
        self.is_processing = False
        self.is_recording = False
    
    def initialize_camera(self):
        """初始化摄像头"""
        self.cap = cv2.VideoCapture(self.camera_id)
        
        # Set camera parameters
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        
        if not self.cap.isOpened():
            raise RuntimeError("Could not open camera")
        
        print(f"Camera initialized: {self.width}x{self.height}")
    
    def get_frame(self):
        """获取当前帧"""
        if not self.cap or not self.cap.isOpened():
            return None, None
        
        ret, frame = self.cap.read()
        if not ret:
            return None, None
        
        # Store raw frame
        with self.frame_lock:
            self.latest_raw_frame = frame
        
        return ret, frame
    
    def get_latest_raw_frame(self):
        """获取最新的原始帧"""
        with self.frame_lock:
            return self.latest_raw_frame
    
    def update_processed_frame(self, processed_frame):
        """更新处理后的帧"""
        with self.frame_lock:
            self.latest_frame = processed_frame
    
    def get_latest_processed_frame(self):
        """获取最新的处理后帧"""
        with self.frame_lock:
            return self.latest_frame
    
    def add_status_overlay(self, frame):
        """添加状态叠加层"""
        # Status overlay
        status_color = (0, 255, 0) if not self.is_processing else (0, 165, 255)
        cv2.putText(frame, f"Status: {self.status_message}", (20, 40), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, status_color, 2)
        
        # Recording indicator
        if self.is_recording:
            cv2.circle(frame, (50, 80), 15, (0, 0, 255), -1)
            cv2.putText(frame, "REC", (80, 90), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
        
        return frame
    
    def update_status(self, message, is_processing=None, is_recording=None):
        """更新状态信息"""
        self.status_message = message
        if is_processing is not None:
            self.is_processing = is_processing
        if is_recording is not None:
            self.is_recording = is_recording
    
    def save_snapshot(self, frame, detector, logs_dir, temp_dir):
        """
        保存快照
        
        Args:
            frame: 要保存的帧
            detector: 检测器实例
            logs_dir: 日志目录路径
            temp_dir: 临时目录路径
        
        Returns:
            tuple: (log_path, temp_path) 保存的文件路径
        """
        # Apply perspective transform
        warped_frame = detector.apply_perspective_transform(frame)
        
        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"capture_{timestamp}.jpg"
        
               
        # Create capture subdirectory
        capture_dir = logs_dir / "capture"
        capture_dir.mkdir(parents=True, exist_ok=True)
        
        # Save to logs (permanent)
        log_path = capture_dir / filename
        cv2.imwrite(str(log_path), warped_frame)
        print(f"Saved to logs: {log_path}")
        
        # Save to temp (for processing)
        temp_path = temp_dir / filename
        cv2.imwrite(str(temp_path), warped_frame)
        
        return log_path, temp_path
    
    def cleanup(self):
        """清理资源"""
        if self.cap:
            self.cap.release()
        print("Camera resources cleaned up")