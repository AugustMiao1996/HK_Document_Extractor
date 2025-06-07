#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_pdf_cleaning_keywords():
    """修复PDF清理逻辑的关键词列表，添加DCCJ支持"""
    
    file_path = "src/extractor.py"
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复关键词列表
    old_keywords = """        critical_keywords = [
            'IN THE HIGH COURT', 'ACTION NO', 'COURT OF FIRST INSTANCE', 
            'HCA', 'BETWEEN', 'PLAINTIFF', 'DEFENDANT'
        ]"""
    
    new_keywords = """        critical_keywords = [
            'IN THE HIGH COURT', 'IN THE DISTRICT COURT', 'ACTION NO', 'CIVIL ACTION NO',
            'COURT OF FIRST INSTANCE', 'HCA', 'DCCJ', 'BETWEEN', 'PLAINTIFF', 'DEFENDANT'
        ]"""
    
    if old_keywords in content:
        content = content.replace(old_keywords, new_keywords)
        print("✅ 成功修复关键词列表")
    else:
        print("❌ 未找到需要修复的关键词列表")
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("PDF清理逻辑修复完成")

if __name__ == "__main__":
    fix_pdf_cleaning_keywords() 