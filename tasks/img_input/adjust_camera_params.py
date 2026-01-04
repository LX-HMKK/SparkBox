import cv2
import numpy as np
import os
import yaml
from datetime import datetime


def nothing(x):
    pass


def adjust_camera_params():
    # 设置图片保存路径
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

    # 打开摄像头
    cap = cv2.VideoCapture(1)

    # 尝试设置分辨率（但实际可能因摄像头能力而异）
    cap.set(3, 1280)  # Width
    cap.set(4, 720)  # Height
    cap.set(cv2.CAP_PROP_FPS, 30)  # FPS

    # 创建窗口
    cv2.namedWindow('Camera Adjust')

    # 创建滑块来调整参数
    cv2.createTrackbar('Brightness', 'Camera Adjust', 50, 100, nothing)
    cv2.createTrackbar('Contrast', 'Camera Adjust', 50, 100, nothing)
    cv2.createTrackbar('Saturation', 'Camera Adjust', 64, 100, nothing)
    cv2.createTrackbar('Exposure', 'Camera Adjust', 6, 15, nothing)  # -11 to 1 -> 0 to 15 (mapped)
    cv2.createTrackbar('Gain', 'Camera Adjust', 50, 100, nothing)

    # 显示当前参数的初始值
    print(f"初始分辨率: {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}x{cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"初始FPS: {cap.get(cv2.CAP_PROP_FPS)}")
    print(f"初始亮度: {cap.get(cv2.CAP_PROP_BRIGHTNESS)}")
    print(f"初始对比度: {cap.get(cv2.CAP_PROP_CONTRAST)}")
    print(f"初始饱和度: {cap.get(cv2.CAP_PROP_SATURATION)}")
    print(f"初始曝光: {cap.get(cv2.CAP_PROP_EXPOSURE)}")
    print(f"初始增益: {cap.get(cv2.CAP_PROP_GAIN)}")
    print("\n使用滑块调整参数，按 's' 键保存图像，按 'q' 键退出")

    while True:
        ret, frame = cap.read()
        if not ret:
            print("无法获取摄像头画面")
            break

        # 去畸变处理
        if camera_matrix is not None and dist_coeffs is not None:
            frame_ = cv2.undistort(frame, camera_matrix, dist_coeffs)
        else:
            frame_ = frame

        # 获取滑块值（仅在窗口存在时）
        try:
            brightness = cv2.getTrackbarPos('Brightness', 'Camera Adjust')
            contrast = cv2.getTrackbarPos('Contrast', 'Camera Adjust')
            saturation = cv2.getTrackbarPos('Saturation', 'Camera Adjust')
            exposure = cv2.getTrackbarPos('Exposure', 'Camera Adjust') - 11  # 转换回-11到1的范围
            gain = cv2.getTrackbarPos('Gain', 'Camera Adjust')

            # 尝试设置参数（注意：不是所有参数都能成功设置）
            cap.set(cv2.CAP_PROP_BRIGHTNESS, brightness)
            cap.set(cv2.CAP_PROP_CONTRAST, contrast)
            cap.set(cv2.CAP_PROP_SATURATION, saturation)
            cap.set(cv2.CAP_PROP_EXPOSURE, exposure)
            cap.set(cv2.CAP_PROP_GAIN, gain)

            # 获取当前实际参数值
            current_brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
            current_contrast = cap.get(cv2.CAP_PROP_CONTRAST)
            current_saturation = cap.get(cv2.CAP_PROP_SATURATION)
            current_exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
            current_gain = cap.get(cv2.CAP_PROP_GAIN)

            # 在画面上显示参数信息
            info_text = f"B:{current_brightness}, C:{current_contrast}, S:{current_saturation}, E:{current_exposure}, G:{current_gain}"
            cv2.putText(frame_, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 1, cv2.LINE_AA)
        except:
            # 如果窗口已关闭，跳出循环
            break

        cv2.imshow('Camera Adjust', frame_)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            # 保存图像
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            img_path = os.path.join(img_dir, f'adjusted_{timestamp}.png')
            cv2.imwrite(img_path, frame_)
            print(f'Image saved: {img_path}')
        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("参数调整完成！")


if __name__ == "__main__":
    adjust_camera_params()