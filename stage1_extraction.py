#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
第一阶段：纯粹的文档信息提取 (无LLM)

用法:
    python stage1_extraction.py --input /path/to/documents --output results.json
    python stage1_extraction.py --input /path/to/documents --parallel  # 并行处理
"""

import argparse
import sys
import os
from pathlib import Path

# 添加src路径
sys.path.append('src')

def stage1_single_thread(input_path: str, output_file: str = None):
    """第一阶段：单线程处理"""
    print("🔄 第一阶段：单线程文档提取（无LLM）")
    print(f"📁 输入目录: {input_path}")
    
    # 导入并调用main.py的逻辑
    from main import main as main_extract
    
    # 构建命令行参数
    args = ['--input', input_path, '--output', 'json']
    if output_file:
        args.extend(['--output-file', output_file])
    
    # 模拟命令行调用
    import sys
    old_argv = sys.argv
    sys.argv = ['main.py'] + args
    
    try:
        main_extract()
        print("✅ 第一阶段提取完成！")
    finally:
        sys.argv = old_argv

def stage1_parallel(input_path: str, output_file: str = None):
    """第一阶段：并行处理"""
    print("🚀 第一阶段：并行文档提取（无LLM）")
    print(f"📁 输入目录: {input_path}")
    
    # 导入并调用run_parallel.py的逻辑
    from run_parallel import main as parallel_main
    
    # 构建命令行参数
    args = ['--input', input_path, '--output', 'json']
    if output_file:
        args.extend(['--output-file', output_file])
    
    # 模拟命令行调用
    import sys
    old_argv = sys.argv
    sys.argv = ['run_parallel.py'] + args
    
    try:
        parallel_main()
        print("✅ 第一阶段并行提取完成！")
    finally:
        sys.argv = old_argv

def main():
    parser = argparse.ArgumentParser(
        description='第一阶段：纯粹的文档信息提取（无LLM）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 单线程处理
  python stage1_extraction.py --input C:/Documents/HCA
  
  # 并行处理（推荐）
  python stage1_extraction.py --input C:/Documents/HCA --parallel
  
  # 指定输出文件
  python stage1_extraction.py --input C:/Documents/DCCJ --output my_results.json
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='输入文档目录路径')
    parser.add_argument('--output', '-o', 
                       help='输出文件名（可选）')
    parser.add_argument('--parallel', '-p', action='store_true',
                       help='使用并行处理（推荐）')
    
    args = parser.parse_args()
    
    # 验证输入目录
    if not os.path.exists(args.input):
        print(f"❌ 错误：输入目录不存在: {args.input}")
        sys.exit(1)
    
    print("=" * 60)
    print("🎯 香港法院文书提取系统 - 第一阶段")
    print("=" * 60)
    print("📋 功能: 纯粹的信息提取（基于规则，无LLM）")
    print("🔍 支持: HCA (ACTION格式) 和 DCCJ (CIVIL格式)")
    print()
    
    try:
        if args.parallel:
            stage1_parallel(args.input, args.output)
        else:
            stage1_single_thread(args.input, args.output)
            
        print()
        print("🎉 第一阶段提取完成！")
        print("💡 如需LLM智能分析，请使用: python stage2_llm_analysis.py")
        
    except Exception as e:
        print(f"❌ 第一阶段提取失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 