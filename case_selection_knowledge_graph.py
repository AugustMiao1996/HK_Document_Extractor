#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法院文书知识图谱 - 案件选择式系统
先选择案件，再查看该案件的知识图谱
"""

import dash
from dash import dcc, html, Input, Output, State, callback_context, dash_table
import dash_cytoscape as cyto
import pandas as pd
import json
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

# 加载Cytoscape样式
cyto.load_extra_layouts()

class CaseSelectionKnowledgeGraph:
    """案件选择式知识图谱系统"""
    
    def __init__(self, data_file: str):
        self.data_file = data_file
        self.cases_data = self.load_cases_data()
        self.app = dash.Dash(__name__, suppress_callback_exceptions=True)
        self.logger = logging.getLogger(__name__)
        self.selected_case = None
        
        self.setup_layout()
        self.setup_callbacks()
    
    def load_cases_data(self) -> List[Dict]:
        """加载案件数据"""
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"成功加载 {len(data)} 个案件")
            return data
        except Exception as e:
            print(f"加载数据失败: {e}")
            return []
    
    def create_cases_table_data(self) -> List[Dict]:
        """创建案件表格数据"""
        table_data = []
        for i, case in enumerate(self.cases_data):
            table_data.append({
                'id': i,
                'case_number': case.get('case_number', ''),
                'file_name': case.get('file_name', ''),
                'trial_date': case.get('trial_date', ''),
                'case_type': case.get('case_type', ''),
                'judgment_result': case.get('judgment_result', ''),
                'language': case.get('language', '')
            })
        return table_data
    
    def setup_layout(self):
        """设置应用布局"""
        
        # 案件表格数据
        table_data = self.create_cases_table_data()
        
        self.app.layout = html.Div([
            # 顶部标题
            html.Div([
                html.H1("[*] 香港法院文书知识图谱系统", 
                       style={
                           'textAlign': 'center', 
                           'color': '#2c3e50', 
                           'marginBottom': '10px',
                           'fontFamily': 'Arial, sans-serif'
                       }),
                html.P("Hong Kong Court Documents Knowledge Graph", 
                      style={
                          'textAlign': 'center', 
                          'color': '#7f8c8d', 
                          'marginTop': '0px',
                          'marginBottom': '20px'
                      })
            ]),
            
            # 标签页
            dcc.Tabs(id="tabs", value="case-selection", children=[
                # 案件选择标签页
                dcc.Tab(label="案件选择", value="case-selection", children=[
                    html.Div([
                        html.H3("选择要分析的案件", 
                               style={'color': '#2c3e50', 'marginBottom': '20px'}),
                        
                        # 搜索框
                        html.Div([
                            dcc.Input(
                                id='search-input',
                                type='text',
                                placeholder='搜索案件号、当事人、法官...',
                                style={
                                    'width': '70%',
                                    'padding': '10px',
                                    'marginRight': '10px',
                                    'border': '1px solid #ddd',
                                    'borderRadius': '4px'
                                }
                            ),
                            html.Button(
                                '搜索',
                                id='search-button',
                                n_clicks=0,
                                style={
                                    'padding': '10px 20px',
                                    'backgroundColor': '#3498db',
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '4px',
                                    'cursor': 'pointer'
                                }
                            )
                        ], style={'marginBottom': '20px'}),
                        
                        # 案件表格
                        dash_table.DataTable(
                            id='cases-table',
                            columns=[
                                {'name': '案件号', 'id': 'case_number'},
                                {'name': '文件名', 'id': 'file_name'},
                                {'name': '审理日期', 'id': 'trial_date'},
                                {'name': '案件类型', 'id': 'case_type'},
                                {'name': '判决结果', 'id': 'judgment_result'},
                                {'name': '语言', 'id': 'language'}
                            ],
                            data=table_data,
                            row_selectable='single',
                            selected_rows=[],
                            style_cell={
                                'textAlign': 'left',
                                'padding': '10px',
                                'fontFamily': 'Arial, sans-serif'
                            },
                            style_header={
                                'backgroundColor': '#3498db',
                                'color': 'white',
                                'fontWeight': 'bold'
                            },
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f8f9fa'
                                }
                            ],
                            style_table={'height': '400px', 'overflowY': 'auto'},
                            page_size=15
                        ),
                        
                        # 进入知识图谱按钮
                        html.Div([
                            html.Button(
                                '进入案件知识图谱',
                                id='enter-graph-button',
                                n_clicks=0,
                                disabled=True,
                                style={
                                    'padding': '15px 30px',
                                    'fontSize': '16px',
                                    'backgroundColor': '#27ae60',
                                    'color': 'white',
                                    'border': 'none',
                                    'borderRadius': '4px',
                                    'cursor': 'pointer',
                                    'marginTop': '20px'
                                }
                            )
                        ], style={'textAlign': 'center'})
                        
                    ], style={'padding': '20px'})
                ]),
                
                # 知识图谱标签页
                dcc.Tab(label="知识图谱", value="knowledge-graph", children=[
                    html.Div([
                        # 案件信息显示
                        html.Div(id='selected-case-info', style={'marginBottom': '20px'}),
                        
                        # 控制面板
                        html.Div([
                            html.Div([
                                html.H4("图谱控制"),
                                html.Label("布局算法:"),
                                dcc.Dropdown(
                                    id='layout-dropdown',
                                    options=[
                                        {'label': '力导向布局', 'value': 'cose'},
                                        {'label': '分层布局', 'value': 'dagre'},
                                        {'label': '圆形布局', 'value': 'circle'},
                                        {'label': '网格布局', 'value': 'grid'}
                                    ],
                                    value='cose',
                                    style={'marginBottom': '15px'}
                                ),
                                
                                html.Label("显示关系类型:"),
                                dcc.Checklist(
                                    id='relationship-filter',
                                    options=[
                                        {'label': '起诉关系', 'value': 'SUES'},
                                        {'label': '代理关系', 'value': 'REPRESENTS'},
                                        {'label': '审理关系', 'value': 'JUDGED_BY'},
                                        {'label': '法院关系', 'value': 'HEARD_IN'},
                                        {'label': '雇佣关系', 'value': 'WORKS_FOR'},
                                        {'label': '涉及关系', 'value': 'INVOLVES'}
                                    ],
                                    value=['SUES', 'REPRESENTS', 'JUDGED_BY', 'HEARD_IN'],
                                    style={'marginBottom': '15px'}
                                ),
                                
                                html.Button(
                                    '返回案件选择',
                                    id='back-to-selection-button',
                                    n_clicks=0,
                                    style={
                                        'width': '100%',
                                        'padding': '10px',
                                        'backgroundColor': '#95a5a6',
                                        'color': 'white',
                                        'border': 'none',
                                        'borderRadius': '4px',
                                        'cursor': 'pointer'
                                    }
                                )
                                
                            ], style={
                                'width': '25%',
                                'padding': '20px',
                                'backgroundColor': '#f8f9fa',
                                'float': 'left',
                                'height': '600px',
                                'overflowY': 'auto'
                            }),
                            
                            # 知识图谱区域
                            html.Div([
                                cyto.Cytoscape(
                                    id='knowledge-graph',
                                    layout={'name': 'cose'},
                                    style={'width': '100%', 'height': '500px'},
                                    elements=[],
                                    stylesheet=[
                                        # Case节点样式
                                        {
                                            'selector': 'node[type="Case"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#3498db',
                                                'width': '60px',
                                                'height': '60px',
                                                'font-size': '12px',
                                                'color': 'white',
                                                'text-wrap': 'wrap',
                                                'text-max-width': '50px'
                                            }
                                        },
                                        # Plaintiff节点样式
                                        {
                                            'selector': 'node[type="Plaintiff"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#27ae60',
                                                'width': '50px',
                                                'height': '50px',
                                                'font-size': '10px',
                                                'color': 'white'
                                            }
                                        },
                                        # Defendant节点样式
                                        {
                                            'selector': 'node[type="Defendant"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#e74c3c',
                                                'width': '50px',
                                                'height': '50px',
                                                'font-size': '10px',
                                                'color': 'white'
                                            }
                                        },
                                        # Judge节点样式
                                        {
                                            'selector': 'node[type="Judge"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#9b59b6',
                                                'width': '45px',
                                                'height': '45px',
                                                'font-size': '10px',
                                                'color': 'white'
                                            }
                                        },
                                        # Lawyer节点样式
                                        {
                                            'selector': 'node[type="Lawyer"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#f39c12',
                                                'width': '40px',
                                                'height': '40px',
                                                'font-size': '9px',
                                                'color': 'white'
                                            }
                                        },
                                        # LawFirm节点样式
                                        {
                                            'selector': 'node[type="LawFirm"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#e91e63',
                                                'width': '40px',
                                                'height': '40px',
                                                'font-size': '9px',
                                                'color': 'white'
                                            }
                                        },
                                        # Court节点样式
                                        {
                                            'selector': 'node[type="Court"]',
                                            'style': {
                                                'content': 'data(label)',
                                                'text-valign': 'center',
                                                'text-halign': 'center',
                                                'background-color': '#95a5a6',
                                                'width': '45px',
                                                'height': '45px',
                                                'font-size': '10px',
                                                'color': 'white'
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
                                                'text-margin-y': -10
                                            }
                                        }
                                    ]
                                ),
                                
                                # 节点详情面板
                                html.Div(id='node-details', 
                                        style={
                                            'marginTop': '20px',
                                            'padding': '15px',
                                            'backgroundColor': '#ecf0f1',
                                            'borderRadius': '5px',
                                            'minHeight': '60px'
                                        })
                                
                            ], style={'width': '75%', 'float': 'right', 'padding': '20px'})
                        ], style={'overflow': 'hidden'})
                        
                    ], style={'padding': '20px'})
                ])
            ]),
            
            # 隐藏的数据存储
            dcc.Store(id='selected-case-data')
            
        ])
    
    def create_case_graph(self, case_data: Dict) -> List[Dict]:
        """为单个案件创建知识图谱"""
        elements = []
        
        # 案件节点
        case_id = f"case_{case_data.get('file_name', 'unknown')}"
        elements.append({
            'data': {
                'id': case_id,
                'label': case_data.get('case_number', '案件'),
                'type': 'Case',
                'details': case_data
            }
        })
        
        # 原告节点和关系
        plaintiff = case_data.get('plaintiff', '').strip()
        if plaintiff:
            plaintiff_id = f"plaintiff_{hash(plaintiff)}"
            elements.append({
                'data': {
                    'id': plaintiff_id,
                    'label': plaintiff[:20] + "..." if len(plaintiff) > 20 else plaintiff,
                    'type': 'Plaintiff',
                    'details': {'name': plaintiff, 'role': '原告'}
                }
            })
            elements.append({
                'data': {
                    'source': case_id,
                    'target': plaintiff_id,
                    'label': '涉及原告',
                    'type': 'INVOLVES'
                }
            })
        
        # 被告节点和关系
        defendant = case_data.get('defendant', '').strip()
        if defendant:
            defendant_id = f"defendant_{hash(defendant)}"
            elements.append({
                'data': {
                    'id': defendant_id,
                    'label': defendant[:20] + "..." if len(defendant) > 20 else defendant,
                    'type': 'Defendant',
                    'details': {'name': defendant, 'role': '被告'}
                }
            })
            elements.append({
                'data': {
                    'source': case_id,
                    'target': defendant_id,
                    'label': '涉及被告',
                    'type': 'INVOLVES'
                }
            })
            
            # 原告起诉被告关系
            if plaintiff:
                elements.append({
                    'data': {
                        'source': plaintiff_id,
                        'target': defendant_id,
                        'label': '起诉',
                        'type': 'SUES'
                    }
                })
        
        # 法官节点和关系
        judge = case_data.get('judge', '').strip()
        if judge:
            judge_id = f"judge_{hash(judge)}"
            elements.append({
                'data': {
                    'id': judge_id,
                    'label': judge,
                    'type': 'Judge',
                    'details': {'name': judge, 'role': '法官'}
                }
            })
            elements.append({
                'data': {
                    'source': case_id,
                    'target': judge_id,
                    'label': '审理',
                    'type': 'JUDGED_BY'
                }
            })
        
        # 法院节点和关系
        court = case_data.get('court_name', '').strip()
        if court:
            court_id = f"court_{hash(court)}"
            elements.append({
                'data': {
                    'id': court_id,
                    'label': court[:15] + "..." if len(court) > 15 else court,
                    'type': 'Court',
                    'details': {'name': court, 'type': '法院'}
                }
            })
            elements.append({
                'data': {
                    'source': case_id,
                    'target': court_id,
                    'label': '审理于',
                    'type': 'HEARD_IN'
                }
            })
        
        # 原告律师和关系
        plaintiff_lawyer = case_data.get('plaintiff_lawyer', '').strip()
        if plaintiff_lawyer and plaintiff:
            lawyer_id = f"lawyer_{hash(plaintiff_lawyer)}_p"
            elements.append({
                'data': {
                    'id': lawyer_id,
                    'label': plaintiff_lawyer[:15] + "..." if len(plaintiff_lawyer) > 15 else plaintiff_lawyer,
                    'type': 'Lawyer',
                    'details': {'name': plaintiff_lawyer, 'role': '原告律师'}
                }
            })
            elements.append({
                'data': {
                    'source': lawyer_id,
                    'target': plaintiff_id,
                    'label': '代理',
                    'type': 'REPRESENTS'
                }
            })
        
        # 被告律师和关系
        defendant_lawyer = case_data.get('defendant_lawyer', '').strip()
        if defendant_lawyer and defendant:
            lawyer_id = f"lawyer_{hash(defendant_lawyer)}_d"
            elements.append({
                'data': {
                    'id': lawyer_id,
                    'label': defendant_lawyer[:15] + "..." if len(defendant_lawyer) > 15 else defendant_lawyer,
                    'type': 'Lawyer',
                    'details': {'name': defendant_lawyer, 'role': '被告律师'}
                }
            })
            elements.append({
                'data': {
                    'source': lawyer_id,
                    'target': defendant_id,
                    'label': '代理',
                    'type': 'REPRESENTS'
                }
            })
        
        return elements
    
    def setup_callbacks(self):
        """设置回调函数"""
        
        # 表格选择回调
        @self.app.callback(
            Output('enter-graph-button', 'disabled'),
            Input('cases-table', 'selected_rows')
        )
        def enable_enter_button(selected_rows):
            return len(selected_rows) == 0
        
        # 搜索功能
        @self.app.callback(
            Output('cases-table', 'data'),
            [Input('search-button', 'n_clicks')],
            [State('search-input', 'value')]
        )
        def search_cases(n_clicks, search_value):
            if not search_value:
                return self.create_cases_table_data()
            
            filtered_data = []
            search_lower = search_value.lower()
            
            for i, case in enumerate(self.cases_data):
                # 搜索多个字段
                search_fields = [
                    case.get('case_number', ''),
                    case.get('file_name', ''),
                    case.get('plaintiff', ''),
                    case.get('defendant', ''),
                    case.get('judge', ''),
                    case.get('case_type', '')
                ]
                
                if any(search_lower in str(field).lower() for field in search_fields):
                    filtered_data.append({
                        'id': i,
                        'case_number': case.get('case_number', ''),
                        'file_name': case.get('file_name', ''),
                        'trial_date': case.get('trial_date', ''),
                        'case_type': case.get('case_type', ''),
                        'judgment_result': case.get('judgment_result', ''),
                        'language': case.get('language', '')
                    })
            
            return filtered_data
        
        # 进入知识图谱回调
        @self.app.callback(
            [Output('tabs', 'value'),
             Output('selected-case-data', 'data')],
            [Input('enter-graph-button', 'n_clicks')],
            [State('cases-table', 'selected_rows'),
             State('cases-table', 'data')]
        )
        def enter_knowledge_graph(n_clicks, selected_rows, table_data):
            if n_clicks > 0 and selected_rows:
                selected_case_id = table_data[selected_rows[0]]['id']
                selected_case = self.cases_data[selected_case_id]
                return 'knowledge-graph', selected_case
            return 'case-selection', {}
        
        # 返回案件选择回调
        @self.app.callback(
            Output('tabs', 'value', allow_duplicate=True),
            Input('back-to-selection-button', 'n_clicks'),
            prevent_initial_call=True
        )
        def back_to_selection(n_clicks):
            if n_clicks > 0:
                return 'case-selection'
            return 'knowledge-graph'
        
        # 显示选中案件信息
        @self.app.callback(
            Output('selected-case-info', 'children'),
            Input('selected-case-data', 'data')
        )
        def display_selected_case_info(case_data):
            if not case_data:
                return html.Div("请先选择案件")
            
            return html.Div([
                html.H3(f"案件: {case_data.get('case_number', '未知')}", 
                       style={'color': '#2c3e50', 'marginBottom': '10px'}),
                html.Div([
                    html.Span(f"案件类型: {case_data.get('case_type', '未知')}", 
                             style={'marginRight': '20px'}),
                    html.Span(f"判决结果: {case_data.get('judgment_result', '未知')}", 
                             style={'marginRight': '20px'}),
                    html.Span(f"审理日期: {case_data.get('trial_date', '未知')}")
                ], style={'color': '#7f8c8d'})
            ], style={
                'padding': '15px',
                'backgroundColor': '#ecf0f1',
                'borderRadius': '5px',
                'border': '1px solid #bdc3c7'
            })
        
        # 更新知识图谱
        @self.app.callback(
            [Output('knowledge-graph', 'elements'),
             Output('knowledge-graph', 'layout')],
            [Input('selected-case-data', 'data'),
             Input('layout-dropdown', 'value'),
             Input('relationship-filter', 'value')]
        )
        def update_knowledge_graph(case_data, layout_name, relationship_filter):
            if not case_data:
                return [], {'name': layout_name}
            
            # 创建图谱元素
            elements = self.create_case_graph(case_data)
            
            # 根据关系筛选过滤边
            if relationship_filter:
                filtered_elements = []
                for element in elements:
                    if 'source' in element['data']:  # 这是一条边
                        if element['data'].get('type') in relationship_filter:
                            filtered_elements.append(element)
                    else:  # 这是一个节点
                        filtered_elements.append(element)
                elements = filtered_elements
            
            layout = {'name': layout_name, 'nodeSpacing': 100, 'edgeElasticity': 100}
            return elements, layout
        
        # 节点点击显示详情
        @self.app.callback(
            Output('node-details', 'children'),
            Input('knowledge-graph', 'tapNodeData')
        )
        def display_node_details(node_data):
            if not node_data:
                return html.P("点击节点查看详细信息")
            
            details = node_data.get('details', {})
            node_type = node_data.get('type', 'Unknown')
            
            if node_type == 'Case':
                return html.Div([
                    html.H4(f"案件详情: {details.get('case_number', 'N/A')}"),
                    html.P(f"文件名: {details.get('file_name', 'N/A')}"),
                    html.P(f"案件类型: {details.get('case_type', 'N/A')}"),
                    html.P(f"判决结果: {details.get('judgment_result', 'N/A')}"),
                    html.P(f"申请金额: {details.get('claim_amount', 'N/A')}"),
                    html.P(f"判决金额: {details.get('judgment_amount', 'N/A')}")
                ])
            else:
                return html.Div([
                    html.H4(f"{node_type} 详情"),
                    html.P(f"姓名: {details.get('name', 'N/A')}"),
                    html.P(f"角色: {details.get('role', details.get('type', 'N/A'))}")
                ])
    
    def run(self, host: str = "127.0.0.1", port: int = 8051, debug: bool = False):
        """运行应用"""
        print(f"[>] 启动案件选择式知识图谱系统")
        print(f"[>] 访问地址: http://{host}:{port}")
        print(f"[>] 共加载 {len(self.cases_data)} 个案件")
        
        self.app.run(host=host, port=port, debug=debug)

def main():
    """主函数"""
    data_file = "output/llm_analysis_20250603_110724.json"
    
    if not Path(data_file).exists():
        print(f"[!] 数据文件不存在: {data_file}")
        print(f"[>] 请先运行 LLM 分析生成数据文件")
        return
    
    # 设置日志
    logging.basicConfig(level=logging.INFO)
    
    # 创建并运行应用
    app = CaseSelectionKnowledgeGraph(data_file)
    app.run(debug=False)

if __name__ == "__main__":
    main() 