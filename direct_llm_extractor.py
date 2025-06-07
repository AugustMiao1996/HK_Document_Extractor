#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DCCJ文档直接LLM提取器 - 跳过第一阶段，直接用LLM+Prompt提取所有信息
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests

# 添加src路径
sys.path.append('src')

class DirectLLMExtractor:
    def __init__(self):
        """初始化直接LLM提取器"""
        self.setup_deepseek()
        self.lock = threading.Lock()  # 用于线程安全的输出
        
    def setup_deepseek(self):
        """设置Deepseek客户端"""
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.api_key = "sk-9bea11198fbb45b1a58bc3f98aad5758"
        self.model = "deepseek-chat"
        print("✅ Deepseek API配置成功")
        
    def get_extraction_prompt(self):
        """获取完整的提取prompt"""
        return """请从这份香港区域法院(DCCJ)判决书中提取以下信息，严格按照指定格式输出JSON：

【提取字段说明】
1. file_name: PDF文件名(不含扩展名)
2. trial_date: 审判日期(格式：7 May 2024)
3. court_name: 完整法院名称(通常在文档开头)
4. case_number: 完整案件编号(必须是完整版本如"CIVIL ACTION NO DCCJ000019 OF 2017"，不能是缩写如"DCCJ000019")
5. plaintiff: 原告信息(多个用"|"分隔)
6. defendant: 被告信息(多个用"|"分隔)  
7. judge: 法官姓名
8. case_type: 案件类型(从内容推断：Contract Dispute, Tort, Appeal等)
9. judgment_result: 判决结果(从ORDER部分提取主要判决)
10. claim_amount: 原告申请金额(格式：HK$xxx,xxx)
11. judgment_amount: 判决赔偿金额(格式：HK$xxx,xxx)
12. plaintiff_lawyer: 原告律师(格式：律师名 (律师事务所))
13. defendant_lawyer: 被告律师(格式：律师名 (律师事务所))
14. judgment_relationships: 判决关系(格式：(主体, 行为, 对象, 金额))
15. lawyer_segment: 完整律师信息段落
16. language: 文档语言(固定为"english")
17. document_type: 文档类型(固定为"DCCJ")

【DCCJ格式特征】
- 法院名称：DISTRICT COURT OF THE HONG KONG SPECIAL ADMINISTRATIVE REGION
- 案件编号：CIVIL ACTION NO DCCJ000019 OF 2017
- 当事人格式：
  GERMAC TECHNOLOGY LIMITED
  Plaintiff
  
  and
  
  HILLJOY CORPORATION LIMITED
  Defendant

【各字段位置指导】
- court_name: 文档第一页顶部，全大写
- case_number: 紧跟法院名称，完整的"CIVIL ACTION NO"格式
- trial_date: 在"Before"部分附近或文档开头
- plaintiff/defendant: 第一页中部，公司名+身份标识
- judge: "Before:"后面的法官姓名
- judgment_result: 文档末尾"IT IS ORDERED THAT"部分
- judgment_amount: ORDER中的具体赔偿金额
- lawyer_segment: 文档最后的律师代表信息
- judgment_relationships: 从判决书ORDER部分提取，格式如"(Defendants, ordered to pay, Plaintiffs, HK$16,000)"

【输出示例】
{
  "file_name": "DCCJ000019_2017",
  "trial_date": "4 July 2019",
  "court_name": "DISTRICT COURT OF THE HONG KONG SPECIAL ADMINISTRATIVE REGION",
  "case_number": "CIVIL ACTION NO DCCJ000019 OF 2017",
  "plaintiff": "GERMAC TECHNOLOGY LIMITED",
  "defendant": "HILLJOY CORPORATION LIMITED",
  "judge": "Mr. Recorder Manzoni",
  "case_type": "Contract Dispute",
  "judgment_result": "Claim dismissed with costs",
  "claim_amount": "HK$839,051",
  "judgment_amount": "HK$844,851",
  "plaintiff_lawyer": "Mr Lo Sek Man (Huen & Partners)",
  "defendant_lawyer": "Ms Lily Yu (Ivan Tang & Co)",
  "judgment_relationships": "(Plaintiff, pay costs to, Defendant, HK$844,851)",
  "lawyer_segment": "Mr Lo Sek Man, instructed by Huen & Partners, for the plaintiff | Ms Lily Yu, instructed by Ivan Tang & Co, for the defendant",
  "language": "english",
  "document_type": "DCCJ"
}

【重要要求】
1. case_number必须是完整版本，不能是缩写
2. 如果找不到某字段，返回"unknown"
3. 金额必须包含HK$前缀
4. 只返回JSON格式，不要任何额外解释
5. judgment_relationships必须提取判决中的主要关系
6. 保持所有名称的原始大小写格式

请提取以下文档的信息：

"""

    def extract_from_pdf(self, pdf_path: str, file_name: str = None, show_logs: bool = False):
        """从PDF直接提取信息 - 使用完整原始文本，不经过任何清理"""
        
        if show_logs:
            print(f"📄 直接提取PDF文本: {pdf_path}")
        
        # 直接提取PDF文本，不使用DocumentExtractor的清理逻辑
        try:
            import PyPDF2
            
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                # 提取所有页面的完整文本
                full_text = ""
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    if page_text:
                        full_text += f"\n=== PAGE {page_num + 1} ===\n"
                        full_text += page_text
                        full_text += f"\n=== END PAGE {page_num + 1} ===\n"
                
                if not full_text.strip():
                    if show_logs:
                        print("❌ PDF文本提取失败：无法获取文本内容")
                    return None
                
                if show_logs:
                    print(f"✅ 直接PDF文本提取成功")
                    print(f"   总页数: {len(pdf_reader.pages)}")
                    print(f"   文本长度: {len(full_text)} 字符")
                    print(f"   前100字符: {full_text[:100].replace(chr(10), ' ')}")
                
        except ImportError:
            if show_logs:
                print("❌ 错误：PyPDF2库未安装，尝试使用pdfplumber")
            
            try:
                import pdfplumber
                
                full_text = ""
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages):
                        page_text = page.extract_text()
                        if page_text:
                            full_text += f"\n=== PAGE {page_num + 1} ===\n"
                            full_text += page_text
                            full_text += f"\n=== END PAGE {page_num + 1} ===\n"
                
                if not full_text.strip():
                    if show_logs:
                        print("❌ PDF文本提取失败：无法获取文本内容")
                    return None
                
                if show_logs:
                    print(f"✅ 直接PDF文本提取成功（pdfplumber）")
                    print(f"   总页数: {len(pdf.pages)}")
                    print(f"   文本长度: {len(full_text)} 字符")
                
            except ImportError:
                if show_logs:
                    print("❌ 错误：需要安装 PyPDF2 或 pdfplumber")
                    print("请运行: pip install PyPDF2 或 pip install pdfplumber")
                return None
                
        except Exception as e:
            if show_logs:
                print(f"❌ PDF文本提取错误: {e}")
            return None
        
        # 准备prompt - 完整文本
        prompt = self.get_extraction_prompt()
        full_prompt = prompt + "\n\n=== 完整PDF文档内容 ===\n" + full_text
        
        # 如果没有提供file_name，从路径提取
        if not file_name:
            file_name = Path(pdf_path).stem
        
        if show_logs:
            print("🤖 调用Deepseek API进行完整文档分析...")
            print(f"   Prompt长度: {len(full_prompt)} 字符")
        
        try:
            # 使用deepseek API调用
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "system", 
                        "content": "你是一个专业的香港法院文书信息提取专家。请从完整的PDF文档内容中严格按照要求提取信息并输出JSON格式。注意：我提供的是完整文档内容，包含所有页面，请仔细分析第一页的法院信息、当事人信息等。"
                    },
                    {
                        "role": "user", 
                        "content": full_prompt
                    }
                ],
                "stream": False,
                "max_tokens": 2000,
                "temperature": 0.1,
                "top_p": 0.8
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            result_text = result['choices'][0]['message']['content'].strip()
            
            # 尝试解析JSON
            try:
                # 清理可能的markdown标记
                if result_text.startswith('```json'):
                    result_text = result_text.replace('```json', '').replace('```', '')
                elif '```' in result_text:
                    json_start = result_text.find('```') + 3
                    json_end = result_text.find('```', json_start)
                    result_text = result_text[json_start:json_end].strip()
                elif '{' in result_text and '}' in result_text:
                    json_start = result_text.find('{')
                    json_end = result_text.rfind('}') + 1
                    result_text = result_text[json_start:json_end]
                
                result = json.loads(result_text)
                
                # 确保file_name正确
                result['file_name'] = file_name
                
                if show_logs:
                    print("✅ Deepseek API完整文档分析成功")
                
                return result
                
            except json.JSONDecodeError as e:
                if show_logs:
                    print(f"❌ JSON解析失败: {e}")
                    print(f"API响应前200字符: {result_text[:200]}")
                return None
                
        except Exception as e:
            if show_logs:
                print(f"❌ Deepseek API调用失败: {e}")
            return None

    def extract_from_pdf_with_index(self, pdf_file, index, total):
        """带索引的PDF提取方法，用于并行处理"""
        thread_id = threading.current_thread().ident
        
        with self.lock:
            print(f"[{index:2d}/{total}] 🧵{thread_id % 1000:03d} 开始处理: {pdf_file.name}")
        
        try:
            result = self.extract_from_pdf(str(pdf_file), pdf_file.stem, show_logs=False)
            if result:
                # 显示关键提取结果
                plaintiff = result.get('plaintiff', '未知')[:40]
                defendant = result.get('defendant', '未知')[:40]
                case_number = result.get('case_number', '未知')[:50]
                
                with self.lock:
                    print(f"        🧵{thread_id % 1000:03d} ✅ 提取成功")
                    print(f"        🧵{thread_id % 1000:03d}    案件: {case_number}")
                    print(f"        🧵{thread_id % 1000:03d}    原告: {plaintiff}")
                    print(f"        🧵{thread_id % 1000:03d}    被告: {defendant}")
                
                return result, True
            else:
                with self.lock:
                    print(f"        🧵{thread_id % 1000:03d} ❌ 提取失败")
                return None, False
                
        except Exception as e:
            with self.lock:
                print(f"        🧵{thread_id % 1000:03d} ❌ 错误: {e}")
            return None, False

    def process_folder(self, input_folder: str, output_file: str = None, max_workers: int = 6):
        """处理整个DCCJ文件夹 - 支持并行处理"""
        print("🚀 DCCJ直接LLM提取器（并行版）")
        print("=" * 50)
        
        if not os.path.exists(input_folder):
            print(f"❌ 错误：输入文件夹不存在: {input_folder}")
            return
        
        # 获取所有PDF文件
        pdf_files = list(Path(input_folder).glob("*.pdf"))
        if not pdf_files:
            print(f"❌ 错误：未找到PDF文件在: {input_folder}")
            return
            
        print(f"📁 输入文件夹: {input_folder}")
        print(f"📄 找到 {len(pdf_files)} 个PDF文件")
        print(f"🔀 并行线程数: {max_workers}")
        print()
        
        # 生成输出文件名
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"output/direct_llm_results_{timestamp}.json"
        
        # 确保输出目录存在
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        results = []
        success_count = 0
        start_time = time.time()
        
        # 并行处理
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_file = {}
            for i, pdf_file in enumerate(pdf_files, 1):
                future = executor.submit(self.extract_from_pdf_with_index, pdf_file, i, len(pdf_files))
                future_to_file[future] = (pdf_file, i)
            
            # 收集结果
            for future in as_completed(future_to_file):
                pdf_file, index = future_to_file[future]
                try:
                    result, success = future.result()
                    if success and result:
                        results.append(result)
                        success_count += 1
                    
                    # 进度显示
                    completed = len([f for f in future_to_file if f.done()])
                    with self.lock:
                        print(f"📊 进度: {completed}/{len(pdf_files)} ({completed/len(pdf_files)*100:.1f}%)")
                        print()
                        
                except Exception as e:
                    with self.lock:
                        print(f"❌ 处理 {pdf_file.name} 时出错: {e}")
        
        processing_time = time.time() - start_time
        
        # 保存结果
        if results:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print("=" * 50)
            print("📊 处理完成统计:")
            print(f"   总文件数: {len(pdf_files)}")
            print(f"   成功提取: {success_count}")
            print(f"   成功率: {success_count/len(pdf_files)*100:.1f}%")
            print(f"   处理时间: {processing_time:.1f}秒")
            print(f"   平均每文件: {processing_time/len(pdf_files):.1f}秒")
            print(f"💾 结果已保存到: {output_file}")
            
            # 简要字段统计
            field_stats = {}
            for field in ['plaintiff', 'defendant', 'case_number', 'judge', 'judgment_amount']:
                count = sum(1 for r in results if r.get(field, '').strip() and r.get(field) != 'unknown')
                field_stats[field] = f"{count}/{success_count} ({count/success_count*100:.1f}%)"
            
            print()
            print("📈 关键字段提取统计:")
            for field, stat in field_stats.items():
                print(f"   {field}: {stat}")
                
        else:
            print("❌ 没有成功提取任何文件")

def main():
    parser = argparse.ArgumentParser(
        description='DCCJ文档直接LLM提取器（并行版）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 处理DCCJ文件夹（默认6并行）
  python direct_llm_extractor.py --input ../HK/DCCJ
  
  # 指定并行数
  python direct_llm_extractor.py --input ../HK/DCCJ --workers 8
  
  # 指定输出文件
  python direct_llm_extractor.py --input ../HK/DCCJ --output my_results.json --workers 6
        """
    )
    
    parser.add_argument('--input', '-i', required=True,
                       help='DCCJ文件夹路径')
    parser.add_argument('--output', '-o', 
                       help='输出文件名（可选）')
    parser.add_argument('--workers', '-w', type=int, default=6,
                       help='并行线程数（默认6）')
    
    args = parser.parse_args()
    
    if args.workers < 1 or args.workers > 20:
        print("❌ 错误：并行线程数必须在1-20之间")
        sys.exit(1)
    
    extractor = DirectLLMExtractor()
    extractor.process_folder(args.input, args.output, args.workers)

if __name__ == "__main__":
    main() 