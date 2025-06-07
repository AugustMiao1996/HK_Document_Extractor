#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 数据导入模块
"""

import json
import re
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
import logging
from .graph_database import GraphDatabaseManager
from .config import KnowledgeGraphConfig

@dataclass
class EntityInfo:
    """实体信息类"""
    name: str
    entity_type: str
    properties: Dict[str, Any]

class DataImporter:
    """数据导入器"""
    
    def __init__(self, db_manager: GraphDatabaseManager):
        self.db = db_manager
        self.config = KnowledgeGraphConfig()
        self.logger = logging.getLogger(__name__)
        self.entity_cache = {}  # 缓存已创建的实体
        
    def load_llm_analysis_data(self, file_path: str) -> List[Dict[str, Any]]:
        """加载LLM分析结果数据"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.logger.info(f"📁 成功加载 {len(data)} 条案件数据")
            return data
        except Exception as e:
            self.logger.error(f"❌ 加载数据失败: {e}")
            return []
    
    def parse_multiple_parties(self, party_string: str) -> List[str]:
        """解析多方当事人字符串"""
        if not party_string or party_string.strip() == "":
            return []
        
        # 处理多个当事人的分隔符
        parties = []
        
        # 使用 | 分隔符分割
        if '|' in party_string:
            raw_parties = party_string.split('|')
        else:
            raw_parties = [party_string]
        
        for party in raw_parties:
            party = party.strip()
            if party:
                # 移除序号和角色描述
                party = re.sub(r'^\d+st\s+', '', party)
                party = re.sub(r'^\d+nd\s+', '', party)
                party = re.sub(r'^\d+rd\s+', '', party)
                party = re.sub(r'^\d+th\s+', '', party)
                party = re.sub(r'\s*\([^)]*\)\s*', '', party)  # 移除括号内容
                party = re.sub(r'\s*(Plaintiff|Defendant|plaintiff|defendant)\s*', '', party)
                party = party.strip()
                
                if party and len(party) > 1:
                    parties.append(party)
        
        return parties
    
    def parse_lawyer_segment(self, lawyer_segment: str) -> Tuple[List[str], List[str], List[str]]:
        """解析律师段落，提取律师和律师事务所信息"""
        lawyers = []
        law_firms = []
        relationships = []
        
        if not lawyer_segment:
            return lawyers, law_firms, relationships
        
        # 分割不同的律师表述
        segments = re.split(r'\|', lawyer_segment)
        
        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue
            
            # 提取律师姓名 (Mr/Ms/Miss + 姓名)
            lawyer_pattern = r'(Mr|Ms|Miss)\s+([A-Za-z\s]+?)(?=,|\s+instructed|\s+of|\s+for|$)'
            lawyer_matches = re.findall(lawyer_pattern, segment)
            
            for title, name in lawyer_matches:
                full_name = f"{title} {name}".strip()
                if full_name not in lawyers:
                    lawyers.append(full_name)
            
            # 提取律师事务所名称
            firm_patterns = [
                r'instructed by ([^,]+?)(?=,|for|$)',
                r'of ([^,]+?)(?=,|for|$)',
                r'\(([^)]+)\)',
            ]
            
            for pattern in firm_patterns:
                firm_matches = re.findall(pattern, segment)
                for firm in firm_matches:
                    firm = firm.strip()
                    if firm and len(firm) > 3 and firm not in law_firms:
                        law_firms.append(firm)
        
        return lawyers, law_firms, relationships
    
    def extract_entities_from_case(self, case_data: Dict[str, Any]) -> List[EntityInfo]:
        """从案件数据中提取所有实体"""
        entities = []
        
        # 数据清理函数
        def clean_field(value, default=''):
            if not value or str(value).strip() == '' or str(value).lower() == 'unknown':
                return default
            return str(value).strip()
        
        # 1. 案件实体 - 确保有有效的标识符
        case_number = clean_field(case_data.get('case_number'))
        file_name = clean_field(case_data.get('file_name'))
        
        # 确保至少有一个有效标识符
        if not case_number and not file_name:
            case_number = f"case_{hash(str(case_data))}"[:16]
        elif not case_number:
            case_number = file_name
        
        case_entity = EntityInfo(
            name=case_number,  # 使用清理后的case_number作为name
            entity_type='Case',
            properties={
                'case_number': case_number,
                'file_name': file_name or case_number,
                'trial_date': clean_field(case_data.get('trial_date')),
                'case_type': clean_field(case_data.get('case_type')),
                'case_type_cn': self.config.CASE_TYPES.get(case_data.get('case_type', ''), ''),
                'judgment_result': clean_field(case_data.get('judgment_result')),
                'judgment_result_cn': self.config.JUDGMENT_RESULTS.get(case_data.get('judgment_result', ''), ''),
                'claim_amount': clean_field(case_data.get('claim_amount')),
                'judgment_amount': clean_field(case_data.get('judgment_amount')),
                'language': clean_field(case_data.get('language')),
                'document_type': clean_field(case_data.get('document_type')),
                'court_name': clean_field(case_data.get('court_name')),
                'judge': clean_field(case_data.get('judge')),
                'plaintiff': clean_field(case_data.get('plaintiff')),
                'defendant': clean_field(case_data.get('defendant')),
            }
        )
        entities.append(case_entity)
        
        # 2. 法院实体
        court_name = clean_field(case_data.get('court_name'))
        if court_name:
            court_entity = EntityInfo(
                name=court_name,
                entity_type='Court',
                properties={
                    'name': court_name,
                    'type': 'court'
                }
            )
            entities.append(court_entity)
        
        # 3. 法官实体
        judge_name = clean_field(case_data.get('judge'))
        if judge_name:
            judge_entity = EntityInfo(
                name=judge_name,
                entity_type='Judge',
                properties={
                    'name': judge_name,
                    'role': 'judge'
                }
            )
            entities.append(judge_entity)
        
        # 4. 原告实体
        plaintiffs = self.parse_multiple_parties(case_data.get('plaintiff', ''))
        for plaintiff in plaintiffs:
            plaintiff_entity = EntityInfo(
                name=plaintiff,
                entity_type='Plaintiff',
                properties={
                    'name': plaintiff,
                    'role': 'plaintiff'
                }
            )
            entities.append(plaintiff_entity)
        
        # 5. 被告实体
        defendants = self.parse_multiple_parties(case_data.get('defendant', ''))
        for defendant in defendants:
            defendant_entity = EntityInfo(
                name=defendant,
                entity_type='Defendant',
                properties={
                    'name': defendant,
                    'role': 'defendant'
                }
            )
            entities.append(defendant_entity)
        
        # 6. 律师和律师事务所实体
        lawyer_segment = case_data.get('lawyer_segment', '')
        lawyers, law_firms, _ = self.parse_lawyer_segment(lawyer_segment)
        
        for lawyer in lawyers:
            lawyer_entity = EntityInfo(
                name=lawyer,
                entity_type='Lawyer',
                properties={
                    'name': lawyer,
                    'role': 'lawyer'
                }
            )
            entities.append(lawyer_entity)
        
        for firm in law_firms:
            firm_entity = EntityInfo(
                name=firm,
                entity_type='LawFirm',
                properties={
                    'name': firm,
                    'type': 'law_firm'
                }
            )
            entities.append(firm_entity)
        
        return entities
    
    def create_entity_node(self, entity: EntityInfo) -> str:
        """创建实体节点并返回节点ID"""
        # 检查缓存
        cache_key = f"{entity.entity_type}:{entity.name}"
        if cache_key in self.entity_cache:
            return self.entity_cache[cache_key]
        
        # 创建节点
        node_id = self.db.create_node(entity.entity_type, entity.properties)
        if node_id:
            self.entity_cache[cache_key] = node_id
        
        return node_id
    
    def create_relationships_for_case(self, case_data: Dict[str, Any], case_node_id: str):
        """为案件创建所有关系"""
        
        # 获取相关实体的节点ID
        def get_entity_node_id(entity_type: str, name: str) -> str:
            cache_key = f"{entity_type}:{name}"
            return self.entity_cache.get(cache_key)
        
        # 1. 案件 - 法院关系
        court_name = case_data.get('court_name', '')
        if court_name:
            court_node_id = get_entity_node_id('Court', court_name)
            if court_node_id:
                self.db.create_relationship(case_node_id, court_node_id, 'HEARD_IN')
        
        # 2. 案件 - 法官关系
        judge_name = case_data.get('judge', '')
        if judge_name:
            judge_node_id = get_entity_node_id('Judge', judge_name)
            if judge_node_id:
                self.db.create_relationship(case_node_id, judge_node_id, 'JUDGED_BY')
        
        # 3. 案件 - 原告关系
        plaintiffs = self.parse_multiple_parties(case_data.get('plaintiff', ''))
        for plaintiff in plaintiffs:
            plaintiff_node_id = get_entity_node_id('Plaintiff', plaintiff)
            if plaintiff_node_id:
                self.db.create_relationship(case_node_id, plaintiff_node_id, 'INVOLVES_PLAINTIFF')
        
        # 4. 案件 - 被告关系
        defendants = self.parse_multiple_parties(case_data.get('defendant', ''))
        for defendant in defendants:
            defendant_node_id = get_entity_node_id('Defendant', defendant)
            if defendant_node_id:
                self.db.create_relationship(case_node_id, defendant_node_id, 'INVOLVES_DEFENDANT')
        
        # 5. 原告起诉被告关系
        for plaintiff in plaintiffs:
            plaintiff_node_id = get_entity_node_id('Plaintiff', plaintiff)
            if plaintiff_node_id:
                for defendant in defendants:
                    defendant_node_id = get_entity_node_id('Defendant', defendant)
                    if defendant_node_id:
                        self.db.create_relationship(plaintiff_node_id, defendant_node_id, 'SUES')
        
        # 6. 律师代理关系
        plaintiff_lawyer = case_data.get('plaintiff_lawyer', '')
        defendant_lawyer = case_data.get('defendant_lawyer', '')
        
        # 解析律师段落获取更详细的代理关系
        lawyer_segment = case_data.get('lawyer_segment', '')
        lawyers, law_firms, _ = self.parse_lawyer_segment(lawyer_segment)
        
        # 创建律师和律师事务所的关系
        for lawyer in lawyers:
            lawyer_node_id = get_entity_node_id('Lawyer', lawyer)
            if lawyer_node_id:
                # 简单的代理关系创建（可以后续优化具体代理哪一方）
                for plaintiff in plaintiffs:
                    plaintiff_node_id = get_entity_node_id('Plaintiff', plaintiff)
                    if plaintiff_node_id and 'plaintiff' in lawyer_segment.lower():
                        self.db.create_relationship(lawyer_node_id, plaintiff_node_id, 'REPRESENTED_BY')
                
                for defendant in defendants:
                    defendant_node_id = get_entity_node_id('Defendant', defendant)
                    if defendant_node_id and 'defendant' in lawyer_segment.lower():
                        self.db.create_relationship(lawyer_node_id, defendant_node_id, 'REPRESENTED_BY')
                
                # 律师与律师事务所关系
                for firm in law_firms:
                    firm_node_id = get_entity_node_id('LawFirm', firm)
                    if firm_node_id:
                        self.db.create_relationship(lawyer_node_id, firm_node_id, 'WORKS_FOR')
    
    def import_data(self, data_file_path: str) -> bool:
        """导入数据到图数据库"""
        try:
            # 加载数据
            cases_data = self.load_llm_analysis_data(data_file_path)
            if not cases_data:
                return False
            
            total_cases = len(cases_data)
            self.logger.info(f"🚀 开始导入 {total_cases} 个案件到知识图谱")
            
            # 分批处理
            batch_size = 50
            for i in range(0, total_cases, batch_size):
                batch = cases_data[i:i+batch_size]
                
                self.logger.info(f"📦 处理批次 {i//batch_size + 1}: 案件 {i+1}-{min(i+batch_size, total_cases)}")
                
                # 第一轮：创建所有实体节点
                all_entities = []
                for case_data in batch:
                    entities = self.extract_entities_from_case(case_data)
                    all_entities.extend(entities)
                
                # 去重并创建节点
                unique_entities = {}
                for entity in all_entities:
                    key = f"{entity.entity_type}:{entity.name}"
                    if key not in unique_entities:
                        unique_entities[key] = entity
                
                for entity in unique_entities.values():
                    self.create_entity_node(entity)
                
                # 第二轮：创建关系
                for case_data in batch:
                    case_number = case_data.get('case_number', 'Unknown')
                    case_node_id = self.entity_cache.get(f"Case:{case_number}")
                    if case_node_id:
                        self.create_relationships_for_case(case_data, case_node_id)
                
                self.logger.info(f"✅ 批次 {i//batch_size + 1} 处理完成")
            
            self.logger.info(f"🎉 数据导入完成！共处理 {total_cases} 个案件")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ 数据导入失败: {e}")
            return False
    
    def get_import_statistics(self) -> Dict[str, Any]:
        """获取导入统计信息"""
        node_stats = self.db.get_node_statistics()
        relationship_stats = self.db.get_relationship_statistics()
        
        return {
            'nodes': node_stats,
            'relationships': relationship_stats,
            'total_nodes': sum(node_stats.values()),
            'total_relationships': sum(relationship_stats.values()),
            'cached_entities': len(self.entity_cache)
        } 