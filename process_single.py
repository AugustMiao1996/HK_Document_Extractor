#!/usr/bin/env python3
"""
处理单个PDF文件
"""

import sys
import os
sys.path.append('src')

from extractor import DocumentExtractor
import logging
import json

def process_single_pdf(pdf_path):
    """处理单个PDF文件"""
    
    if not os.path.exists(pdf_path):
        print(f"❌ 文件不存在: {pdf_path}")
        return
    
    print(f"📄 处理文件: {pdf_path}")
    
    # 创建提取器
    extractor = DocumentExtractor(log_level=logging.INFO)
    
    # 提取信息
    result = extractor.process_pdf(pdf_path)
    
    if result:
        print(f"\n✅ 提取成功！")
        
        # 显示关键信息
        key_fields = [
            ('文档类型', 'document_type'),
            ('原告', 'plaintiff'), 
            ('被告', 'defendant'),
            ('法院', 'court_name'),
            ('案件编号', 'case_number'),
            ('审判日期', 'trial_date'),
        ]
        
        print(f"\n📋 关键信息:")
        for name, key in key_fields:
            value = result.get(key, '').strip()
            status = "✅" if value else "❌"
            print(f"  {status} {name}: {value[:50]}{'...' if len(value) > 50 else ''}")
        
        # 保存结果
        output_file = f"{os.path.splitext(os.path.basename(pdf_path))[0]}_result.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 详细结果已保存到: {output_file}")
        
    else:
        print(f"❌ 提取失败")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 从命令行参数获取文件路径
        pdf_path = sys.argv[1]
    else:
        # 交互式输入
        pdf_path = input("请输入PDF文件路径: ").strip().strip('"')
    
    process_single_pdf(pdf_path) 