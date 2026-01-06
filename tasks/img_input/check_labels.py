import glob, os
root = r"D:\StudyWorks\3.1\item1\Sparkbox_ws\labels"
bad = []
for p in glob.glob(os.path.join(root, "**", "*.txt"), recursive=True):
    with open(p) as f:
        for i, line in enumerate(f, 1):
            n = len(line.strip().split())
            if n != 17:
                bad.append((p, i, n, line.strip()))
if bad:
    print("列数不匹配的行：")
    for p, i, n, line in bad:
        print(f"{p} 行{i} 列数={n} 内容={line}")
else:
    print("所有标签列数均为17，格式正确")