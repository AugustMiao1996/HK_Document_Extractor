#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
第二阶段：LLM智能分析

用法:
    python stage2_llm_analysis.py --input output/parallel_extraction_results_20250605_171021.json
    python stage2_llm_analysis.py --input output/parallel_extraction_results_20250605_171021.json --output custom_output.json
"""

import argparse
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加src路径
sys.path.append('src')

def stage2_llm_analysis(input_file: str, output_file: str = None):
    """第二阶段：LLM智能分析"""
    print("🧠 第二阶段：LLM智能分析")
    print(f"📥 输入文件: {input_file}")
    
    # 检查输入文件
    if not os.path.exists(input_file):
        print(f"❌ 错误：输入文件不存在: {input_file}")
        return False
    
    # 加载输入数据
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            cases = json.load(f)
        print(f"✅ 成功加载 {len(cases)} 个案件")
    except Exception as e:
        print(f"❌ 错误：无法加载输入文件: {e}")
        return False
    
    # 生成输出文件名
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"output/llm_analysis_{timestamp}.json"
    
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    print(f"📤 输出文件: {output_file}")
    print()
    
    # 导入LLM处理器
    try:
        from optimized_llm_processor import OptimizedLLMProcessor
        processor = OptimizedLLMProcessor()
        print("✅ LLM处理器初始化成功")
    except Exception as e:
        print(f"❌ 错误：无法初始化LLM处理器: {e}")
        return False
    
    # 启动LLM分析
    print("🚀 开始LLM分析...")
    try:
        # 使用processor处理
        processor.process_batch(input_file, output_file, delay=2.0, batch_size=3)
        
        print()
        print("🎉 第二阶段LLM分析完成！")
        print(f"📊 分析结果已保存到: {output_file}")
        
        # 显示简要统计
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # 统计分析结果
            total_cases = len(results)
            case_type_success = sum(1 for r in results if r.get('case_type', '').strip())
            judgment_success = sum(1 for r in results if r.get('judgment_result', '').strip())
            plaintiff_lawyer_success = sum(1 for r in results if r.get('plaintiff_lawyer', '').strip())
            defendant_lawyer_success = sum(1 for r in results if r.get('defendant_lawyer', '').strip())
            
            print()
            print("📈 分析结果统计:")
            print(f"   总案件数: {total_cases}")
            print(f"   案件类型分析成功: {case_type_success}/{total_cases} ({case_type_success/total_cases*100:.1f}%)")
            print(f"   判决结果分析成功: {judgment_success}/{total_cases} ({judgment_success/total_cases*100:.1f}%)")
            print(f"   原告律师提取成功: {plaintiff_lawyer_success}/{total_cases} ({plaintiff_lawyer_success/total_cases*100:.1f}%)")
            print(f"   被告律师提取成功: {defendant_lawyer_success}/{total_cases} ({defendant_lawyer_success/total_cases*100:.1f}%)")
            
            # 显示示例结果
            print()
            print("🔍 分析结果示例 (前3个):")
            for i, case in enumerate(results[:3]):
                print(f"\n  📋 案件 {i+1}: {case.get('case_number', 'Unknown')}")
                print(f"     文件: {case.get('file_name', 'Unknown')}")
                print(f"     案件类型: {case.get('case_type', 'unknown')[:80]}...")
                print(f"     判决结果: {case.get('judgment_result', 'unknown')[:80]}...")
                print(f"     原告律师: {case.get('plaintiff_lawyer', 'unknown')}")
                print(f"     被告律师: {case.get('defendant_lawyer', 'unknown')}")
        
        return True
        
    except Exception as e:
        print(f"❌ LLM分析失败: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description='第二阶段：LLM智能分析',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 分析stage1的输出结果
  python stage2_llm_analysis.py --input output/parallel_extraction_results_20250605_171021.json
  
  # 指定输出文件
  python stage2_llm_analysis.py --input output/parallel_extraction_results_20250605_171021.json --output my_llm_results.json
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='Stage1输出的JSON文件路径')
    parser.add_argument('--output', '-o', 
                       help='输出文件名（可选）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🤖 香港法院文书提取系统 - 第二阶段（LLM分析）")
    print("=" * 60)
    print("📋 功能: 案件类型分析 + 判决结果分析 + 律师信息分离")
    print("🧠 技术: OpenAI GPT模型智能分析")
    print()
    
    try:
        success = stage2_llm_analysis(args.input, args.output)
        
        if success:
            print()
            print("🎉 第二阶段LLM分析完成！")
            print("💡 下一步可以使用知识图谱可视化: python start_knowledge_graph.py")
        else:
            print()
            print("❌ 第二阶段LLM分析失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ 第二阶段分析失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 