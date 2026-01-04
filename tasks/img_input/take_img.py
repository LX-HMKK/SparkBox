import cv2
import numpy as np
import os
import yaml
from datetime import datetime

# 设置图片保存路径（根目录下的img文件夹）
img_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'img')
os.makedirs(img_dir, exist_ok=True)

# 读取标定数据
asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'asset')
calibration_file = os.path.join(asset_dir, 'camera.yaml')

camera_matrix = None
dist_coeffs = None

if os.path.exists(calibration_file):
    with open(calibration_file, 'r', encoding='utf-8') as f:
        calib_data = yaml.safe_load(f)
        camera_matrix = np.array(calib_data['camera_matrix'], dtype=np.float32)
        dist_coeffs = np.array(calib_data['dist_coeffs'], dtype=np.float32)
    print(f"Loaded calibration data from {calibration_file}")
else:
    print(f"Warning: Calibration file not found at {calibration_file}")
    print("Images will be saved without distortion correction")

cap = cv2.VideoCapture(1)

# 设置相机基本参数
cap.set(3, 1280)  # Width
cap.set(4, 720)  # Height 
cap.set(cv2.CAP_PROP_FPS, 30)  # FPS

# 设置更多相机参数
cap.set(cv2.CAP_PROP_BRIGHTNESS, 50)   # 亮度 0-100
cap.set(cv2.CAP_PROP_CONTRAST, 32)     # 对比度 0-100
cap.set(cv2.CAP_PROP_SATURATION, 64)   # 饱和度 0-100
cap.set(cv2.CAP_PROP_HUE, 50)          # 色调 0-100
cap.set(cv2.CAP_PROP_GAIN, 35)         # 增益 0-100
cap.set(cv2.CAP_PROP_EXPOSURE, -5)     # 曝光值 -11(最暗) 到 1(最亮)
cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # 关闭自动曝光 (0.25 = 手动模式, 0.75 = 自动模式)

# 如果摄像头支持，启用自动对焦
# cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)  # 启用自动对焦
# cap.set(cv2.CAP_PROP_FOCUS, 0)      # 手动设置对焦 (0-255)

# 设置图像质量
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)    # 设置缓冲区大小为1帧，减少延迟

# 显示实际的相机参数
print(f"实际分辨率: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
print(f"实际FPS: {cap.get(cv2.CAP_PROP_FPS)}")
print(f"实际亮度: {cap.get(cv2.CAP_PROP_BRIGHTNESS)}")
print(f"实际对比度: {cap.get(cv2.CAP_PROP_CONTRAST)}")
print(f"实际饱和度: {cap.get(cv2.CAP_PROP_SATURATION)}")
print(f"实际曝光: {cap.get(cv2.CAP_PROP_EXPOSURE)}")
print(f"实际增益: {cap.get(cv2.CAP_PROP_GAIN)}")
print(f"实际伽马: {cap.get(cv2.CAP_PROP_GAMMA)}")

while True:
    ret, frame = cap.read()
    
    # 去畸变处理
    if camera_matrix is not None and dist_coeffs is not None:
        frame_ = cv2.undistort(frame, camera_matrix, dist_coeffs)
    
    cv2.imshow('frame_', frame_)
    # cv2.imshow('frame', frame)
    if cv2.waitKey(1) & 0xFF == ord('s'):
        # 使用时间戳作为文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # 精确到毫秒
        img_path = os.path.join(img_dir, f'{timestamp}.png')
        cv2.imwrite(img_path, frame_)
        print(f'Image saved: {img_path}')
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()