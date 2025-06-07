#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并两个JSON文件
"""

import json
import os
from datetime import datetime

def merge_json_files():
    """合并两个JSON结果文件"""
    
    # 文件路径
    file1 = "output/direct_llm_results_20250606_083246.json"
    file2 = "output/llm_analysis_20250606_072009.json"
    
    print("🔄 合并JSON文件...")
    print(f"文件1: {file1}")
    print(f"文件2: {file2}")
    
    # 读取第一个文件
    try:
        with open(file1, 'r', encoding='utf-8') as f:
            data1 = json.load(f)
        print(f"✅ 文件1加载成功: {len(data1)} 个案件")
    except Exception as e:
        print(f"❌ 无法读取文件1: {e}")
        return
    
    # 读取第二个文件
    try:
        with open(file2, 'r', encoding='utf-8') as f:
            data2 = json.load(f)
        print(f"✅ 文件2加载成功: {len(data2)} 个案件")
    except Exception as e:
        print(f"❌ 无法读取文件2: {e}")
        return
    
    # 合并数据
    merged_data = []
    
    # 添加第一个文件的数据
    merged_data.extend(data1)
    print(f"📝 添加文件1的 {len(data1)} 个案件")
    
    # 添加第二个文件的数据，检查重复
    existing_files = {item.get('file_name', '') for item in data1}
    added_count = 0
    duplicate_count = 0
    
    for item in data2:
        file_name = item.get('file_name', '')
        if file_name not in existing_files:
            merged_data.append(item)
            existing_files.add(file_name)
            added_count += 1
        else:
            duplicate_count += 1
    
    print(f"📝 从文件2添加了 {added_count} 个新案件")
    print(f"⚠️ 跳过了 {duplicate_count} 个重复案件")
    
    # 生成输出文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"output/merged_results_{timestamp}.json"
    
    # 保存合并结果
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 合并完成！")
        print(f"📊 合并统计:")
        print(f"   文件1案件数: {len(data1)}")
        print(f"   文件2案件数: {len(data2)}")
        print(f"   合并后总数: {len(merged_data)}")
        print(f"   重复案件数: {duplicate_count}")
        print(f"💾 结果保存到: {output_file}")
        
    except Exception as e:
        print(f"❌ 保存失败: {e}")

if __name__ == "__main__":
    merge_json_files() 