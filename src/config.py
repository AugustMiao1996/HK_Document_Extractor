#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件
Configuration for Hong Kong Court Document Extractor

Author: AI Assistant
Version: 1.0
"""

# 支持的文档类型
SUPPORTED_DOCUMENT_TYPES = [
    'HCA',    # High Court of Appeal
    'HCAL',   # High Court Administrative Law
    'CACC',   # Court of Appeal Criminal Cases
    'CAMP',   # Court of Appeal Miscellaneous Proceedings
    'CACV',   # Court of Appeal Civil
    'DCCC',   # District Court Criminal Cases
    'DCMP',   # District Court Miscellaneous Proceedings
    'DCCJ',   # District Court Civil Jurisdiction
    'LD',     # Labor Department
    'HC',     # High Court
    'FCMC'    # Family Court Miscellaneous Cases
]

# 提取规则配置
EXTRACTION_RULES = {
    'english': {
        'trial_date': {
            'patterns': [
                r'Date of Hearing:\s*([^\n]+)',
                r'Hearing Date:\s*([^\n]+)',
                r'Date of Decision:\s*([^\n]+)'
            ],
            'description': '提取审理日期'
        },
        'court_name': {
            'patterns': [
                r'IN THE (.*?COURT.*?)(?=\n|ACTION)',
                r'IN THE (.*?COURT.*?)(?=\n|PROCEEDING)',
            ],
            'description': '提取完整法庭名称'
        },
        'case_number': {
            'patterns': [
                r'ACTION NO\s+(\d+\s+OF\s+\d+)',      # ACTION NO 1812 OF 2022
                r'HCMP\s+(\d+/\d+)',                  # HCMP 1803/2024
                r'HCA\s+(\d+/\d+)',                   # HCA 1812/2022
                r'HCAL\s+(\d+/\d+)',                  # HCAL 001031/2025
                r'CACC\s+(\d+/\d+)',                  # CACC 000111A/2022
                r'DCCC\s+(\d+/\d+)',                  # DCCC 000055/2025
            ],
            'description': '提取完整案件编号'
        },
        'plaintiff': {
            'patterns': [
                r'BETWEEN\s*(.*?)\s*Plaintiff',
                r'APPLICANT\s*(.*?)(?=\n|and)',
            ],
            'description': '提取原告/申请人信息'
        },
        'defendant': {
            'patterns': [
                r'and\s*(.*?)(?=Before:|\n\n)',
                r'RESPONDENT\s*(.*?)(?=\n\n|Before:)',
            ],
            'description': '提取被告/被申请人信息'
        },
        'case_type': {
            'patterns': [
                r'applications? before me:.*?(?=\n\n|Before:)',
                r'There are.*?applications?.*?(?=\n\n)',
                r'This is.*?(?:action|application|proceeding).*?(?=\n)',
                r'The (?:present|instant) (?:action|application|proceeding).*?(?=\n\n)',
            ],
            'description': '提取案件类型描述段落'
        },
        'judgment_result': {
            'patterns': [
                r'(?:dismissed|granted|ordered|held).*?(?=\n\n)',
                r'(?:decision|judgment|ruling|order).*?(?=\n\n)',
                r'I (?:dismiss|grant|order|hold).*?(?=\n)',
                r'(?:CONCLUSION|DISPOSITION).*?(?=\n\n)',
            ],
            'description': '提取判决结果相关段落'
        },
        'amount_keywords': {
            'claim': ['claim', 'damage', 'sum', 'amount', 'cost', 'fee', 'security', 'value'],
            'judgment': ['order', 'grant', 'award', 'judgment', 'dismiss', 'costs', 'assess', 'injunction', 'freeze']
        },
        'currency_pattern': r'(?:HK\$|USD|US\$|\$|€|£)\s*[\d,\.]+'
    },
    'chinese': {
        'trial_date': {
            'patterns': [
                r'聆訊日期[：:]\s*([^\n]+)',
                r'審訊日期[：:]\s*([^\n]+)',
                r'開庭日期[：:]\s*([^\n]+)',
            ],
            'description': '提取中文审理日期'
        },
        'court_name': {
            'patterns': [
                r'香港特別行政區(.*?法院.*?)(?=\n|案件)',
                r'在(.*?法院.*?)(?=\n|案件)',
            ],
            'description': '提取中文法庭名称'
        },
        'case_number': {
            'patterns': [
                r'案件編號[：:]\s*([^\n]+)',
                r'民事案件編號[：:]\s*([^\n]+)',
                r'刑事案件編號[：:]\s*([^\n]+)',
            ],
            'description': '提取中文案件编号'
        },
        'amount_keywords': {
            'claim': ['申請', '損害', '金額', '費用', '保證金', '擔保'],
            'judgment': ['判決', '裁定', '命令', '費用', '評估', '禁令', '凍結']
        },
        'currency_pattern': r'(?:港幣|港元|HK\$|USD|\$)[\d,\.]+'
    }
}

# 输出配置
OUTPUT_CONFIG = {
    'formats': ['json', 'csv', 'excel'],
    'encoding': 'utf-8',
    'fields_order': [
        'file_name',
        'language',
        'case_number',
        'trial_date',
        'court_name',
        'plaintiff',
        'defendant',
        'case_type',
        'judgment_result',
        'claim_amount',
        'judgment_amount',
        'file_path',
        'text_length'
    ]
}

# 日志配置
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file_encoding': 'utf-8'
}

# PDF处理配置
PDF_CONFIG = {
    'preferred_libraries': ['fitz', 'pdfplumber', 'PyPDF2'],
    'max_file_size_mb': 100,
    'timeout_seconds': 300,
    'encoding_fallback': 'utf-8'
}

# 语言检测配置
LANGUAGE_DETECTION = {
    'sample_tokens': 50,
    'chinese_threshold': 0.5,
    'chinese_unicode_range': ('\u4e00', '\u9fff')
}

# 段落提取配置
PARAGRAPH_CONFIG = {
    'min_paragraph_length': 50,
    'max_segments_per_field': 3,
    'paragraph_separator': r'\n\s*\n'
}

# 错误处理配置
ERROR_HANDLING = {
    'continue_on_error': True,
    'max_retries': 3,
    'retry_delay_seconds': 1
} 