#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单案件知识图谱系统 - 快速启动脚本
解决原系统的问题，使用端口8051
"""

import os
import sys
import subprocess

def print_banner():
    """打印启动横幅"""
    banner = """
    🕸️ 单案件知识图谱系统
    ==========================================
    ✨ 专注单案件的清晰图谱展示
    ✨ 修复了原系统的数据问题  
    ✨ 使用端口8051避免冲突
    ==========================================
    """
    print(banner)

def check_requirements():
    """检查依赖"""
    print("🔍 检查系统环境...")
    
    required_packages = ['dash', 'dash_cytoscape', 'pandas', 'plotly']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package} 未安装")
    
    if missing_packages:
        print(f"\n📦 安装缺失的包:")
        print(f"pip install {' '.join(missing_packages)}")
        if input("是否自动安装？(y/N): ").lower() == 'y':
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        else:
            return False
    
    return True

def find_data_file():
    """查找数据文件"""
    print("\n📁 查找数据文件...")
    
    possible_paths = [
        "output/llm_analysis_20250603_110724.json",
        "../output/llm_analysis_20250603_110724.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ 找到数据文件: {path}")
            return path
    
    print("❌ 未找到LLM分析数据文件")
    return None

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    if not check_requirements():
        print("\n❌ 环境检查失败，程序退出")
        return 1
    
    # 查找数据文件
    data_file = find_data_file()
    if not data_file:
        print("\n❌ 数据文件检查失败，程序退出")
        return 1
    
    # 启动系统
    print("\n🚀 启动单案件知识图谱系统...")
    print("🌐 访问地址: http://127.0.0.1:8051")
    print("📝 使用说明:")
    print("  1. 在'案件选择'tab中选择要分析的案件")
    print("  2. 点击'分析选中案件'按钮")
    print("  3. 自动跳转到'知识图谱'tab查看图谱")
    print("  4. 点击节点查看详细信息")
    print("  5. 使用左侧控制面板调整布局和关系显示")
    print("\n" + "="*50)
    
    try:
        # 直接运行单案件知识图谱
        from single_case_knowledge_graph import SingleCaseKnowledgeGraph
        kg = SingleCaseKnowledgeGraph(data_file)
        kg.run()
    except KeyboardInterrupt:
        print("\n👋 用户中断，程序退出")
    except Exception as e:
        print(f"\n❌ 启动失败: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 