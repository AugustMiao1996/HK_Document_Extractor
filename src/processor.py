#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量文档处理器
Batch Document Processor for Hong Kong Court Documents

Author: AI Assistant
Version: 1.0
"""

import os
import json
import csv
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd

# 修复import路径
try:
    from extractor import DocumentExtractor
except ImportError:
    from .extractor import DocumentExtractor

class BatchProcessor:
    """批量文档处理器"""
    
    def __init__(self, output_dir: str = "output", log_dir: str = "logs"):
        """
        初始化批量处理器
        
        Args:
            output_dir: 输出目录
            log_dir: 日志目录
        """
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.extractor = DocumentExtractor()
        
        # 创建目录
        self.output_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """设置处理器日志"""
        logger = logging.getLogger('BatchProcessor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 文件日志
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"batch_process_{timestamp}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            
            # 控制台日志
            console_handler = logging.StreamHandler()
            
            # 格式化
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def find_pdf_files(self, input_dir: str, pattern: str = "*.pdf") -> List[str]:
        """
        查找PDF文件
        
        Args:
            input_dir: 输入目录
            pattern: 文件匹配模式
            
        Returns:
            PDF文件路径列表
        """
        input_path = Path(input_dir)
        if not input_path.exists():
            self.logger.error(f"Input directory does not exist: {input_dir}")
            return []
        
        pdf_files = list(input_path.glob(pattern))
        self.logger.info(f"Found {len(pdf_files)} PDF files in {input_dir}")
        
        return [str(pdf_file) for pdf_file in pdf_files]
    
    def process_directory(self, input_dir: str) -> List[Dict[str, str]]:
        """
        处理目录下的所有PDF文件
        
        Args:
            input_dir: 输入目录路径
            
        Returns:
            处理结果列表
        """
        self.logger.info(f"Starting batch processing for directory: {input_dir}")
        
        # 查找PDF文件
        pdf_files = self.find_pdf_files(input_dir)
        if not pdf_files:
            self.logger.warning("No PDF files found")
            return []
        
        # 处理文件
        results = []
        successful = 0
        failed = 0
        
        for i, pdf_file in enumerate(pdf_files, 1):
            self.logger.info(f"Processing {i}/{len(pdf_files)}: {Path(pdf_file).name}")
            
            try:
                result = self.extractor.process_pdf(pdf_file)
                if result:
                    results.append(result)
                    successful += 1
                    self.logger.info(f"✅ Successfully processed: {Path(pdf_file).name}")
                else:
                    failed += 1
                    self.logger.error(f"❌ Failed to process: {Path(pdf_file).name}")
            except Exception as e:
                failed += 1
                self.logger.error(f"❌ Error processing {Path(pdf_file).name}: {e}")
        
        self.logger.info(f"Batch processing completed: {successful} successful, {failed} failed")
        return results
    
    def save_results(self, results: List[Dict[str, str]], format_type: str = "all") -> Dict[str, str]:
        """
        保存处理结果
        
        Args:
            results: 处理结果列表
            format_type: 输出格式 ('json', 'csv', 'excel', 'all')
            
        Returns:
            保存的文件路径字典
        """
        if not results:
            self.logger.warning("No results to save")
            return {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        # JSON格式
        if format_type in ['json', 'all']:
            json_file = self.output_dir / f"extraction_results_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            saved_files['json'] = str(json_file)
            self.logger.info(f"Results saved to JSON: {json_file}")
        
        # CSV格式
        if format_type in ['csv', 'all']:
            csv_file = self.output_dir / f"extraction_results_{timestamp}.csv"
            df = pd.DataFrame(results)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            saved_files['csv'] = str(csv_file)
            self.logger.info(f"Results saved to CSV: {csv_file}")
        
        # Excel格式
        if format_type in ['excel', 'all']:
            excel_file = self.output_dir / f"extraction_results_{timestamp}.xlsx"
            df = pd.DataFrame(results)
            df.to_excel(excel_file, index=False, engine='openpyxl')
            saved_files['excel'] = str(excel_file)
            self.logger.info(f"Results saved to Excel: {excel_file}")
        
        return saved_files
    
    def generate_summary_report(self, results: List[Dict[str, str]]) -> Dict:
        """
        生成处理摘要报告
        
        Args:
            results: 处理结果列表
            
        Returns:
            摘要报告字典
        """
        if not results:
            return {}
        
        # 统计信息
        total_files = len(results)
        language_stats = {}
        court_stats = {}
        case_type_stats = {}
        
        # 统计各项指标
        for result in results:
            # 语言统计
            lang = result.get('language', 'unknown')
            language_stats[lang] = language_stats.get(lang, 0) + 1
            
            # 法庭统计
            court = result.get('court_name', 'unknown')
            if court and court != 'unknown':
                court_key = court[:50] + "..." if len(court) > 50 else court
                court_stats[court_key] = court_stats.get(court_key, 0) + 1
            
            # 案件类型统计
            case_type = result.get('case_type', 'unknown')
            if case_type and case_type != 'unknown':
                # 提取案件类型关键词
                if 'application' in case_type.lower():
                    case_type_stats['Application'] = case_type_stats.get('Application', 0) + 1
                elif 'action' in case_type.lower():
                    case_type_stats['Action'] = case_type_stats.get('Action', 0) + 1
                else:
                    case_type_stats['Other'] = case_type_stats.get('Other', 0) + 1
        
        # 字段完整性统计 - 统计所有字段
        field_completeness = {}
        
        # 从第一个结果中获取所有字段名（除了文件路径相关字段）
        if results:
            all_fields = [key for key in results[0].keys() if key not in ['file_name', 'file_path']]
        else:
            all_fields = ['trial_date', 'court_name', 'case_number', 'plaintiff', 'defendant', 
                         'judge', 'case_type', 'lawyer', 'judgment_result', 'claim_amount', 
                         'judgment_amount', 'language', 'document_type']
        
        for field in all_fields:
            complete_count = sum(1 for result in results if result.get(field, '').strip())
            field_completeness[field] = {
                'complete': complete_count,
                'missing': total_files - complete_count,
                'percentage': (complete_count / total_files * 100) if total_files > 0 else 0
            }
        
        summary = {
            'processing_time': datetime.now().isoformat(),
            'total_files_processed': total_files,
            'language_distribution': language_stats,
            'court_distribution': court_stats,
            'case_type_distribution': case_type_stats,
            'field_completeness': field_completeness,
            'success_rate': 100.0  # 因为只有成功的结果才会被包含在results中
        }
        
        # 保存摘要报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"summary_report_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Summary report saved: {summary_file}")
        return summary
    
    def run(self, input_dir: str, output_format: str = "all") -> Dict:
        """
        运行批量处理
        
        Args:
            input_dir: 输入目录
            output_format: 输出格式
            
        Returns:
            处理结果摘要
        """
        self.logger.info("=" * 50)
        self.logger.info("Starting Hong Kong Court Document Extraction")
        self.logger.info("=" * 50)
        
        # 处理文档
        results = self.process_directory(input_dir)
        
        if results:
            # 保存结果
            saved_files = self.save_results(results, output_format)
            
            # 生成摘要报告
            summary = self.generate_summary_report(results)
            summary['saved_files'] = saved_files
            
            self.logger.info("=" * 50)
            self.logger.info("Processing completed successfully!")
            self.logger.info(f"Total files processed: {len(results)}")
            self.logger.info(f"Output files: {list(saved_files.values())}")
            self.logger.info("=" * 50)
            
            return summary
        else:
            self.logger.error("No files were successfully processed")
            return {} 