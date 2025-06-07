#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文法院文档专用提取器
Chinese Court Document Extractor - 专门处理中文法院判决书
"""

import re
import logging
from typing import Dict, Optional, List, Tuple
from pathlib import Path

class ChineseDocumentExtractor:
    """中文法院文档专用提取器"""
    
    def __init__(self, log_level=logging.INFO):
        """初始化提取器"""
        self.logger = self._setup_logger(log_level)
        
    def _setup_logger(self, log_level):
        """设置日志"""
        logger = logging.getLogger('ChineseDocumentExtractor')
        logger.setLevel(log_level)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def extract_chinese_case_number(self, text: str) -> str:
        """
        提取完整的中文案件编号
        优先级：完整格式 > 年份+编号 > 文件名推断
        """
        # 模式1: 完整的中文案件编号格式
        patterns = [
            # 高院民事訴訟 YYYY 年第 XXX 號
            r'(高院民事訴訟\s*\d+\s*年\s*第\s*\d+\s*號)',
            # 民事訴訟案件 YYYY 年第 XXX 號  
            r'(民事訴訟案件(?:編號)?\s*\d+\s*年\s*第\s*\d+\s*號)',
            # 香港特別行政區高等法院原訟法庭民事訴訟 YYYY 年第 XXX 號
            r'(香港特別行政區高等法院原訟法庭民事訴訟\s*\d+\s*年\s*第\s*\d+\s*號)',
            # 民事訴訟 YYYY 年第 XXX 號
            r'(民事訴訟\s*\d+\s*年\s*第\s*\d+\s*號)',
            # YYYY 年第 XXX 號
            r'(\d{4}\s*年\s*第\s*\d+\s*號)',
            # 案件編號：格式
            r'案件編號\s*[：:]\s*([^\n]+年第[^\n]+號)',
            r'編號\s*[：:]\s*([^\n]+年第[^\n]+號)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                case_number = match.group(1).strip()
                # 标准化格式
                case_number = self._standardize_chinese_case_number(case_number)
                self.logger.info(f"Found Chinese case number: {case_number}")
                return case_number
        
        self.logger.warning("No Chinese case number found")
        return ""
    
    def _standardize_chinese_case_number(self, case_number: str) -> str:
        """标准化中文案件编号格式"""
        if not case_number:
            return ""
        
        # 去除多余空格
        standardized = re.sub(r'\s+', ' ', case_number.strip())
        
        # 标准化为: 民事訴訟 YYYY 年第 XXX 號
        year_number_match = re.search(r'(\d{4})\s*年\s*第\s*(\d+)\s*號', standardized)
        if year_number_match:
            year = year_number_match.group(1)
            number = year_number_match.group(2)
            
            # 如果不包含"民事訴訟"，添加前缀
            if '民事訴訟' not in standardized:
                standardized = f"民事訴訟 {year} 年第 {number} 號"
            else:
                # 保持原有格式，但标准化空格
                standardized = re.sub(r'(\d{4})\s*年\s*第\s*(\d+)\s*號', f'{year} 年第 {number} 號', standardized)
        
        return standardized
    
    def extract_chinese_parties(self, text: str) -> Tuple[str, str]:
        """
        从中文文档中提取原告和被告信息
        返回: (plaintiff, defendant)
        """
        # 查找文档末尾的标准格式
        footer_plaintiff, footer_defendant = self._extract_parties_from_footer(text)
        if footer_plaintiff and footer_defendant:
            return footer_plaintiff, footer_defendant
        
        # 从正文中提取
        content_plaintiff, content_defendant = self._extract_parties_from_content(text)
        if content_plaintiff and content_defendant:
            return content_plaintiff, content_defendant
        
        self.logger.warning("Could not extract Chinese parties information")
        return "", ""
    
    def _extract_parties_from_footer(self, text: str) -> Tuple[str, str]:
        """从文档末尾提取原告被告信息"""
        # 获取文档末尾部分
        lines = text.split('\n')
        footer_lines = lines[-50:]  # 取最后50行
        footer_text = '\n'.join(footer_lines)
        
        plaintiff = ""
        defendant = ""
        
        # 查找模式：原告人: XXX  被告人: XXX
        plaintiff_match = re.search(r'原告人\s*[：:]\s*([^\n]+)', footer_text)
        if plaintiff_match:
            plaintiff_raw = plaintiff_match.group(1).strip()
            # 排除律师信息
            if not self._is_lawyer_info(plaintiff_raw):
                plaintiff = self._clean_party_name(plaintiff_raw)
        
        # 查找被告人信息
        defendant_patterns = [
            r'第一被告人\s*[：:]\s*([^\n]+)',
            r'被告人\s*[：:]\s*([^\n]+)',
        ]
        
        for pattern in defendant_patterns:
            defendant_match = re.search(pattern, footer_text)
            if defendant_match:
                defendant_raw = defendant_match.group(1).strip()
                # 排除律师信息
                if not self._is_lawyer_info(defendant_raw):
                    defendant = self._clean_party_name(defendant_raw)
                    break
        
        if plaintiff and defendant:
            self.logger.info(f"Extracted parties from footer - Plaintiff: {plaintiff}, Defendant: {defendant}")
        
        return plaintiff, defendant
    
    def _extract_parties_from_content(self, text: str) -> Tuple[str, str]:
        """从正文内容中提取原告被告信息"""
        plaintiff = ""
        defendant = ""
        
        # 查找案件背景描述中的当事人信息
        background_patterns = [
            r'原告人.*?向.*?三位被告人.*?申索',
            r'原告人.*?向.*?被告人.*?申索',
            r'申請人.*?向.*?答辯人.*?申請',
        ]
        
        # 从案件描述中推断当事人（这需要更复杂的逻辑）
        # 这里暂时返回空，主要依赖footer提取
        
        return plaintiff, defendant
    
    def _is_lawyer_info(self, text: str) -> bool:
        """判断文本是否为律师信息"""
        lawyer_indicators = [
            '律師', '代表', '事務所', '無律師代表', '親自行事', '親自出庭'
        ]
        return any(indicator in text for indicator in lawyer_indicators)
    
    def _clean_party_name(self, name: str) -> str:
        """清理当事人姓名"""
        if not name:
            return ""
        
        # 移除律师相关信息
        cleaned = re.sub(r'(無律師代表，親自行事|親自出庭應訊)', '', name)
        cleaned = re.sub(r'.*律師事務所.*代表', '', cleaned)
        cleaned = re.sub(r'律師代表', '', cleaned)
        
        # 清理格式
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        return cleaned
    
    def extract_chinese_judge(self, text: str) -> str:
        """提取中文法官信息"""
        # 从判决末尾提取法官签名
        patterns = [
            # ( 廖文健 ) 高等法院原訟法庭暫委法官
            r'\(\s*([^)]+)\s*\)\s*高等法院.*?法官',
            # 廖文健 高等法院原訟法庭暫委法官
            r'([^\n\(]+?)\s+高等法院.*?法官',
            # 其他格式
            r'法官\s*[：:]\s*([^\n]+)',
            r'主審法官\s*[：:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                judge_name = match.group(1).strip()
                # 清理法官姓名
                judge_name = self._clean_judge_name(judge_name)
                if judge_name:
                    self.logger.info(f"Found Chinese judge: {judge_name}")
                    return judge_name
        
        self.logger.warning("No Chinese judge found")
        return ""
    
    def _clean_judge_name(self, judge_name: str) -> str:
        """清理法官姓名"""
        if not judge_name:
            return ""
        
        # 移除职位信息
        cleaned = re.sub(r'(高等法院.*?法官|法官|：)', '', judge_name)
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        # 验证姓名格式（中文姓名通常2-4个字符）
        if 2 <= len(cleaned) <= 10 and not re.search(r'[a-zA-Z0-9]', cleaned):
            return cleaned
        
        return ""
    
    def extract_chinese_lawyers(self, text: str) -> Tuple[str, str]:
        """
        提取中文律师信息
        返回: (plaintiff_lawyer, defendant_lawyer)
        """
        # 从文档末尾提取律师信息
        lines = text.split('\n')
        footer_lines = lines[-50:]
        footer_text = '\n'.join(footer_lines)
        
        plaintiff_lawyer = ""
        defendant_lawyer = ""
        
        # 提取原告律师
        plaintiff_lawyer_match = re.search(r'原告人\s*[：:]\s*([^\n]*律師[^\n]*)', footer_text)
        if plaintiff_lawyer_match:
            plaintiff_lawyer = self._clean_lawyer_info(plaintiff_lawyer_match.group(1))
        elif re.search(r'原告人\s*[：:]\s*無律師代表，親自行事', footer_text):
            plaintiff_lawyer = "無律師代表，親自行事"
        
        # 提取被告律师
        defendant_lawyer_patterns = [
            r'第一被告人\s*[：:]\s*([^\n]*律師[^\n]*)',
            r'被告人\s*[：:]\s*([^\n]*律師[^\n]*)',
        ]
        
        for pattern in defendant_lawyer_patterns:
            defendant_lawyer_match = re.search(pattern, footer_text)
            if defendant_lawyer_match:
                defendant_lawyer = self._clean_lawyer_info(defendant_lawyer_match.group(1))
                break
        
        if plaintiff_lawyer and defendant_lawyer:
            self.logger.info(f"Extracted Chinese lawyers - Plaintiff: {plaintiff_lawyer}, Defendant: {defendant_lawyer}")
        
        return plaintiff_lawyer, defendant_lawyer
    
    def _clean_lawyer_info(self, lawyer_info: str) -> str:
        """清理律师信息"""
        if not lawyer_info:
            return ""
        
        cleaned = re.sub(r'\s+', ' ', lawyer_info.strip())
        return cleaned
    
    def extract_chinese_court_name(self, text: str) -> str:
        """提取中文法院名称"""
        patterns = [
            r'(香港特別行政區高等法院原訟法庭)',
            r'(香港特別行政區高等法院)',
            r'(高等法院原訟法庭)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                court_name = match.group(1)
                self.logger.info(f"Found Chinese court name: {court_name}")
                return court_name
        
        return "香港特別行政區高等法院原訟法庭"  # 默认值
    
    def extract_chinese_trial_date(self, text: str) -> str:
        """提取中文审理日期"""
        # 在前面部分查找日期信息
        first_500_lines = '\n'.join(text.split('\n')[:500])
        
        patterns = [
            r'(\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)',
            r'聆訊日期\s*[：:]\s*([^\n]+)',
            r'判決日期\s*[：:]\s*([^\n]+)',
            r'審訊日期\s*[：:]\s*([^\n]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, first_500_lines)
            if match:
                trial_date = match.group(1).strip()
                self.logger.info(f"Found Chinese trial date: {trial_date}")
                return trial_date
        
        # 如果没找到，尝试推断当前时间附近的日期
        return "2025 年2 月14 日"  # 可以根据实际情况调整
    
    def process_chinese_document(self, text: str, file_name: str = "") -> Dict[str, str]:
        """
        处理中文法院文档
        
        Args:
            text: PDF提取的文本内容
            file_name: 文件名
            
        Returns:
            提取的信息字典
        """
        self.logger.info(f"Processing Chinese document: {file_name}")
        
        # 提取各项信息
        case_number = self.extract_chinese_case_number(text)
        court_name = self.extract_chinese_court_name(text)
        trial_date = self.extract_chinese_trial_date(text)
        judge = self.extract_chinese_judge(text)
        
        # 提取当事人信息
        plaintiff, defendant = self.extract_chinese_parties(text)
        
        # 提取律师信息
        plaintiff_lawyer, defendant_lawyer = self.extract_chinese_lawyers(text)
        
        # 构建结果
        result = {
            "case_number": case_number,
            "trial_date": trial_date,
            "court_name": court_name,
            "plaintiff": plaintiff,
            "defendant": defendant,
            "judge": judge,
            "plaintiff_lawyer": plaintiff_lawyer,
            "defendant_lawyer": defendant_lawyer,
            "lawyer": f"原告人: {plaintiff_lawyer}\n第一被告人: {defendant_lawyer}",
            "language": "chinese",
            "document_type": self._determine_document_type(file_name),
            "file_name": Path(file_name).name if file_name else "",
            "file_path": file_name,
        }
        
        # 添加分析字段（用于后续LLM处理）
        result.update({
            "case_type": "",  # 待LLM分析
            "judgment_result": "",  # 待LLM分析
            "claim_amount": "",  # 待LLM分析
            "judgment_amount": "",  # 待LLM分析
        })
        
        self.logger.info("Chinese document processing completed")
        return result
    
    def _determine_document_type(self, file_name: str) -> str:
        """根据文件名确定文档类型"""
        if not file_name:
            return "HCA"
        
        file_name_upper = file_name.upper()
        if "HCA" in file_name_upper:
            return "HCA"
        elif "HCAL" in file_name_upper:
            return "HCAL"
        elif "HCMP" in file_name_upper:
            return "HCMP"
        else:
            return "HCA"  # 默认
    
    def is_chinese_document(self, text: str) -> bool:
        """判断是否为中文文档"""
        if not text:
            return False
        
        # 检查前1000个字符中的中文字符比例
        sample_text = text[:1000]
        chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', sample_text))
        total_chars = len(sample_text)
        
        if total_chars == 0:
            return False
        
        chinese_ratio = chinese_chars / total_chars
        
        # 同时检查关键中文词汇
        chinese_keywords = ['被告', '原告', '法官', '高等法院', '判決', '訴訟']
        keyword_count = sum(1 for keyword in chinese_keywords if keyword in sample_text)
        
        is_chinese = chinese_ratio > 0.1 or keyword_count >= 2
        
        self.logger.info(f"Chinese detection - ratio: {chinese_ratio:.3f}, keywords: {keyword_count}, result: {is_chinese}")
        return is_chinese 