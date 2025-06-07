#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
香港法庭文书信息提取器
Core Document Information Extractor for Hong Kong Court Documents

性能优化说明：
- 法庭名称：第1页开头必有，无需全文搜索
- 审判日期：前2页头部区域必有，无需全文搜索  
- 案件编号：第1页顶部必有，无需全文搜索
- 当事人信息：前3页必有，无需全文搜索

Author: AI Assistant
Version: 1.1 - 前页优化版
"""

import sys
import os
import re
import logging
from typing import Dict, Optional, List
from pathlib import Path

# 设置输出编码
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 导入中文文档处理器
try:
    # 尝试从父目录导入
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
    from chinese_document_extractor import ChineseDocumentExtractor
except ImportError:
    # 如果导入失败，创建一个简单的占位符
    ChineseDocumentExtractor = None

class DocumentExtractor:
    """香港法庭文书信息提取器"""
    
    def __init__(self, log_level=logging.INFO):
        """初始化提取器"""
        self.logger = self._setup_logger(log_level)
        
        # 初始化中文文档处理器
        if ChineseDocumentExtractor:
            self.chinese_extractor = ChineseDocumentExtractor(log_level)
        else:
            self.chinese_extractor = None
            self.logger.warning("Chinese document extractor not available")
        
    def _setup_logger(self, log_level):
        """设置日志"""
        logger = logging.getLogger('DocumentExtractor')
        logger.setLevel(log_level)
        
        # 避免重复添加handler
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def extract_pdf_text(self, pdf_path: str) -> Optional[str]:
        """
        从PDF文件提取文本内容
        
        Args:
            pdf_path: PDF文件路径
            
        Returns:
            提取的文本内容，失败返回None
        """
        text = ""
        
        # 尝试PyPDF2
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                for i, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        text += page_text + "\n"
                    except Exception as e:
                        self.logger.warning(f"Error extracting page {i}: {e}")
                        continue
            self.logger.info(f"PyPDF2: Successfully extracted {len(reader.pages)} pages")
            if text:
                text = self._clean_pdf_index_artifacts(text)
            return text
        except Exception as e:
            self.logger.warning(f"PyPDF2 failed: {e}")
        
        # 尝试pymupdf (fitz)
        try:
            import fitz
            doc = fitz.open(pdf_path)
            text = ""
            for page_num in range(len(doc)):
                try:
                    page = doc.load_page(page_num)
                    page_text = page.get_text()
                    # 处理编码问题
                    page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                    text += page_text + "\n"
                except Exception as e:
                    self.logger.warning(f"Error extracting page {page_num}: {e}")
                    continue
            self.logger.info(f"Fitz: Successfully extracted {len(doc)} pages")
            doc.close()
            if text:
                text = self._clean_pdf_index_artifacts(text)
            return text
        except Exception as e:
            self.logger.warning(f"Fitz failed: {e}")
        
        # 尝试pdfplumber
        try:
            import pdfplumber
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text() or ""
                        # 处理编码问题
                        page_text = page_text.encode('utf-8', errors='ignore').decode('utf-8')
                        text += page_text + "\n"
                    except Exception as e:
                        self.logger.warning(f"Error extracting page {i}: {e}")
                        continue
            self.logger.info(f"Pdfplumber: Successfully extracted {len(pdf.pages)} pages")
            if text:
                text = self._clean_pdf_index_artifacts(text)
            return text
        except Exception as e:
            self.logger.warning(f"Pdfplumber failed: {e}")
        
        self.logger.error("All PDF extraction methods failed")
        return None
    
    def _clean_pdf_index_artifacts(self, text: str) -> str:
        """
        清理PDF索引干扰内容，跳过A、B、C、D等单字母行
        专门处理Motion/AM类型文件的格式问题
        增强版：保护法院名称和案件编号区域
        """
        if not text:
            return text
        
        lines = text.split('\n')
        
        # 首先检查前50行是否包含重要的法院信息，如果有则不进行清理
        early_lines = '\n'.join(lines[:50])
        critical_keywords = [
            'IN THE HIGH COURT', 'IN THE DISTRICT COURT', 'ACTION NO', 'CIVIL ACTION NO',
            'COURT OF FIRST INSTANCE', 'HCA', 'DCCJ', 'BETWEEN', 'PLAINTIFF', 'DEFENDANT'
        ]
        
        # 如果前50行包含关键法院信息，则跳过清理
        if any(keyword in early_lines.upper() for keyword in critical_keywords):
            self.logger.info("检测到关键法院信息，完全跳过PDF清理以保护第一页内容")
            return text
        
        # 检测是否有索引模式：连续的单字母行 (A, B, C, D...)
        consecutive_single_letters = 0
        index_start = -1
        content_start = -1
        max_consecutive = 0
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检查是否是单字母行（可能包含少量空格）
            if re.match(r'^[A-Z]\s*$', line_stripped):
                if consecutive_single_letters == 0:
                    index_start = i
                consecutive_single_letters += 1
                max_consecutive = max(max_consecutive, consecutive_single_letters)
            elif consecutive_single_letters > 0:
                # 如果已经有连续的单字母，检查是否到了内容区
                if (max_consecutive >= 15 and  # 提高阈值到15个
                    any(keyword in line_stripped.upper() for keyword in [
                        'HCA', 'HKCFI', 'HIGH COURT', 'COURT OF', 'BETWEEN', 'PLAINTIFF', 'DEFENDANT', 'ACTION NO'
                    ])):
                    content_start = i
                    break
                # 如果不是内容行，但遇到空行，继续计数
                elif line_stripped == '':
                    continue
                # 遇到其他内容，重置计数
                else:
                    consecutive_single_letters = 0
                    index_start = -1
        
        # 如果发现了索引模式且找到了内容开始位置
        if max_consecutive >= 10 and content_start > 0:
            self.logger.info(f"检测到PDF索引干扰：跳过前{content_start}行（{max_consecutive}个单字母行）")
            cleaned_lines = lines[content_start:]
            cleaned_text = '\n'.join(cleaned_lines)
            
            # 验证清理效果
            if len(cleaned_text) > 200 and any(keyword in cleaned_text.upper() for keyword in [
                'HIGH COURT', 'COURT', 'PLAINTIFF', 'DEFENDANT', 'BETWEEN', 'HCA'
            ]):
                self.logger.info(f"成功清理PDF索引，文本长度从{len(text)}减少到{len(cleaned_text)}")
                return cleaned_text
        
        # 备用策略：如果前50%的行都是单字母，尝试查找第一个实质内容
        if len(lines) > 50:
            single_letter_count = 0
            for i in range(min(100, len(lines))):
                line = lines[i].strip()
                if re.match(r'^[A-Z]\s*$', line):
                    single_letter_count += 1
            
            # 如果前100行中超过30%是单字母行，使用更宽松的策略
            if single_letter_count > 30:
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    if any(keyword in line_stripped.upper() for keyword in [
                        'HCA', 'HKCFI', 'HIGH COURT', 'COURT OF FIRST', 'ACTION NO'
                    ]):
                        self.logger.info(f"备用策略：从第{i}行开始提取内容（单字母行占比{single_letter_count}%）")
                        cleaned_lines = lines[i:]
                        cleaned_text = '\n'.join(cleaned_lines)
                        if len(cleaned_text) > 500:
                            return cleaned_text
        
        # 如果没有发现明显的索引模式，返回原文本
        return text
    
    def detect_language(self, text: str) -> str:
        """检测文档语言"""
        if not text:
            self.logger.warning("Empty text for language detection")
            return 'english'
        
        # 取前200个词进行检测
        words = text.split()[:200]
        analysis_text = ' '.join(words)
        
        # 简单判断：如果包含"被告"就是中文文档
        is_chinese = '被告' in analysis_text
        language = 'chinese' if is_chinese else 'english'
                
        self.logger.info(f"Language detected: {language} (contains '被告': {is_chinese})")
        return language

    def extract_trial_date(self, text: str, language: str, file_name: str = "") -> str:
        """提取审理日期 - 根据文档类型使用专门的提取策略"""
        if language == 'english':
            # 针对前几页优化的模式，简化匹配逻辑
            patterns = [
                r'Dates of Hearing\s*:?\s*([^\n]+)',
                r'Date of Decision\s*:?\s*([^\n]+)',
                r'Date of Judgment\s*:?\s*([^\n]+)',
                r'Date of Trial\s*:?\s*([^\n]+)',
                r'Date of Hearing\s*:?\s*([^\n]+)',
                r'Hearing Date\s*:?\s*([^\n]+)',
                # 通用模式
                r'Date of (?:Hearing|Decision|Judgment|Trial|Decision on Costs)\s*:?\s*([^\n]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1).strip()
                    cleaned_date = self._clean_trial_date(date_str)
                    if cleaned_date and len(cleaned_date) > 5:
                        self.logger.info(f"Found trial date: {cleaned_date}")
                        return cleaned_date
        else:
            # 中文模式，针对前几页优化
            patterns = [
                r'聆訊日期\s*[：:︰]\s*([^\n]+)',
                r'判決日期\s*[：:︰]\s*([^\n]+)',
                r'判案書日期\s*[：:︰]\s*([^\n]+)',
                r'審訊日期\s*[：:︰]\s*([^\n]+)',
                r'開庭日期\s*[：:︰]\s*([^\n]+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    date_str = match.group(1).strip()
                    cleaned_date = self._clean_trial_date(date_str)
                    if cleaned_date and len(cleaned_date) > 3:
                        self.logger.info(f"Found Chinese trial date: {cleaned_date}")
                        return cleaned_date
        return ""
    
    def _clean_trial_date(self, date_str: str) -> str:
        """清理提取的日期字符串"""
        if not date_str:
            return ""
        
        cleaned = re.sub(r'\s+', ' ', date_str.strip())
        cleaned = re.sub(r'\s*-\s*\d+\s*-\s*', '', cleaned)
        cleaned = re.sub(r'\s*第\s*\d+\s*页.*$', '', cleaned)
        cleaned = re.sub(r'\s+(?:and|&|及)\s*$', '', cleaned)
        cleaned = re.sub(r'\s*(?:Date of|Before|Hon\.|J\.|in Chambers?|in Court).*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(?:Reasons? for|REASONS).*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(?:DECISION|JUDGMENT|D E C I S I O N|J U D G M E N T).*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(?:原告人|被告人|判案書|主審法官).*$', '', cleaned)
        cleaned = re.sub(r'\s*(?:進一步陳詞日期|最後書面陳詞日期).*$', '', cleaned)
        cleaned = re.sub(r'\s*_{5,}.*$', '', cleaned)
        cleaned = re.sub(r'\s*(?:Introduction|This is an? application|made by).*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'[,\s]+$', '', cleaned)
        cleaned = re.sub(r'^[,\s]+', '', cleaned)
        
        if len(cleaned) > 150:
            sentences = re.split(r'[.!?]\s+', cleaned)
            if sentences and len(sentences[0]) > 10:
                cleaned = sentences[0]
            else:
                cleaned = cleaned[:150]
        
        if re.search(r'(?:page|頁|第.*號)', cleaned, re.IGNORECASE):
            date_match = re.search(r'((?:\d{1,2}[-/]\d{1,2}[-/]\d{4}|\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日|\d{1,2}\s+\w+\s+\d{4})+)', cleaned)
            if date_match:
                cleaned = date_match.group(1)
        
        return cleaned.strip()
    
    def extract_court_name(self, text: str, language: str) -> str:
        """提取法庭名称 - 优化版（针对前4页内容，支持跨行匹配）"""
        if language == 'english':
            # 针对前几页优化的模式，法庭名称必定在第1页开头，支持跨行
            patterns = [
                # 跨行匹配的完整格式 - 使用DOTALL模式
                r'IN THE\s+(HIGH COURT OF THE\s+HONG KONG SPECIAL ADMINISTRATIVE REGION\s+COURT OF FIRST INSTANCE)',
                r'IN THE\s+(HIGH COURT OF THE\s+HONG KONG SPECIAL ADMINISTRATIVE REGION\s+COURT OF APPEAL)',
                r'IN THE\s+(COURT OF FIRST INSTANCE\s+OF THE HIGH COURT)',
                # 更灵活的跨行匹配
                r'IN THE\s+(HIGH COURT OF THE[^\n]*?\n[^\n]*?HONG KONG SPECIAL ADMINISTRATIVE REGION[^\n]*?\n[^\n]*?COURT OF FIRST INSTANCE)',
                r'IN THE\s+(HIGH COURT OF THE[^\n]*?\n[^\n]*?HONG KONG SPECIAL ADMINISTRATIVE REGION[^\n]*?\n[^\n]*?COURT OF APPEAL)',
                # 简化格式的跨行匹配
                r'IN THE\s+(.*?COURT OF FIRST INSTANCE)',
                r'IN THE\s+(.*?COURT OF APPEAL)',
                r'IN THE\s+(HIGH COURT OF THE\s+HONG KONG SPECIAL ADMINISTRATIVE REGION)',
                # 兜底模式
                r'IN THE\s+(.*?HIGH COURT.*?)(?=ACTION|PROCEEDING|BETWEEN)',
                r'IN THE\s+(.*?COURT.*?)(?=ACTION|PROCEEDING|BETWEEN)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if match:
                    court_name = match.group(1).strip()
                    court_name = self._clean_court_name(court_name)
                    if self._validate_court_name(court_name, language):
                        self.logger.info(f"Found court name: {court_name[:50]}...")
                        return court_name
        else:
            # 中文模式，针对前几页优化
            patterns = [
                r'(香港特別行政區高等法院原訟法庭)',
                r'(香港特別行政區高等法院)',
                r'(香\s*港\s*特\s*別\s*行\s*政\s*區\s*高等法院原訟法庭)',
                r'(香\s*港\s*特\s*別\s*行\s*政\s*區\s*高等法院)',
                r'(高等法院原訟法庭)',
                r'(.*?高等法院.*?原訟法庭)',
                r'(.*?高等法院.*?法庭)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    court_name = match.group(1).strip()
                    court_name = self._clean_court_name(court_name)
                    if self._validate_court_name(court_name, language):
                        self.logger.info(f"Found Chinese court name: {court_name}")
                        return court_name
        return ""
    
    def _clean_court_name(self, court_name: str) -> str:
        """清理法庭名称"""
        if not court_name:
            return ""
        
        cleaned = re.sub(r'\s+', ' ', court_name.strip())
        
        # 特殊处理：标准化中文法院名称的空格
        # 将"香 港 特 別 行 政 區"标准化为"香港特別行政區"
        cleaned = re.sub(r'香\s*港\s*特\s*別\s*行\s*政\s*區', '香港特別行政區', cleaned)
        # 去除"香港特別行政區"和"高等法院"之间的多余空格
        cleaned = re.sub(r'香港特別行政區\s+高等法院', '香港特別行政區高等法院', cleaned)
        
        cleaned = re.sub(r'\s*-\s*\d+\s*-.*$', '', cleaned)
        cleaned = re.sub(r'\s*_{5,}.*$', '', cleaned)
        cleaned = re.sub(r'\s*(?:ACTION NO\.|PROCEEDING|BETWEEN).*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\s*(?:案件編號|民事訴訟案件|原告人|被告人).*$', '', cleaned)
        
        return cleaned.strip()
    
    def _validate_court_name(self, court_name: str, language: str) -> bool:
        """验证法庭名称的合理性"""
        if not court_name or len(court_name) < 5:
            return False
        
        if len(court_name) > 200:
            return False
        
        if language == 'english':
            if 'COURT' not in court_name.upper():
                return False
            
            bad_words = ['BETWEEN', 'PLAINTIFF', 'DEFENDANT', 'ACTION NO', 'PROCEEDING', 'BEFORE']
            if any(word in court_name.upper() for word in bad_words):
                return False
                
            good_indicators = ['HIGH COURT', 'COURT OF FIRST INSTANCE', 'HONG KONG', 'ADMINISTRATIVE REGION']
            if any(indicator in court_name.upper() for indicator in good_indicators):
                return True
                
            return len(court_name) <= 100
            
        else:
            if not any(keyword in court_name for keyword in ['法院', '法庭']):
                return False
            
            bad_words = ['原告', '被告', '案件編號', '申請', '判決', '上訴', '評估', '考慮', '決定']
            if any(word in court_name for word in bad_words):
                return False
                
            good_indicators = ['香港特別行政區', '高等法院', '原訟法庭', '民事司法管轄']
            if any(indicator in court_name for indicator in good_indicators):
                return True
                
            return len(court_name) <= 50
        
        return False
    
    def extract_case_number(self, text: str, language: str) -> str:
        """提取完整案件编号 - 简化版：直接查找ACTION开头的行"""
        if language == 'english':
            # 简单有效的方法：直接在前两页查找ACTION开头的完整行
            case_number = self._extract_action_line_directly(text)
            if case_number:
                self.logger.info(f"Found ACTION line directly: '{case_number}'")
                return case_number
            
            # 备用策略：HCA格式转换
            hca_match = re.search(r'HCA\s+(\d+[A-Z]?)/(\d{4})', text[:15000], re.IGNORECASE)
            if hca_match:
                groups = hca_match.groups()
                case_number = f"ACTION NO {groups[0]} OF {groups[1]}"
                self.logger.info(f"Found and converted HCA format: '{case_number}'")
                return case_number
                    
        else:
            # 中文案件编号提取 - 同样优先考虑位置
            case_number = self._extract_chinese_case_number_positioned(text)
            if case_number:
                return case_number
            
            # 回退模式
            patterns = [
                r'(高院民事訴訟\s*\d+\s*年\s*第\s*\d+[A-Z]?\s*號)',
                r'((?:高院)?民事訴訟案件(?:編號)?\s*\d+\s*年\s*第\s*\d+[A-Z]?\s*號)',
                r'(ACTION NO\.?\s*\d+[A-Z]?\s+OF\s+\d{4})',
                r'(HCA\d{6}[A-Z]?_\d{4})',
                r'(HCA\s+\d+[A-Z]?/\d{4})',
            ]
            
            text_start = text[:min(len(text), 15000)]
            for pattern in patterns:
                match = re.search(pattern, text_start)
                if match:
                    case_number = re.sub(r'\s+', ' ', match.group(1).strip())
                    self.logger.info(f"Found Chinese case number: '{case_number}'")
                    return case_number
                    
        self.logger.warning("No case number found in document")
        return ""
    
    def _extract_action_line_directly(self, text: str) -> str:
        """直接提取ACTION开头的完整行 - 最简单有效的方法"""
        # 取前两页内容（约15000字符）
        text_start = text[:15000]
        lines = text_start.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # 查找以ACTION开头的行，支持ACTION和NO分离的情况
            if line.upper().startswith('ACTION'):
                self.logger.info(f"Found ACTION line at line {i}: '{line}'")
                
                # 检查这行是否已经包含完整的案件编号
                # 完整格式应该是: ACTION NO xxx OF yyyy
                # 支持: ACTION NO, ACTION N O, ACTION NO ., ACTION NO. 等格式
                if re.match(r'ACTION\s+(?:N\s+)?O\s*\.?\s*\d+[A-Z]?\s+OF\s+\d{4}', line, re.IGNORECASE):
                    # 已经完整，直接返回
                    cleaned_line = re.sub(r'\s+', ' ', line.strip())
                    # 修复ACTION N O -> ACTION NO
                    cleaned_line = re.sub(r'ACTION\s+N\s+O\b', 'ACTION NO', cleaned_line, flags=re.IGNORECASE)
                    # 修复NO . -> NO
                    cleaned_line = re.sub(r'NO\s*\.\s*', 'NO ', cleaned_line, flags=re.IGNORECASE)
                    return cleaned_line
                elif re.match(r'ACTION\s+(?:N\s+)?O\s*\.?\s*\d+[A-Z]?\s+OF\s+\d{2,3}\s+\d{1,2}', line, re.IGNORECASE):
                    # 年份有空格，需要清理 - 支持各种分割模式: 20 22, 202 5, 20 5 等
                    cleaned_line = re.sub(r'(\bOF\s+)(\d{2,3})\s+(\d{1,2})', r'\1\2\3', line.strip())
                    # 修复ACTION N O -> ACTION NO
                    cleaned_line = re.sub(r'ACTION\s+N\s+O\b', 'ACTION NO', cleaned_line, flags=re.IGNORECASE)
                    # 修复NO . -> NO
                    cleaned_line = re.sub(r'NO\s*\.\s*', 'NO ', cleaned_line, flags=re.IGNORECASE)
                    cleaned_line = re.sub(r'\s+', ' ', cleaned_line)
                    return cleaned_line
                
                # 如果不完整，尝试与下一行组合
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    combined = f"{line} {next_line}"
                    
                    # 检查组合后是否完整
                    if re.match(r'ACTION\s+(?:N\s+)?O\s*\.?\s*\d+[A-Z]?\s+OF\s+\d{4}', combined, re.IGNORECASE):
                        cleaned_combined = re.sub(r'\s+', ' ', combined.strip())
                        # 修复ACTION N O -> ACTION NO
                        cleaned_combined = re.sub(r'ACTION\s+N\s+O\b', 'ACTION NO', cleaned_combined, flags=re.IGNORECASE)
                        # 修复NO . -> NO
                        cleaned_combined = re.sub(r'NO\s*\.\s*', 'NO ', cleaned_combined, flags=re.IGNORECASE)
                        return cleaned_combined
                    elif re.match(r'ACTION\s+(?:N\s+)?O\s*\.?\s*\d+[A-Z]?\s+OF\s+\d{2,3}\s+\d{1,2}', combined, re.IGNORECASE):
                        # 组合后年份有空格，需要清理 - 支持各种分割模式
                        cleaned_combined = re.sub(r'(\bOF\s+)(\d{2,3})\s+(\d{1,2})', r'\1\2\3', combined.strip())
                        # 修复ACTION N O -> ACTION NO
                        cleaned_combined = re.sub(r'ACTION\s+N\s+O\b', 'ACTION NO', cleaned_combined, flags=re.IGNORECASE)
                        # 修复NO . -> NO
                        cleaned_combined = re.sub(r'NO\s*\.\s*', 'NO ', cleaned_combined, flags=re.IGNORECASE)
                        cleaned_combined = re.sub(r'\s+', ' ', cleaned_combined)
                        return cleaned_combined
                
                # 如果还不完整，尝试在当前行附近查找年份
                # 在前后3行范围内查找4位年份
                start_search = max(0, i - 3)
                end_search = min(len(lines), i + 4)
                
                for j in range(start_search, end_search):
                    year_match = re.search(r'20[0-9]{2}', lines[j])
                    if year_match:
                        year = year_match.group()
                        
                        # 从ACTION行提取案件号
                        number_match = re.search(r'NO\.?\s*(\d+[A-Z]?)', line, re.IGNORECASE)
                        if number_match:
                            number = number_match.group(1)
                            case_number = f"ACTION NO {number} OF {year}"
                            self.logger.info(f"Constructed case number: '{case_number}' from line {i} and year from line {j}")
                            return case_number
                
                # 如果找到ACTION但无法构建完整案件号，至少返回找到的部分
                if re.search(r'(?:N\s+)?O\s*\.?\s*\d+', line, re.IGNORECASE):
                    self.logger.warning(f"Found incomplete ACTION line: '{line}'")
                    cleaned_line = re.sub(r'\s+', ' ', line.strip())
                    # 修复ACTION N O -> ACTION NO
                    cleaned_line = re.sub(r'ACTION\s+N\s+O\b', 'ACTION NO', cleaned_line, flags=re.IGNORECASE)
                    # 修复NO . -> NO
                    cleaned_line = re.sub(r'NO\s*\.\s*', 'NO ', cleaned_line, flags=re.IGNORECASE)
                    return cleaned_line
        
        return ""
    
    def _extract_case_number_between_court_and_parties(self, text: str) -> str:
        """在法院名称和当事人之间提取案件编号"""
        # 查找法院名称结束位置
        court_patterns = [
            r'HIGH COURT OF THE HONG KONG SPECIAL ADMINISTRATIVE REGION',
            r'COURT OF FIRST INSTANCE',
            r'ADMINISTRATIVE LAW LIST',
            r'CONSTITUTIONAL AND ADMINISTRATIVE LAW LIST',
            r'高等法院.*?上訴法庭',
            r'香港特別行政區.*?高等法院',
        ]
        
        court_end_pos = 0
        for pattern in court_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                court_end_pos = max(court_end_pos, match.end())
        
        if court_end_pos == 0:
            return ""
        
        # 查找BETWEEN或当事人开始位置
        parties_patterns = [
            r'BETWEEN',
            r'原告人',
            r'被告人',
            r'申請人',
        ]
        
        parties_start_pos = len(text)
        for pattern in parties_patterns:
            match = re.search(pattern, text[court_end_pos:], re.IGNORECASE)
            if match:
                parties_start_pos = min(parties_start_pos, court_end_pos + match.start())
        
        if parties_start_pos == len(text):
            return ""
        
        # 在法院名称和当事人之间查找案件编号
        middle_section = text[court_end_pos:parties_start_pos]
        
        # 案件编号模式 - 针对中间区域优化
        case_patterns = [
            # 优先匹配：ACTION NO xxx OF yyyy 格式
            r'ACTION\s+NO\.?\s*(\d+[A-Z]?)\s+OF\s+(\d{4})',
            # 标准格式：NO xxx OF yyyy
            r'NO\.?\s*(\d+[A-Z]?)\s+OF\s+(\d{4})',
            # 新增：HCA xxx/yyyy 格式转换为标准格式
            r'HCA\s+(\d+[A-Z]?)/(\d{4})',
            # 新增：HIGH COURT ACTION NO xxx OF yyyy 格式  
            r'HIGH COURT ACTION NO\.?\s*(\d+[A-Z]?)\s+OF\s+(\d{4})',
            # CACV xxx, xxx, xxx/yyyy 格式
            r'(CACV\s+\d+(?:[A-Z]?)(?:\s*,\s*\d+(?:[A-Z]?))*)(?:/(\d{4})|(?:\s+OF\s+(\d{4})))',
            # 中文格式：2022年第 342, 463 & 487 號
            r'(\d{4})年第\s*(\d+(?:\s*,\s*\d+)*(?:\s*&\s*\d+)*)\s*號',
            # 其他标准格式
            r'(HCAL|HCMP|HCPI)\s+NO\.?\s*(\d+[A-Z]?)\s+OF\s+(\d{4})',
        ]
        
        for pattern in case_patterns:
            match = re.search(pattern, middle_section, re.IGNORECASE)
            if match:
                groups = match.groups()
                
                # 根据匹配的模式构建案件编号
                if 'HCA' in pattern and '/(' in pattern:
                    # HCA xxx/yyyy 格式 -> 转换为 NO xxx OF yyyy
                    case_number = f"NO {groups[0]} OF {groups[1]}"
                elif 'ACTION.*NO' in pattern and len(groups) >= 2:
                    # ACTION NO xxx OF yyyy 或 HIGH COURT ACTION NO xxx OF yyyy
                    case_number = f"NO {groups[0]} OF {groups[1]}"
                elif 'NO' in pattern and len(groups) >= 2:
                    # NO xxx OF yyyy
                    case_number = f"NO {groups[0]} OF {groups[1]}"
                elif 'CACV' in pattern:
                    # CACV 格式
                    if len(groups) >= 2:
                        year = groups[1] or groups[2] or ""
                        case_number = f"{groups[0]}/{year}" if year else groups[0]
                    else:
                        case_number = groups[0]
                elif len(groups) >= 3:
                    # 标准格式 TYPE NO xxx OF yyyy
                    case_number = f"{groups[0]} NO {groups[1]} OF {groups[2]}"
                else:
                    case_number = match.group(0)
                
                # 清理和标准化
                case_number = re.sub(r'\s+', ' ', case_number.strip())
                self.logger.info(f"Found case number in middle section: '{case_number}' (pattern: {pattern[:30]}...)")
                return case_number
        
        return ""
    
    def _extract_chinese_case_number_positioned(self, text: str) -> str:
        """基于位置的中文案件编号提取"""
        # 查找中文法院名称结束位置
        court_patterns = [
            r'香港特別行政區.*?高等法院.*?上訴法庭',
            r'高等法院.*?原訟法庭',
            r'民事上訴案件',
            r'雜項案件',
        ]
        
        court_end_pos = 0
        for pattern in court_patterns:
            match = re.search(pattern, text)
            if match:
                court_end_pos = max(court_end_pos, match.end())
        
        if court_end_pos == 0:
            return ""
        
        # 查找当事人开始位置
        parties_patterns = [r'原告人', r'被告人', r'申請人', r'上訴人']
        
        parties_start_pos = len(text)
        for pattern in parties_patterns:
            match = re.search(pattern, text[court_end_pos:])
            if match:
                parties_start_pos = min(parties_start_pos, court_end_pos + match.start())
        
        if parties_start_pos == len(text):
            return ""
        
        # 在中间区域查找案件编号
        middle_section = text[court_end_pos:parties_start_pos]
        
        chinese_patterns = [
            r'民事上訴案件\s*(\d{4})年第\s*([^號]+)\s*號',
            r'(\d{4})年第\s*([^號]+)\s*號',
            r'案件編號[：:]\s*([^\n]+)',
        ]
        
        for pattern in chinese_patterns:
            match = re.search(pattern, middle_section)
            if match:
                return re.sub(r'\s+', ' ', match.group(0).strip())
        
        return ""
    

    
    
    
    def extract_plaintiff(self, text: str, language: str, doc_type: str = 'GENERIC') -> str:
        """提取原告信息 - 改进版：修复不完整提取并智能格式化，支持DCCJ和HCA格式"""
        if language == 'english':
            return self._extract_plaintiff_improved(text, doc_type)
        else:
            # 中文原告提取保持原逻辑
            patterns = [
                r'原告人\s*\n\s*([A-Za-z\s,]+?)(?=\n|\s*及\s*)',
                r'原告人\s*\n\s*([^\n]+?)(?=\s*第|\s*被告|\s*_)',
                r'(?:第一原告人|原告人)\s*[：:]\s*([^\n第被]+)',
                r'(?:第一原告人|原告人)\s*([A-Za-z\s,\.]+)(?=\s*第|\s*被告|\s*及)',
                r'原告[：:]\s*([^\n]+)',
                r'申請人[：:]\s*([^\n]+)',
                r'上訴人[：:]\s*([^\n]+)',
                r'第一原告人\s*([A-Za-z\s,]+)(?=\n|第二|第三|被告)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    plaintiff = match.group(1).strip()
                    plaintiff = re.sub(r'\s+', ' ', plaintiff)
                    plaintiff = re.sub(r'^\s*[：:]\s*', '', plaintiff)
                    if len(plaintiff) > 3 and len(plaintiff) < 200 and not re.match(r'^\d+\s*$', plaintiff):
                        return plaintiff
        return ""
    
    def _extract_plaintiff_improved(self, text: str, doc_type: str = 'GENERIC') -> str:
        """改进的英文原告提取方法 - 支持DCCJ和HCA格式"""
        
        # 根据文档类型选择处理策略
        if doc_type == 'DCCJ':
            # DCCJ格式：直接搜索"XXX Plaintiff"格式
            dccj_patterns = [
                r'([A-Z][A-Z\s&\.,\(\)]+?)\s*\n\s*Plaintiff\s*(?:\n|$)',
                r'([A-Z][A-Z\s&\.,\(\)]+?)\s+Plaintiff\s*(?:\n|$)',
                r'([A-Z][A-Z\s&\.,\(\)\-]+?)\s*\n\s*Plaintiff',
                r'([A-Z][A-Z\s&\.,\(\)\-]+?)\s+Plaintiff',
            ]
            
            for pattern in dccj_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                if matches:
                    for match in matches:
                        clean_name = re.sub(r'\s+', ' ', match.strip())
                        clean_name = re.sub(r'^and\s+', '', clean_name, flags=re.IGNORECASE)
                        # 确保是有效的公司名称（全大写或首字母大写）
                        if len(clean_name) > 3 and len(clean_name) < 100:
                            self.logger.info(f"DCCJ格式原告匹配: '{clean_name}'")
                            return clean_name
        else:
            # HCA格式：标准BETWEEN段落格式
            between_match = re.search(r'BETWEEN\s*(.*?)\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
            if between_match:
                between_content = between_match.group(1).strip()
                
                # 找到"AND"的位置，提取"AND"之前的所有内容作为原告段落
                and_match = re.search(r'\s+AND\s+', between_content, re.IGNORECASE)
                if and_match:
                    plaintiff_section = between_content[:and_match.start()].strip()
                    
                    # 提取原告信息
                    plaintiffs = self._extract_parties_robust(plaintiff_section, 'Plaintiff')
                    
                    # 智能格式化
                    return self._format_parties_smart(plaintiffs, 'Plaintiff')
        
        return ""
    
    def extract_defendant(self, text: str, language: str, doc_type: str = 'GENERIC') -> str:
        """提取被告信息 - 改进版：修复不完整提取并智能格式化，支持DCCJ和HCA格式"""
        if language == 'english':
            return self._extract_defendant_improved(text, doc_type)
        else:
            # 中文被告提取保持原逻辑
            patterns = [
                r'第一被告人\s*\n?\s*([A-Za-z\s,]+?)(?=\s*第二被告人|\s*第三被告人|\s*_)',
                r'第一被告人\s*([A-Za-z\s,\.]+)(?=\s*第二|\s*第三|\s*_)',
                r'第三被告人\s*([^_\n]+?)(?=_|Before|Date|\s*$)',
                r'第三被告人\s*([^\n]+?)(?=\s*主審|\s*聆訊|\s*判)',
                r'(?:第一被告人|被告人)\s*[：:]\s*([^\n第原]+)',
                r'(?:被告|被申請人)\s*[：:]\s*([^\n]+)',
                r'被告[：:]\s*([^\n]+)',
                r'被申請人[：:]\s*([^\n]+)',
                r'被上訴人[：:]\s*([^\n]+)',
                r'(?:第一被告人|被告人)\s*([A-Za-z\s,]+)(?=\n|第二|第三|原告|Before)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text)
                if match:
                    defendant = match.group(1).strip()
                    defendant = re.sub(r'\s+', ' ', defendant)
                    defendant = re.sub(r'^\s*[：:]\s*', '', defendant)
                    if len(defendant) > 3 and len(defendant) < 500 and not re.match(r'^\d+\s*$', defendant):
                        return defendant
        return ""
    
    def _extract_defendant_improved(self, text: str, doc_type: str = 'GENERIC') -> str:
        """改进的英文被告提取方法 - 支持DCCJ和HCA格式"""
        
        # 根据文档类型选择处理策略
        if doc_type == 'DCCJ':
            # DCCJ格式：直接搜索"XXX Defendant"格式
            dccj_patterns = [
                r'([A-Z][A-Z\s&\.,\(\)]+?)\s*\n\s*Defendant\s*(?:\n|$)',
                r'([A-Z][A-Z\s&\.,\(\)]+?)\s+Defendant\s*(?:\n|$)',
                r'([A-Z][A-Z\s&\.,\(\)\-]+?)\s*\n\s*Defendant',
                r'([A-Z][A-Z\s&\.,\(\)\-]+?)\s+Defendant',
            ]
            
            for pattern in dccj_patterns:
                matches = re.findall(pattern, text, re.MULTILINE)
                if matches:
                    for match in matches:
                        clean_name = re.sub(r'\s+', ' ', match.strip())
                        clean_name = re.sub(r'^and\s+', '', clean_name, flags=re.IGNORECASE)
                        # 确保是有效的公司名称（全大写或首字母大写）
                        if len(clean_name) > 3 and len(clean_name) < 100:
                            self.logger.info(f"DCCJ格式被告匹配: '{clean_name}'")
                            return clean_name
        else:
            # HCA格式：标准BETWEEN段落格式
            between_match = re.search(r'BETWEEN\s*(.*?)\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
            if between_match:
                between_content = between_match.group(1).strip()
                
                # 找到"AND"的位置，提取"AND"之后的所有内容作为被告段落
                and_match = re.search(r'\s+AND\s+', between_content, re.IGNORECASE)
                if and_match:
                    defendant_section = between_content[and_match.end():].strip()
                    
                    # 清理被告段落，移除下划线等无关内容
                    defendant_section = re.sub(r'_{5,}.*$', '', defendant_section, flags=re.DOTALL).strip()
                    
                    # 提取被告信息
                    defendants = self._extract_parties_robust(defendant_section, 'Defendant')
                    
                    # 智能格式化
                    return self._format_parties_smart(defendants, 'Defendant')
        
        return ""
    
    def _extract_parties_robust(self, section: str, party_type: str) -> list:
        """鲁棒的当事人提取方法 - 支持各种格式"""
        parties = []
        
        # 方法1：提取编号当事人（如：1st Plaintiff, 2nd Defendant等）
        numbered_parties = self._extract_numbered_parties_enhanced(section, party_type)
        if numbered_parties:
            parties.extend(numbered_parties)
        
        # 方法2：如果没有编号当事人，尝试提取简单格式
        if not parties:
            simple_party = self._extract_simple_party(section, party_type)
            if simple_party:
                parties.append(simple_party)
        
        return parties
    
    def _extract_numbered_parties_enhanced(self, section: str, party_type: str) -> list:
        """增强的编号当事人提取"""
        parties = []
        
        # 改进的模式：更准确地捕获姓名
        patterns = [
            # 模式1：多行格式 - 姓名在上，编号在下
            rf'([A-Z][A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)\s*\n\s*(\d+)(?:st|nd|rd|th)\s+{party_type}',
            
            # 模式2：同行格式 - 姓名和编号在同一行
            rf'([A-Z][A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)\s+(\d+)(?:st|nd|rd|th)\s+{party_type}',
            
            # 模式3：反向格式 - 编号在前，姓名在后
            rf'(\d+)(?:st|nd|rd|th)\s+{party_type}\s*\n\s*([A-Z][A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)',
            
            # 模式4：简化格式 - 只有姓名+身份（无编号）
            rf'([A-Z][A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)\s+{party_type}(?!\s*\d)',
        ]
        
        for i, pattern in enumerate(patterns):
            matches = re.findall(pattern, section, re.IGNORECASE | re.MULTILINE)
            
            for match in matches:
                if i < 3:  # 前3个模式有编号
                    if i == 2:  # 反向格式
                        number, name = match
                    else:  # 正向格式
                        name, number = match
                    
                    clean_name = self._clean_party_name(name)
                    if clean_name:
                        suffix = self._get_ordinal_suffix(int(number))
                        party_info = {
                            'name': clean_name,
                            'number': int(number),
                            'formatted': f"{clean_name} ({number}{suffix} {party_type})"
                        }
                        parties.append(party_info)
                else:  # 第4个模式无编号
                    name = match
                    clean_name = self._clean_party_name(name)
                    if clean_name:
                        party_info = {
                            'name': clean_name,
                            'number': None,
                            'formatted': f"{clean_name} ({party_type})"
                        }
                        parties.append(party_info)
            
            # 如果已经找到当事人，不继续尝试其他模式
            if parties:
                break
        
        # 去重并排序
        unique_parties = []
        seen_names = set()
        
        for party in parties:
            if party['name'] not in seen_names:
                unique_parties.append(party)
                seen_names.add(party['name'])
        
        # 按编号排序（如果有编号的话）
        unique_parties.sort(key=lambda x: x['number'] if x['number'] is not None else 0)
        
        return unique_parties
    
    def _extract_simple_party(self, section: str, party_type: str) -> dict:
        """提取简单格式的当事人（无编号）"""
        # 先清理段落
        clean_section = re.sub(r'\s+', ' ', section.strip())
        
        # 移除身份标识
        clean_section = re.sub(rf'\s*{party_type}\s*$', '', clean_section, flags=re.IGNORECASE)
        
        # 移除常见的干扰词
        clean_section = re.sub(r'\s*(?:and|&)\s*$', '', clean_section, flags=re.IGNORECASE)
        
        # 验证是否是有效的姓名
        if self._is_valid_party_name(clean_section):
            return {
                'name': clean_section,
                'number': None,
                'formatted': f"{clean_section} ({party_type})"
            }
        
        return None
    
    def _clean_party_name(self, name: str) -> str:
        """清理当事人姓名"""
        if not name:
            return ""
        
        # 基本清理
        clean = re.sub(r'\s+', ' ', name.strip())
        
        # 移除开头和结尾的干扰词
        clean = re.sub(r'^(?:and\s+|&\s+)', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'\s*(?:and|&)\s*$', '', clean, flags=re.IGNORECASE)
        
        # 移除多余的标点
        clean = re.sub(r'^[,\s]+|[,\s]+$', '', clean)
        
        # 验证清理后的结果
        if self._is_valid_party_name(clean):
            return clean
        
        return ""
    
    def _is_valid_party_name(self, name: str) -> bool:
        """验证是否是有效的当事人姓名"""
        if not name or len(name) < 2:
            return False
        
        if len(name) > 200:
            return False
        
        # 必须包含字母
        if not re.search(r'[A-Za-z]', name):
            return False
        
        # 不能全是数字
        if re.match(r'^\d+$', name):
            return False
        
        # 不能是常见的干扰词
        bad_words = [
            'and', 'or', 'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'before', 'after', 'during', 'plaintiff', 'defendant', 'court', 'judge',
            'chambers', 'sitting', 'hearing', 'date', 'action', 'case'
        ]
        
        if name.lower().strip() in bad_words:
            return False
        
        return True
    
    def _format_parties_smart(self, parties: list, party_type: str) -> str:
        """智能格式化当事人信息"""
        if not parties:
            return ""
        
        if len(parties) == 1:
            # 单个当事人：只显示名字
            return parties[0]['name']
        else:
            # 多个当事人：显示完整标识
            formatted_list = []
            for party in parties:
                if party['number'] is not None:
                    suffix = self._get_ordinal_suffix(party['number'])
                    formatted_list.append(f"{party['name']} ({party['number']}{suffix} {party_type})")
                else:
                    formatted_list.append(f"{party['name']} ({party_type})")
            
            return ' | '.join(formatted_list)
    

    
    def _extract_defendant_with_format(self, text: str) -> str:
        """按照原文格式提取被告信息"""
        # 查找BETWEEN段落
        between_match = re.search(r'BETWEEN\s*(.*?)\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
        if not between_match:
            return ""
        
        between_content = between_match.group(1).strip()
        
        # 找到"AND"的位置，提取"AND"之后的所有内容作为被告段落
        and_match = re.search(r'\s+AND\s+', between_content, re.IGNORECASE)
        if not and_match:
            return ""
        
        defendant_section = between_content[and_match.end():].strip()
        
        # 清理被告段落，移除下划线等无关内容
        # 先移除末尾的下划线分隔符
        defendant_section = re.sub(r'_{5,}.*$', '', defendant_section, flags=re.DOTALL).strip()
        
        defendants = []
        
        # 使用更精确的模式匹配被告信息
        # 模式1：标准格式 - 多行姓名 + 编号 (如用户图片所示)
        
        # 按行处理，但更智能地组合名称和编号
        lines = defendant_section.split('\n')
        current_name_parts = []
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # 跳过单独的布局字符
            if re.match(r'^[A-Z\-\+\s]{1,3}$', line):
                i += 1
                continue
            
            # 检查当前行是否是编号标识行
            defendant_match = re.match(r'^(\d+)(?:st|nd|rd|th)\s+Defendant\s*$', line, re.IGNORECASE)
            if defendant_match:
                # 这是一个编号行，前面的内容应该是姓名
                if current_name_parts:
                    name = ' '.join(current_name_parts).strip()
                    ordinal_num = int(defendant_match.group(1))
                    suffix = self._get_ordinal_suffix(ordinal_num)
                    defendants.append(f"{name} ({ordinal_num}{suffix} Defendant)")
                    current_name_parts = []
                i += 1
            elif re.match(r'^Defendant\s*$', line, re.IGNORECASE):
                # 单独的 "Defendant" 标识
                if current_name_parts:
                    name = ' '.join(current_name_parts).strip()
                    defendants.append(f"{name} (Defendant)")
                    current_name_parts = []
                i += 1
            else:
                # 这可能是姓名的一部分，或者是包含编号的行
                # 检查这行是否包含编号信息
                inline_match = re.match(r'^(.*?)\s+(\d+)(?:st|nd|rd|th)\s+Defendant\s*$', line, re.IGNORECASE)
                if inline_match:
                    # 同一行包含姓名和编号
                    name_part = inline_match.group(1).strip()
                    if current_name_parts:
                        name = ' '.join(current_name_parts + [name_part]).strip()
                    else:
                        name = name_part
                    ordinal_num = int(inline_match.group(2))
                    suffix = self._get_ordinal_suffix(ordinal_num)
                    defendants.append(f"{name} ({ordinal_num}{suffix} Defendant)")
                    current_name_parts = []
                else:
                    # 这是姓名的一部分
                    current_name_parts.append(line)
                i += 1
        
        # 处理剩余的姓名部分（如果有的话）
        if current_name_parts:
            name = ' '.join(current_name_parts).strip()
            if name and not re.match(r'^_{3,}|Before:|Date:', name, re.IGNORECASE):
                # 如果已经有被告，这个应该是下一个编号
                if defendants:
                    next_num = len(defendants) + 1
                    suffix = self._get_ordinal_suffix(next_num)
                    defendants.append(f"{name} ({next_num}{suffix} Defendant)")
                else:
                    defendants.append(f"{name} (Defendant)")
        
        if defendants:
            result = ' | '.join(defendants)
            self.logger.info(f"格式化提取被告: '{result}'")
            return result
        
        return ""
    
    def _extract_multiple_parties(self, text: str, party_type: str) -> str:
        """提取多方当事人（英文）- 增强版"""
        # 查找BETWEEN段落
        between_pattern = r'BETWEEN\s*(.*?)\s*(?=Before:|__________|Date|主審)'
        match = re.search(between_pattern, text, re.DOTALL | re.IGNORECASE)
        
        if not match:
            return ""
        
        between_content = match.group(1).strip()
        
        if party_type == 'Plaintiff':
            return self._extract_plaintiffs_improved(between_content)
        else:  # Defendant
            return self._extract_defendants_improved(between_content, text)
    
    def _extract_plaintiffs_improved(self, between_content: str) -> str:
        """改进的原告提取"""
        # 按"and"分割，取第一部分作为原告段落
        and_split = re.split(r'\s+and\s+', between_content, flags=re.IGNORECASE)
        if len(and_split) < 2:
            return ""
        
        plaintiff_section = and_split[0].strip()
        
        # 提取编号原告
        plaintiffs = self._extract_numbered_parties(plaintiff_section, 'Plaintiff')
        
        if len(plaintiffs) > 1:
            return ' | '.join(plaintiffs)
        elif len(plaintiffs) == 1:
            return plaintiffs[0]
        else:
            # 非编号的单一原告
            clean_section = re.sub(r'\s+', ' ', plaintiff_section.strip())
            clean_section = re.sub(r'\s*Plaintiff\s*$', '', clean_section, flags=re.IGNORECASE)
            if len(clean_section) > 3 and len(clean_section) < 300:
                return clean_section
        
        return ""
    
    def _extract_defendants_improved(self, between_content: str, full_text: str) -> str:
        """改进的被告提取 - 多策略approach"""
        
        # 策略1：从BETWEEN段落提取编号被告
        strategy1_result = self._extract_defendants_from_between(between_content)
        if strategy1_result:
            return strategy1_result
        
        # 策略2：从全文搜索被告信息（用于处理格式异常的情况）
        strategy2_result = self._extract_defendants_from_fulltext(full_text)
        if strategy2_result:
            return strategy2_result
        
        # 策略3：简单的"and"分割方法（回退）
        strategy3_result = self._extract_defendants_simple_split(between_content)
        if strategy3_result:
            return strategy3_result
        
        return ""
    
    def _extract_defendants_from_between(self, between_content: str) -> str:
        """从BETWEEN段落提取编号被告"""
        # 按"and"分割，取后面部分作为被告段落
        and_split = re.split(r'\s+and\s+', between_content, flags=re.IGNORECASE)
        if len(and_split) < 2:
            return ""
        
        defendant_section = ' and '.join(and_split[1:]).strip()
        
        # 提取编号被告
        defendants = self._extract_numbered_parties(defendant_section, 'Defendant')
        
        if len(defendants) > 1:
            return ' | '.join(defendants)
        elif len(defendants) == 1:
            return defendants[0]
        
        return ""
    
    def _extract_defendants_from_fulltext(self, text: str) -> str:
        """从全文搜索被告信息（处理格式异常）"""
        defendants = []
        
        # 扩展的被告搜索模式
        patterns = [
            # 模式1：直接的编号被告
            r'([A-Za-z\s,\.\(\)&\-\']+?)\s*\n\s*(\d+)(?:st|nd|rd|th)\s+Defendant',
            # 模式2：单一被告（无编号）
            r'and\s+([A-Z][A-Za-z\s,\.\(\)&\-\']{10,80}?)\s*\n\s*Defendant(?!\s*\d)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    name, number = match
                    clean_name = re.sub(r'\s+', ' ', name.strip())
                    clean_name = re.sub(r'^(?:and\s+)?', '', clean_name, flags=re.IGNORECASE)
                    if len(clean_name) > 3:
                        suffix = self._get_ordinal_suffix(int(number))
                        defendants.append(f"{clean_name} ({number}{suffix} Defendant)")
                else:
                    clean_name = re.sub(r'\s+', ' ', str(match).strip())
                    clean_name = re.sub(r'^(?:and\s+)?', '', clean_name, flags=re.IGNORECASE)
                    if len(clean_name) > 3:
                        defendants.append(clean_name)
        
        # 去重并限制数量
        unique_defendants = []
        for defendant in defendants:
            if defendant not in unique_defendants:
                unique_defendants.append(defendant)
            if len(unique_defendants) >= 10:  # 最多10个被告
                break
        
        if len(unique_defendants) > 1:
            return ' | '.join(unique_defendants)
        elif len(unique_defendants) == 1:
            return unique_defendants[0]
        
        return ""
    
    def _extract_defendants_simple_split(self, between_content: str) -> str:
        """简单分割方法（回退策略）"""
        # 查找最后一个"and"后的内容
        and_matches = list(re.finditer(r'\s+and\s+', between_content, re.IGNORECASE))
        if and_matches:
            last_and = and_matches[-1]
            defendant_section = between_content[last_and.end():].strip()
            
            # 简单清理
            defendant_section = re.sub(r'\s*Defendant.*$', '', defendant_section, flags=re.IGNORECASE)
            defendant_section = re.sub(r'\s+', ' ', defendant_section)
            
            if 5 < len(defendant_section) < 200:
                return defendant_section
        
        return ""
    
    def _extract_numbered_parties(self, section: str, party_type: str) -> list:
        """从段落中提取编号的当事人 - 优化姓名捕获"""
        parties = []
        
        # 扩展的匹配模式，支持更多序数词
        ordinals = [
            '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th',
            '11th', '12th', '13th', '14th', '15th', '16th', '17th', '18th', '19th', '20th'
        ]
        
        for ordinal in ordinals:
            # 更精确的模式匹配，确保捕获完整姓名
            patterns = [
                # 模式1：标准换行格式 - 针对BETWEEN段落优化
                rf'([A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)\s*\n\s*{ordinal}\s+{party_type}',
                # 模式2：同行格式
                rf'([A-Za-z\s,\.\(\)&\-\'（）]+?(?:\([^)]*\))?(?:（[^）]*）)?)\s+{ordinal}\s+{party_type}',
                # 模式3：中间有括号注释的换行格式
                rf'([A-Za-z\s,\.\(\)&\-\'（）]+?)\s*\n\s*\([^)]*\)\s*\n\s*{ordinal}\s+{party_type}',
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, section, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    clean_name = re.sub(r'\s+', ' ', match.strip())
                    clean_name = re.sub(r'^(?:and\s+)?', '', clean_name, flags=re.IGNORECASE)
                    
                    # 更严格的验证：确保是有效的姓名
                    name_for_validation = re.sub(r'\([^)]*\)', '', clean_name)
                    name_for_validation = re.sub(r'（[^）]*）', '', name_for_validation).strip()
                    
                    # 确保不是空的或只有标点符号
                    if len(name_for_validation) > 2 and re.search(r'[A-Za-z]', name_for_validation):
                        party_entry = f"{clean_name} ({ordinal} {party_type})"
                        if party_entry not in parties:  # 避免重复
                            parties.append(party_entry)
        
        # 如果上述模式失败，尝试更直接的方法专门针对BETWEEN段落
        if not parties and party_type == 'Defendant':
            parties = self._extract_defendants_direct_from_between(section)
        
        return parties
    
    def _extract_defendants_direct_from_between(self, section: str) -> list:
        """专门从BETWEEN段落直接提取被告 - 兜底方法"""
        defendants = []
        
        # 分析BETWEEN段落的具体结构
        lines = section.split('\n')
        
        current_name = ""
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # 检查是否是被告编号行
            defendant_match = re.match(r'(\d+)(?:st|nd|rd|th)\s+Defendant', line, re.IGNORECASE)
            if defendant_match and current_name:
                ordinal_num = defendant_match.group(1)
                ordinal = ordinal_num + self._get_ordinal_suffix(int(ordinal_num))
                clean_name = re.sub(r'\s+', ' ', current_name.strip())
                defendants.append(f"{clean_name} ({ordinal} Defendant)")
                current_name = ""
            
            # 如果不是被告编号行，可能是姓名行
            elif not re.match(r'^\d+(?:st|nd|rd|th)\s+(?:Plaintiff|Defendant)', line, re.IGNORECASE):
                # 排除明显的干扰行
                if not re.match(r'^(?:and|Plaintiff)$', line, re.IGNORECASE):
                    # 如果有中文括号，可能是注释，跳过
                    if not re.match(r'^\([^)]*\)$', line) and not re.match(r'^（[^）]*）$', line):
                        if current_name:
                            current_name += " " + line
                        else:
                            current_name = line
        
        return defendants
    
    def extract_judge(self, text: str, language: str) -> str:
        """提取法官信息"""
        if language == 'english':
            return self._extract_english_judge(text)
        else:
            return self._extract_chinese_judge(text)
    
    def _extract_english_judge(self, text: str) -> str:
        """提取英文法官信息 - 优化版，支持更多格式"""
        
        # 第1层：特殊格式优先模式 - 增强精度
        special_patterns = [
            # Recorder 格式 (如: Mr. Recorder Manzoni, SC) - 要求至少2个词
            r'(?i)(?:mr\.?\s+|ms\.?\s+)?recorder\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?:\s*,?\s*sc)?(?=\s+in\s+(?:court|chambers)|\n|$)',
            
            # Master 格式 (如: Master Isaac Chan) - 要求至少2个词
            r'(?i)master\s+([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?=\s+in\s+(?:court|chambers)|\n|$)',
            
            # 括号内法官格式 (如: (Manzoni, SC)) - 至少3个字符
            r'\(([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)*)\s*,?\s*sc?\)',
            
            # Deputy Judge 格式 - 要求至少2个词
            r'(?i)(?:deputy\s+(?:high\s+court\s+)?judge\s+|dhcj\s+)([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?:\s+sc)?(?=\s+in\s+(?:court|chambers)|\n|$)',
        ]
        
        for pattern in special_patterns:
            matches = re.findall(pattern, text)
            if matches:
                judge_raw = matches[0].strip()
                # 额外验证：确保不是明显的错误匹配
                if len(judge_raw) >= 3 and not re.match(r'^(?:to|at|in|on|for|and|or|the|of|with|from)$', judge_raw, re.IGNORECASE):
                    judge_clean = self._clean_judge_name_enhanced(judge_raw)
                    if judge_clean:
                        self.logger.info(f"找到特殊格式法官: {judge_clean}")
                        return judge_clean
        
        # 第2层：标准Before格式模式 - 增强精度
        before_patterns = [
            # 更精确的Before模式 - 要求姓名格式
            r'(?i)before:\s*(?:the\s+hon(?:ourable)?\.\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?:\s+j\.?)?(?=\s+in\s+(?:court|chambers)|\n)',
            r'(?i)before:\s*(?:deputy\s+(?:high\s+court\s+)?judge\s+)?([A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?:\s+j\.?)?(?=\s+sitting|\n)',
            
            # 兜底模式 - 但要求至少包含大写字母开头的词
            r'(?i)before:\s*([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)*(?:\s+j\.?)?)',
        ]
        
        for pattern in before_patterns:
            matches = re.findall(pattern, text)
            if matches:
                judge_raw = matches[0].strip()
                # 预过滤明显错误的匹配
                if (len(judge_raw) >= 3 and 
                    not re.match(r'^(?:to|at|in|on|for|and|or|the|of|with|from|by|this|that|these|those)$', judge_raw, re.IGNORECASE) and
                    not re.match(r'^(?:court|chambers|sitting|hearing|judgment|decision|order)$', judge_raw, re.IGNORECASE)):
                    
                    judge_clean = self._clean_judge_name_enhanced(judge_raw)
                    if judge_clean:
                        self.logger.info(f"找到Before格式法官: {judge_clean}")
                        return judge_clean
        
        # 第3层：备用模式 - 更严格的验证
        alternative_patterns = [
            # 要求完整的职称+姓名组合
            r'(?i)(deputy\s+(?:high\s+court\s+)?judge\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?=\s+sitting|\s+in\s+(?:court|chambers)|\n)',
            r'(?i)(justice\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+)(?=\s+sitting|\s+in\s+(?:court|chambers)|\n)',
            r'(?i)(the\s+hon(?:ourable)?\.\s+[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]+)+\s+j\.?)(?=\s|\n)',
            
            # 判决书末尾的法官签名格式 - 要求合理的姓名长度
            r'(?i)\(([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)+)\s*\)\s*(?:deputy\s+high\s+court\s+)?judge\s+of\s+the\s+court',
            r'(?i)\(([A-Z][A-Za-z]{2,}(?:\s+[A-Z][A-Za-z]+)+)\s*\)\s*recorder\s+of\s+the\s+high\s+court',
        ]
        
        for pattern in alternative_patterns:
            matches = re.findall(pattern, text)
            if matches:
                judge_raw = matches[0].strip()
                # 额外的合理性检查
                if (len(judge_raw) >= 5 and 
                    ' ' in judge_raw and  # 确保至少有两个词
                    not re.match(r'^(?:court|chambers|sitting|hearing|judgment|decision|order).*', judge_raw, re.IGNORECASE)):
                    
                    judge_clean = self._clean_judge_name_enhanced(judge_raw)
                    if judge_clean:
                        self.logger.info(f"找到备用格式法官: {judge_clean}")
                        return judge_clean
        
        return ""
    
    def _extract_chinese_judge(self, text: str) -> str:
        """提取中文法官信息"""
        patterns = [
            r'主審法官[：:]\s*([^\n]+)',
            r'審訊法官[：:]\s*([^\n]+)',
            r'(?:高等法院原訟法庭法官|法官)\s*([^\n\s]{2,10})',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                judge_raw = matches[0].strip()
                judge_clean = self._clean_judge_name(judge_raw)
                if judge_clean:
                    return judge_clean
        
        return ""
    
    def _clean_judge_name(self, judge_raw: str) -> str:
        """清理法官姓名，移除职称 - 改进版"""
        if not judge_raw:
            return ""
        
        # 移除常见职称和修饰词
        clean = re.sub(r'(?i)\b(?:deputy|high|court|judge|justice|the|hon\.?|honourable|mr|ms|mrs)\b\s*', '', judge_raw)
        clean = re.sub(r'\s*j\.?\s*$', '', clean, re.IGNORECASE)  # 移除末尾的 J.
        clean = re.sub(r'\s*(?:sitting|in|chambers)\s*.*$', '', clean, re.IGNORECASE)
        
        # 额外清理：处理"Hon XXX J"格式
        clean = re.sub(r'(?i)^(?:hon\.?\s+)?(.+?)\s*j\.?\s*$', r'\1', clean)
        
        # 移除多余空格
        clean = re.sub(r'\s+', ' ', clean).strip()
        
        # 验证结果
        if 2 <= len(clean) <= 50 and not re.match(r'^\d+$', clean):
            return clean
        
        return ""
    
    def _clean_judge_name_enhanced(self, judge_raw: str) -> str:
        """增强版法官姓名清理，支持更多格式 - 修复版"""
        if not judge_raw:
            return ""
        
        original_input = judge_raw
        clean = judge_raw.strip()
        
        # 第0步：预验证 - 立即拒绝明显错误的输入
        pre_invalid_patterns = [
            r'^[A-Z]$',                              # 单个大写字母
            r'^[a-z]$',                              # 单个小写字母
            r'^[A-Za-z]{1,2}$',                      # 1-2个字母（如'e', 'To'）
            r'^\d+$',                                # 纯数字
            r'^[,.\s\-_:;]+$',                       # 纯标点和空格
            r'(?i)^(?:to|at|in|on|for|and|or|the|of|with|from|by|if|is|as|be|it|he|she|we|they|this|that|these|those)$',  # 常见介词/代词
            r'(?i)^(?:court|chambers|sitting|hearing|judgment|judgement|decision|order|matter|case|action|appeal|application)$',  # 法律术语
            r'(?i)^(?:before|after|during|while|when|where|what|who|how|why)$',  # 疑问词/时间词
            r'(?i)^(?:granted|dismissed|allowed|refused|upheld|affirmed|reversed)$',  # 判决用词
            r'(?i)^(?:plaintiff|defendant|applicant|respondent|appellant)$',  # 当事人
            r'^(?:held|gave|said|found|noted|stated|ordered|directed)$',  # 动词
            r'^(?:[0-9]{1,4}|[ivxlc]+)$',            # 数字或罗马数字
            r'(?i)^(?:must|shall|should|would|could|may|might|can|will)$',  # 情态动词
        ]
        
        is_pre_invalid = any(re.match(pattern, clean) for pattern in pre_invalid_patterns)
        if is_pre_invalid:
            self.logger.warning(f"法官姓名预验证失败（明显错误）: '{original_input}' -> '{clean}'")
            return ""
        
        # 第1步：处理常见的完整格式
        # 处理 "Hon XXX J" -> "XXX"
        hon_j_match = re.search(r'(?i)^(?:the\s+)?hon\.?\s+(.+?)\s*j\.?\s*(?:in\s+(?:court|chambers).*)?$', clean)
        if hon_j_match:
            clean = hon_j_match.group(1).strip()
        
        # 处理 "Mr/Ms Recorder XXX" -> "XXX"
        recorder_match = re.search(r'(?i)^(?:mr\.?\s+|ms\.?\s+)?recorder\s+(.+?)(?:\s*,?\s*sc)?(?:\s+in\s+(?:court|chambers).*)?$', clean)
        if recorder_match:
            clean = recorder_match.group(1).strip()
        
        # 处理 "Master XXX" -> "XXX"
        master_match = re.search(r'(?i)^master\s+(.+?)(?:\s+in\s+(?:court|chambers).*)?$', clean)
        if master_match:
            clean = master_match.group(1).strip()
        
        # 处理 "Deputy High Court Judge XXX" -> "XXX"
        deputy_match = re.search(r'(?i)^deputy\s+(?:high\s+court\s+)?judge\s+(.+?)(?:\s+in\s+(?:court|chambers).*)?$', clean)
        if deputy_match:
            clean = deputy_match.group(1).strip()
        
        # 处理括号格式 "(XXX, SC)" -> "XXX"
        bracket_match = re.search(r'^\(([A-Za-z\s]+?)\s*,?\s*sc?\)$', clean, re.IGNORECASE)
        if bracket_match:
            clean = bracket_match.group(1).strip()
        
        # 第2步：移除末尾的职称后缀
        clean = re.sub(r'\s*,?\s*sc\s*$', '', clean, re.IGNORECASE)  # 移除末尾的 SC
        clean = re.sub(r'\s*j\.?\s*$', '', clean, re.IGNORECASE)     # 移除末尾的 J.
        
        # 第3步：移除位置信息
        clean = re.sub(r'\s*(?:sitting|in|at)\s+(?:court|chambers).*$', '', clean, re.IGNORECASE)
        
        # 第4步：只移除开头的明确职称词汇（保守清理）
        clean = re.sub(r'^(?:the\s+|hon\.?\s+|honourable\s+)', '', clean, re.IGNORECASE)
        
        # 第5步：清理空格和标点
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = re.sub(r'^[,\s]+|[,\s]+$', '', clean)
        
        # 第6步：增强验证结果
        if clean:
            # 基本长度检查
            if len(clean) < 3 or len(clean) > 50:
                self.logger.warning(f"法官姓名清理失败（长度不符）: '{original_input}' -> '{clean}'")
                return ""
            
            # 检查是否包含有效的姓名字符
            if not re.search(r'[A-Za-z]', clean):
                self.logger.warning(f"法官姓名清理失败（无字母）: '{original_input}' -> '{clean}'")
                return ""
            
            # 增强的无效模式检查
            invalid_patterns = [
                r'^[A-Za-z]{1,2}$',                      # 1-2个字母（如'e', 'To', 'In'）
                r'^\d+$',                                # 纯数字
                r'^[,.\s\-_:;]+$',                       # 纯标点和空格
                r'(?i)^(?:to|at|in|on|for|and|or|the|of|with|from|by|if|is|as|be|it|he|she|we|they)$',  # 介词/代词
                r'(?i)^(?:court|chambers|sitting|hearing|judgment|judgement|decision|order|matter|case|action|appeal)$',  # 法律术语
                r'(?i)^(?:before|after|during|while|when|where|what|who|how|why|shall|must|would|could)$',  # 其他常见词
                r'(?i)^(?:plaintiff|defendant|applicant|respondent|appellant|petitioner)$',  # 当事人
                r'(?i)^(?:granted|dismissed|allowed|refused|upheld|affirmed|reversed|held|gave|said|found)$',  # 判决/动词
                r'^[ivxlc]+$',                           # 罗马数字
                r'(?i)^(?:less than|more than|between|among|within|without|unless|until|since|because)$',  # 长介词短语的开头
                r'(?i)^(?:hearing|trial|motion|summons|application|appeal|judgment)s?$',  # 法律程序术语
                r'(?i)^(?:inclusive|exclusive|interest|cost|costs|fee|fees)$',  # 财务术语
                r'(?i)^(?:one|two|three|four|five|six|seven|eight|nine|ten|week|month|year|day)s?$',  # 数字/时间
            ]
            
            is_invalid = any(re.match(pattern, clean) for pattern in invalid_patterns)
            
            if is_invalid:
                self.logger.warning(f"法官姓名清理失败（匹配无效模式）: '{original_input}' -> '{clean}'")
                return ""
            
            # 最后验证：确保至少包含一个大写字母（姓名特征）
            if not re.search(r'[A-Z]', clean):
                self.logger.warning(f"法官姓名清理失败（无大写字母）: '{original_input}' -> '{clean}'")
                return ""
            
            # 验证通过
            self.logger.info(f"法官姓名清理成功: '{original_input}' -> '{clean}'")
            return clean
        
        self.logger.warning(f"法官姓名清理失败（清理后为空）: '{original_input}' -> '{clean}'")
        return ""
    
    def extract_lawyer(self, text: str, language: str) -> str:
        """提取律师信息"""
        if language == 'english':
            return self._extract_english_lawyers(text)
        else:
            return self._extract_chinese_lawyers(text)
    
    def _extract_english_lawyers(self, text: str) -> str:
        """提取英文律师信息"""
        lawyers = []
        
        # 主要模式：represented by 格式
        representation_patterns = [
            r'(?i)(?:plaintiff|applicant|p)\s+(?:was\s+)?represented\s+by\s+(.*?)(?=\s+and\s+(?:defendant|d\s+|the\s+defendant)|\.|\n)',
            r'(?i)(?:defendant|respondent|d)\s+(?:was\s+)?represented\s+by\s+(.*?)(?=\.|\n)',
            r'(?i)at\s+the\s+(?:trial|hearing),?\s+(?:p|plaintiff)\s+(?:was\s+)?represented\s+by\s+(.*?)(?=\s+and\s+d\s+|\.|\n)',
        ]
        
        for pattern in representation_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                extracted_lawyers = self._extract_lawyer_names(match)
                lawyers.extend(extracted_lawyers)
        
        # 备用模式：counsel for 格式
        counsel_patterns = [
            r'(?i)counsel\s+for\s+(?:the\s+)?(?:plaintiff|defendant|applicant|respondent)[:\s]+([^\n\.]+)',
            r'(?i)for\s+the\s+(?:plaintiff|defendant)[:\s]+([^\n\.]+)',
        ]
        
        for pattern in counsel_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                extracted_lawyers = self._extract_lawyer_names(match)
                lawyers.extend(extracted_lawyers)
        
        # 去重并限制数量
        unique_lawyers = []
        for lawyer in lawyers:
            if lawyer not in unique_lawyers:
                unique_lawyers.append(lawyer)
            if len(unique_lawyers) >= 8:  # 最多8个律师
                break
        
        if unique_lawyers:
            return ' | '.join(unique_lawyers)
        
        return ""
    
    def _extract_chinese_lawyers(self, text: str) -> str:
        """提取中文律师信息"""
        patterns = [
            r'委托律师[：:]\s*([^\n]+)',
            r'代理律师[：:]\s*([^\n]+)',
            r'(?:原告|申請人).*?委託.*?([^\n]{2,20}).*?代理',
            r'(?:被告|被申請人).*?委託.*?([^\n]{2,20}).*?代理',
        ]
        
        lawyers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                clean_lawyer = re.sub(r'\s+', ' ', match.strip())
                if 2 <= len(clean_lawyer) <= 30:
                    lawyers.append(clean_lawyer)
        
        if lawyers:
            return ' | '.join(lawyers[:5])  # 最多5个
        
        return ""
    
    def _extract_lawyer_names(self, lawyer_text: str) -> list:
        """从律师文本中提取具体姓名"""
        lawyers = []
        
        # 匹配 Mr/Ms + 姓名模式
        name_patterns = [
            r'(?i)mr\.?\s+([A-Za-z\s]+?)(?:\s+sc\s*|\s+leading|\s+and|\s*,|\s*$)',
            r'(?i)ms\.?\s+([A-Za-z\s]+?)(?:\s+sc\s*|\s+leading|\s+and|\s*,|\s*$)',
            r'(?i)(?:leading\s+)?([A-Z][a-z]+\s+[A-Z][a-z]+)(?:\s+sc)?',
        ]
        
        for pattern in name_patterns:
            matches = re.findall(pattern, lawyer_text)
            for match in matches:
                clean_name = re.sub(r'\s+', ' ', match.strip())
                if 3 <= len(clean_name) <= 50 and clean_name not in lawyers:
                    lawyers.append(clean_name)
        
        return lawyers
    
    def extract_case_type(self, text: str, language: str, doc_type: str = 'GENERIC') -> str:
        """提取案件类型相关文本段落，供LLM分析判断"""
        try:
            self.logger.info("开始提取case_type - 增强版")
            
            # 限制文档长度
            if len(text) > 80000:
                text = text[:80000]
                self.logger.info("文档过长，截取前80000字符进行case_type提取")
            
            if language == 'english':
                result = self._extract_english_case_type_comprehensive(text)
            else:
                result = self._extract_chinese_case_type_comprehensive(text)
            
            self.logger.info(f"case_type提取完成，长度: {len(result)}")
            return result
        except Exception as e:
            self.logger.warning(f"case_type提取失败: {e}")
            return ""
    
    def _extract_english_case_type_comprehensive(self, text: str) -> str:
        """增强版英文案件类型提取 - 基于PDF结构分析"""
        case_segments = []
        
        # 第1层：提取关键段落 - Introduction/Background/Facts (最高优先级)
        key_section_patterns = [
            # Introduction段落 - 通常包含案件概述
            (r'Introduction\s*[:\.]?\s*\n((?:[^\n]+\n){3,20})', 10, 'introduction'),
            
            # Background段落 - 案件背景
            (r'(?:BACKGROUND|Background)\s*[:\.]?\s*\n((?:[^\n]+\n){5,25})', 9, 'background'),
            
            # Facts段落 - 案件事实
            (r'(?:FACTS?|Facts?)\s*[:\.]?\s*\n((?:[^\n]+\n){3,20})', 8, 'facts'),
            
            # 案件性质描述
            (r'(?:This is|These are)\s+(?:an?\s+)?(action|application|proceeding|matter|case|appeal|motion|summons)([^\n.]{20,300})', 7, 'nature'),
            
            # 申请描述
            (r'(?:The|This)\s+(?:plaintiff|applicant|defendant|appellant)\s+(?:seeks?|applies?|brings?|claims?)\s+([^\n.]{30,400})', 6, 'application'),
        ]
        
        for pattern, weight, section_type in key_section_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.DOTALL))
            for match in matches[:2]:  # 每个模式最多2个匹配
                content = match.group(1) if match.lastindex >= 1 else match.group(0)
                clean_content = self._clean_comprehensive_content(content)
                
                if 50 <= len(clean_content) <= 2000:
                    case_segments.append({
                        'content': clean_content,
                        'weight': weight,
                        'type': section_type,
                        'length': len(clean_content)
                    })
        
        # 第2层：提取判决相关描述
        judgment_context_patterns = [
            (r'(?:ORDER|ORDERS|JUDGMENT|HELD|DISPOSITION)\s*[:\.]?\s*\n((?:[^\n]+\n){2,15})', 5, 'judgment_context'),
            (r'(?:For (?:these reasons|the foregoing reasons)|Accordingly|In (?:conclusion|the result))\s*[,.]?\s*([^\n.]{50,500})', 4, 'conclusion'),
        ]
        
        for pattern, weight, section_type in judgment_context_patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.DOTALL))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_comprehensive_content(content)
                
                if 30 <= len(clean_content) <= 1500:
                    case_segments.append({
                        'content': clean_content,
                        'weight': weight,
                        'type': section_type,
                        'length': len(clean_content)
                    })
        
        # 第3层：提取长段落中的案件描述
        paragraphs = re.split(r'\n\s*\n', text)
        for paragraph in paragraphs:
            if 200 <= len(paragraph) <= 2000:
                # 检查段落是否包含案件相关关键词
                case_keywords = ['application', 'proceeding', 'action', 'dispute', 'matter', 'claim', 'relief', 'judgment', 'order']
                if any(keyword in paragraph.lower() for keyword in case_keywords):
                    clean_para = self._clean_comprehensive_content(paragraph)
                    if 100 <= len(clean_para) <= 1500:
                        case_segments.append({
                            'content': clean_para,
                            'weight': 2,
                            'type': 'long_paragraph',
                            'length': len(clean_para)
                        })
                        if len(case_segments) >= 8:  # 限制段落数量
                            break
        
        return self._combine_comprehensive_segments(case_segments, max_length=3000)
    
    def _clean_comprehensive_content(self, content: str) -> str:
        """清理案件类型内容"""
        if not content:
            return ""
        
        # 基本清理
        cleaned = re.sub(r'\s+', ' ', content.strip())
        
        # 移除页码和分隔符
        cleaned = re.sub(r'\s*-\s*\d+\s*-\s*', ' ', cleaned)
        cleaned = re.sub(r'\s*_{3,}\s*', ' ', cleaned)
        
        # 移除明显的干扰信息
        cleaned = re.sub(r'\s*(?:page|頁)\s*\d+.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^\s*(?:\d+\.\s*)?', '', cleaned)  # 移除段落编号
        
        # 移除多余的标点
        cleaned = re.sub(r'^[,;.:\s]+', '', cleaned)
        cleaned = re.sub(r'[.\s]+$', '', cleaned)
        
        return cleaned.strip()
    
    def _combine_comprehensive_segments(self, segments, max_length=3000):
        """合并案件类型段落"""
        if not segments:
            return ""
        
        # 按权重排序
        segments.sort(key=lambda x: x.get('weight', 0), reverse=True)
        
        # 选择最有价值的段落
        selected_parts = []
        total_length = 0
        
        for segment in segments:
            content = segment.get('content', '')
            if not content:
                continue
                
            # 避免重复内容
            is_duplicate = False
            for existing in selected_parts:
                if len(content) > 30 and len(existing) > 30:
                    # 简单相似度检查
                    if content[:30] == existing[:30]:
                        is_duplicate = True
                        break
            
            if not is_duplicate and total_length + len(content) <= max_length:
                selected_parts.append(content)
                total_length += len(content)
                
                # 限制段落数量
                if len(selected_parts) >= 5:
                    break
        
        if selected_parts:
            result = ' | '.join(selected_parts)
            if len(result) > max_length:
                result = result[:max_length-3] + '...'
            return result
        
        return ""
    
    def _extract_chinese_case_type_comprehensive(self, text: str) -> str:
        """增强版中文案件类型提取"""
        case_segments = []
        
        # 第1层：关键段落提取
        key_section_patterns = [
            # 背景/事实段落
            (r'(?:背景|事實|案情|簡介)\s*[：:.]?\s*\n((?:[^\n]+\n){3,20})', 10, 'background'),
            
            # 争议/问题段落  
            (r'(?:爭議|問題|焦點|糾紛)\s*[：:.]?\s*\n((?:[^\n]+\n){2,15})', 9, 'dispute'),
            
            # 申请人请求
            (r'(?:申請人|原告人?)\s*(?:申請|請求|要求|尋求|指稱)\s*([^\n。]{50,500})', 8, 'application'),
            
            # 案件性质
            (r'(?:本案|該案|此案)\s*(?:涉及|關於|係|為)\s*([^\n。]{30,400})', 7, 'nature'),
        ]
        
        for pattern, weight, section_type in key_section_patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_comprehensive_content(content)
                
                if 30 <= len(clean_content) <= 1500:
                    case_segments.append({
                        'content': clean_content,
                        'weight': weight,
                        'type': section_type,
                        'length': len(clean_content)
                    })
        
        # 第2层：判决相关段落
        judgment_patterns = [
            (r'(?:命令|判令|裁定|判決)\s*[：:.]?\s*\n((?:[^\n]+\n){2,15})', 6, 'judgment'),
            (r'(?:綜上所述|因此|故此|據此)\s*[，,]?\s*([^\n。]{30,400})', 5, 'conclusion'),
        ]
        
        for pattern, weight, section_type in judgment_patterns:
            matches = list(re.finditer(pattern, text))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_comprehensive_content(content)
                
                if 20 <= len(clean_content) <= 1000:
                    case_segments.append({
                        'content': clean_content,
                        'weight': weight,
                        'type': section_type,
                        'length': len(clean_content)
                    })
        
        # 第3层：长段落提取
        paragraphs = re.split(r'\n\s*\n', text)
        for paragraph in paragraphs:
            if 150 <= len(paragraph) <= 1500:
                case_keywords = ['申請', '爭議', '糾紛', '案件', '法庭', '法院', '判決', '命令', '裁定']
                if any(keyword in paragraph for keyword in case_keywords):
                    clean_para = self._clean_comprehensive_content(paragraph)
                    if 80 <= len(clean_para) <= 1200:
                        case_segments.append({
                            'content': clean_para,
                            'weight': 2,
                            'type': 'long_paragraph',
                            'length': len(clean_para)
                        })
                        if len(case_segments) >= 8:
                            break
        
        return self._combine_comprehensive_segments(case_segments, max_length=2500)
    
    def extract_judgment_result(self, text: str, language: str) -> str:
        """基于位置特性的判决结果提取 - 性能优化版"""
        try:
            self.logger.info("开始提取judgment_result - 位置优化版")
            
            # 重点扫描最后15% (判决结果通常在文档末尾)
            total_chars = len(text)
            last_15_percent_start = max(total_chars * 85 // 100, total_chars - 5000)
            judgment_section = text[last_15_percent_start:]
            
            self.logger.info(f"判决结果搜索范围: 最后{len(judgment_section)}字符")
            
            if language == 'english':
                result = self._extract_judgment_result_focused(judgment_section)
            else:
                result = self._extract_chinese_judgment_result_focused(judgment_section)
            
            self.logger.info(f"judgment_result提取完成，长度: {len(result)}")
            return result
        except Exception as e:
            self.logger.warning(f"judgment_result提取失败: {e}")
            return ""
    
    def _extract_judgment_result_focused(self, judgment_section: str) -> str:
        """聚焦版英文判决结果提取 - 只扫描关键段落"""
        if not judgment_section or len(judgment_section) < 100:
            return ""
        
        judgment_segments = []
        
        # 优先级1: ORDER/JUDGMENT段落 (最重要，90%有效) - 增强版
        order_patterns = [
            # 原有模式
            r'(?:ORDER|ORDERS|JUDGMENT|CONCLUSION|DISPOSITION)\s*[:\.]?\s*\n((?:[^\n]+\n?){2,12})',
            r'(?:IT IS ORDERED|I ORDER|THE COURT ORDERS?)\s*[:\.]?\s*((?:[^\n]+\n?){1,8})',
            r'(?:For (?:these reasons|the foregoing reasons)|Accordingly|Therefore)\s*[,.]?\s*([^\n.]{30,500})',
            
            # 新增模式 - 更灵活的判决表达
            r'(I (?:make an )?[Oo]rder[^.]*?(?:that|in terms of)[^.]*?[.\n])',  # "I make an Order that..." 或 "I order that..."
            r'(I (?:would )?(?:make|grant|allow|dismiss|refuse)[^.]*?(?:order|application|claim)[^.]*?[.\n])',  # "I would make/grant/allow..."
            r'([Bb]ased on the above[^.]*?[Oo]rder[^.]*?[.\n])',  # "Based on the above, I make an Order..."
            r'([Ii]n conclusion[^.]*?(?:order|grant|dismiss|allow)[^.]*?[.\n])',  # "In conclusion, I..."
            r'([Ff]or the (?:above )?reasons?[^.]*?(?:order|grant|dismiss|allow)[^.]*?[.\n])',  # "For the reasons..."
        ]
        
        for pattern in order_patterns:
            matches = list(re.finditer(pattern, judgment_section, re.IGNORECASE | re.DOTALL))
            for match in matches[:2]:  # 每个模式最多2个匹配
                content = match.group(1)
                clean_content = self._clean_judgment_content(content)
                
                if 20 <= len(clean_content) <= 1000:
                    judgment_segments.append(clean_content)
        
        # 优先级2: 明确的判决语句 (95%有效) - 增强版
        decision_patterns = [
            # 原有模式
            r'((?:dismiss|grant|refuse|allow|upheld|affirmed).*?(?:application|claim|appeal|action))',
            r'((?:Judgment|judgment)\s+(?:be\s+)?entered\s+for.*?)',
            r'(I\s+(?:dismiss|grant|order|hold|refuse|allow).*?)',
            r'((?:The\s+)?(?:application|appeal|claim)\s+(?:is|shall be)\s+(?:granted|dismissed|refused|allowed).*?)',
            
            # 新增模式 - 更多判决表达
            r'((?:The\s+)?[Dd]efendants?.*?(?:pay|liable|responsible)[^.]*?(?:costs|damages|compensation)[^.]*?[.\n])',  # 被告支付费用
            r'((?:The\s+)?[Pp]laintiffs?.*?(?:entitled|succeed)[^.]*?[.\n])',  # 原告胜诉
            r'([Ss]ummary judgment.*?(?:granted|entered|allowed)[^.]*?[.\n])',  # 简易判决
            r'([Cc]osts.*?(?:assessed|taxed|awarded)[^.]*?[.\n])',  # 费用裁定
            r'([Ii]nterest.*?(?:awarded|granted|payable)[^.]*?[.\n])',  # 利息裁定
            r'([Aa]pplication.*?(?:granted|dismissed|refused|allowed)[^.]*?[.\n])',  # 申请结果
        ]
        
        for pattern in decision_patterns:
            matches = list(re.finditer(pattern, judgment_section, re.IGNORECASE))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_judgment_content(content)
                
                if 15 <= len(clean_content) <= 800:
                    judgment_segments.append(clean_content)
        
        # 合并结果，去重
        if judgment_segments:
            # 简单去重
            unique_segments = []
            for segment in judgment_segments:
                is_duplicate = False
                for existing in unique_segments:
                    if len(segment) > 0 and len(existing) > 0:
                        if segment[:30] == existing[:30]:
                            is_duplicate = True
                            break
                if not is_duplicate:
                    unique_segments.append(segment)
            
            # 限制数量和总长度
            if len(unique_segments) > 4:
                unique_segments = unique_segments[:4]
            
            result = ' | '.join(unique_segments)
            if len(result) > 2500:
                result = result[:2497] + '...'
            
            return result
        
        return ""
    
    def _extract_chinese_judgment_result_focused(self, judgment_section: str) -> str:
        """聚焦版中文判决结果提取"""
        if not judgment_section or len(judgment_section) < 100:
            return ""
        
        judgment_segments = []
        
        # 优先级1: 中文判决段落
        order_patterns = [
            r'(?:命令|判令|裁定|判決|判决)\s*[：:.]?\s*\n((?:[^\n]+\n?){2,10})',
            r'(?:本庭|法庭|法院)\s*(?:命令|判令|裁定|判決|判决)\s*([^\n。]{15,400})',
            r'(?:綜上所述|因此|故此|據此)\s*[，,：:.]*\s*([^\n。]{20,400})'
        ]
        
        for pattern in order_patterns:
            matches = list(re.finditer(pattern, judgment_section))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_judgment_content(content)
                
                if 10 <= len(clean_content) <= 800:
                    judgment_segments.append(clean_content)
        
        # 优先级2: 明确的判决动词
        decision_patterns = [
            r'((?:批准|拒絕|駁回|允許|准許|不准).*?(?:申請|請求|上訴))',
            r'((?:勝訴|敗訴|得直|不得直).*?)',
            r'((?:撤回|撤訴).*?)'
        ]
        
        for pattern in decision_patterns:
            matches = list(re.finditer(pattern, judgment_section))
            for match in matches[:2]:
                content = match.group(1)
                clean_content = self._clean_judgment_content(content)
                
                if 8 <= len(clean_content) <= 600:
                    judgment_segments.append(clean_content)
        
        # 合并结果
        if judgment_segments:
            unique_segments = []
            for segment in judgment_segments:
                is_duplicate = False
                for existing in unique_segments:
                    if len(segment) > 0 and len(existing) > 0:
                        if segment[:20] == existing[:20]:
                            is_duplicate = True
                            break
                if not is_duplicate:
                    unique_segments.append(segment)
            
            if len(unique_segments) > 4:
                unique_segments = unique_segments[:4]
            
            result = ' | '.join(unique_segments)
            if len(result) > 2000:
                result = result[:1997] + '...'
            
            return result
        
        return ""
    
    def _clean_judgment_content(self, content: str) -> str:
        """清理判决内容 - 简化版"""
        if not content:
            return ""
        
        # 基本清理
        cleaned = re.sub(r'\s+', ' ', content.strip())
        
        # 移除页码和分隔符
        cleaned = re.sub(r'\s*-\s*\d+\s*-\s*', ' ', cleaned)
        cleaned = re.sub(r'\s*_{3,}\s*', ' ', cleaned)
        
        # 移除明显的干扰信息
        cleaned = re.sub(r'\s*(?:page|頁)\s*\d+.*$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'^\s*(?:\d+\.\s*)?', '', cleaned)  # 移除段落编号
        
        # 移除多余的标点
        cleaned = re.sub(r'^[,;.:\s]+', '', cleaned)
        cleaned = re.sub(r'[.\s]+$', '', cleaned)
        
        return cleaned.strip()
    
    def extract_amount_segments(self, text: str, language: str, segment_type: str) -> str:
        """
        增强版金额段落提取 - 三层递进策略
        
        Args:
            text: 文档文本
            language: 语言
            segment_type: 'claim' 或 'judgment'
            
        Returns:
            包含金额的段落文本
        """
        try:
            self.logger.info(f"开始增强版{segment_type}_amount提取")
            
            if segment_type == 'claim':
                result = self._extract_claim_amount_enhanced(text, language)
            else:  # judgment
                result = self._extract_judgment_amount_enhanced(text, language)
            
            self.logger.info(f"{segment_type}_amount提取完成，长度: {len(result)}")
            return result
        except Exception as e:
            self.logger.warning(f"{segment_type}_amount提取失败: {e}")
            return ""
    
    def _extract_claim_amount_enhanced(self, text: str, language: str) -> str:
        """增强版申请金额提取 - 三层递进策略"""
        
        # 第一层：精确搜索（前30% + 后30%）
        result = self._extract_amounts_precise(text, language, 'claim')
        if result:
            self.logger.info("第一层精确搜索成功")
            return result
        
        # 第二层：扩展搜索（前50% + 中间30%-80%）
        result = self._extract_amounts_extended(text, language, 'claim')
        if result:
            self.logger.info("第二层扩展搜索成功")
            return result
        
        # 第三层：全文宽松搜索
        result = self._extract_amounts_loose(text, language, 'claim')
        if result:
            self.logger.info("第三层宽松搜索成功")
            return result
        
        self.logger.info("所有层级搜索均未找到申请金额")
        return ""

    def _extract_judgment_amount_enhanced(self, text: str, language: str) -> str:
        """增强版判决金额提取 - 三层递进策略"""
        
        # 第一层：精确搜索（后40%）
        result = self._extract_amounts_precise(text, language, 'judgment')
        if result:
            self.logger.info("第一层精确搜索成功")
            return result
        
        # 第二层：扩展搜索（中间40%-90%）
        result = self._extract_amounts_extended(text, language, 'judgment')
        if result:
            self.logger.info("第二层扩展搜索成功")
            return result
        
        # 第三层：全文宽松搜索
        result = self._extract_amounts_loose(text, language, 'judgment')
        if result:
            self.logger.info("第三层宽松搜索成功")
            return result
        
        self.logger.info("所有层级搜索均未找到判决金额")
        return ""
    
    def _extract_amounts_precise(self, text: str, language: str, amount_type: str) -> str:
        """第一层：精确搜索"""
        total_chars = len(text)
        
        if amount_type == 'claim':
            # 前30% + 后30%
            front_30_end = min(total_chars * 3 // 10, 10000)
            back_30_start = max(total_chars * 7 // 10, total_chars - 8000)
            
            front_section = text[:front_30_end]
            back_section = text[back_30_start:]
            
            self.logger.info(f"精确搜索申请金额: 前{front_30_end}字符 + 后{len(back_section)}字符")
            
            # 使用增强关键词搜索
            front_result = self._extract_amounts_by_enhanced_keywords(front_section, language, amount_type, threshold=2.5)
            back_result = self._extract_amounts_by_enhanced_keywords(back_section, language, amount_type, threshold=2.5)
            
            return self._combine_amount_results([front_result, back_result])
            
        else:  # judgment
            # 后40%
            back_40_start = max(total_chars * 6 // 10, total_chars - 12000)
            judgment_section = text[back_40_start:]
            
            self.logger.info(f"精确搜索判决金额: 后{len(judgment_section)}字符")
            
            return self._extract_amounts_by_enhanced_keywords(judgment_section, language, amount_type, threshold=2.5)

    def _extract_amounts_extended(self, text: str, language: str, amount_type: str) -> str:
        """第二层：扩展搜索"""
        total_chars = len(text)
        
        if amount_type == 'claim':
            # 前50% + 中间30%-80%
            front_50_end = min(total_chars * 5 // 10, 15000)
            middle_start = total_chars * 3 // 10
            middle_end = total_chars * 8 // 10
            
            front_section = text[:front_50_end]
            middle_section = text[middle_start:middle_end]
            
            self.logger.info(f"扩展搜索申请金额: 前{front_50_end}字符 + 中间{len(middle_section)}字符")
            
            front_result = self._extract_amounts_by_enhanced_keywords(front_section, language, amount_type, threshold=2.0)
            middle_result = self._extract_amounts_by_enhanced_keywords(middle_section, language, amount_type, threshold=2.0)
            
            return self._combine_amount_results([front_result, middle_result])
            
        else:  # judgment
            # 中间40%-90%
            middle_start = total_chars * 4 // 10
            middle_end = total_chars * 9 // 10
            judgment_section = text[middle_start:middle_end]
            
            self.logger.info(f"扩展搜索判决金额: 中间{len(judgment_section)}字符")
            
            return self._extract_amounts_by_enhanced_keywords(judgment_section, language, amount_type, threshold=2.0)

    def _extract_amounts_loose(self, text: str, language: str, amount_type: str) -> str:
        """第三层：全文宽松搜索"""
        self.logger.info(f"宽松搜索{amount_type}金额: 全文{len(text)}字符")
        
        # 降低阈值，进行全文搜索
        return self._extract_amounts_by_enhanced_keywords(text, language, amount_type, threshold=1.0)

    def _extract_amounts_by_enhanced_keywords(self, text: str, language: str, amount_type: str, threshold: float = 2.0) -> str:
        """使用增强关键词库的金额提取"""
        if not text or len(text) < 50:
            return ""
        
        # 获取增强的关键词库
        keywords, context_words = self._get_enhanced_keywords(language, amount_type)
        
        # 获取增强的金额模式
        amount_patterns = self._get_enhanced_amount_patterns(language)
        
        # 先找到所有潜在金额
        potential_amounts = self._find_potential_amounts(text, amount_patterns)
        
        # 验证每个金额的上下文相关性
        validated_amounts = []
        for amount_info in potential_amounts:
            score = self._validate_amount_context(amount_info, amount_type, language, keywords, context_words)
            if score >= threshold:
                validated_amounts.append({
                    'text': amount_info['context'],
                    'score': score,
                    'amount': amount_info['amount']
                })
        
        # 按分数排序并返回结果
        if validated_amounts:
            validated_amounts.sort(key=lambda x: x['score'], reverse=True)
            # 最多返回前3个最相关的结果
            top_results = validated_amounts[:3]
            result_texts = [item['text'] for item in top_results]
            
            combined_result = ' | '.join(result_texts)
            if len(combined_result) > 3000:
                combined_result = combined_result[:2997] + '...'
            
            # LLM分析：从文本中提取具体的金额数字
            analyzed_amount = self._analyze_amount_with_llm(combined_result, amount_type, language)
            if analyzed_amount:
                return analyzed_amount
            
            return combined_result
        
        return ""

    def _get_enhanced_keywords(self, language: str, amount_type: str) -> tuple:
        """获取增强的关键词库"""
        if language == 'english':
            if amount_type == 'claim':
                keywords = [
                    # 原有关键词
                    'claims', 'seeks', 'damages', 'compensation', 'plaintiff seeks', 
                    'applicant seeks', 'prays for', 'relief sought',
                    
                    # 新增关键词
                    'sum of', 'amount of', 'payment of', 'recovery of', 'reimbursement of',
                    'refund of', 'outstanding', 'principal amount', 'principal sum',
                    'loan amount', 'debt of', 'owing', 'due and owing', 'balance of',
                    'unpaid sum', 'contractual amount', 'agreed sum', 'deposit of',
                    'security of', 'guarantee of', 'liability of', 'quantum of',
                    'monetary claim', 'financial claim', 'pecuniary loss', 'loss and damage'
                ]
                context_words = ['claim', 'seek', 'damage', 'compensation', 'debt', 'owing', 'recovery', 'loss']
            else:  # judgment
                keywords = [
                    # 原有关键词
                    'ordered to pay', 'judgment for', 'costs assessed', 'defendant shall pay',
                    'award', 'grant', 'summarily assessed',
                    
                    # 新增关键词
                    'I order', 'the court orders', 'hereby ordered', 'it is ordered',
                    'judgment is entered', 'decree that', 'direct payment', 'liable to pay',
                    'responsible for', 'costs of', 'costs in the sum', 'interest on',
                    'penalty of', 'fine of', 'damages awarded', 'compensation ordered',
                    'restitution of', 'refund ordered', 'payment directed', 'sum awarded',
                    'amount granted', 'relief granted', 'monetary judgment', 'pecuniary award',
                    'costs summarily assessed', 'costs taxed', 'interest at', 'compound interest',
                    'default judgment for', 'judgment in favour', 'enter judgment for'
                ]
                context_words = ['order', 'pay', 'costs', 'assess', 'award', 'judgment', 'grant', 'liable']
        else:  # chinese
            if amount_type == 'claim':
                keywords = [
                    '申請', '索償', '賠償', '損失', '要求', '請求', '原告申請', '申請人請求',
                    '欠款', '債務', '借款', '貸款', '本金', '利息', '違約金', '罰款'
                ]
                context_words = ['申請', '索償', '賠償', '要求', '損失', '債務']
            else:  # judgment
                keywords = [
                    '判令', '命令', '賠償', '支付', '費用', '法庭命令', '判決', '裁定支付',
                    '責令', '判給', '給予', '授予', '課以', '罰款', '利息'
                ]
                context_words = ['判令', '支付', '費用', '賠償', '命令', '判決']
        
        return keywords, context_words

    def _get_enhanced_amount_patterns(self, language: str) -> list:
        """获取增强的金额识别模式"""
        patterns = [
            # 完整货币表达
            r'HK\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'USD?[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?', 
            r'US\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'RMB[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            
            # 文字描述
            r'(?:Hong Kong|US|United States)\s+Dollars?\s*[\d,]+(?:\.\d{2})?',
            r'(?:the\s+)?sum of\s+HK\$[\d,]+(?:\.\d{2})?',
            r'(?:the\s+)?amount of\s+USD?[\d,]+(?:\.\d{2})?',
            
            # 复合表达（本金+利息）
            r'HK\$[\d,]+(?:\.\d{2})?\s+(?:plus|together with|and)\s+interest',
            r'principal sum of\s+HK\$[\d,]+(?:\.\d{2})?',
            r'outstanding balance of\s+USD?[\d,]+(?:\.\d{2})?',
            
            # 数字先行模式
            r'[\d,]+(?:\.\d{2})?\s*(?:Hong Kong Dollars|US Dollars|USD|HKD)',
            r'[\d,]+(?:\.\d{2})?\s*(?:million|billion|thousand)?\s*(?:dollars?|USD|HKD)',
            
            # 简单数字模式（大金额）
            r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'[\d]{1,3}(?:,\d{3})+(?:\.\d{2})?',  # 格式化大数字
        ]
        
        if language == 'chinese':
            patterns.extend([
                r'(?:港幣|港币|美金|美元|人民幣|人民币)[\d,\.]+(?:萬|万|億|亿)?',
                r'[\d,]+(?:\.\d{2})?\s*(?:港元|美元|人民币)',
                r'[\d,]+\s*(?:萬|万|億|亿)\s*(?:港元|美元)'
            ])
        
        return patterns

    def _find_potential_amounts(self, text: str, amount_patterns: list) -> list:
        """查找所有潜在的金额表达"""
        potential_amounts = []
        
        for pattern in amount_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # 提取上下文（前后各150字符）
                start = max(0, match.start() - 150)
                end = min(len(text), match.end() + 150)
                context = text[start:end]
                
                # 清理上下文
                context = re.sub(r'\s+', ' ', context.strip())
                
                potential_amounts.append({
                    'amount': match.group(),
                    'context': context,
                    'position': match.start(),
                    'full_text_len': len(text)
                })
        
        return potential_amounts

    def _validate_amount_context(self, amount_info: dict, amount_type: str, language: str, 
                                keywords: list, context_words: list) -> float:
        """验证金额上下文的相关性，返回置信度分数"""
        context = amount_info['context'].lower()
        score = 0.0
        
        # 关键词匹配得分
        for keyword in keywords:
            if keyword.lower() in context:
                if len(keyword) > 10:  # 长关键词权重更高
                    score += 3
                elif len(keyword) > 5:
                    score += 2
                else:
                    score += 1
        
        # 上下文词汇得分
        for word in context_words:
            if word.lower() in context:
                score += 1
        
        # 负面关键词扣分（避免误判）
        if amount_type == 'claim':
            negative_words = ['costs', 'legal fees', 'court fees', 'filing fee', 'ordered to pay']
        else:  # judgment
            negative_words = ['claims', 'seeks damages', 'plaintiff seeks', 'applicant seeks']
        
        for neg_word in negative_words:
            if neg_word in context:
                score -= 1.5
        
        # 位置加分
        if amount_info.get('full_text_len', 0) > 0:
            text_position = amount_info['position'] / amount_info['full_text_len']
            if amount_type == 'judgment' and text_position > 0.6:
                score += 1  # 判决金额在后部分
            elif amount_type == 'claim' and text_position < 0.4:
                score += 1  # 申请金额在前部分
        
        return max(0.0, score)

    def _analyze_amount_with_llm(self, text: str, amount_type: str, language: str) -> str:
        """使用LLM分析文本，提取具体的金额数字"""
        if not text or len(text.strip()) < 20:
            return ""
        
        try:
            # 构建分析提示
            if language == 'english':
                if amount_type == 'claim':
                    prompt = f"""
分析以下法律文档文本，提取所有被告要求赔偿的现金总额。

要求：
1. 只返回一个具体的金额数字（如：HK$100,000 或 USD50,000）
2. 如果有多个金额，计算总和
3. 如果没有明确的金额，返回unknown
4. 不要包含解释或其他文字

文本内容：
{text}

分析结果（只返回金额数字）："""
                else:  # judgment
                    prompt = f"""
分析以下法律文档文本，提取所有被告实际需要赔偿的总额（判决金额）。

要求：
1. 只返回一个具体的金额数字（如：HK$100,000 或 USD50,000）
2. 如果有多个金额，计算总和
3. 如果没有明确的判决金额，返回unknown
4. 不要包含解释或其他文字

文本内容：
{text}

分析结果（只返回金额数字）："""
            else:  # chinese
                if amount_type == 'claim':
                    prompt = f"""
分析以下中文法律文档文本，提取所有申请人要求的赔偿总额。

要求：
1. 只返回一个具体的金额数字（如：港币100,000元 或 人民币50,000元）
2. 如果有多个金额，计算总和
3. 如果没有明确的金额，返回空字符串
4. 不要包含解释或其他文字

文本内容：
{text}

分析结果（只返回金额数字）："""
                else:  # judgment
                    prompt = f"""
分析以下中文法律文档文本，提取所有被告实际需要赔偿的总额（判决金额）。

要求：
1. 只返回一个具体的金额数字（如：港币100,000元 或 人民币50,000元）
2. 如果有多个金额，计算总和
3. 如果没有明确的判决金额，返回空字符串
4. 不要包含解释或其他文字

文本内容：
{text}

分析结果（只返回金额数字）："""
            
            # 这里可以集成实际的LLM API调用
            # 目前先使用基于规则的方法作为备选
            analyzed_amount = self._extract_amount_numbers_from_text(text)
            
            if analyzed_amount:
                self.logger.info(f"LLM分析成功提取{amount_type}金额: {analyzed_amount}")
                return analyzed_amount
                
        except Exception as e:
            self.logger.warning(f"LLM金额分析失败: {e}")
        
        return ""
    
    def _extract_amount_numbers_from_text(self, text: str) -> str:
        """从文本中提取并计算金额数字（增强版）"""
        # 更全面的金额识别模式
        amount_patterns = [
            # 标准货币格式
            r'HK\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'USD?\s*[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'US\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'RMB[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            
            # 文字表达
            r'(?:Hong Kong|US|United States)\s+Dollars?\s*[\d,]+(?:\.\d{2})?',
            r'(?:the\s+)?sum of\s+(?:HK\$|USD?|US\$)[\d,]+(?:\.\d{2})?',
            r'(?:the\s+)?amount of\s+(?:HK\$|USD?|US\$)[\d,]+(?:\.\d{2})?',
            
            # 数字在前格式
            r'[\d,]+(?:\.\d{2})?\s*(?:Hong Kong Dollars|US Dollars|USD|HKD)',
            r'[\d,]+(?:\.\d{2})?\s*(?:million|billion|thousand)?\s*(?:dollars?|USD|HKD)',
            
            # 简单数字（大金额）
            r'\$[\d,]+(?:\.\d{2})?(?:\s*(?:million|billion|thousand))?',
            r'[\d]{1,3}(?:,\d{3})+(?:\.\d{2})?',  # 格式化大数字
            
            # 中文格式
            r'(?:港币|港幣|美金|美元|人民币|人民幣)[\d,]+(?:\.\d{2})?(?:\s*(?:万|萬|亿|億))?',
            r'[\d,]+(?:\.\d{2})?\s*(?:港元|美元|人民币|元)',
            r'[\d,]+\s*(?:万|萬|亿|億)\s*(?:港元|美元|元)',
            
            # 法律文档常见表达
            r'damages?\s+(?:of|in the sum of|totaling|amounting to)\s+(?:HK\$|USD?|US\$|\$)[\d,]+(?:\.\d{2})?',
            r'compensation\s+(?:of|in the sum of)\s+(?:HK\$|USD?|US\$|\$)[\d,]+(?:\.\d{2})?',
            r'costs?\s+(?:of|in the sum of|assessed at)\s+(?:HK\$|USD?|US\$|\$)[\d,]+(?:\.\d{2})?'
        ]
        
        found_amounts = []
        amount_values = []
        currencies = set()
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # 提取数字和币种
                amount_data = self._parse_amount_match(match)
                if amount_data:
                    value, currency = amount_data
                    if value > 0:  # 排除零值
                        amount_values.append(value)
                        currencies.add(currency)
                        found_amounts.append(f"{currency}{value:,.0f}")
        
        if not amount_values:
            return ""
        
        # 选择最合适的金额
        if len(currencies) == 1:
            # 单一币种，计算总和
            currency = list(currencies)[0]
            total_value = sum(amount_values)
            return f"{currency}{total_value:,.0f}"
        else:
            # 多币种，返回最大金额
            max_value = max(amount_values)
            max_index = amount_values.index(max_value)
            return found_amounts[max_index] if found_amounts else ""
    
    def _parse_amount_match(self, match: str) -> tuple:
        """解析匹配到的金额字符串，返回(数值, 币种)"""
        try:
            # 确定币种
            if 'HK' in match.upper() or '港' in match:
                currency = 'HK$'
            elif 'USD' in match.upper() or 'US$' in match.upper() or 'US ' in match.upper() or '美' in match:
                currency = 'USD'
            elif 'RMB' in match.upper() or '人民' in match:
                currency = 'RMB'
            else:
                currency = '$'
            
            # 提取数字
            number_match = re.search(r'[\d,]+(?:\.\d{2})?', match)
            if not number_match:
                return None
            
            number_str = number_match.group().replace(',', '')
            value = float(number_str)
            
            # 处理单位（million, billion等）
            if re.search(r'\bmillion\b', match, re.IGNORECASE):
                value *= 1000000
            elif re.search(r'\bbillion\b', match, re.IGNORECASE):
                value *= 1000000000
            elif re.search(r'\bthousand\b', match, re.IGNORECASE):
                value *= 1000
            elif '万' in match or '萬' in match:
                value *= 10000
            elif '亿' in match or '億' in match:
                value *= 100000000
            
            return (value, currency)
            
        except (ValueError, AttributeError):
            return None

    def _combine_amount_results(self, results: list) -> str:
        """合并多个搜索结果"""
        valid_results = [r for r in results if r and r.strip()]
        
        if not valid_results:
            return ""
        
        # 去重
        unique_results = []
        for result in valid_results:
            # 简单去重：检查前50个字符是否相似
            is_duplicate = False
            for existing in unique_results:
                if len(result) > 50 and len(existing) > 50:
                    if result[:50] == existing[:50]:
                        is_duplicate = True
                        break
            if not is_duplicate:
                unique_results.append(result)
        
        combined = ' | '.join(unique_results)
        if len(combined) > 3000:
            combined = combined[:2997] + '...'
        
        return combined
    
    def detect_document_type(self, text: str, file_name: str) -> str:
        """检测文书类型"""
        if file_name:
            file_upper = file_name.upper()
            for doc_type in ['HCA', 'HCAL', 'CACC', 'CAMP', 'CACV', 'DCCC', 'DCMP', 'DCCJ', 'LD', 'HC', 'FCMC']:
                if doc_type in file_upper:
                    self.logger.info(f"Document type detected from filename: {doc_type}")
                    return doc_type
        return 'GENERIC'
    
    def extract_information(self, text: str, file_name: str = "") -> Dict[str, str]:
        """
        从文本中提取关键信息 - 支持中文文档专门处理
        
        Args:
            text: 文档文本内容
            file_name: 文件名（可选）
            
        Returns:
            包含提取信息的字典
        """
        if not text:
            self.logger.warning("Empty text provided for extraction")
            return {}

        language = self.detect_language(text)
        
        # === 中文文档专门处理 ===
        if language == 'chinese' and self.chinese_extractor:
            # 使用专门的中文文档处理器
            if self.chinese_extractor.is_chinese_document(text):
                self.logger.info("使用专门的中文文档处理器")
                return self.chinese_extractor.process_chinese_document(text, file_name)
        
        # === 英文文档或回退处理 ===
        doc_type = self.detect_document_type(text, file_name)
        
        # 检测是否为勘误文档
        if self._is_corrigendum_document(text):
            self.logger.info("检测到勘误文档，使用专门处理逻辑")
            return self._extract_corrigendum_information(text, file_name, language)
        
        self.logger.info("开始分层提取策略：前4页提取基本信息 + 末尾提取律师信息")
        
        # === 第一层：前4页提取基本信息（性能优化） ===
        # 估算前4页内容（约15000字符）- 确保包含完整的法庭名称、审判日期、案件编号、当事人信息
        first_pages = text[:15000]
        
        # === 第二层：末尾提取律师信息段落 ===
        lawyer_segment = self.extract_lawyer_segment(text, language)
        
        # === 第三层：全文提取复杂字段（如金额信息） ===
        # 这些字段可能分散在整个文档中
        
        return {
            # === 第一层：前4页基本信息（高效提取） ===
            'case_number': self.extract_case_number(first_pages, language),
            'trial_date': self.extract_trial_date(first_pages, language),  # 优化：前4页足够
            'court_name': self.extract_court_name(first_pages, language),  # 优化：第1页开头必有
            'plaintiff': self.extract_plaintiff(first_pages, language, doc_type),
            'defendant': self.extract_defendant(first_pages, language, doc_type),
            'judge': self.extract_judge(first_pages, language),
            'case_type': self.extract_case_type(first_pages, language, doc_type),
            
            # === 第二层：律师信息段落（从末尾提取） ===
            'lawyer': lawyer_segment,  # 律师信息段落而不是具体姓名
            
            # === 第三层：复杂字段（需要特定位置或全文） ===
            'judgment_result': self.extract_judgment_result(text, language),  # 判决结果在文档末尾
            'claim_amount': self.extract_amount_segments(text, language, 'claim'),  # 金额信息分散
            'judgment_amount': self.extract_amount_segments(text, language, 'judgment'),
            
            # === 元信息 ===
            'language': language,
            'document_type': doc_type,
            'file_name': Path(file_name).name if file_name else "",
            'file_path': file_name
        }
    
    def _is_corrigendum_document(self, text: str) -> bool:
        """检测是否为勘误文档"""
        corrigendum_indicators = [
            'CORRIGENDUM',
            'C O R R I G E N D U M', 
            'corrigendum in the Judgment',
            'corrigendum in the Decision',
            'Please note the following corrigendum'
        ]
        
        return any(indicator in text for indicator in corrigendum_indicators)
    
    def _extract_corrigendum_information(self, text: str, file_name: str, language: str) -> Dict[str, str]:
        """提取勘误文档的专门信息"""
        
        # 基本信息提取
        basic_info = {
            'case_number': self.extract_case_number(text, language),
            'trial_date': self.extract_trial_date(text, language),
            'court_name': self.extract_court_name(text, language),
            'plaintiff': self.extract_plaintiff(text, language, 'Corrigendum'),
            'defendant': self.extract_defendant(text, language, 'Corrigendum'),
            'language': language,
            'document_type': 'Corrigendum'
        }
        
        # 勘误文档特殊字段设置
        basic_info.update({
            'case_type': 'Corrigendum Document',
            'judgment_result': 'N/A - Corrigendum',
            'claim_amount': '',  # 勘误文档不涉及金额
            'judgment_amount': '',  # 勘误文档不涉及金额
        })
        
        # 提取勘误特定信息
        corrigendum_info = self._extract_corrigendum_details(text)
        basic_info.update(corrigendum_info)
        
        return basic_info
    
    def _extract_corrigendum_details(self, text: str) -> Dict[str, str]:
        """提取勘误文档的具体信息"""
        details = {}
        
        # 提取原文档日期
        original_date_patterns = [
            r'corrigendum in the (Judgment|Decision) dated (\d{1,2} \w+ \d{4})',
            r'in the (Judgment|Decision) dated (\d{1,2} \w+ \d{4})',
        ]
        
        for pattern in original_date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                details['corrected_document_type'] = match.group(1)
                details['original_document_date'] = match.group(2)
                break
        
        # 提取勘误日期
        corrigendum_date_match = re.search(r'Date of Corrigendum:\s*(\d{1,2} \w+ \d{4})', text)
        if corrigendum_date_match:
            details['corrigendum_date'] = corrigendum_date_match.group(1)
        
        # 提取更正内容摘要
        correction_patterns = [
            r'At page \d+.*?"([^"]+)" be corrected to "([^"]+)"',
            r'should read:?\s*"([^"]+)"',
            r'The names of.*?are added',
            r'corrected to\s*"([^"]+)"',
        ]
        
        corrections = []
        for pattern in correction_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                for match in matches[:2]:  # 最多2个更正
                    if isinstance(match, tuple) and len(match) == 2:
                        corrections.append(f"{match[0]} → {match[1]}")
                    elif isinstance(match, tuple):
                        corrections.append(' '.join(match))
                    else:
                        corrections.append(str(match))
        
        if not corrections:
            # 简单描述
            if 'names' in text.lower() and 'added' in text.lower():
                corrections.append("添加律师姓名")
            elif 'corrected' in text.lower():
                corrections.append("文字更正")
            else:
                corrections.append("格式或内容更正")
        
        details['correction_summary'] = '; '.join(corrections[:2])
        
        return details
    
    def process_pdf(self, pdf_path: str) -> Optional[Dict[str, str]]:
        """处理单个PDF文件"""
        self.logger.info(f"Processing PDF: {pdf_path}")
        
        text = self.extract_pdf_text(pdf_path)
        if not text:
            self.logger.error(f"Failed to extract text from {pdf_path}")
            return None
        
        file_name = Path(pdf_path).name
        result = self.extract_information(text, file_name)
        result['file_path'] = pdf_path
        result['file_name'] = file_name
        
        self.logger.info(f"Successfully processed {pdf_path}")
        return result 
    
    def _extract_multiple_parties_chinese(self, text: str, party_type: str) -> str:
        """提取多方当事人（中文）- 增强版，支持诉讼描述格式"""
        
        if party_type == '原告':
            # 策略1：诉讼描述格式 - "原告人XXX起訴..." (优先级更高)
            litigation_plaintiffs = self._extract_litigation_format_plaintiffs(text)
            if litigation_plaintiffs:
                return litigation_plaintiffs
                
        else:  # 被告
            # 策略1：诉讼描述格式 - "起訴第一被告人、第二被告人..." (优先级更高)
            litigation_defendants = self._extract_litigation_format_defendants(text)
            if litigation_defendants:
                return litigation_defendants
            
            # 策略2：标准格式 - 第一被告人、第二被告人 (回退)
            standard_defendants = self._extract_standard_chinese_defendants(text)
            if standard_defendants:
                return standard_defendants
        
        return ""
    
    def _extract_standard_chinese_plaintiffs(self, text: str) -> str:
        """提取标准格式中文原告"""
        patterns = [
            r'第一原告人\s*([^第\n]+)(?=第二原告人|第三原告人|被告)',
            r'第二原告人\s*([^第\n]+)(?=第三原告人|第四原告人|被告)',
            r'第三原告人\s*([^第\n]+)(?=第四原告人|第五原告人|被告)',
            r'第四原告人\s*([^第\n]+)(?=第五原告人|第六原告人|被告)',
            r'第五原告人\s*([^第\n]+)(?=第六原告人|被告)',
        ]
        
        parties = []
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, text)
            if match:
                party_name = re.sub(r'\s+', ' ', match.group(1).strip())
                if len(party_name) > 2:
                    parties.append(f"{party_name} (第{i}原告人)")
        
        if len(parties) > 1:
            return ' | '.join(parties)
        elif len(parties) == 1:
            return parties[0]
        
        return ""
    
    def _extract_standard_chinese_defendants(self, text: str) -> str:
        """提取标准格式中文被告"""
        patterns = [
            r'第一被告人\s*([^第\n]+)(?=第二被告人|第三被告人|Before)',
            r'第二被告人\s*([^第\n]+)(?=第三被告人|第四被告人|Before)',
            r'第三被告人\s*([^第\n]+)(?=第四被告人|第五被告人|Before)',
            r'第四被告人\s*([^第\n]+)(?=第五被告人|第六被告人|Before)',
            r'第五被告人\s*([^第\n]+)(?=第六被告人|Before)',
        ]
        
        parties = []
        for i, pattern in enumerate(patterns, 1):
            match = re.search(pattern, text)
            if match:
                party_name = re.sub(r'\s+', ' ', match.group(1).strip())
                if len(party_name) > 2:
                    parties.append(f"{party_name} (第{i}被告人)")
        
        if len(parties) > 1:
            return ' | '.join(parties)
        elif len(parties) == 1:
            return parties[0]
        
        return ""
    
    def _extract_litigation_format_plaintiffs(self, text: str) -> str:
        """提取诉讼描述格式的原告 - 新增方法"""
        # 模式：原告人XXX起訴...
        patterns = [
            # 模式1：之原告人XXX起訴
            r'之原告人([^起訴\n]+?)(?:起訴|女士起訴|先生起訴)',
            # 模式2：原告人XXX起訴  
            r'原告人([^起訴\n]+?)(?:起訴|女士起訴|先生起訴)',
            # 模式3：申請人XXX申請
            r'申請人([^申請\n]+?)(?:申請|女士申請|先生申請)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                plaintiff_raw = match.group(1).strip()
                
                # 清理格式
                plaintiff_clean = re.sub(r'\s+', ' ', plaintiff_raw)
                plaintiff_clean = re.sub(r'^[^\u4e00-\u9fff]*', '', plaintiff_clean)  # 移除开头非中文字符
                plaintiff_clean = plaintiff_clean.strip()
                
                if 2 <= len(plaintiff_clean) <= 50:
                    return plaintiff_clean
        
        return ""
    
    def _extract_litigation_format_defendants(self, text: str) -> str:
        """提取诉讼描述格式的被告 - 新增方法"""
        defendants = []
        
        # 方法1：从完整诉讼描述中提取编号被告
        litigation_patterns = [
            # 匹配：起訴第一被告人XXX、第二被告人YYY...
            r'起訴.*?第一被告人([^，、第]+?)(?:女士|先生)?[，、].*?第二被告人([^，、第]+?)(?:女士|先生)?(?:[，、].*?第三被告人([^，、第]+?)(?:女士|先生)?)?(?:[，、].*?第四被告人([^，、第]+?)(?:女士|先生)?)?',
            # 简化模式：第X被告人XXX
            r'第([一二三四五六七八九十])被告人([^，、第\n]+?)(?:女士|先生)?(?:[，、]|$)'
        ]
        
        for pattern in litigation_patterns:
            matches = re.findall(pattern, text)
            if matches:
                if pattern == litigation_patterns[0]:  # 完整模式
                    for match in matches:
                        for i, defendant_name in enumerate(match, 1):
                            if defendant_name and defendant_name.strip():
                                clean_name = re.sub(r'\s+', ' ', defendant_name.strip())
                                # 进一步清理
                                clean_name = self._clean_chinese_defendant_name(clean_name)
                                if clean_name:
                                    defendants.append(f"{clean_name} (第{i}被告人)")
                else:  # 简化模式
                    chinese_nums = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
                    for num_text, name in matches:
                        if num_text in chinese_nums:
                            clean_name = re.sub(r'\s+', ' ', name.strip())
                            clean_name = self._clean_chinese_defendant_name(clean_name)
                            if clean_name:
                                defendants.append(f"{clean_name} (第{chinese_nums[num_text]}被告人)")
        
        # 方法2：直接搜索被告模式（回退）
        if not defendants:
            direct_patterns = [
                r'第一被告人[：:\s]*([^，、第\n]+?)(?:女士|先生)?(?:[，、]|、第二被告人)',
                r'第二被告人[：:\s]*([^，、第\n]+?)(?:女士|先生)?(?:[，、]|、第三被告人)',  
                r'第三被告人[：:\s]*([^，、第\n]+?)(?:女士|先生)?(?:[，、]|、第四被告人)',
                r'第四被告人[：:\s]*([^，、第\n]+?)(?:女士|先生)?(?:[，、]|$)',
            ]
            
            for i, pattern in enumerate(direct_patterns, 1):
                match = re.search(pattern, text)
                if match:
                    clean_name = self._clean_chinese_defendant_name(match.group(1))
                    if clean_name:
                        defendants.append(f"{clean_name} (第{i}被告人)")
        
        # 去重并排序
        unique_defendants = []
        for defendant in defendants:
            if defendant not in unique_defendants:
                unique_defendants.append(defendant)
        
        if len(unique_defendants) > 1:
            return ' | '.join(unique_defendants)
        elif len(unique_defendants) == 1:
            return unique_defendants[0]
        
        return ""
    
    def _clean_chinese_defendant_name(self, name: str) -> str:
        """清理中文被告姓名"""
        if not name:
            return ""
        
        # 基本清理
        clean = re.sub(r'\s+', ' ', name.strip())
        
        # 移除常见后缀词
        clean = re.sub(r'(?:女士|先生|小姐)$', '', clean)
        
        # 移除干扰词
        clean = re.sub(r'^(?:及|、|，|,|\s)+', '', clean)
        clean = re.sub(r'(?:及|、|，|,|\s)+$', '', clean)
        
        # 移除明显的干扰内容
        if '無律師代' in clean or '缺席應訊' in clean or '親自出庭' in clean:
            return ""
        
        # 验证长度和有效性
        if 2 <= len(clean) <= 30 and not re.match(r'^[\s\d，、,]+$', clean):
            return clean
        
        return ""
    
    def _get_ordinal_suffix(self, num: int) -> str:
        """获取序数词后缀"""
        if 10 <= num % 100 <= 13:
            return 'th'
        else:
            return {1: 'st', 2: 'nd', 3: 'rd'}.get(num % 10, 'th')
    
    def extract_lawyer_segment(self, text: str, language: str) -> str:
        """
        提取律师信息段落 - 优化版本
        
        策略：
        1. 扫描文档最后20%的内容（律师信息通常在末尾）
        2. 查找包含'instructed by'等关键模式的段落
        3. 提取300-500字的律师信息段落供LLM处理
        4. 返回结构化段落而不是具体姓名
        
        Args:
            text: 完整文档文本
            language: 文档语言
            
        Returns:
            包含律师信息的段落文本，格式化供LLM进一步处理
        """
        if not text:
            return ""
        
        self.logger.info("开始提取律师信息段落（从文档末尾）")
        
        # === 策略1：扫描文档最后20%的内容 ===
        last_section_start = max(0, len(text) - len(text) // 5)
        last_section = text[last_section_start:]
        
        if language == 'english':
            return self._extract_english_lawyer_segment(last_section, text)
        else:
            return self._extract_chinese_lawyer_segment(last_section, text)
    
    def _extract_english_lawyer_segment(self, last_section: str, full_text: str) -> str:
        """提取英文律师信息段落 - 增强版"""
        lawyer_segments = []
        
        # === 增强的律师信息模式 ===
        lawyer_patterns = [
            # 标准格式
            r'(?i)(?:mr|ms|miss)\.?\s+[A-Z][a-z]+[^.]*?instructed\s+by[^.]*?for\s+(?:the\s+)?(?:plaintiff|defendant)',
            r'(?i)instructed\s+by[^.]*?for\s+(?:the\s+)?(?:plaintiff|defendant)',
            r'(?i)counsel\s+for\s+(?:the\s+)?(?:plaintiff|defendant)[:\s]+([^\n\.]+)',
            r'(?i)(?:plaintiff|defendant).*?represented\s+by[^.]*?instructed\s+by',
            
            # 新增格式
            r'(?i)for\s+(?:the\s+)?(?:plaintiff|defendant)[:\s]+(?:mr|ms|miss)\.?\s+[A-Z][a-z]+',
            r'(?i)(?:mr|ms|miss)\.?\s+[A-Z][a-z]+.*?(?:instructed\s+by|of\s+[A-Z][a-z]+.*?(?:chambers|solicitors?))',
            r'(?i)(?:mr|ms|miss)\.?\s+[A-Z][a-z]+.*?for\s+(?:the\s+)?(?:plaintiff|defendant|1st|2nd|3rd|4th)',
            r'(?i)(?:leading\s+)?counsel.*?(?:instructed\s+by|for\s+(?:the\s+)?(?:plaintiff|defendant))',
            r'(?i)(?:the\s+)?(?:plaintiff|defendant).*?(?:was\s+)?not\s+represented',
        ]
        
        # === 方法1：扫描段落 ===
        paragraphs = re.split(r'\n\s*\n', last_section)
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) < 30:  # 降低最小长度要求
                continue
                
            # 检查律师信息模式
            has_lawyer_info = any(re.search(pattern, paragraph) for pattern in lawyer_patterns)
            
            # 扩展关键词检查
            lawyer_keywords = [
                'instructed by', 'counsel for', 'represented by', 'chambers', 'solicitor',
                'barrister', 'appeared for', 'acting for', 'solicitors', 'law firm',
                'not represented', 'in person', 'did not appear'
            ]
            has_keywords = any(keyword in paragraph.lower() for keyword in lawyer_keywords)
            
            # 检查律师姓名模式
            has_name_pattern = bool(re.search(r'(?i)(?:mr|ms|miss)\.?\s+[A-Z][a-z]+', paragraph))
            
            if has_lawyer_info or (has_keywords and has_name_pattern):
                cleaned = self._clean_lawyer_segment(paragraph)
                if 15 <= len(cleaned) <= 1000:  # 放宽长度限制
                    lawyer_segments.append(cleaned)
        
        # === 方法2：扫描最后几行（很多律师信息在文档最末尾）===
        if not lawyer_segments:
            lines = last_section.split('\n')[-10:]  # 取最后10行
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # 检查是否包含律师信息
                line_lower = line.lower()
                if any(keyword in line_lower for keyword in ['instructed', 'counsel', 'represented', 'chambers']):
                    # 收集相关的连续行
                    context_lines = []
                    start_idx = max(0, i-2)
                    end_idx = min(len(lines), i+3)
                    
                    for j in range(start_idx, end_idx):
                        if j < len(lines) and lines[j].strip():
                            context_lines.append(lines[j].strip())
                    
                    if context_lines:
                        segment = ' '.join(context_lines)
                        cleaned = self._clean_lawyer_segment(segment)
                        if 15 <= len(cleaned) <= 800:
                            lawyer_segments.append(cleaned)
                            break  # 找到一个就够了
        
        # === 方法3：如果还是没找到，扩大搜索范围到文档后30% ===
        if not lawyer_segments:
            extended_section_start = max(0, len(full_text) - len(full_text) * 30 // 100)
            extended_section = full_text[extended_section_start:]
            
            # 在更大范围内搜索明确的律师信息模式
            clear_patterns = [
                r'(?i)(?:mr|ms|miss)\.?\s+[A-Z][a-z]+.*?instructed\s+by.*?for\s+(?:the\s+)?(?:plaintiff|defendant)',
                r'(?i)for\s+(?:the\s+)?(?:plaintiff|defendant)[:\s]+(?:mr|ms|miss)\.?\s+[A-Z][a-z]+.*?(?:instructed|chambers)',
                r'(?i)(?:the\s+)?(?:plaintiff|defendant).*?not\s+represented',
                r'(?i)(?:the\s+)?(?:plaintiff|defendant).*?did\s+not\s+appear'
            ]
            
            for pattern in clear_patterns:
                matches = re.finditer(pattern, extended_section)
                for match in matches:
                    # 获取匹配内容及其上下文
                    start = max(0, match.start() - 100)
                    end = min(len(extended_section), match.end() + 100)
                    context = extended_section[start:end]
                    
                    cleaned = self._clean_lawyer_segment(context)
                    if 20 <= len(cleaned) <= 600:
                        lawyer_segments.append(cleaned)
                        if len(lawyer_segments) >= 2:  # 最多2个
                            break
        
        # === 组合结果 ===
        if lawyer_segments:
            # 去重
            unique_segments = []
            for segment in lawyer_segments:
                is_duplicate = False
                for existing in unique_segments:
                    # 简单重复检查
                    if len(segment) > 30 and len(existing) > 30:
                        if segment[:30] == existing[:30]:
                            is_duplicate = True
                            break
                if not is_duplicate:
                    unique_segments.append(segment)
            
            # 限制总长度
            result_segments = []
            total_length = 0
            
            for segment in unique_segments[:3]:  # 最多3个段落
                if total_length + len(segment) <= 600:  # 增加总长度限制
                    result_segments.append(segment)
                    total_length += len(segment)
                else:
                    # 截断最后一个段落
                    remaining = 600 - total_length
                    if remaining > 30:
                        result_segments.append(segment[:remaining-3] + '...')
                    break
            
            result = ' | '.join(result_segments)
            self.logger.info(f"提取到英文律师信息段落，长度: {len(result)}")
            return result
        
        self.logger.warning("未找到英文律师信息段落")
        return ""
    
    def _extract_chinese_lawyer_segment(self, last_section: str, full_text: str) -> str:
        """提取中文律师信息段落"""
        # 中文律师信息模式
        chinese_patterns = [
            r'委托律师[：:]\s*[^\n]+',
            r'代理律师[：:]\s*[^\n]+',
            r'(?:原告|申請人|被告|被申請人).*?委託.*?代理',
            r'律师.*?(?:代表|代理)',
        ]
        
        lawyer_segments = []
        
        # 按段落搜索
        paragraphs = re.split(r'\n\s*\n', last_section)
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if len(paragraph) < 20:
                continue
                
            # 检查是否包含中文律师信息
            has_lawyer_info = any(re.search(pattern, paragraph) for pattern in chinese_patterns)
            
            chinese_keywords = ['委托律师', '代理律师', '委託', '代理', '律师']
            has_keywords = any(keyword in paragraph for keyword in chinese_keywords)
            
            if has_lawyer_info or has_keywords:
                cleaned = self._clean_lawyer_segment(paragraph)
                if 15 <= len(cleaned) <= 600:
                    lawyer_segments.append(cleaned)
        
        if lawyer_segments:
            result = ' | '.join(lawyer_segments[:2])  # 中文最多2个段落
            self.logger.info(f"提取到中文律师信息段落，长度: {len(result)}")
            return result
        
        self.logger.warning("未找到中文律师信息段落")
        return ""
    
    def _is_lawyer_segment(self, text: str) -> bool:
        """判断文本是否是律师信息段落"""
        text_lower = text.lower()
        
        # 必须包含的关键词
        required_keywords = ['instructed', 'counsel', 'represented', 'solicitor', 'chambers']
        has_required = any(keyword in text_lower for keyword in required_keywords)
        
        # 律师姓名模式
        has_name_pattern = bool(re.search(r'(?:mr|ms|miss)\.?\s+[A-Z][a-z]+', text))
        
        # 当事方关键词
        has_party_ref = any(word in text_lower for word in ['plaintiff', 'defendant', 'applicant', 'respondent'])
        
        return has_required and (has_name_pattern or has_party_ref)
    
    def _clean_lawyer_segment(self, text: str) -> str:
        """清理律师信息段落"""
        if not text:
            return ""
        
        # 基本清理
        cleaned = re.sub(r'\s+', ' ', text.strip())
        
        # 移除页码和分隔符
        cleaned = re.sub(r'\s*-\s*\d+\s*-\s*', ' ', cleaned)
        cleaned = re.sub(r'\s*_{5,}\s*', ' ', cleaned)
        
        # 移除明显的非律师信息内容
        cleaned = re.sub(r'(?i)\s*(?:page|頁|第.*頁).*$', '', cleaned)
        cleaned = re.sub(r'^\s*[,;.:\s]+', '', cleaned)
        cleaned = re.sub(r'[.\s]*$', '', cleaned)
        
        return cleaned.strip()