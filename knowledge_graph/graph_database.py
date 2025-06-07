#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 图数据库处理模块
"""

from neo4j import GraphDatabase
from typing import Dict, List, Any, Optional
import logging
from .config import KnowledgeGraphConfig

class GraphDatabaseManager:
    """图数据库管理器"""
    
    def __init__(self):
        self.config = KnowledgeGraphConfig()
        self.driver = None
        self.logger = logging.getLogger(__name__)
        
    def connect(self) -> bool:
        """连接到Neo4j数据库"""
        try:
            self.driver = GraphDatabase.driver(
                self.config.NEO4J_URI,
                auth=(self.config.NEO4J_USER, self.config.NEO4J_PASSWORD)
            )
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info("✅ 成功连接到Neo4j数据库")
            return True
        except Exception as e:
            self.logger.error(f"❌ 连接Neo4j数据库失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.driver:
            self.driver.close()
            self.logger.info("🔒 Neo4j数据库连接已关闭")
    
    def clear_database(self) -> bool:
        """清空数据库（谨慎使用）"""
        try:
            with self.driver.session() as session:
                session.run("MATCH (n) DETACH DELETE n")
            self.logger.info("🗑️ 数据库已清空")
            return True
        except Exception as e:
            self.logger.error(f"❌ 清空数据库失败: {e}")
            return False
    
    def create_indexes(self):
        """创建索引以提高查询性能"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (c:Case) ON (c.case_number)",
            "CREATE INDEX IF NOT EXISTS FOR (p:Person) ON (p.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Court) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (l:Lawyer) ON (l.name)",
            "CREATE INDEX IF NOT EXISTS FOR (f:LawFirm) ON (f.name)",
            "CREATE INDEX IF NOT EXISTS FOR (d:LegalDocument) ON (d.type)",
        ]
        
        try:
            with self.driver.session() as session:
                for index_query in indexes:
                    session.run(index_query)
            self.logger.info("📊 数据库索引创建完成")
        except Exception as e:
            self.logger.error(f"❌ 创建索引失败: {e}")
    
    def create_node(self, label: str, properties: Dict[str, Any]) -> Optional[str]:
        """创建节点"""
        try:
            with self.driver.session() as session:
                # 处理不同节点类型的唯一标识
                if label == 'Case':
                    # Case节点使用case_number作为唯一标识
                    unique_key = properties.get('case_number')
                    if not unique_key or unique_key.strip() == '' or unique_key.lower() == 'unknown':
                        # 如果case_number为空，使用file_name作为备用
                        unique_key = properties.get('file_name', f'case_{hash(str(properties))}'[:16])
                    
                    query = f"""
                    MERGE (n:{label} {{case_number: $unique_key}})
                    SET n += $properties
                    RETURN elementId(n) as node_id
                    """
                    result = session.run(query, unique_key=unique_key, properties=properties)
                else:
                    # 其他节点使用name字段
                    unique_key = properties.get('name')
                    if not unique_key or unique_key.strip() == '' or unique_key.lower() == 'unknown':
                        # 如果name为空，跳过创建此节点
                        self.logger.warning(f"⚠️ 跳过创建{label}节点，name字段为空: {properties}")
                        return None
                    
                    query = f"""
                    MERGE (n:{label} {{name: $unique_key}})
                    SET n += $properties
                    RETURN elementId(n) as node_id
                    """
                    result = session.run(query, unique_key=unique_key, properties=properties)
                
                record = result.single()
                if record:
                    return record['node_id']
                    
        except Exception as e:
            self.logger.error(f"❌ 创建{label}节点失败: {e}")
            self.logger.error(f"节点属性: {properties}")
        return None
    
    def create_relationship(self, from_node_id: str, to_node_id: str, 
                          relationship_type: str, properties: Dict[str, Any] = None) -> bool:
        """创建关系"""
        try:
            with self.driver.session() as session:
                if properties:
                    query = f"""
                    MATCH (a), (b)
                    WHERE elementId(a) = $from_id AND elementId(b) = $to_id
                    MERGE (a)-[r:{relationship_type}]->(b)
                    SET r += $properties
                    """
                    session.run(query, from_id=from_node_id, to_id=to_node_id, properties=properties)
                else:
                    query = f"""
                    MATCH (a), (b)
                    WHERE elementId(a) = $from_id AND elementId(b) = $to_id
                    MERGE (a)-[:{relationship_type}]->(b)
                    """
                    session.run(query, from_id=from_node_id, to_id=to_node_id)
                return True
        except Exception as e:
            self.logger.error(f"❌ 创建关系失败: {e}")
        return False
    
    def query_nodes(self, label: str = None, properties: Dict[str, Any] = None, 
                   limit: int = 100) -> List[Dict[str, Any]]:
        """查询节点"""
        try:
            with self.driver.session() as session:
                if label and properties:
                    query = f"MATCH (n:{label}) WHERE "
                    where_conditions = [f"n.{key} = ${key}" for key in properties.keys()]
                    query += " AND ".join(where_conditions)
                    query += f" RETURN n LIMIT {limit}"
                    result = session.run(query, **properties)
                elif label:
                    query = f"MATCH (n:{label}) RETURN n LIMIT {limit}"
                    result = session.run(query)
                else:
                    query = f"MATCH (n) RETURN n LIMIT {limit}"
                    result = session.run(query)
                
                nodes = []
                for record in result:
                    node = record['n']
                    nodes.append({
                        'id': node.element_id,
                        'labels': list(node.labels),
                        'properties': dict(node)
                    })
                return nodes
        except Exception as e:
            self.logger.error(f"❌ 查询节点失败: {e}")
        return []
    
    def query_relationships(self, relationship_type: str = None, 
                          limit: int = 100) -> List[Dict[str, Any]]:
        """查询关系"""
        try:
            with self.driver.session() as session:
                if relationship_type:
                    query = f"""
                    MATCH (a)-[r:{relationship_type}]->(b)
                    RETURN elementId(a) as from_id, elementId(b) as to_id, 
                           type(r) as relationship, properties(r) as props
                    LIMIT {limit}
                    """
                else:
                    query = f"""
                    MATCH (a)-[r]->(b)
                    RETURN elementId(a) as from_id, elementId(b) as to_id, 
                           type(r) as relationship, properties(r) as props
                    LIMIT {limit}
                    """
                result = session.run(query)
                
                relationships = []
                for record in result:
                    relationships.append({
                        'from': record['from_id'],
                        'to': record['to_id'],
                        'type': record['relationship'],
                        'properties': record['props']
                    })
                return relationships
        except Exception as e:
            self.logger.error(f"❌ 查询关系失败: {e}")
        return []
    
    def get_node_statistics(self) -> Dict[str, int]:
        """获取节点统计信息"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (n)
                RETURN labels(n)[0] as label, count(*) as count
                ORDER BY count DESC
                """
                result = session.run(query)
                stats = {}
                for record in result:
                    stats[record['label']] = record['count']
                return stats
        except Exception as e:
            self.logger.error(f"❌ 获取统计信息失败: {e}")
        return {}
    
    def get_relationship_statistics(self) -> Dict[str, int]:
        """获取关系统计信息"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH ()-[r]->()
                RETURN type(r) as relationship, count(*) as count
                ORDER BY count DESC
                """
                result = session.run(query)
                stats = {}
                for record in result:
                    stats[record['relationship']] = record['count']
                return stats
        except Exception as e:
            self.logger.error(f"❌ 获取关系统计失败: {e}")
        return {}
    
    def find_similar_cases(self, case_id: str, similarity_threshold: float = 0.7) -> List[Dict[str, Any]]:
        """查找相似案件"""
        try:
            with self.driver.session() as session:
                query = """
                MATCH (c1:Case) WHERE elementId(c1) = $case_id
                MATCH (c2:Case) WHERE elementId(c2) <> $case_id
                WITH c1, c2,
                     CASE WHEN c1.case_type = c2.case_type THEN 0.4 ELSE 0 END +
                     CASE WHEN c1.court_name = c2.court_name THEN 0.2 ELSE 0 END +
                     CASE WHEN c1.judgment_result = c2.judgment_result THEN 0.2 ELSE 0 END +
                     CASE WHEN abs(toFloat(c1.claim_amount) - toFloat(c2.claim_amount)) < 1000000 THEN 0.2 ELSE 0 END
                     as similarity
                WHERE similarity >= $threshold
                RETURN c2, similarity
                ORDER BY similarity DESC
                LIMIT 10
                """
                result = session.run(query, case_id=case_id, threshold=similarity_threshold)
                
                similar_cases = []
                for record in result:
                    case = record['c2']
                    similar_cases.append({
                        'id': case.element_id,
                        'properties': dict(case),
                        'similarity': record['similarity']
                    })
                return similar_cases
        except Exception as e:
            self.logger.error(f"❌ 查找相似案件失败: {e}")
        return [] 