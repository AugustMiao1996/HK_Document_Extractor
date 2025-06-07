#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 可视化模块
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context
import dash_cytoscape as cyto
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
import json
from .graph_database import GraphDatabaseManager
from .config import KnowledgeGraphConfig

class KnowledgeGraphVisualizer:
    """知识图谱可视化器"""
    
    def __init__(self, db_manager: GraphDatabaseManager):
        self.db = db_manager
        self.config = KnowledgeGraphConfig()
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.logger = logging.getLogger(__name__)
        
        # 加载Cytoscape样式
        cyto.load_extra_layouts()
        
        self.setup_layout()
        self.setup_callbacks()
    
    def setup_layout(self):
        """设置应用布局"""
        self.app.layout = html.Div([
            # 标题栏
            html.Div([
                html.H1("🏛️ 香港法院文书知识图谱", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '0px'}),
                html.P("Hong Kong Court Documents Knowledge Graph", 
                      style={'textAlign': 'center', 'color': '#7f8c8d', 'marginTop': '5px'})
            ], style={'marginBottom': '20px'}),
            
            # 控制面板
            html.Div([
                html.Div([
                    # 搜索区域
                    html.H4("🔍 搜索"),
                    dcc.Input(
                        id='search-input',
                        type='text',
                        placeholder='搜索案件号、当事人姓名、律师...',
                        style={'width': '100%', 'marginBottom': '10px'}
                    ),
                    html.Button('搜索', id='search-button', n_clicks=0, 
                               style={'width': '100%', 'marginBottom': '15px'}),
                    
                    # 筛选区域
                    html.H4("🎛️ 筛选"),
                    html.Label("案件类型:"),
                    dcc.Dropdown(
                        id='case-type-filter',
                        options=[{'label': v, 'value': k} for k, v in self.config.CASE_TYPES.items()],
                        placeholder="选择案件类型",
                        style={'marginBottom': '10px'}
                    ),
                    html.Label("判决结果:"),
                    dcc.Dropdown(
                        id='judgment-filter',
                        options=[{'label': v, 'value': k} for k, v in self.config.JUDGMENT_RESULTS.items()],
                        placeholder="选择判决结果",
                        style={'marginBottom': '10px'}
                    ),
                    html.Label("节点类型:"),
                    dcc.Dropdown(
                        id='node-type-filter',
                        options=[
                            {'label': '案件', 'value': 'Case'},
                            {'label': '原告', 'value': 'Plaintiff'},
                            {'label': '被告', 'value': 'Defendant'},
                            {'label': '法官', 'value': 'Judge'},
                            {'label': '律师', 'value': 'Lawyer'},
                            {'label': '律师事务所', 'value': 'LawFirm'},
                            {'label': '法院', 'value': 'Court'},
                        ],
                        placeholder="选择节点类型",
                        style={'marginBottom': '10px'}
                    ),
                    html.Button('应用筛选', id='filter-button', n_clicks=0, 
                               style={'width': '100%', 'marginBottom': '15px'}),
                    html.Button('重置', id='reset-button', n_clicks=0, 
                               style={'width': '100%', 'marginBottom': '15px'}),
                    
                    # 布局控制
                    html.H4("📐 布局"),
                    dcc.Dropdown(
                        id='layout-dropdown',
                        options=[
                            {'label': '力导向布局', 'value': 'cose'},
                            {'label': '分层布局', 'value': 'dagre'},
                            {'label': '圆形布局', 'value': 'circle'},
                            {'label': '网格布局', 'value': 'grid'},
                            {'label': '随机布局', 'value': 'random'},
                        ],
                        value='cose',
                        style={'marginBottom': '15px'}
                    ),
                    
                    # 统计信息
                    html.H4("📊 统计"),
                    html.Div(id='statistics-display')
                    
                ], style={'width': '25%', 'padding': '20px', 'backgroundColor': '#f8f9fa', 
                         'height': '100vh', 'overflowY': 'auto', 'float': 'left'}),
                
                # 主图谱区域
                html.Div([
                    cyto.Cytoscape(
                        id='knowledge-graph',
                        layout={'name': 'cose', 'nodeSpacing': 100, 'edgeElasticity': 100},
                        style={'width': '100%', 'height': '80vh'},
                        elements=[],
                        stylesheet=[
                            # 节点样式
                            {
                                'selector': 'node',
                                'style': {
                                    'content': 'data(label)',
                                    'text-valign': 'center',
                                    'text-halign': 'center',
                                    'background-color': 'data(color)',
                                    'width': 'data(size)',
                                    'height': 'data(size)',
                                    'font-size': '12px',
                                    'font-family': 'Arial',
                                    'border-width': 2,
                                    'border-color': '#2c3e50',
                                    'border-opacity': 0.8,
                                }
                            },
                            # 选中节点样式
                            {
                                'selector': 'node:selected',
                                'style': {
                                    'border-width': 4,
                                    'border-color': '#e74c3c',
                                    'background-color': '#ecf0f1'
                                }
                            },
                            # 边样式
                            {
                                'selector': 'edge',
                                'style': {
                                    'curve-style': 'bezier',
                                    'target-arrow-shape': 'triangle',
                                    'target-arrow-color': '#7f8c8d',
                                    'line-color': '#7f8c8d',
                                    'width': 2,
                                    'font-size': '10px',
                                    'content': 'data(label)',
                                    'text-rotation': 'autorotate',
                                    'text-margin-y': -10,
                                }
                            },
                        ]
                    ),
                    
                    # 详情面板
                    html.Div(id='detail-panel', 
                            style={'marginTop': '20px', 'padding': '15px', 
                                  'backgroundColor': '#ecf0f1', 'borderRadius': '5px'})
                    
                ], style={'width': '75%', 'padding': '20px', 'float': 'right'})
            ])
        ])
    
    def get_graph_data(self, case_type: str = None, judgment_result: str = None, 
                      node_type: str = None, search_term: str = None, limit: int = 200) -> Dict[str, List]:
        """获取图数据"""
        try:
            # 构建查询条件
            query_conditions = []
            params = {}
            
            if case_type:
                query_conditions.append("c.case_type = $case_type")
                params['case_type'] = case_type
            
            if judgment_result:
                query_conditions.append("c.judgment_result = $judgment_result")
                params['judgment_result'] = judgment_result
            
            if search_term:
                query_conditions.append(
                    "(c.case_number CONTAINS $search_term OR "
                    "c.file_name CONTAINS $search_term OR "
                    "any(prop in keys(c) WHERE toString(c[prop]) CONTAINS $search_term))"
                )
                params['search_term'] = search_term
            
            # 构建节点查询
            if node_type:
                node_query = f"""
                MATCH (n:{node_type})
                RETURN elementId(n) as id, labels(n) as labels, properties(n) as props
                LIMIT {limit}
                """
            else:
                where_clause = ""
                if query_conditions:
                    where_clause = "WHERE " + " AND ".join(query_conditions)
                
                node_query = f"""
                MATCH (n)
                OPTIONAL MATCH (c:Case)
                {where_clause}
                RETURN DISTINCT elementId(n) as id, labels(n) as labels, properties(n) as props
                LIMIT {limit}
                """
            
            # 执行节点查询
            with self.db.driver.session() as session:
                node_result = session.run(node_query, **params)
                nodes = []
                node_ids = set()
                
                for record in node_result:
                    node_id = record['id']
                    node_labels = record['labels']
                    node_props = record['props']
                    
                    if node_id not in node_ids:
                        node_ids.add(node_id)
                        
                        # 确定节点标签和颜色
                        primary_label = node_labels[0] if node_labels else 'Unknown'
                        color = self.config.NODE_COLORS.get(primary_label, '#95a5a6')
                        
                        # 确定节点大小
                        size = 30
                        if primary_label == 'Case':
                            size = 50
                        elif primary_label in ['Judge', 'Court']:
                            size = 40
                        elif primary_label in ['Lawyer', 'LawFirm']:
                            size = 35
                        
                        # 节点标签
                        label = node_props.get('name', node_props.get('case_number', 'Unknown'))
                        if len(label) > 20:
                            label = label[:17] + "..."
                        
                        nodes.append({
                            'data': {
                                'id': node_id,
                                'label': label,
                                'type': primary_label,
                                'color': color,
                                'size': size,
                                'props': node_props
                            }
                        })
                
                # 获取关系
                if node_ids:
                    node_ids_str = "'" + "', '".join(node_ids) + "'"
                    relationship_query = f"""
                    MATCH (a)-[r]->(b)
                    WHERE elementId(a) IN [{node_ids_str}] AND elementId(b) IN [{node_ids_str}]
                    RETURN elementId(a) as source, elementId(b) as target, 
                           type(r) as relationship, properties(r) as props
                    LIMIT {limit * 2}
                    """
                    
                    rel_result = session.run(relationship_query)
                    edges = []
                    
                    for record in rel_result:
                        relationship_label = self.config.RELATIONSHIP_TYPES.get(
                            record['relationship'], record['relationship']
                        )
                        
                        edges.append({
                            'data': {
                                'source': record['source'],
                                'target': record['target'],
                                'label': relationship_label,
                                'type': record['relationship'],
                                'props': record['props']
                            }
                        })
                
                return {'nodes': nodes, 'edges': edges}
                
        except Exception as e:
            self.logger.error(f"❌ 获取图数据失败: {e}")
            return {'nodes': [], 'edges': []}
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        node_stats = self.db.get_node_statistics()
        rel_stats = self.db.get_relationship_statistics()
        
        return {
            'total_nodes': sum(node_stats.values()),
            'total_relationships': sum(rel_stats.values()),
            'node_breakdown': node_stats,
            'relationship_breakdown': rel_stats
        }
    
    def setup_callbacks(self):
        """设置回调函数"""
        
        @self.app.callback(
            Output('knowledge-graph', 'elements'),
            Output('knowledge-graph', 'layout'),
            [Input('search-button', 'n_clicks'),
             Input('filter-button', 'n_clicks'),
             Input('reset-button', 'n_clicks')],
            [State('search-input', 'value'),
             State('case-type-filter', 'value'),
             State('judgment-filter', 'value'),
             State('node-type-filter', 'value'),
             State('layout-dropdown', 'value')]
        )
        def update_graph(search_clicks, filter_clicks, reset_clicks, 
                        search_term, case_type, judgment, node_type, layout_name):
            
            ctx = callback_context
            if not ctx.triggered:
                # 初始加载
                graph_data = self.get_graph_data(limit=100)
            else:
                button_id = ctx.triggered[0]['prop_id'].split('.')[0]
                
                if button_id == 'reset-button':
                    # 重置所有筛选
                    graph_data = self.get_graph_data(limit=100)
                else:
                    # 应用筛选
                    graph_data = self.get_graph_data(
                        case_type=case_type,
                        judgment_result=judgment,
                        node_type=node_type,
                        search_term=search_term,
                        limit=200
                    )
            
            elements = graph_data['nodes'] + graph_data['edges']
            layout = {'name': layout_name, 'nodeSpacing': 100, 'edgeElasticity': 100}
            
            return elements, layout
        
        @self.app.callback(
            Output('statistics-display', 'children'),
            [Input('knowledge-graph', 'elements')]
        )
        def update_statistics(elements):
            try:
                stats = self.get_statistics()
                
                stats_display = html.Div([
                    html.P(f"📊 总节点数: {stats['total_nodes']}"),
                    html.P(f"🔗 总关系数: {stats['total_relationships']}"),
                    html.Hr(),
                    html.P("节点分布:", style={'fontWeight': 'bold'}),
                ] + [
                    html.P(f"• {label}: {count}") 
                    for label, count in stats['node_breakdown'].items()
                ] + [
                    html.Hr(),
                    html.P("关系分布:", style={'fontWeight': 'bold'}),
                ] + [
                    html.P(f"• {self.config.RELATIONSHIP_TYPES.get(rel_type, rel_type)}: {count}") 
                    for rel_type, count in stats['relationship_breakdown'].items()
                ])
                
                return stats_display
            except Exception as e:
                return html.P(f"❌ 统计信息加载失败: {str(e)}")
        
        @self.app.callback(
            Output('detail-panel', 'children'),
            [Input('knowledge-graph', 'tapNodeData')]
        )
        def display_node_details(nodeData):
            if not nodeData:
                return html.P("点击节点查看详细信息")
            
            props = nodeData.get('props', {})
            node_type = nodeData.get('type', 'Unknown')
            
            details = [
                html.H4(f"🔍 {node_type} 详情"),
                html.Hr()
            ]
            
            # 根据节点类型显示不同的详情
            if node_type == 'Case':
                details.extend([
                    html.P(f"📋 案件号: {props.get('case_number', 'N/A')}"),
                    html.P(f"📁 文件名: {props.get('file_name', 'N/A')}"),
                    html.P(f"📅 审理日期: {props.get('trial_date', 'N/A')}"),
                    html.P(f"⚖️ 案件类型: {props.get('case_type_cn', props.get('case_type', 'N/A'))}"),
                    html.P(f"📊 判决结果: {props.get('judgment_result_cn', props.get('judgment_result', 'N/A'))}"),
                    html.P(f"💰 申请金额: {props.get('claim_amount', 'N/A')}"),
                    html.P(f"💵 判决金额: {props.get('judgment_amount', 'N/A')}"),
                    html.P(f"🌐 语言: {props.get('language', 'N/A')}"),
                ])
            else:
                details.extend([
                    html.P(f"👤 姓名: {props.get('name', 'N/A')}"),
                    html.P(f"🎭 角色: {props.get('role', props.get('type', 'N/A'))}"),
                ])
                
                # 显示所有其他属性
                for key, value in props.items():
                    if key not in ['name', 'role', 'type']:
                        details.append(html.P(f"{key}: {value}"))
            
            return html.Div(details)
    
    def run(self, host: str = None, port: int = None, debug: bool = None):
        """运行可视化应用"""
        host = host or self.config.WEB_HOST
        port = port or self.config.WEB_PORT
        debug = debug if debug is not None else self.config.WEB_DEBUG
        
        self.logger.info(f"🚀 启动知识图谱可视化界面 http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug) 