#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 修复extractor.py的语法错误

def fix_syntax_error():
    """修复extractor.py第261行的缩进错误"""
    file_path = "src/extractor.py"
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 修复第261行的缩进错误（数组是0-based，所以是索引260）
    if len(lines) > 260:
        original_line = lines[260]
        if "return language" in original_line and original_line.startswith("                "):
            # 修复过度缩进
            lines[260] = "        return language\n"
            print(f"修复前: {repr(original_line)}")
            print(f"修复后: {repr(lines[260])}")
        else:
            print(f"第261行内容: {repr(original_line)}")
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("语法错误修复完成")

if __name__ == "__main__":
    fix_syntax_error() 