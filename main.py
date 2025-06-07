#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法庭文书信息提取器 - 主程序
Hong Kong Court Document Information Extractor - Main Program

使用方法:
    python main.py --input /path/to/HCA --output json
    python main.py --help

Author: AI Assistant
Version: 1.0
"""

import sys
import argparse
import os
from pathlib import Path

# 添加src目录到路径
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from processor import BatchProcessor
    from config import SUPPORTED_DOCUMENT_TYPES, OUTPUT_CONFIG
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有依赖已正确安装: pip install -r requirements.txt")
    sys.exit(1)

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='香港法庭文书信息提取器 - Hong Kong Court Document Information Extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 处理HCA文件夹下的所有PDF文件，输出所有格式
  python main.py --input ../HK/HCA --output all
  
  # 只输出JSON格式
  python main.py --input ../HK/HCA --output json
  
  # 指定自定义输出目录
  python main.py --input ../HK/HCA --output-dir custom_output --log-dir custom_logs
  
支持的文档类型: {}
支持的输出格式: {}
""".format(', '.join(SUPPORTED_DOCUMENT_TYPES), ', '.join(OUTPUT_CONFIG['formats']) + ', all')
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入目录路径 (包含PDF文件的目录)'
    )
    
    parser.add_argument(
        '--output', '-o',
        choices=['json', 'csv', 'excel', 'all'],
        default='all',
        help='输出格式 (默认: all)'
    )
    
    parser.add_argument(
        '--output-dir',
        default='output',
        help='输出目录 (默认: output)'
    )
    
    parser.add_argument(
        '--log-dir',
        default='logs',
        help='日志目录 (默认: logs)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出模式'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0'
    )
    
    return parser

def validate_input_directory(input_dir):
    """验证输入目录"""
    input_path = Path(input_dir)
    
    if not input_path.exists():
        print(f"错误: 输入目录不存在: {input_dir}")
        return False
    
    if not input_path.is_dir():
        print(f"错误: 指定路径不是目录: {input_dir}")
        return False
    
    # 检查是否有PDF文件
    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"警告: 在目录 {input_dir} 中未找到PDF文件")
        return True  # 允许继续，让处理器处理
    
    print(f"找到 {len(pdf_files)} 个PDF文件")
    return True

def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print(" 香港法庭文书信息提取器")
    print(" Hong Kong Court Document Information Extractor")
    print(" Version: 1.0")
    print("=" * 60)

def print_results_summary(summary):
    """打印处理结果摘要"""
    if not summary:
        print("\n❌ 处理失败，未生成任何结果")
        return
    
    print("\n📊 处理结果摘要:")
    print(f"  总处理文件数: {summary.get('total_files_processed', 0)}")
    
    # 语言分布
    lang_dist = summary.get('language_distribution', {})
    if lang_dist:
        print(f"  语言分布: {dict(lang_dist)}")
    
    # 字段完整性
    field_comp = summary.get('field_completeness', {})
    if field_comp:
        print("  字段完整性:")
        for field, stats in field_comp.items():
            percentage = stats.get('percentage', 0)
            print(f"    {field}: {percentage:.1f}% ({stats.get('complete', 0)}/{stats.get('complete', 0) + stats.get('missing', 0)})")
    
    # 输出文件
    saved_files = summary.get('saved_files', {})
    if saved_files:
        print("  输出文件:")
        for format_type, file_path in saved_files.items():
            file_name = Path(file_path).name
            print(f"    {format_type.upper()}: {file_name}")

def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 打印欢迎信息
    if args.verbose:
        print_welcome()
    
    # 验证输入目录
    if not validate_input_directory(args.input):
        sys.exit(1)
    
    try:
        # 创建处理器
        processor = BatchProcessor(
            output_dir=args.output_dir,
            log_dir=args.log_dir
        )
        
        # 运行处理
        print(f"\n🚀 开始处理目录: {args.input}")
        print(f"📁 输出目录: {args.output_dir}")
        print(f"📄 输出格式: {args.output}")
        
        summary = processor.run(
            input_dir=args.input,
            output_format=args.output
        )
        
        # 打印结果摘要
        if args.verbose:
            print_results_summary(summary)
        
        print("\n✅ 处理完成!")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断处理")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main() 