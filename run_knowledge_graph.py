#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 主程序入口
运行这个脚本来启动完整的知识图谱系统
"""

import logging
import argparse
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from knowledge_graph import (
    GraphDatabaseManager, 
    DataImporter, 
    KnowledgeGraphVisualizer,
    KnowledgeGraphConfig
)

def setup_logging(level=logging.INFO):
    """设置日志"""
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('knowledge_graph.log', encoding='utf-8')
        ]
    )

def check_neo4j_connection(db_manager: GraphDatabaseManager) -> bool:
    """检查Neo4j连接"""
    print("🔍 检查Neo4j数据库连接...")
    if db_manager.connect():
        print("✅ Neo4j连接成功")
        return True
    else:
        print("❌ Neo4j连接失败")
        print("请确保：")
        print("1. Neo4j数据库已启动")
        print("2. 连接配置正确（URI、用户名、密码）")
        print("3. 防火墙允许连接")
        return False

def import_data(db_manager: GraphDatabaseManager, data_file: str, clear_existing: bool = False):
    """导入数据"""
    print(f"📊 开始数据导入流程...")
    
    if clear_existing:
        print("⚠️ 清空现有数据...")
        if input("确认清空数据库吗？(y/N): ").lower() == 'y':
            db_manager.clear_database()
        else:
            print("取消清空操作")
    
    # 创建索引
    print("📊 创建数据库索引...")
    db_manager.create_indexes()
    
    # 导入数据
    print(f"📁 导入数据文件: {data_file}")
    importer = DataImporter(db_manager)
    
    if importer.import_data(data_file):
        print("✅ 数据导入成功")
        
        # 显示统计信息
        stats = importer.get_import_statistics()
        print("\n📊 导入统计:")
        print(f"节点总数: {stats['total_nodes']}")
        print(f"关系总数: {stats['total_relationships']}")
        print("\n节点分布:")
        for node_type, count in stats['nodes'].items():
            print(f"  • {node_type}: {count}")
        print("\n关系分布:")
        for rel_type, count in stats['relationships'].items():
            print(f"  • {rel_type}: {count}")
        
        return True
    else:
        print("❌ 数据导入失败")
        return False

def start_visualizer(db_manager: GraphDatabaseManager):
    """启动可视化界面"""
    print("🎨 启动知识图谱可视化界面...")
    visualizer = KnowledgeGraphVisualizer(db_manager)
    visualizer.run()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='香港法院文书知识图谱系统')
    parser.add_argument('--mode', choices=['import', 'visualize', 'full'], 
                       default='full', help='运行模式')
    parser.add_argument('--data-file', type=str, 
                       default='output/llm_analysis_20250603_110724.json',
                       help='LLM分析结果数据文件路径')
    parser.add_argument('--clear-db', action='store_true', 
                       help='清空数据库后重新导入')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging(getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    
    print("🏛️ 香港法院文书知识图谱系统")
    print("=" * 50)
    
    # 检查数据文件
    if args.mode in ['import', 'full']:
        if not os.path.exists(args.data_file):
            print(f"❌ 数据文件不存在: {args.data_file}")
            print("请检查文件路径或先运行LLM分析")
            return 1
    
    # 初始化数据库管理器
    db_manager = GraphDatabaseManager()
    
    try:
        # 检查数据库连接
        if not check_neo4j_connection(db_manager):
            return 1
        
        # 根据模式执行不同操作
        if args.mode == 'import':
            # 仅导入数据
            if import_data(db_manager, args.data_file, args.clear_db):
                print("🎉 数据导入完成")
            else:
                return 1
                
        elif args.mode == 'visualize':
            # 仅启动可视化
            start_visualizer(db_manager)
            
        elif args.mode == 'full':
            # 完整流程：导入数据 + 启动可视化
            if import_data(db_manager, args.data_file, args.clear_db):
                print("\n" + "=" * 50)
                start_visualizer(db_manager)
            else:
                return 1
    
    except KeyboardInterrupt:
        print("\n👋 用户中断，程序退出")
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        return 1
    finally:
        db_manager.close()
    
    return 0

if __name__ == "__main__":
    exit(main()) 