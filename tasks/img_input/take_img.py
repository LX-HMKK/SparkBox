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
cap.set(3, 1280)  # Width
cap.set(4, 720)  # Height 
cap.set(cv2.CAP_PROP_FPS, 30)  # FPS

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