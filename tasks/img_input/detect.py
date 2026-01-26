"""
传统方法识别180mm宽的白色正方形和内部20mm黑色边框
包含透视变换和保存图片功能
识别一个180mm的正方形，内部有20mm宽的黑框，形成一个140mm的内部白色区域
"""

import cv2
import numpy as np
import yaml
import os
from pathlib import Path
from datetime import datetime


class SquareDetector:
    def __init__(self, camera_yaml_path):
        """
        初始化正方形检测器
        
        Args:
            camera_yaml_path: 相机标定参数文件路径
        """
        # 加载相机标定参数
        print(f"正在加载相机参数: {camera_yaml_path}")
        with open(camera_yaml_path, 'r', encoding='utf-8') as f:
            camera_params = yaml.safe_load(f)
        
        self.camera_matrix = np.array(camera_params['camera_matrix'])
        self.dist_coeffs = np.array(camera_params['dist_coeffs'])
        self.image_width = camera_params['image_width']
        self.image_height = camera_params['image_height']
        
        # 存储检测到的四个角点
        self.corners = []
        
        # 外部白色正方形尺寸(mm)和内部黑框宽度(mm)
        self.outer_square_mm = 180  # 外部白色正方形边长
        self.black_border_mm = 20   # 黑色边框宽度
        self.inner_square_mm = 140  # 内部白色正方形边长 (180 - 2*20 = 140)
        
        # 目标输出尺寸(px)
        self.target_size_px = 720  # 180mm对应720px，即每毫米约4px
        
        print("SquareDetector初始化完成！")

    def detect_white_square_with_black_border(self, frame):
        """
        检测180mm白色正方形和内部20mm黑色边框
        识别一个180mm的正方形，内部有20mm宽的黑框，形成一个140mm的内部白色区域
        """
        # 畸变矫正
        undistorted_frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
        
        # 转换为灰度图
        gray = cv2.cvtColor(undistorted_frame, cv2.COLOR_BGR2GRAY)
        
        # 高斯模糊以减少噪声
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 使用Otsu自动阈值方法进行二值化
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 寻找最大的四边形轮廓（假设是我们的外部白色正方形）
        largest_contour = None
        max_area = 0
        
        for contour in contours:
            # 计算轮廓面积
            area = cv2.contourArea(contour)
            
            # 过滤掉太小的轮廓
            if area < 5000:
                continue
            
            # 近似轮廓为多边形
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # 检查是否为四边形且面积足够大
            if len(approx) == 4 and area > max_area:
                # 检查凸性
                if cv2.isContourConvex(approx):
                    # 添加边长筛选，剔除不够正方形的目标
                    # 计算四条边的长度
                    pts = approx.reshape(4, 2)
                    sides = []
                    for i in range(4):
                        p1 = pts[i]
                        p2 = pts[(i+1)%4]
                        side_length = np.linalg.norm(p1 - p2)
                        sides.append(side_length)
                    
                    # 计算边长的最大值和最小值
                    sides = np.array(sides)
                    max_side = np.max(sides)
                    min_side = np.min(sides)
                    
                    # 计算边长比例，如果最长边不超过最短边的一定倍数，则认为是正方形
                    aspect_ratio = max_side / min_side if min_side > 0 else float('inf')
                    aspect_threshold = 1.5  # 设定长宽比阈值，可根据实际情况调整
                    
                    if aspect_ratio <= aspect_threshold:
                        max_area = area
                        largest_contour = approx
        
        if largest_contour is not None:
            # 打印识别的外部正方形面积
            # print(f"外部白色正方形面积: {max_area:.2f} 像素²")
            
            # 绘制白色正方形的轮廓
            cv2.drawContours(undistorted_frame, [largest_contour], -1, (0, 255, 0), 2)
            
            # 获取四个角点并排序为 TL, TR, BR, BL
            corners = self.order_points(largest_contour.reshape(4, 2))
            self.corners = corners
            
            # 在角点处绘制标记
            for i, point in enumerate(corners):
                cv2.circle(undistorted_frame, tuple(point.astype(int)), 8, (0, 0, 255), -1)
                cv2.putText(undistorted_frame, f"Corner {i}", tuple(point.astype(int)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                
            # 通过检测内部的黑色边框来识别内部白色正方形
            inner_square_corners = self.detect_inner_white_square_from_black_border(
                gray, largest_contour
            )
            
            if inner_square_corners is not None:
                # 绘制内部白色区域的轮廓
                cv2.drawContours(undistorted_frame, [inner_square_corners], -1, (255, 0, 0), 2)
                
                # 计算并打印内部白色正方形的面积
                inner_area = cv2.contourArea(inner_square_corners)
                # print(f"内部白色正方形面积: {inner_area:.2f} 像素²")
                
                # 在角点处绘制标记
                for i, point in enumerate(inner_square_corners.reshape(4, 2)):
                    cv2.circle(undistorted_frame, tuple(point.astype(int)), 8, (0, 0, 255), -1)
                    cv2.putText(undistorted_frame, f"Inner {i}", tuple(point.astype(int)), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
        return undistorted_frame, thresh

    def detect_inner_white_square_from_black_border(self, gray_image, outer_contour):
        """
        通过检测黑色厚边框的内圈来识别内部的白色正方形
        """
        # 获取外接矩形的边界
        outer_rect = cv2.boundingRect(outer_contour)
        x, y, w, h = outer_rect
        
        # 提取感兴趣区域（ROI）
        roi = gray_image[y:y+h, x:x+w]
        
        # 应用高斯模糊
        blurred_roi = cv2.GaussianBlur(roi, (5, 5), 0)
        
        # 使用Otsu阈值，因为我们要找的是黑色边框，所以可能需要反转
        _, thresh_roi = cv2.threshold(blurred_roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 寻找轮廓（这里我们寻找黑色边框的轮廓）
        contours, _ = cv2.findContours(thresh_roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # 寻找位于外轮廓内部的黑色边框
        for contour in contours:
            # 转换轮廓坐标到全图坐标系
            converted_contour = contour.copy()
            converted_contour[:, :, 0] += x
            converted_contour[:, :, 1] += y
            
            # 检查轮廓是否在外部白色正方形内部
            if cv2.contourArea(converted_contour) < 1000:  # 忽略过小的轮廓
                continue
                
            # 近似为多边形
            epsilon = 0.02 * cv2.arcLength(converted_contour, True)
            approx = cv2.approxPolyDP(converted_contour, epsilon, True)
            
            # 检查是否为四边形
            if len(approx) == 4:
                # 检查是否在外部轮廓内部
                mbr = cv2.boundingRect(converted_contour)
                center_x, center_y = mbr[0] + mbr[2]//2, mbr[1] + mbr[3]//2
                
                # 使用pointPolygonTest检查中心点是否在外轮廓内部
                if cv2.pointPolygonTest(outer_contour, (center_x, center_y), False) >= 0:
                    # 这是一个候选的黑色边框
                    # 现在查找这个黑色边框内的内部白色正方形
                    inner_white_square = self.find_inner_white_square(gray_image, converted_contour)
                    if inner_white_square is not None:
                        return inner_white_square
        
        return None

    def find_inner_white_square(self, gray_image, black_border_contour):
        """
        在黑色边框内部查找白色正方形
        """
        # 获取黑色边框的边界框
        bx, by, bw, bh = cv2.boundingRect(black_border_contour)
        
        # 提取感兴趣区域（ROI）
        roi = gray_image[by:by+bh, bx:bx+bw]
        
        # 应用高斯模糊
        blurred_roi = cv2.GaussianBlur(roi, (5, 5), 0)
        
        # 使用Otsu阈值找到内部白色区域
        _, thresh_roi = cv2.threshold(blurred_roi, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # 查找内部的白色轮廓
        inner_contours, _ = cv2.findContours(thresh_roi, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        max_inner_area = 0
        best_inner_contour = None
        
        for inner_contour in inner_contours:
            # 转换轮廓坐标到全图坐标系
            converted_contour = inner_contour.copy()
            converted_contour[:, :, 0] += bx
            converted_contour[:, :, 1] += by
            
            # 检查面积
            area = cv2.contourArea(converted_contour)
            
            # 检查是否在黑色边框内部
            if area > 1000:  # 过滤小轮廓
                # 近似为多边形
                epsilon = 0.02 * cv2.arcLength(converted_contour, True)
                approx = cv2.approxPolyDP(converted_contour, epsilon, True)
                
                # 检查是否为四边形且面积适中
                if len(approx) == 4 and cv2.isContourConvex(approx):
                    # 计算边长比例，确保是接近正方形的形状
                    pts = approx.reshape(4, 2)
                    sides = []
                    for i in range(4):
                        p1 = pts[i]
                        p2 = pts[(i+1)%4]
                        side_length = np.linalg.norm(p1 - p2)
                        sides.append(side_length)
                    
                    sides = np.array(sides)
                    max_side = np.max(sides)
                    min_side = np.min(sides)
                    
                    aspect_ratio = max_side / min_side if min_side > 0 else float('inf')
                    
                    # 检查是否在黑色边框内部
                    mbr = cv2.boundingRect(converted_contour)
                    center_x, center_y = mbr[0] + mbr[2]//2, mbr[1] + mbr[3]//2
                    
                    if cv2.pointPolygonTest(black_border_contour, (center_x, center_y), False) >= 0 and aspect_ratio <= 1.2:
                        if area > max_inner_area:
                            max_inner_area = area
                            best_inner_contour = approx
        
        return best_inner_contour

    def order_points(self, pts):
        """
        将四个点按 TL, TR, BR, BL 顺序排列
        """
        rect = np.zeros((4, 2), dtype="float32")
        
        # 左上角是最小的和，右下角是最大的和
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]  # TL
        rect[2] = pts[np.argmax(s)]  # BR
        
        # 右上角是差值最小的，左下角是差值最大的
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]  # TR
        rect[3] = pts[np.argmax(diff)]  # BL
        
        return rect

    def detect_inner_black_border(self, frame, outer_corners):
        """
        检测白色正方形内部的黑色边框
        识别180mm白色正方形内的20mm黑色边框，内部是140mm的白色区域
        """
        # 计算透视变换矩阵，将四边形转换为标准正方形
        target_size = self.target_size_px
        target_square = np.float32([
            [0, 0],                    # 左上
            [target_size - 1, 0],      # 右上
            [target_size - 1, target_size - 1],  # 右下
            [0, target_size - 1]       # 左下
        ])
        
        # 计算透视变换矩阵
        matrix = cv2.getPerspectiveTransform(outer_corners, target_square)
        
        # 应用透视变换
        warped = cv2.warpPerspective(frame, matrix, (target_size, target_size))
        
        # 转换为灰度图
        gray_warped = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)
        
        # 检测内部黑色边框
        # 180mm外部白色区域 -> target_size px
        # 20mm黑边框 -> (20/180)*target_size px
        # 140mm内部白色区域 -> (140/180)*target_size px
        outer_size_px = target_size
        border_size_px = int((self.black_border_mm / self.outer_square_mm) * target_size)
        inner_size_px = int((self.inner_square_mm / self.outer_square_mm) * target_size)
        
        # 计算中心位置
        center = (target_size // 2, target_size // 2)
        
        # 创建掩码来突出黑色边框区域（在外部白色区域和内部白色区域之间的环形区域）
        mask = np.zeros_like(gray_warped)
        
        # 先标记内部白色区域为1（不感兴趣）
        cv2.rectangle(mask, 
                     (center[0] - inner_size_px//2, center[1] - inner_size_px//2),
                     (center[0] + inner_size_px//2, center[1] + inner_size_px//2), 
                     1, -1)
        
        # 标记外部白色区域为2（感兴趣）
        cv2.rectangle(mask, 
                     (center[0] - outer_size_px//2, center[1] - outer_size_px//2),
                     (center[0] + outer_size_px//2, center[1] + outer_size_px//2), 
                     2, -1)
        
        # 将内部区域设为0（不感兴趣）
        cv2.rectangle(mask, 
                     (center[0] - inner_size_px//2, center[1] - inner_size_px//2),
                     (center[0] + inner_size_px//2, center[1] + inner_size_px//2), 
                     0, -1)
        
        # 选择只包含边框区域的像素
        border_region = np.where(mask == 2, gray_warped, 0)
        
        # 使用Otsu自动阈值方法寻找黑色边框的轮廓
        # 因为我们寻找黑色区域，所以使用THRESH_BINARY_INV
        _, thresh_border = cv2.threshold(border_region, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        
        # 查找边框轮廓
        border_contours, _ = cv2.findContours(thresh_border, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 寻找合适的边框轮廓
        for contour in border_contours:
            area = cv2.contourArea(contour)
            # 调整最小面积阈值，适应新的尺寸比例
            min_area = (border_size_px * target_size * 0.3)  # 至少占边框区域的30%
            if area > min_area:
                # 近似为多边形
                epsilon = 0.02 * cv2.arcLength(contour, True)
                approx = cv2.approxPolyDP(contour, epsilon, True)
                
                # 如果近似为四边形，则认为找到了黑色边框
                if len(approx) >= 4:
                    return approx
        
        return None

    def apply_perspective_transform(self, frame):
        """
        对输入帧应用透视变换，将检测到的四个角点变换为矩形
        """
        if len(self.corners) != 4:
            # 如果没有检测到4个角点，返回原图
            return frame
        
        # 先对整个图像进行去畸变处理
        undistorted_frame = cv2.undistort(frame, self.camera_matrix, self.dist_coeffs)
        
        # 获取当前角点
        corners = self.corners
        
        # 定义目标矩形的四个角点
        target_size = self.target_size_px
        target_square = np.float32([
            [0, 0],                    # 左上
            [target_size - 1, 0],      # 右上
            [target_size - 1, target_size - 1],  # 右下
            [0, target_size - 1]       # 左下
        ])
        
        # 计算透视变换矩阵
        matrix = cv2.getPerspectiveTransform(corners, target_square)
        
        # 应用透视变换
        warped = cv2.warpPerspective(undistorted_frame, matrix, (target_size, target_size))
        
        return warped

    def run(self, camera_id=0):
        """
        运行实时检测
        """
        # 打开相机
        cap = cv2.VideoCapture(camera_id)
        
        # 设置相机参数
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.image_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.image_height)
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 减少缓冲区，降低延迟
        
        if not cap.isOpened():
            print("错误: 无法打开相机")
            return
        
        print("相机已打开，按 'q' 退出，按 's' 保存透视变换图片")
        
        # 创建窗口
        cv2.namedWindow('Square Detection', cv2.WINDOW_AUTOSIZE)
        cv2.namedWindow('Warped Output', cv2.WINDOW_AUTOSIZE)
        
        while True:
            # 读取帧
            ret, frame = cap.read()
            if not ret:
                print("错误: 无法读取帧")
                break
            
            # 获取原始帧的尺寸
            h, w = frame.shape[:2]
            
            # 检测180mm白色正方形和内部20mm黑色边框
            detected_frame, thresh = self.detect_white_square_with_black_border(frame)
            
            # 应用透视变换
            warped_frame = self.apply_perspective_transform(frame)
            
            # 显示画面
            cv2.imshow('Square Detection', detected_frame)
            # cv2.imshow('Thresholded', thresh)
            cv2.imshow('Warped Output', warped_frame)
            
            # 按 'q' 退出，按 's' 保存透视变换图片
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("退出程序...")
                break
            elif key == ord('s'):
                # 创建保存图片的目录 - 使用项目根目录下的asset/img文件夹
                workspace_root = Path(__file__).parent.parent.parent
                save_dir = workspace_root / "asset" / "img"
                save_dir.mkdir(parents=True, exist_ok=True)
                
                # 生成带时间戳的文件名
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 精确到毫秒
                filename = save_dir / f"perspective_{timestamp}.jpg"
                
                # 保存透视变换后的图片
                success = cv2.imwrite(str(filename), warped_frame)
                if success:
                    print(f"透视变换图片已保存: {filename}")
                else:
                    print(f"保存图片失败: {filename}")

        # 释放资源
        cap.release()
        cv2.destroyAllWindows()


def main():
    """主函数"""
    # 设置路径
    workspace_root = Path(__file__).parent.parent.parent
    
    # 配置文件路径
    camera_yaml_path = workspace_root / "asset" / "camera.yaml"
    
    # 检查相机参数文件
    if not camera_yaml_path.exists():
        print(f"错误: 相机参数文件不存在: {camera_yaml_path}")
        return
    
    # 创建矩形检测系统
    detector = SquareDetector(str(camera_yaml_path))
    
    # 运行实时检测
    detector.run(camera_id=0)


if __name__ == "__main__":
    main()