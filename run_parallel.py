#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行处理启动脚本
Parallel Processing Launcher for Hong Kong Court Document Extractor

Author: AI Assistant
Version: 1.0
"""

import sys
import argparse
import time
from pathlib import Path

# 添加src目录到路径
current_dir = Path(__file__).parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

try:
    from parallel_processor import ParallelBatchProcessor
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保所有依赖已正确安装")
    sys.exit(1)

def create_parser():
    """创建命令行参数解析器"""
    parser = argparse.ArgumentParser(
        description='香港法庭文书信息提取器 - 并行版本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 并行处理示例:
  # 自动检测最佳进程数，处理HCA文件夹
  python run_parallel.py --input ../HK/HCA --output json
  
  # 指定使用4个进程
  python run_parallel.py --input ../HK/HCA --output all --workers 4
  
  # 处理500个文档
  python run_parallel.py --input ../POC500个文件 --output all --workers 6
  
⚡ 性能提升：预期可获得 3-6倍 速度提升！
"""
    )
    
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='输入目录路径 (包含PDF文件的目录)'
    )
    
    parser.add_argument(
        '--output', '-o',
        choices=['json', 'csv', 'excel', 'all'],
        default='json',
        help='输出格式 (默认: json)'
    )
    
    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help='并行进程数 (默认: 自动检测)'
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
        '--test', '-t',
        action='store_true',
        help='测试模式：只处理前10个文件'
    )
    
    parser.add_argument(
        '--benchmark', '-b',
        action='store_true',
        help='性能测试：对比串行vs并行处理速度'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出模式'
    )
    
    return parser

def print_welcome():
    """打印欢迎信息"""
    print("=" * 60)
    print(" 🚀 香港法庭文书信息提取器 - 并行版")
    print(" Hong Kong Court Document Extractor - Parallel Version")
    print(" Version: 1.0")
    print("=" * 60)

def run_benchmark(input_dir: str, args):
    """运行性能测试"""
    print("\n🔥 性能测试模式")
    print("对比串行处理 vs 并行处理速度...")
    
    # 获取前10个PDF文件用于测试
    from pathlib import Path
    pdf_files = list(Path(input_dir).glob("*.pdf"))[:10]
    
    if len(pdf_files) < 5:
        print("❌ 测试文件数量不足，至少需要5个PDF文件")
        return
    
    print(f"📊 使用 {len(pdf_files)} 个文件进行测试")
    
    # 1. 串行处理测试
    print("\n1️⃣ 串行处理测试...")
    from processor import BatchProcessor
    serial_processor = BatchProcessor(args.output_dir, args.log_dir)
    
    start_time = time.time()
    serial_results = []
    for pdf_file in pdf_files:
        from extractor import DocumentExtractor
        extractor = DocumentExtractor()
        result = extractor.process_pdf(str(pdf_file))
        if result:
            serial_results.append(result)
    serial_time = time.time() - start_time
    
    # 2. 并行处理测试
    print("\n2️⃣ 并行处理测试...")
    parallel_processor = ParallelBatchProcessor(
        args.output_dir, args.log_dir, args.workers
    )
    
    start_time = time.time()
    # 创建临时目录只包含测试文件
    import tempfile
    import shutil
    with tempfile.TemporaryDirectory() as temp_dir:
        for pdf_file in pdf_files:
            shutil.copy2(pdf_file, temp_dir)
        parallel_results = parallel_processor.process_directory_parallel(temp_dir)
    parallel_time = time.time() - start_time
    
    # 3. 结果对比
    print("\n📊 性能测试结果:")
    print(f"  串行处理: {serial_time:.2f} 秒 ({len(serial_results)} 个文件)")
    print(f"  并行处理: {parallel_time:.2f} 秒 ({len(parallel_results)} 个文件)")
    
    if parallel_time > 0:
        speedup = serial_time / parallel_time
        print(f"  🚀 性能提升: {speedup:.1f}x 倍")
        
        if speedup > 1.5:
            print("  ✅ 并行处理效果显著！")
        elif speedup > 1.1:
            print("  ⚠️ 并行处理有一定提升")
        else:
            print("  ❌ 并行处理提升不明显，可能由于文件过小或I/O瓶颈")

def main():
    """主函数"""
    parser = create_parser()
    args = parser.parse_args()
    
    # 打印欢迎信息
    if args.verbose:
        print_welcome()
    
    # 验证输入目录
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ 错误: 输入目录不存在: {args.input}")
        sys.exit(1)
    
    if not input_path.is_dir():
        print(f"❌ 错误: 指定路径不是目录: {args.input}")
        sys.exit(1)
    
    # 检查PDF文件
    pdf_files = list(input_path.glob("*.pdf"))
    if not pdf_files:
        print(f"⚠️ 警告: 在目录 {args.input} 中未找到PDF文件")
        return
    
    print(f"📁 找到 {len(pdf_files)} 个PDF文件")
    
    # 性能测试模式
    if args.benchmark:
        run_benchmark(args.input, args)
        return
    
    # 测试模式：只处理前10个文件
    if args.test:
        print("🧪 测试模式：只处理前10个文件")
        import tempfile
        import shutil
        temp_dir = tempfile.mkdtemp()
        for pdf_file in pdf_files[:10]:
            shutil.copy2(pdf_file, temp_dir)
        args.input = temp_dir
    
    try:
        # 创建并行处理器
        processor = ParallelBatchProcessor(
            output_dir=args.output_dir,
            log_dir=args.log_dir,
            max_workers=args.workers
        )
        
        # 运行并行处理
        print(f"\n🚀 开始并行处理目录: {args.input}")
        print(f"📁 输出目录: {args.output_dir}")
        print(f"📄 输出格式: {args.output}")
        print(f"⚡ 进程数: {processor.max_workers}")
        
        summary = processor.run(
            input_dir=args.input,
            output_format=args.output
        )
        
        # 打印结果摘要
        if summary and args.verbose:
            print("\n📊 处理结果摘要:")
            print(f"  总处理文件数: {summary.get('total_files_processed', 0)}")
            print(f"  使用进程数: {summary.get('max_workers', 0)}")
            
            # 语言分布
            lang_dist = summary.get('language_distribution', {})
            if lang_dist:
                print(f"  语言分布: {dict(lang_dist)}")
            
            # 输出文件
            saved_files = summary.get('saved_files', {})
            if saved_files:
                print("  输出文件:")
                for format_type, file_path in saved_files.items():
                    file_name = Path(file_path).name
                    print(f"    {format_type.upper()}: {file_name}")
        
        print("\n✅ 并行处理完成!")
        
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