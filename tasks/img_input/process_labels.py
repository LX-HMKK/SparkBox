import json
import os
from pathlib import Path


def categorize_points_by_position(points):
    """
    根据x、y坐标将四个点分为point_tl（左上）、point_tr（右上）、point_br（右下）、point_bl（左下）
    :param points: 包含四个点坐标的列表，每个点为[x, y]
    :return: 按照tl, tr, br, bl顺序排序的点列表
    """
    # 按照坐标排序：左上、右上、左下、右下
    # 左上：x和y都较小；右上：x大y小；左下：x小y大；右下：x和y都大
    sorted_points = sorted(points, key=lambda p: (p[1], p[0]))  # 先按y坐标排序，再按x坐标排序
    
    # 前两个点是y值较小的点（上方的两个点）
    top_points = sorted_points[:2]
    bottom_points = sorted_points[2:]
    
    # 对上方的点按x坐标排序，左上角和右上角
    top_points = sorted(top_points, key=lambda p: p[0])
    tl = top_points[0]  # 左上角
    tr = top_points[1]  # 右上角
    
    # 对下方的点按x坐标排序，左下角和右下角
    bottom_points = sorted(bottom_points, key=lambda p: p[0])
    bl = bottom_points[0]  # 左下角
    br = bottom_points[1]  # 右下角
    
    return tl, tr, br, bl


def process_json_file(file_path):
    """
    处理单个JSON标注文件
    :param file_path: JSON文件路径
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 分离出canvas矩形和point点（包括已分类的点）
    canvas_shapes = []
    point_shapes = []
    
    for shape in data['shapes']:
        if shape['label'] == 'canvas':
            # 更新canvas的group_id为1
            updated_shape = shape.copy()
            updated_shape['group_id'] = 1
            canvas_shapes.append(updated_shape)
        elif shape['label'] == 'point':  # 原始未分类的点
            point_shapes.append(shape)
        elif shape['label'].startswith('point_'):  # 已分类的点，也包含在point_shapes中用于兼容性
            # 保留已分类的点，但更新其group_id
            updated_shape = shape.copy()
            updated_shape['group_id'] = 1
            point_shapes.append(updated_shape)
    
    # 只处理恰好有4个点的文件
    if len(point_shapes) != 4:
        # 如果有4个点但已分类，我们只更新它们的group_id
        if len([s for s in data['shapes'] if s['label'].startswith('point_') and s['label'] != 'point']) == 4:
            # 文件已经处理过，只需确保canvas的group_id为1
            updated_shapes = []
            for shape in data['shapes']:
                if shape['label'] == 'canvas':
                    updated_shape = shape.copy()
                    updated_shape['group_id'] = 1
                    updated_shapes.append(updated_shape)
                elif shape['label'].startswith('point_'):
                    updated_shape = shape.copy()
                    updated_shape['group_id'] = 1
                    updated_shapes.append(updated_shape)
                else:
                    updated_shapes.append(shape)
            data['shapes'] = updated_shapes
        else:
            print(f"警告: 文件 {file_path} 中有 {len([s for s in data['shapes'] if s['label'] == 'point'])} 个未分类点，不是4个点，跳过处理")
            return
    else:
        # 处理未分类的点
        # 提取所有point的坐标
        points = [shape['points'][0] for shape in point_shapes]
        
        # 根据坐标对点进行分类
        tl, tr, br, bl = categorize_points_by_position(points)
        
        # 创建新的point shapes，按顺序排列
        new_point_shapes = []
        
        # 找到对应的原始形状并更新标签和group_id
        for i, target_point in enumerate([tl, tr, br, bl]):
            label_names = ['point_tl', 'point_tr', 'point_br', 'point_bl']
            for j, shape in enumerate(point_shapes):
                original_point = shape['points'][0]
                # 比较坐标是否相同（考虑浮点数精度）
                if abs(original_point[0] - target_point[0]) < 1e-5 and abs(original_point[1] - target_point[1]) < 1e-5:
                    updated_shape = shape.copy()
                    updated_shape['label'] = label_names[i]
                    updated_shape['group_id'] = 1
                    new_point_shapes.append(updated_shape)
                    break
        
        # 重新构建shapes列表
        data['shapes'] = canvas_shapes + new_point_shapes
    
    # 保存更新后的文件
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"已处理文件: {file_path}")


def process_all_json_files(folder_path):
    """
    处理指定文件夹中的所有JSON文件
    :param folder_path: 文件夹路径
    """
    folder_path = Path(folder_path)
    
    # 获取所有JSON文件
    json_files = list(folder_path.glob('*.json'))
    
    if not json_files:
        print(f"在文件夹 {folder_path} 中未找到JSON文件")
        return
    
    print(f"找到 {len(json_files)} 个JSON文件，开始处理...")
    
    processed_count = 0
    for json_file in json_files:
        try:
            process_json_file(json_file)
            processed_count += 1
        except Exception as e:
            print(f"处理文件 {json_file} 时出错: {str(e)}")
    
    print(f"处理完成! 共处理了 {processed_count} 个文件")


if __name__ == "__main__":
    # 指定要处理的文件夹路径
    folder_path = input("请输入要处理的文件夹路径 (直接回车使用默认的img文件夹): ").strip()
    
    if not folder_path:
        folder_path = "D:/StudyWorks/3.1/item1/SparkBox/imgs"
    
    if not os.path.exists(folder_path):
        print(f"路径 {folder_path} 不存在")
        exit(1)
    
    process_all_json_files(folder_path)