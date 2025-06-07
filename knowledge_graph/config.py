#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 配置文件
"""

import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

class KnowledgeGraphConfig:
    """知识图谱配置类"""
    
    # Neo4j 数据库配置
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')
    
    # 数据文件路径
    LLM_ANALYSIS_PATH = os.path.join(os.path.dirname(__file__), '..', 'output')
    
    # Web界面配置
    WEB_HOST = '127.0.0.1'
    WEB_PORT = 8050
    WEB_DEBUG = True
    
    # 节点颜色配置
    NODE_COLORS = {
        'Case': '#1f77b4',           # 蓝色 - 案件
        'Person': '#ff7f0e',         # 橙色 - 人员
        'Plaintiff': '#2ca02c',      # 绿色 - 原告
        'Defendant': '#d62728',      # 红色 - 被告
        'Judge': '#9467bd',          # 紫色 - 法官
        'Lawyer': '#8c564b',         # 棕色 - 律师
        'LawFirm': '#e377c2',        # 粉色 - 律师事务所
        'Court': '#7f7f7f',          # 灰色 - 法院
        'LegalDocument': '#bcbd22',  # 黄绿色 - 法律文书
    }
    
    # 关系类型配置
    RELATIONSHIP_TYPES = {
        'SUES': '起诉',
        'INVOLVES_PLAINTIFF': '涉及原告',
        'INVOLVES_DEFENDANT': '涉及被告',
        'JUDGED_BY': '由...审理',
        'HEARD_IN': '在...法院审理',
        'REPRESENTED_BY': '由...代理',
        'WORKS_FOR': '受雇于',
        'SIMILAR_TO': '相似案件',
        'CITES': '引用',
        'RELATED_TO': '相关',
    }
    
    # 案件类型映射
    CASE_TYPES = {
        'Trust Dispute': '信托纠纷',
        'Commercial Dispute': '商业纠纷',
        'Debt Recovery': '债务追讨',
        'Contract Dispute': '合同纠纷',
        'Civil Action': '民事诉讼',
        'Appeal': '上诉',
        'Mareva Injunction Discharge Application': '马瑞华禁制令撤销申请',
        'Setting Aside Application': '撤销申请',
        'Amendment Application': '修正申请',
        'Miscellaneous Proceedings': '杂项法律程序',
    }
    
    # 判决结果映射
    JUDGMENT_RESULTS = {
        'Win': '胜诉',
        'Lose': '败诉',
        'Appeal Dismissed': '上诉被驳回',
        'Plaintiff Withdrawn': '原告撤诉',
        'unknown': '未知',
    } 