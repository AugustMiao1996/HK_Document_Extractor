#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单案件知识图谱系统 - 快速版本
专注于单个案件的清晰图谱展示
"""

import json
import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_cytoscape as cyto
import pandas as pd
import re
from typing import Dict, List, Any, Optional
import logging

class SingleCaseKnowledgeGraph:
    """单案件知识图谱系统"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.cases_data = self.load_data()
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        
        # 加载Cytoscape样式
        cyto.load_extra_layouts()
        
        # 节点颜色配置
        self.node_colors = {
            'Case': '#1f77b4',           # 蓝色 - 案件
            'Plaintiff': '#2ca02c',      # 绿色 - 原告
            'Defendant': '#d62728',      # 红色 - 被告
            'Judge': '#9467bd',          # 紫色 - 法官
            'Court': '#7f7f7f',          # 灰色 - 法院
            'Lawyer': '#8c564b',         # 棕色 - 律师
            'LawFirm': '#e377c2',        # 粉色 - 律师事务所
            'Amount': '#ff7f0e',         # 橙色 - 金额
        }
        
        self.setup_layout()
        self.setup_callbacks()
    
    def load_data(self) -> List[Dict[str, Any]]:
        """加载案件数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ 成功加载 {len(data)} 条案件数据")
            return data
        except Exception as e:
            print(f"❌ 加载数据失败: {e}")
            return []
    
    def clean_text(self, text: str) -> str:
        """清理文本，移除空值和异常字符"""
        if not text or text.strip() == "" or text.lower() == "unknown":
            return None
        return text.strip()
    
    def parse_parties(self, party_string: str) -> List[str]:
        """解析当事人字符串"""
        if not party_string:
            return []
        
        # 处理多个当事人的分隔符
        parties = []
        if '|' in party_string:
            raw_parties = party_string.split('|')
        else:
            raw_parties = [party_string]
        
        for party in raw_parties:
            party = party.strip()
            if party and len(party) > 2 and party not in ['whether the', 'Defendant', 'Plaintiff']:
                # 清理序号和角色描述
                party = re.sub(r'^\d+\w*\s+', '', party)
                party = re.sub(r'\s*\([^)]*\)\s*', '', party)
                party = re.sub(r'\s*(Plaintiff|Defendant|plaintiff|defendant)\s*', '', party)
                party = party.strip()
                if party and len(party) > 2:
                    parties.append(party)
        
        return parties
    
    def parse_lawyers(self, lawyer_string: str) -> List[Dict[str, str]]:
        """解析律师信息"""
        lawyers = []
        if not lawyer_string:
            return lawyers
        
        # 提取律师姓名
        lawyer_pattern = r'(Mr|Ms|Miss)\s+([A-Za-z\s]+?)(?=,|\s+\(|$)'
        matches = re.findall(lawyer_pattern, lawyer_string)
        
        for title, name in matches:
            full_name = f"{title} {name}".strip()
            if len(full_name) > 5:
                lawyers.append({
                    'name': full_name,
                    'type': 'lawyer'
                })
        
        # 提取律师事务所
        firm_patterns = [
            r'instructed by ([^,]+?)(?=,|for|$)',
            r'\(([^)]+)\)',
        ]
        
        for pattern in firm_patterns:
            matches = re.findall(pattern, lawyer_string)
            for firm in matches:
                firm = firm.strip()
                if firm and len(firm) > 3 and 'Ltd' not in firm and 'Co' not in firm:
                    lawyers.append({
                        'name': firm,
                        'type': 'law_firm'
                    })
        
        return lawyers
    
    def create_case_graph(self, case_data: Dict[str, Any]) -> Dict[str, List]:
        """为单个案件创建图数据"""
        nodes = []
        edges = []
        
        # 1. 案件中心节点
        case_node = {
            'data': {
                'id': 'case',
                'label': f"案件\n{case_data.get('case_number', 'Unknown')}",
                'type': 'Case',
                'color': self.node_colors['Case'],
                'size': 80,
                'props': case_data
            }
        }
        nodes.append(case_node)
        
        # 2. 原告节点
        plaintiffs = self.parse_parties(case_data.get('plaintiff', ''))
        for i, plaintiff in enumerate(plaintiffs):
            node_id = f'plaintiff_{i}'
            nodes.append({
                'data': {
                    'id': node_id,
                    'label': f"原告\n{plaintiff}",
                    'type': 'Plaintiff',
                    'color': self.node_colors['Plaintiff'],
                    'size': 60,
                    'props': {'name': plaintiff, 'role': 'plaintiff'}
                }
            })
            edges.append({
                'data': {
                    'source': node_id,
                    'target': 'case',
                    'label': '参与案件',
                    'type': 'INVOLVES'
                }
            })
        
        # 3. 被告节点
        defendants = self.parse_parties(case_data.get('defendant', ''))
        for i, defendant in enumerate(defendants):
            node_id = f'defendant_{i}'
            nodes.append({
                'data': {
                    'id': node_id,
                    'label': f"被告\n{defendant}",
                    'type': 'Defendant',
                    'color': self.node_colors['Defendant'],
                    'size': 60,
                    'props': {'name': defendant, 'role': 'defendant'}
                }
            })
            edges.append({
                'data': {
                    'source': node_id,
                    'target': 'case',
                    'label': '参与案件',
                    'type': 'INVOLVES'
                }
            })
        
        # 4. 原告起诉被告关系
        for i, plaintiff in enumerate(plaintiffs):
            for j, defendant in enumerate(defendants):
                edges.append({
                    'data': {
                        'source': f'plaintiff_{i}',
                        'target': f'defendant_{j}',
                        'label': '起诉',
                        'type': 'SUES'
                    }
                })
        
        # 5. 法官节点
        judge = self.clean_text(case_data.get('judge', ''))
        if judge:
            nodes.append({
                'data': {
                    'id': 'judge',
                    'label': f"法官\n{judge}",
                    'type': 'Judge',
                    'color': self.node_colors['Judge'],
                    'size': 50,
                    'props': {'name': judge, 'role': 'judge'}
                }
            })
            edges.append({
                'data': {
                    'source': 'case',
                    'target': 'judge',
                    'label': '审理法官',
                    'type': 'JUDGED_BY'
                }
            })
        
        # 6. 法院节点
        court = self.clean_text(case_data.get('court_name', ''))
        if court:
            nodes.append({
                'data': {
                    'id': 'court',
                    'label': f"法院\n{court[:30]}...",
                    'type': 'Court',
                    'color': self.node_colors['Court'],
                    'size': 45,
                    'props': {'name': court, 'type': 'court'}
                }
            })
            edges.append({
                'data': {
                    'source': 'case',
                    'target': 'court',
                    'label': '审理法院',
                    'type': 'HEARD_IN'
                }
            })
        
        # 7. 律师节点
        all_lawyers = []
        
        # 原告律师
        plaintiff_lawyers = self.parse_lawyers(case_data.get('plaintiff_lawyer', ''))
        for lawyer in plaintiff_lawyers:
            all_lawyers.append({**lawyer, 'side': 'plaintiff'})
        
        # 被告律师
        defendant_lawyers = self.parse_lawyers(case_data.get('defendant_lawyer', ''))
        for lawyer in defendant_lawyers:
            all_lawyers.append({**lawyer, 'side': 'defendant'})
        
        # 从lawyer_segment解析更多律师
        lawyer_segment_lawyers = self.parse_lawyers(case_data.get('lawyer_segment', ''))
        for lawyer in lawyer_segment_lawyers:
            all_lawyers.append({**lawyer, 'side': 'unknown'})
        
        # 去重并添加律师节点
        seen_lawyers = set()
        for i, lawyer in enumerate(all_lawyers):
            if lawyer['name'] not in seen_lawyers:
                seen_lawyers.add(lawyer['name'])
                node_id = f'lawyer_{i}'
                
                if lawyer['type'] == 'lawyer':
                    color = self.node_colors['Lawyer']
                    label = f"律师\n{lawyer['name']}"
                else:
                    color = self.node_colors['LawFirm']
                    label = f"律师事务所\n{lawyer['name']}"
                
                nodes.append({
                    'data': {
                        'id': node_id,
                        'label': label,
                        'type': 'Lawyer' if lawyer['type'] == 'lawyer' else 'LawFirm',
                        'color': color,
                        'size': 40,
                        'props': lawyer
                    }
                })
                
                # 连接到案件
                edges.append({
                    'data': {
                        'source': node_id,
                        'target': 'case',
                        'label': '参与案件',
                        'type': 'REPRESENTS'
                    }
                })
        
        # 8. 金额节点
        amounts = []
        claim_amount = self.clean_text(case_data.get('claim_amount', ''))
        judgment_amount = self.clean_text(case_data.get('judgment_amount', ''))
        
        if claim_amount:
            amounts.append(('claim', f"申请金额\n{claim_amount}"))
        if judgment_amount:
            amounts.append(('judgment', f"判决金额\n{judgment_amount}"))
        
        for amount_type, label in amounts:
            node_id = f'amount_{amount_type}'
            nodes.append({
                'data': {
                    'id': node_id,
                    'label': label,
                    'type': 'Amount',
                    'color': self.node_colors['Amount'],
                    'size': 35,
                    'props': {'type': amount_type, 'amount': label}
                }
            })
            edges.append({
                'data': {
                    'source': 'case',
                    'target': node_id,
                    'label': '涉及金额',
                    'type': 'INVOLVES_AMOUNT'
                }
            })
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_cases_summary(self) -> pd.DataFrame:
        """获取案件摘要表"""
        summary_data = []
        for case in self.cases_data:
            summary_data.append({
                '案件号': case.get('case_number', 'Unknown'),
                '文件名': case.get('file_name', 'Unknown'),
                '审理日期': case.get('trial_date', 'Unknown'),
                '案件类型': case.get('case_type', 'Unknown'),
                '判决结果': case.get('judgment_result', 'Unknown'),
                '语言': case.get('language', 'Unknown')
            })
        return pd.DataFrame(summary_data)
    
    def setup_layout(self):
        """设置应用布局"""
        self.app.layout = html.Div([
            # 标题
            html.Div([
                html.H1("🏛️ 单案件知识图谱系统", 
                       style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}),
                html.P("Hong Kong Court Documents - Single Case Knowledge Graph", 
                      style={'textAlign': 'center', 'color': '#7f8c8d'})
            ], style={'marginBottom': '20px'}),
            
            # 主界面 - 分为两个Tab
            dcc.Tabs(id='main-tabs', value='case-selector', children=[
                # Tab 1: 案件选择
                dcc.Tab(label='📋 案件选择', value='case-selector', children=[
                    html.Div([
                        html.H3("选择要分析的案件", style={'marginBottom': '20px'}),
                        
                        # 搜索框
                        html.Div([
                            dcc.Input(
                                id='search-input',
                                type='text',
                                placeholder='搜索案件号、当事人、法官...',
                                style={'width': '70%', 'marginRight': '10px'}
                            ),
                            html.Button('搜索', id='search-button', n_clicks=0, 
                                       style={'width': '20%'})
                        ], style={'marginBottom': '20px'}),
                        
                        # 案件表格
                        html.Div(id='cases-table-container'),
                        
                        # 选择按钮
                        html.Div([
                            html.Button('分析选中案件', id='analyze-button', n_clicks=0, 
                                       style={'backgroundColor': '#3498db', 'color': 'white', 
                                             'padding': '10px 20px', 'fontSize': '16px',
                                             'border': 'none', 'borderRadius': '5px',
                                             'marginTop': '20px'})
                        ], style={'textAlign': 'center'})
                        
                    ], style={'padding': '20px'})
                ]),
                
                # Tab 2: 知识图谱
                dcc.Tab(label='🕸️ 知识图谱', value='knowledge-graph', children=[
                    html.Div([
                        # 控制面板
                        html.Div([
                            html.H4("📐 图谱控制"),
                            html.Label("布局类型:"),
                            dcc.Dropdown(
                                id='layout-dropdown',
                                options=[
                                    {'label': '力导向布局', 'value': 'cose'},
                                    {'label': '分层布局', 'value': 'dagre'},
                                    {'label': '圆形布局', 'value': 'circle'},
                                    {'label': '网格布局', 'value': 'grid'},
                                ],
                                value='cose',
                                style={'marginBottom': '15px'}
                            ),
                            html.Label("显示关系:"),
                            dcc.Checklist(
                                id='relationship-filter',
                                options=[
                                    {'label': '起诉关系', 'value': 'SUES'},
                                    {'label': '参与案件', 'value': 'INVOLVES'},
                                    {'label': '法官审理', 'value': 'JUDGED_BY'},
                                    {'label': '法院审理', 'value': 'HEARD_IN'},
                                    {'label': '律师代理', 'value': 'REPRESENTS'},
                                    {'label': '涉及金额', 'value': 'INVOLVES_AMOUNT'},
                                ],
                                value=['SUES', 'INVOLVES', 'JUDGED_BY', 'HEARD_IN', 'REPRESENTS', 'INVOLVES_AMOUNT'],
                                style={'marginBottom': '15px'}
                            ),
                            html.Button('返回案件选择', id='back-button', n_clicks=0,
                                       style={'width': '100%', 'marginBottom': '15px'}),
                        ], style={'width': '25%', 'padding': '20px', 'backgroundColor': '#f8f9fa', 
                                 'height': '100vh', 'overflowY': 'auto', 'float': 'left'}),
                        
                        # 图谱显示区域
                        html.Div([
                            html.Div(id='current-case-info', style={'marginBottom': '10px'}),
                            cyto.Cytoscape(
                                id='case-graph',
                                layout={'name': 'cose', 'nodeSpacing': 100},
                                style={'width': '100%', 'height': '70vh'},
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
                                            'font-size': '10px',
                                            'font-family': 'Arial',
                                            'border-width': 2,
                                            'border-color': '#2c3e50',
                                            'border-opacity': 0.8,
                                            'text-wrap': 'wrap',
                                            'text-max-width': 80,
                                        }
                                    },
                                    # 选中节点样式
                                    {
                                        'selector': 'node:selected',
                                        'style': {
                                            'border-width': 4,
                                            'border-color': '#e74c3c',
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
                            html.Div(id='node-detail-panel', 
                                    style={'marginTop': '20px', 'padding': '15px', 
                                          'backgroundColor': '#ecf0f1', 'borderRadius': '5px'})
                            
                        ], style={'width': '75%', 'padding': '20px', 'float': 'right'})
                    ])
                ])
            ]),
            
            # 隐藏存储
            dcc.Store(id='selected-case-data'),
            dcc.Store(id='graph-data')
        ])
    
    def setup_callbacks(self):
        """设置回调函数"""
        
        @self.app.callback(
            Output('cases-table-container', 'children'),
            [Input('search-button', 'n_clicks'),
             Input('main-tabs', 'value')],
            [State('search-input', 'value')],
            prevent_initial_call=False
        )
        def update_cases_table(search_clicks, active_tab, search_term):
            if active_tab != 'case-selector':
                return []
            
            try:
                df = self.get_cases_summary()
                
                # 应用搜索筛选
                if search_term:
                    mask = df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
                    df = df[mask]
                
                return dash_table.DataTable(
                    id='cases-table',
                    columns=[{"name": col, "id": col} for col in df.columns],
                    data=df.to_dict('records'),
                    row_selectable='single',
                    page_size=15,
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': '#3498db', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f8f9fa'
                        }
                    ]
                )
            except Exception as e:
                return html.Div(f"❌ 加载案件列表失败: {str(e)}")
        
        @self.app.callback(
            [Output('selected-case-data', 'data'),
             Output('main-tabs', 'value')],
            [Input('analyze-button', 'n_clicks'),
             Input('back-button', 'n_clicks')],
            [State('cases-table', 'selected_rows'),
             State('cases-table', 'data'),
             State('main-tabs', 'value')],
            prevent_initial_call=True
        )
        def handle_navigation(analyze_clicks, back_clicks, selected_rows, table_data, current_tab):
            """统一处理导航逻辑，避免多个callback更新同一个output"""
            ctx = callback_context
            if not ctx.triggered:
                return None, current_tab
            
            button_id = ctx.triggered[0]['prop_id'].split('.')[0]
            
            try:
                if button_id == 'analyze-button':
                    if analyze_clicks and selected_rows and table_data:
                        # 分析选中案件
                        selected_row = table_data[selected_rows[0]]
                        case_number = selected_row['案件号']
                        
                        # 找到完整的案件数据
                        for case in self.cases_data:
                            if case.get('case_number') == case_number:
                                return case, 'knowledge-graph'
                    return None, current_tab
                
                elif button_id == 'back-button':
                    if back_clicks:
                        # 返回案件选择
                        return None, 'case-selector'
                    return None, current_tab
                
            except Exception as e:
                print(f"❌ 导航处理错误: {e}")
                return None, current_tab
            
            return None, current_tab
        
        @self.app.callback(
            [Output('graph-data', 'data'),
             Output('current-case-info', 'children')],
            [Input('selected-case-data', 'data')],
            prevent_initial_call=False
        )
        def generate_graph_data(case_data):
            try:
                if not case_data:
                    return None, html.Div("请先选择一个案件", style={'padding': '20px', 'textAlign': 'center'})
                
                graph_data = self.create_case_graph(case_data)
                
                case_info = html.Div([
                    html.H4(f"📋 案件: {case_data.get('case_number', 'Unknown')}"),
                    html.P(f"🏛️ 法院: {case_data.get('court_name', 'Unknown')[:50]}..."),
                    html.P(f"⚖️ 类型: {case_data.get('case_type', 'Unknown')} | 📅 日期: {case_data.get('trial_date', 'Unknown')} | 🏆 结果: {case_data.get('judgment_result', 'Unknown')}")
                ], style={'backgroundColor': '#e8f4fd', 'padding': '15px', 'borderRadius': '5px'})
                
                return graph_data, case_info
            except Exception as e:
                error_info = html.Div([
                    html.H4("❌ 图谱生成失败"),
                    html.P(f"错误信息: {str(e)}")
                ], style={'backgroundColor': '#ffebee', 'padding': '15px', 'borderRadius': '5px', 'color': '#c62828'})
                return None, error_info
        
        @self.app.callback(
            [Output('case-graph', 'elements'),
             Output('case-graph', 'layout')],
            [Input('graph-data', 'data'),
             Input('layout-dropdown', 'value'),
             Input('relationship-filter', 'value')],
            prevent_initial_call=False
        )
        def update_graph(graph_data, layout_name, relationship_filter):
            try:
                if not graph_data:
                    return [], {'name': layout_name or 'cose'}
                
                # 确保relationship_filter不为空
                if not relationship_filter:
                    relationship_filter = ['SUES', 'INVOLVES', 'JUDGED_BY', 'HEARD_IN', 'REPRESENTS', 'INVOLVES_AMOUNT']
                
                # 筛选关系
                filtered_edges = []
                for edge in graph_data.get('edges', []):
                    if edge['data']['type'] in relationship_filter:
                        filtered_edges.append(edge)
                
                elements = graph_data.get('nodes', []) + filtered_edges
                layout = {'name': layout_name or 'cose', 'nodeSpacing': 100}
                
                return elements, layout
            except Exception as e:
                print(f"❌ 图谱更新错误: {e}")
                return [], {'name': layout_name or 'cose'}
        
        @self.app.callback(
            Output('node-detail-panel', 'children'),
            [Input('case-graph', 'tapNodeData')],
            prevent_initial_call=False
        )
        def display_node_details(node_data):
            try:
                if not node_data:
                    return html.P("点击节点查看详细信息", style={'padding': '10px', 'textAlign': 'center', 'color': '#666'})
                
                props = node_data.get('props', {})
                node_type = node_data.get('type', 'Unknown')
                
                details = [html.H4(f"🔍 {node_type} 详情"), html.Hr()]
                
                if node_type == 'Case':
                    details.extend([
                        html.P(f"📋 案件号: {props.get('case_number', 'N/A')}"),
                        html.P(f"📁 文件名: {props.get('file_name', 'N/A')}"),
                        html.P(f"📅 审理日期: {props.get('trial_date', 'N/A')}"),
                        html.P(f"⚖️ 案件类型: {props.get('case_type', 'N/A')}"),
                        html.P(f"🏆 判决结果: {props.get('judgment_result', 'N/A')}"),
                        html.P(f"💰 申请金额: {props.get('claim_amount', 'N/A')}"),
                        html.P(f"💵 判决金额: {props.get('judgment_amount', 'N/A')}"),
                    ])
                else:
                    for key, value in props.items():
                        if key != 'props' and value:
                            details.append(html.P(f"{key}: {value}"))
                
                return html.Div(details)
            except Exception as e:
                return html.Div([
                    html.H4("❌ 详情显示错误"),
                    html.P(f"错误信息: {str(e)}")
                ], style={'color': '#c62828'})
    
    def run(self, host: str = '127.0.0.1', port: int = 8051, debug: bool = True):
        """运行应用"""
        print(f"🚀 启动单案件知识图谱系统")
        print(f"📊 已加载 {len(self.cases_data)} 个案件")
        print(f"🌐 访问地址: http://{host}:{port}")
        self.app.run(host=host, port=port, debug=debug)

def main():
    """主函数"""
    import os
    
    # 查找数据文件
    data_file = "output/llm_analysis_20250603_110724.json"
    if not os.path.exists(data_file):
        print("❌ 数据文件不存在，请检查路径")
        return
    
    # 启动系统
    kg = SingleCaseKnowledgeGraph(data_file)
    kg.run()

if __name__ == "__main__":
    main() 