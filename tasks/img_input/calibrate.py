import cv2
import numpy as np
import os
import yaml
from datetime import datetime

# 棋盘格参数：11列8行，每个小格30mm
CHECKERBOARD = (11, 8)
SQUARE_SIZE = 30  # mm
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# 准备棋盘格世界坐标
objp = np.zeros((1, CHECKERBOARD[0] * CHECKERBOARD[1], 3), np.float32)
objp[0, :, :2] = np.mgrid[0:CHECKERBOARD[0], 0:CHECKERBOARD[1]].T.reshape(-1, 2) * SQUARE_SIZE

# 用于存储所有棋盘格的object points和image points
objpoints = []  # 3D实际世界坐标
imgpoints = []  # 2D图像坐标

# 设置标定数据保存路径
asset_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'asset')
os.makedirs(asset_dir, exist_ok=True)
calibration_file = os.path.join(asset_dir, 'camera.yaml')

# 初始化相机
cap = cv2.VideoCapture(1)
cap.set(3, 1280)  # Width
cap.set(4, 720)  # Height 
cap.set(cv2.CAP_PROP_FPS, 30)  # FPS

frame_count = 0
saved_count = 0

print("Camera calibration started")
print("Instructions:")
print("  Press 'c' to capture current chessboard image (need at least 15)")
print("  Press 'q' to calibrate and save results")
print("  Press 's' to save debug image")

while True:
    ret, frame = cap.read()
    if not ret:
        print("错误：无法读取摄像头")
        break
    
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
    # 检测棋盘格角点
    ret_detect, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    
    # 在图像上绘制检测结果
    if ret_detect:
        # 亚像素精细化
        corners_refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        cv2.drawChessboardCorners(frame, CHECKERBOARD, corners_refined, ret_detect)
        status_text = f"Detected | Saved: {saved_count}/15+ | Press 'c'"
        text_color = (0, 255, 0)
    else:
        status_text = f"Not detected | Saved: {saved_count}/15+ | Adjust"
        text_color = (0, 0, 255)
    
    # 显示状态信息
    cv2.putText(frame, status_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
    cv2.putText(frame, "Press 'c' to capture, 'q' to calibrate, 's' to save debug, 'q' to quit", 
                (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    cv2.imshow('Calibration', frame)
    
    key = cv2.waitKey(1) & 0xFF
    frame_count += 1
    
    if key == ord('c'):  # 捕获
        if ret_detect:
            objpoints.append(objp)
            imgpoints.append(corners_refined)
            saved_count += 1
            print(f"Captured {saved_count} images")
        else:
            print("Chessboard not detected, please adjust position")
    
    elif key == ord('s'):  # 保存调试图像
        debug_dir = os.path.join(asset_dir, 'debug')
        os.makedirs(debug_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        debug_path = os.path.join(debug_dir, f'calibration_{timestamp}.png')
        cv2.imwrite(debug_path, frame)
        print(f"Debug image saved: {debug_path}")
    
    elif key == ord('q'):  # 开始标定
        break

cap.release()
cv2.destroyAllWindows()

# 进行相机标定
if saved_count >= 3:
    print(f"\nStarting camera calibration using {saved_count} images...")
    
    # 获取图像尺寸（从第一个已捕获的图像获取）
    if len(imgpoints) > 0:
        ret_test, test_frame = cap.read()
        if ret_test:
            gray = cv2.cvtColor(test_frame, cv2.COLOR_BGR2GRAY)
            img_size = gray.shape[::-1]  # (width, height)
        else:
            # 备选：使用imgpoints的形状估计
            print("Warning: Could not get frame from camera, using estimated size")
            img_size = (1280, 720)
        cap.release()
    
    # 执行标定
    ret, camera_matrix, dist_coeffs, rvecs, tvecs = cv2.calibrateCamera(
        objpoints, imgpoints, img_size, None, None
    )
    
    if ret:
        print(f"Calibration successful! Reprojection error: {ret:.4f}")
        
        # 计算标定精度
        total_error = 0
        total_points = 0
        for i in range(len(objpoints)):
            imgpoints2, _ = cv2.projectPoints(objpoints[i], rvecs[i], tvecs[i], camera_matrix, dist_coeffs)
            error = cv2.norm(imgpoints[i], imgpoints2, cv2.NORM_L2) / len(imgpoints2)
            total_error += error
            total_points += len(imgpoints2)
        
        mean_error = total_error / len(objpoints)
        print(f"Mean reprojection error: {mean_error:.4f} pixels")
        
        # 保存标定结果到YAML文件
        calibration_data = {
            'camera_matrix': camera_matrix.tolist(),            # 相机矩阵
            'dist_coeffs': dist_coeffs.flatten().tolist(),      # 畸变系数
            'image_width': int(img_size[0]),
            'image_height': int(img_size[1]),
            'reprojection_error': float(ret),                   # 标定精度
            'mean_reprojection_error': float(mean_error),       # 平均重投影误差
            'num_images': saved_count,
            'checkerboard_size': list(CHECKERBOARD),
            'calibration_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        with open(calibration_file, 'w', encoding='utf-8') as f:
            yaml.dump(calibration_data, f, default_flow_style=False, allow_unicode=True)
        
        print(f"\nCalibration results saved to: {calibration_file}")
        print(f"\nCamera matrix:")
        print(camera_matrix)
        print(f"\nDistortion coefficients:")
        print(dist_coeffs)
    else:
        print("Calibration failed!")
else:
    print(f"Insufficient calibration data. Captured {saved_count} images, need at least 3")
