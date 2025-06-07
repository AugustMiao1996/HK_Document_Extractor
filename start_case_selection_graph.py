#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动案件选择式知识图谱系统
"""

import os
import sys
from pathlib import Path

def main():
    """启动案件选择式知识图谱系统"""
    print("=" * 60)
    print("[*] 香港法院文书知识图谱 - 案件选择式系统")
    print("=" * 60)
    print()
    
    # 检查数据文件
    data_file = "output/result.json"
    if not Path(data_file).exists():
        print(f"[!] 数据文件不存在: {data_file}")
        print(f"[>] 请先运行 LLM 分析生成数据文件:")
        print(f"    python run_llm_analysis.py")
        return 1
    
    print(f"[+] 数据文件: {data_file}")
    print(f"[>] 启动系统...")
    print()
    
    try:
        # 导入并运行系统
        from case_selection_knowledge_graph import CaseSelectionKnowledgeGraph
        
        app = CaseSelectionKnowledgeGraph(data_file)
        app.run(debug=False)
        
    except ImportError as e:
        print(f"[!] 导入失败: {e}")
        print(f"[>] 请安装必要的依赖:")
        print(f"    pip install dash dash-cytoscape plotly pandas")
        return 1
    except KeyboardInterrupt:
        print("\n[i] 用户中断，程序退出")
        return 0
    except Exception as e:
        print(f"[!] 启动失败: {e}")
        return 1
    
    print("\n[+] 系统已退出")
    return 0

if __name__ == "__main__":
    exit(main()) 