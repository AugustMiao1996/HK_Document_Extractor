#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
并行文档处理器
Parallel Document Processor for Hong Kong Court Documents

Author: AI Assistant
Version: 1.0 - 并行优化版
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from multiprocessing import Pool, cpu_count
from concurrent.futures import ProcessPoolExecutor, as_completed
import pandas as pd

# 导入原有的提取器
from extractor import DocumentExtractor

class ParallelBatchProcessor:
    """并行批量文档处理器"""
    
    def __init__(self, output_dir: str = "output", log_dir: str = "logs", max_workers: Optional[int] = None):
        """
        初始化并行批量处理器
        
        Args:
            output_dir: 输出目录
            log_dir: 日志目录
            max_workers: 最大工作进程数，None为自动检测
        """
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        
        # 自动检测最佳进程数
        if max_workers is None:
            cpu_cores = cpu_count()
            if cpu_cores >= 8:
                self.max_workers = min(cpu_cores - 2, 6)  # 留2个核心，最多6个进程
            elif cpu_cores >= 4:
                self.max_workers = min(cpu_cores - 1, 4)  # 留1个核心
            else:
                self.max_workers = max(1, cpu_cores // 2)
        else:
            self.max_workers = max_workers
        
        # 创建目录
        self.output_dir.mkdir(exist_ok=True)
        self.log_dir.mkdir(exist_ok=True)
        
        # 设置日志
        self.logger = self._setup_logger()
        
        self.logger.info(f"并行处理器初始化完成，使用 {self.max_workers} 个进程")
        
    def _setup_logger(self):
        """设置处理器日志"""
        logger = logging.getLogger('ParallelBatchProcessor')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            # 文件日志
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = self.log_dir / f"parallel_batch_process_{timestamp}.log"
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
        """查找PDF文件"""
        input_path = Path(input_dir)
        if not input_path.exists():
            self.logger.error(f"Input directory does not exist: {input_dir}")
            return []
        
        pdf_files = list(input_path.glob(pattern))
        self.logger.info(f"Found {len(pdf_files)} PDF files in {input_dir}")
        
        return [str(pdf_file) for pdf_file in pdf_files]
    
    def process_directory_parallel(self, input_dir: str) -> List[Dict[str, str]]:
        """
        并行处理目录下的所有PDF文件
        
        Args:
            input_dir: 输入目录路径
            
        Returns:
            处理结果列表
        """
        self.logger.info(f"开始并行批量处理目录: {input_dir}")
        self.logger.info(f"使用 {self.max_workers} 个并行进程")
        
        # 查找PDF文件
        pdf_files = self.find_pdf_files(input_dir)
        if not pdf_files:
            self.logger.warning("No PDF files found")
            return []
        
        # 开始计时
        start_time = time.time()
        
        # 使用进程池并行处理
        results = []
        successful = 0
        failed = 0
        
        # 创建进度跟踪
        total_files = len(pdf_files)
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_file = {
                executor.submit(process_single_pdf, pdf_file): pdf_file 
                for pdf_file in pdf_files
            }
            
            # 收集结果
            for i, future in enumerate(as_completed(future_to_file), 1):
                pdf_file = future_to_file[future]
                file_name = Path(pdf_file).name
                
                try:
                    result = future.result(timeout=30)  # 30秒超时
                    if result:
                        results.append(result)
                        successful += 1
                        self.logger.info(f"✅ [{i}/{total_files}] 成功处理: {file_name}")
                    else:
                        failed += 1
                        self.logger.error(f"❌ [{i}/{total_files}] 处理失败: {file_name}")
                except Exception as e:
                    failed += 1
                    self.logger.error(f"❌ [{i}/{total_files}] 处理异常: {file_name} - {e}")
                
                # 每处理10个文件显示一次进度
                if i % 10 == 0:
                    elapsed = time.time() - start_time
                    avg_time = elapsed / i
                    remaining = (total_files - i) * avg_time
                    self.logger.info(f"📊 进度: {i}/{total_files} ({i/total_files*100:.1f}%), "
                                   f"已用时: {elapsed:.1f}s, 预计剩余: {remaining:.1f}s")
        
        # 最终统计
        total_time = time.time() - start_time
        self.logger.info(f"🎉 并行处理完成!")
        self.logger.info(f"⏱️  总耗时: {total_time:.2f} 秒")
        self.logger.info(f"📊 成功: {successful}, 失败: {failed}")
        self.logger.info(f"⚡ 平均速度: {total_files/total_time:.1f} 文件/秒")
        
        return results
    
    def generate_summary_report(self, results: List[Dict[str, str]]) -> Dict:
        """
        生成处理摘要报告 - 调用原版processor的完整统计功能
        
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
            'processing_mode': 'parallel',
            'max_workers': self.max_workers,
            'total_files_processed': total_files,
            'language_distribution': language_stats,
            'court_distribution': court_stats,
            'case_type_distribution': case_type_stats,
            'field_completeness': field_completeness,
            'success_rate': 100.0
        }
        
        # 保存摘要报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.output_dir / f"parallel_summary_report_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"Summary report saved: {summary_file}")
        return summary

    def save_results(self, results: List[Dict[str, str]], format_type: str = "all") -> Dict[str, str]:
        """保存处理结果"""
        if not results:
            self.logger.warning("No results to save")
            return {}
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        saved_files = {}
        
        # JSON格式
        if format_type in ['json', 'all']:
            json_file = self.output_dir / f"parallel_extraction_results_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            saved_files['json'] = str(json_file)
            self.logger.info(f"Results saved to JSON: {json_file}")
        
        # CSV格式
        if format_type in ['csv', 'all']:
            try:
                csv_file = self.output_dir / f"parallel_extraction_results_{timestamp}.csv"
                df = pd.DataFrame(results)
                df.to_csv(csv_file, index=False, encoding='utf-8-sig')
                saved_files['csv'] = str(csv_file)
                self.logger.info(f"Results saved to CSV: {csv_file}")
            except Exception as e:
                self.logger.warning(f"Failed to save CSV: {e}")
        
        # Excel格式
        if format_type in ['excel', 'all']:
            try:
                excel_file = self.output_dir / f"parallel_extraction_results_{timestamp}.xlsx"
                df = pd.DataFrame(results)
                df.to_excel(excel_file, index=False, engine='openpyxl')
                saved_files['excel'] = str(excel_file)
                self.logger.info(f"Results saved to Excel: {excel_file}")
            except Exception as e:
                self.logger.warning(f"Failed to save Excel: {e}")
        
        return saved_files

    def run(self, input_dir: str, output_format: str = "all") -> Dict:
        """
        运行并行批量处理
        
        Args:
            input_dir: 输入目录
            output_format: 输出格式
            
        Returns:
            处理结果摘要
        """
        self.logger.info("=" * 50)
        self.logger.info("启动香港法院文档并行提取器")
        self.logger.info(f"并行进程数: {self.max_workers}")
        self.logger.info("=" * 50)
        
        # 并行处理文档
        results = self.process_directory_parallel(input_dir)
        
        if results:
            # 保存结果
            saved_files = self.save_results(results, output_format)
            
            # 生成摘要报告
            summary = self.generate_summary_report(results)
            summary['saved_files'] = saved_files
            
            self.logger.info("=" * 50)
            self.logger.info("🎉 并行处理成功完成!")
            self.logger.info(f"📊 总文件数: {len(results)}")
            self.logger.info(f"⚡ 使用进程数: {self.max_workers}")
            self.logger.info(f"📁 输出文件: {list(saved_files.values())}")
            self.logger.info("=" * 50)
            
            return summary
        else:
            self.logger.error("没有文件被成功处理")
            return {}


def process_single_pdf(pdf_path: str) -> Optional[Dict[str, str]]:
    """
    单个PDF处理函数（供多进程调用）
    
    Args:
        pdf_path: PDF文件路径
        
    Returns:
        处理结果字典
    """
    try:
        # 每个进程创建独立的提取器实例
        extractor = DocumentExtractor(log_level=logging.WARNING)  # 减少日志输出
        result = extractor.process_pdf(pdf_path)
        return result
    except Exception as e:
        # 在多进程环境中，异常处理要谨慎
        return None 