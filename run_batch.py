#!/usr/bin/env python3
"""
批量处理PDF文件 - 修复版
"""

import sys
import os
sys.path.append('src')

from extractor import DocumentExtractor
import logging
import json
from pathlib import Path
from datetime import datetime

def run_batch_processing():
    print("=== 批量PDF信息提取 - 修复版 ===")
    
    # 设置日志级别
    extractor = DocumentExtractor(log_level=logging.WARNING)  # 减少日志输出
    
    # 配置要处理的文件夹
    folders_to_process = [
        "../HK/DCCJ",      # DCCJ文件夹
        "../HK/HCA",       # HCA文件夹  
        # 可以添加更多文件夹
    ]
    
    all_results = []
    
    for folder in folders_to_process:
        if not os.path.exists(folder):
            print(f"⚠️ 文件夹不存在，跳过: {folder}")
            continue
            
        print(f"\n📁 处理文件夹: {folder}")
        
        # 获取所有PDF文件
        pdf_files = list(Path(folder).glob("*.pdf"))
        print(f"找到 {len(pdf_files)} 个PDF文件")
        
        for i, pdf_file in enumerate(pdf_files[:5], 1):  # 限制处理前5个文件作为测试
            print(f"  [{i}/{min(5, len(pdf_files))}] 处理: {pdf_file.name}")
            
            try:
                result = extractor.process_pdf(str(pdf_file))
                if result:
                    all_results.append(result)
                    print(f"      ✅ 成功 - 原告: {result.get('plaintiff', '无')[:30]}...")
                else:
                    print(f"      ❌ 提取失败")
            except Exception as e:
                print(f"      ❌ 错误: {str(e)}")
    
    # 保存结果
    if all_results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON格式
        json_file = f"batch_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        
        print(f"\n📊 处理完成！")
        print(f"   总文件数: {len(all_results)}")
        print(f"   JSON结果: {json_file}")
        
        # 显示原告被告提取统计
        plaintiff_success = sum(1 for r in all_results if r.get('plaintiff', '').strip())
        defendant_success = sum(1 for r in all_results if r.get('defendant', '').strip())
        
        print(f"\n📈 关键字段统计:")
        print(f"   原告提取成功: {plaintiff_success}/{len(all_results)} ({plaintiff_success/len(all_results)*100:.1f}%)")
        print(f"   被告提取成功: {defendant_success}/{len(all_results)} ({defendant_success/len(all_results)*100:.1f}%)")
        
    else:
        print("\n❌ 没有成功处理任何文件")

if __name__ == "__main__":
    run_batch_processing() 