import pytesseract
from PIL import Image
import os
import re

# 设置 Tesseract OCR 引擎路径（Ubuntu 典型路径）
pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

# 图片所在文件夹（当前目录）
image_folder = '.'

# 存储所有提取的代码行（包含行号）
all_code_lines = []

# 遍历处理所有图片
for filename in os.listdir(image_folder):
    if filename.endswith(('.png', '.jpg', '.jpeg')):
        image_path = os.path.join(image_folder, filename)
        try:
            img = Image.open(image_path)
            text = pytesseract.image_to_string(img, lang='eng')
            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                # 匹配行号和代码内容
                code_match = re.match(r'^(\d+)\s+(.*)$', line)
                if code_match:
                    line_num = int(code_match.group(1))
                    code_line = code_match.group(2)
                    all_code_lines.append((line_num, code_line))
        except Exception as e:
            print(f"处理 {filename} 出错: {e}")

# 按行号排序
all_code_lines.sort(key=lambda x: x[0])

# 去除重复代码行，保持行号顺序
unique_code_lines = []
seen_lines = set()
for _, code_line in all_code_lines:
    if code_line not in seen_lines:
        unique_code_lines.append(code_line)
        seen_lines.add(code_line)

# 写入文件
with open('extracted_full_code.py', 'w', encoding='utf-8') as f:
    for code_line in unique_code_lines:
        f.write(code_line + '\n')

print("完整代码已提取并保存至 extracted_full_code.py")