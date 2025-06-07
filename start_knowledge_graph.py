#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 一键启动脚本
简化版启动脚本，无需复杂参数配置
"""

import os
import sys
import subprocess
import time

def print_banner():
    """打印启动横幅"""
    banner = """
    [*] 香港法院文书知识图谱系统
    ==========================================
    [*] 一键启动脚本
    [*] 自动检测环境和数据
    [*] 智能初始化系统
    ==========================================
    """
    print(banner)

def check_requirements():
    """检查依赖"""
    print("[>] 检查系统环境...")
    
    # 检查Python版本
    if sys.version_info < (3, 8):
        print("[!] Python版本过低，需要3.8+")
        return False
    
    # 检查必要的包
    required_packages = ['neo4j', 'dash', 'dash_cytoscape', 'pandas', 'plotly']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"[+] {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"[!] {package} 未安装")
    
    if missing_packages:
        print(f"\n[>] 安装缺失的包:")
        print(f"pip install {' '.join(missing_packages)}")
        if input("是否自动安装？(y/N): ").lower() == 'y':
            subprocess.run([sys.executable, '-m', 'pip', 'install'] + missing_packages)
        else:
            return False
    
    return True

def check_neo4j():
    """检查Neo4j是否运行"""
    print("\n[>] 检查Neo4j数据库...")
    
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "password"))
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        print("[+] Neo4j连接成功")
        return True
    except Exception as e:
        print(f"[!] Neo4j连接失败: {e}")
        print("\n[i] 请确保：")
        print("1. Neo4j已安装并启动")
        print("2. 默认端口7687可用")
        print("3. 用户名：neo4j，密码：password")
        print("\n[>] 快速安装Neo4j：")
        print("- 访问 https://neo4j.com/download/")
        print("- 或使用Docker: docker run -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j")
        return False

def find_data_file():
    """查找数据文件"""
    print("\n[>] 查找数据文件...")
    
    possible_paths = [
        "output/llm_analysis_20250603_110724.json",
        "../output/llm_analysis_20250603_110724.json",
        "HK_Document_Extractor/output/llm_analysis_20250603_110724.json"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"[+] 找到数据文件: {path}")
            return path
    
    print("[!] 未找到LLM分析数据文件")
    print("请先运行LLM分析生成数据文件")
    return None

def main():
    """主函数"""
    print_banner()
    
    # 检查环境
    if not check_requirements():
        print("\n[!] 环境检查失败，程序退出")
        return 1
    
    # 检查Neo4j
    if not check_neo4j():
        print("\n[!] Neo4j检查失败，程序退出")
        return 1
    
    # 查找数据文件
    data_file = find_data_file()
    if not data_file:
        print("\n[!] 数据文件检查失败，程序退出")
        return 1
    
    # 启动主程序
    print("\n[>] 启动知识图谱系统...")
    print("请稍等，系统正在初始化...")
    
    try:
        # 运行主程序
        cmd = [sys.executable, "run_knowledge_graph.py", "--data-file", data_file]
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n[i] 用户中断，程序退出")
    except Exception as e:
        print(f"\n[!] 启动失败: {e}")
        return 1
    
    print("\n[+] 知识图谱系统已退出")
    return 0

if __name__ == "__main__":
    exit(main()) 