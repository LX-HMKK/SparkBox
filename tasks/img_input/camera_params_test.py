import cv2
import numpy as np


def test_camera_params():
    """
    测试并显示摄像头支持的参数范围
    """
    # 尝试打开摄像头
    cap = cv2.VideoCapture(1)
    
    if not cap.isOpened():
        print("无法打开摄像头 1，尝试其他索引...")
        for i in range(5):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f"成功打开摄像头 {i}")
                break
        else:
            print("无法打开任何摄像头")
            return

    print("摄像头已打开，正在检测参数范围...")
    print("当前参数值（初始）：")
    
    # 获取和显示所有可能的参数
    props = [
        (cv2.CAP_PROP_FRAME_WIDTH, "帧宽度"),
        (cv2.CAP_PROP_FRAME_HEIGHT, "帧高度"),
        (cv2.CAP_PROP_FPS, "帧率"),
        (cv2.CAP_PROP_BRIGHTNESS, "亮度"),
        (cv2.CAP_PROP_CONTRAST, "对比度"),
        (cv2.CAP_PROP_SATURATION, "饱和度"),
        (cv2.CAP_PROP_HUE, "色调"),
        (cv2.CAP_PROP_GAIN, "增益"),
        (cv2.CAP_PROP_EXPOSURE, "曝光"),
        (cv2.CAP_PROP_CONVERT_RGB, "转换RGB"),
        (cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, "白平衡蓝U"),
        (cv2.CAP_PROP_ISO_SPEED, "ISO速度"),
        (cv2.CAP_PROP_BUFFERSIZE, "缓冲区大小"),
        (cv2.CAP_PROP_AUTO_EXPOSURE, "自动曝光"),
        (cv2.CAP_PROP_AUTOFOCUS, "自动对焦"),
        (cv2.CAP_PROP_TEMPERATURE, "温度"),
        (cv2.CAP_PROP_WHITE_BALANCE_RED_V, "白平衡红V"),
        (cv2.CAP_PROP_ZOOM, "缩放"),
        (cv2.CAP_PROP_FOCUS, "对焦"),
        (cv2.CAP_PROP_SHARPNESS, "锐度"),
        (cv2.CAP_PROP_GAMMA, "伽马"),
        (cv2.CAP_PROP_BACKLIGHT, "背光补偿"),
    ]
    
    current_values = {}
    
    for prop_id, prop_name in props:
        try:
            value = cap.get(prop_id)
            if value != -1:  # -1 表示不支持该属性
                current_values[prop_id] = value
                print(f"{prop_name}: {value}")
        except:
            print(f"无法获取 {prop_name}")
    
    print("\n" + "="*50)
    print("测试可设置的参数范围...")
    
    # 测试调整参数
    test_params = [
        (cv2.CAP_PROP_BRIGHTNESS, "亮度", 0, 100),
        (cv2.CAP_PROP_CONTRAST, "对比度", 0, 100),
        (cv2.CAP_PROP_SATURATION, "饱和度", 0, 100),
        (cv2.CAP_PROP_HUE, "色调", -180, 180),
        (cv2.CAP_PROP_GAIN, "增益", 0, 100),
        (cv2.CAP_PROP_EXPOSURE, "曝光", -11, 1),
        (cv2.CAP_PROP_FOCUS, "对焦", 0, 255),
        (cv2.CAP_PROP_ZOOM, "缩放", 0, 10),
        (cv2.CAP_PROP_WHITE_BALANCE_BLUE_U, "白平衡", 0, 5000),
        (cv2.CAP_PROP_TEMPERATURE, "温度", 1000, 10000),
        (cv2.CAP_PROP_SHARPNESS, "锐度", 0, 255),
        (cv2.CAP_PROP_GAMMA, "伽马", 1, 500),
        (cv2.CAP_PROP_BACKLIGHT, "背光补偿", 0, 255),
    ]
    
    print("\n参数范围测试（如果值改变表示支持该参数）：")
    for prop_id, prop_name, min_val, max_val in test_params:
        try:
            # 获取当前值
            current = cap.get(prop_id)
            
            # 尝试设置最小值
            cap.set(prop_id, min_val)
            min_test = cap.get(prop_id)
            
            # 尝试设置最大值
            cap.set(prop_id, max_val)
            max_test = cap.get(prop_id)
            
            # 恢复原始值
            cap.set(prop_id, current)
            
            # 如果最小值或最大值与当前值不同，则说明该参数是可设置的
            if min_test != current or max_test != current:
                print(f"{prop_name}: 当前={current}, 最小={min_test}, 最大={max_test}")
            else:
                print(f"{prop_name}: 不支持或固定值={current}")
        except:
            print(f"{prop_name}: 无法设置")
    
    # 读取一帧测试
    ret, frame = cap.read()
    if ret:
        h, w = frame.shape[:2]
        print(f"\n摄像头实际分辨率: {w}x{h}")
    else:
        print("\n无法读取摄像头画面")
    
    cap.release()
    print("\n测试完成！")


if __name__ == "__main__":
    test_camera_params()