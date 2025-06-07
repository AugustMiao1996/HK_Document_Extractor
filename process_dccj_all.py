#!/usr/bin/env python3
"""
处理DCCJ文件夹下的所有PDF文件
"""

import sys
import os
sys.path.append('src')

from extractor import DocumentExtractor
import logging
import json
from pathlib import Path
from datetime import datetime

def process_all_dccj():
    print("=== 处理DCCJ文件夹所有PDF文件 ===")
    
    # 设置日志级别（减少输出）
    extractor = DocumentExtractor(log_level=logging.WARNING)
    
    # DCCJ文件夹路径
    dccj_folder = "../HK/DCCJ"
    
    if not os.path.exists(dccj_folder):
        print(f"❌ DCCJ文件夹不存在: {dccj_folder}")
        return
    
    # 获取所有PDF文件
    pdf_files = list(Path(dccj_folder).glob("*.pdf"))
    total_files = len(pdf_files)
    
    print(f"📁 DCCJ文件夹: {dccj_folder}")
    print(f"📄 找到 {total_files} 个PDF文件")
    print(f"{'='*60}")
    
    if total_files == 0:
        print("❌ 没有找到PDF文件")
        return
    
    # 处理所有文件
    results = []
    success_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"[{i:2d}/{total_files}] {pdf_file.name}")
        
        try:
            result = extractor.process_pdf(str(pdf_file))
            if result:
                results.append(result)
                success_count += 1
                
                # 显示关键提取结果
                plaintiff = result.get('plaintiff', '').strip()[:40]
                defendant = result.get('defendant', '').strip()[:40]
                
                print(f"        ✅ 原告: {plaintiff}{'...' if len(plaintiff) == 40 else ''}")
                print(f"           被告: {defendant}{'...' if len(defendant) == 40 else ''}")
            else:
                print(f"        ❌ 提取失败")
                
        except Exception as e:
            print(f"        ❌ 错误: {str(e)}")
    
    # 保存结果
    if results:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 保存JSON结果
        output_file = f"dccj_all_results_{timestamp}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        # 统计分析
        plaintiff_success = sum(1 for r in results if r.get('plaintiff', '').strip())
        defendant_success = sum(1 for r in results if r.get('defendant', '').strip())
        
        print(f"\n{'='*60}")
        print(f"📊 处理完成统计:")
        print(f"   总文件数: {total_files}")
        print(f"   成功处理: {success_count}")
        print(f"   成功率: {success_count/total_files*100:.1f}%")
        print(f"   原告提取成功: {plaintiff_success}/{success_count} ({plaintiff_success/success_count*100:.1f}%)")
        print(f"   被告提取成功: {defendant_success}/{success_count} ({defendant_success/success_count*100:.1f}%)")
        print(f"💾 结果已保存到: {output_file}")
        
    else:
        print(f"\n❌ 没有成功处理任何文件")

if __name__ == "__main__":
    process_all_dccj() 