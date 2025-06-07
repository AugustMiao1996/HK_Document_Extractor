#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM分析启动脚本 - 完整提取+分析流程
"""

import os
import sys
import time
import json
from datetime import datetime

# 添加src路径
sys.path.append('src')

def main():
    """主函数 - 完整的提取和分析流程"""
    print("🚀 香港法庭文书智能分析系统")
    print("=" * 60)
    print("📋 功能: 分层提取 + LLM智能分析 + 律师信息分离")
    print("⚡ 性能: 优化版 (3-5x 速度提升)")
    print()
    
    # 步骤1：检查输入
    print("📂 步骤1: 检查输入数据")
    pdf_folder = "../HK/HCA"
    if not os.path.exists(pdf_folder):
        print(f"❌ PDF文件夹不存在: {pdf_folder}")
        return
    
    pdf_files = [f for f in os.listdir(pdf_folder) if f.endswith('.pdf')]
    if not pdf_files:
        print(f"❌ 未找到PDF文件在: {pdf_folder}")
        return
    
    print(f"✅ 找到 {len(pdf_files)} 个PDF文件")
    
    # 让用户选择处理范围
    print()
    print("🎯 选择处理范围:")
    print("  1. 测试模式 (前3个文件)")
    print("  2. 小批量 (前10个文件)")
    print("  3. 中批量 (前50个文件)")
    print("  4. 全部文件")
    
    while True:
        choice = input("\n请选择 (1-4): ").strip()
        if choice == '1':
            selected_files = pdf_files[:3]
            mode = "测试"
            break
        elif choice == '2':
            selected_files = pdf_files[:10]
            mode = "小批量"
            break
        elif choice == '3':
            selected_files = pdf_files[:50]
            mode = "中批量"
            break
        elif choice == '4':
            selected_files = pdf_files
            mode = "全部"
            break
        else:
            print("❌ 无效选择，请输入1-4")
    
    print(f"📊 将处理 {len(selected_files)} 个文件 ({mode}模式)")
    
    # 步骤2：分层提取
    print()
    print("📄 步骤2: 分层提取 (前3页基本信息 + 末尾律师段落)")
    
    from extractor import DocumentExtractor
    extractor = DocumentExtractor()
    
    extracted_cases = []
    start_time = time.time()
    
    for i, pdf_file in enumerate(selected_files):
        pdf_path = os.path.join(pdf_folder, pdf_file)
        print(f"   📄 [{i+1}/{len(selected_files)}] {pdf_file}", end=" ... ")
        
        try:
            # 提取文本和信息
            text = extractor.extract_pdf_text(pdf_path)
            if text:
                result = extractor.extract_information(text, pdf_file)
                result['file_name'] = pdf_file
                extracted_cases.append(result)
                print("✅")
            else:
                print("❌ 提取失败")
        except Exception as e:
            print(f"❌ 错误: {e}")
    
    extraction_time = time.time() - start_time
    print(f"⏱️  分层提取完成，用时: {extraction_time:.2f}秒")
    print(f"📊 成功提取: {len(extracted_cases)}/{len(selected_files)} 个文件")
    
    if not extracted_cases:
        print("❌ 没有成功提取的案件，程序结束")
        return
    
    # 保存分层提取结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    layered_output = f"output/layered_extraction_{timestamp}.json"
    
    os.makedirs("output", exist_ok=True)
    with open(layered_output, 'w', encoding='utf-8') as f:
        json.dump(extracted_cases, f, ensure_ascii=False, indent=2)
    
    print(f"💾 分层提取结果已保存: {layered_output}")
    
    # 步骤3：律师信息分析预览
    print()
    print("👨‍💼 步骤3: 律师信息分析预览")
    
    lawyer_available = 0
    for case in extracted_cases:
        lawyer_segment = case.get('lawyer', '')
        if lawyer_segment and len(lawyer_segment.strip()) > 10:
            lawyer_available += 1
    
    print(f"📊 律师信息段落统计:")
    print(f"   可用律师段落: {lawyer_available}/{len(extracted_cases)} ({lawyer_available/len(extracted_cases)*100:.1f}%)")
    
    # 显示示例
    if lawyer_available > 0:
        print(f"📝 律师段落示例:")
        for case in extracted_cases[:3]:
            lawyer_segment = case.get('lawyer', '')
            if lawyer_segment:
                case_num = case.get('case_number', 'Unknown')
                print(f"   🗂️  {case_num}:")
                print(f"      {lawyer_segment[:100]}...")
                break
    
    # 步骤4：选择LLM分析
    print()
    print("🤖 步骤4: LLM智能分析")
    print("   功能: 案件类型判断 + 判决结果分析 + 律师信息分离")
    
    while True:
        llm_choice = input("\n是否启动LLM分析? (y/n): ").strip().lower()
        if llm_choice in ['y', 'yes', '是']:
            run_llm = True
            break
        elif llm_choice in ['n', 'no', '否']:
            run_llm = False
            break
        else:
            print("❌ 请输入 y 或 n")
    
    if not run_llm:
        print("✅ 分层提取完成！结果保存在:", layered_output)
        return
    
    # 步骤5：LLM分析
    print()
    print("🧠 步骤5: 启动LLM分析...")
    
    from optimized_llm_processor import OptimizedLLMProcessor
    processor = OptimizedLLMProcessor()
    
    # LLM分析输出文件
    llm_output = f"output/llm_analysis_{timestamp}.json"
    
    print(f"📤 输入: {layered_output}")
    print(f"📥 输出: {llm_output}")
    print()
    
    # 直接调用processor的方法
    try:
        processor.process_batch(layered_output, llm_output, delay=2.0, batch_size=3)
        
        # 显示最终结果
        print()
        print("🎉 完整分析流程完成！")
        print("=" * 50)
        print(f"📂 分层提取结果: {layered_output}")
        print(f"🧠 LLM分析结果: {llm_output}")
        
        # 显示部分结果示例
        if os.path.exists(llm_output):
            with open(llm_output, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            print()
            print("📊 分析结果示例 (前3个):")
            for i, case in enumerate(results[:3]):
                print(f"\n🗂️  案件 {i+1}: {case.get('case_number', 'Unknown')}")
                print(f"   📋 案件类型: {case.get('case_type', 'unknown')}")
                print(f"   ⚖️  判决结果: {case.get('judgment_result', 'unknown')}")
                print(f"   👨‍💼 原告律师: {case.get('plaintiff_lawyer', 'unknown')}")
                print(f"   👩‍💼 被告律师: {case.get('defendant_lawyer', 'unknown')}")
        
    except Exception as e:
        print(f"❌ LLM分析失败: {e}")
        print(f"✅ 但分层提取结果已保存: {layered_output}")

def quick_test():
    """快速测试模式 - 只处理3个文件"""
    print("⚡ 快速测试模式")
    print("=" * 30)
    
    # 直接运行测试
    from extractor import DocumentExtractor
    extractor = DocumentExtractor()
    
    test_files = ['HCA000751_2022.pdf', 'HCA001002_2024.pdf', 'HCA001515A_2023.pdf']
    
    for pdf_file in test_files:
        pdf_path = f"../HK/HCA/{pdf_file}"
        if os.path.exists(pdf_path):
            print(f"\n📄 测试: {pdf_file}")
            
            try:
                text = extractor.extract_pdf_text(pdf_path)
                if text:
                    result = extractor.extract_information(text, pdf_file)
                    
                    print(f"   ✅ 案件编号: {result.get('case_number', 'N/A')}")
                    print(f"   👥 原告: {result.get('plaintiff', 'N/A')[:50]}...")
                    print(f"   👥 被告: {result.get('defendant', 'N/A')[:50]}...")
                    print(f"   👨‍⚖️ 法官: {result.get('judge', 'N/A')}")
                    
                    lawyer_segment = result.get('lawyer', '')
                    if lawyer_segment:
                        print(f"   👨‍💼 律师段落: {lawyer_segment[:80]}...")
                    else:
                        print(f"   👨‍💼 律师段落: 未找到")
                
            except Exception as e:
                print(f"   ❌ 错误: {e}")

if __name__ == "__main__":
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        quick_test()
    else:
        main() 