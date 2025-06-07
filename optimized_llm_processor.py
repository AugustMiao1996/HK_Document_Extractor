#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
优化版LLM处理器 - 专门处理分层提取结果
包含律师信息段落分析功能
"""

import json
import requests
import time
import logging
from typing import Dict, List, Any

class OptimizedLLMProcessor:
    """优化版LLM处理器 - 处理分层提取结果"""
    
    def __init__(self):
        self.api_url = "https://api.deepseek.com/v1/chat/completions"
        self.api_key = "sk-9bea11198fbb45b1a58bc3f98aad5758"
        self.model = "deepseek-chat"
        
        # 设置日志
        self.logger = logging.getLogger('OptimizedLLMProcessor')
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def create_optimized_analysis_prompt(self, case_data: Dict[str, Any]) -> str:
        """创建优化版分析prompt - 专门处理分层提取结果"""
        
        lawyer_segment = case_data.get('lawyer', '')
        lawyer_analysis = ""
        
        if lawyer_segment and len(lawyer_segment.strip()) > 10:
            lawyer_analysis = f"""
### 律师信息分析:
请从以下律师信息段落中分离出原告律师和被告律师：

律师信息段落:
{lawyer_segment}

请提取：
- plaintiff_lawyer: 原告方律师姓名和律师事务所
- defendant_lawyer: 被告方律师姓名和律师事务所

格式：律师姓名 (律师事务所)，如果有多个律师用逗号分隔
"""
        else:
            lawyer_analysis = "### 律师信息分析:\n未找到律师信息段落"
        
        prompt = f"""You are a professional Hong Kong legal document analyst. Analyze the following court document information and provide standardized results.

## 提取到的文档信息:
- Case Number: {case_data.get('case_number', '')}
- Plaintiff: {case_data.get('plaintiff', '')}
- Defendant: {case_data.get('defendant', '')}
- Judge: {case_data.get('judge', '')}
- Case Type Text: {case_data.get('case_type', '')}
- Judgment Text: {case_data.get('judgment_result', '')}
- Claim Amount Text: {case_data.get('claim_amount', '')}
- Judgment Amount Text: {case_data.get('judgment_amount', '')}

{lawyer_analysis}

## 分析要求:

### 1. case_type (案件类型)
选择最合适的类型：
- "Contract Dispute" (合同纠纷)
- "Trust Dispute" (信托纠纷)
- "Appeal" (上诉案件)
- "Setting Aside Application" (撤销申请)
- "Security for Costs Application" (诉讼费担保申请)
- "Mareva Injunction Discharge Application" (禁制令解除申请)
- "Commercial Dispute" (商业纠纷)
- "Debt Recovery" (债务追讨)
- "Amendment Application" (修正申请)
- "Miscellaneous Proceedings" (杂项程序)
- "Civil Action" (民事诉讼，默认)

### 2. judgment_result (判决结果)
必须使用以下5种标签之一：
- "Win": 原告胜诉，被告被命令支付/执行某事
- "Lose": 原告败诉，申请被驳回/拒绝
- "Appeal Dismissed": 上诉被驳回
- "Judgment Affirmed": 原判决得到维持
- "Plaintiff Withdrawn": 原告撤诉

### 3. claim_amount (被告总索赔金额)
提取原告向被告索赔的总金额，包含货币单位(HK$, USD, RMB)
统计所有被告需要承担的索赔金额总和，如有多个金额用逗号分隔，不明确则用"unknown"

### 4. judgment_amount (被告总赔偿金额)
提取法院判决被告需要支付的总金额，包含货币单位和背景
统计所有被告实际需要赔偿的金额总和，不明确则用"unknown"

### 5. plaintiff_lawyer (原告律师)
从律师信息段落中提取原告方律师
格式：律师姓名 (律师事务所)

### 6. defendant_lawyer (被告律师)
从律师信息段落中提取被告方律师
格式：律师姓名 (律师事务所)

### 7. judgment_relationships (判罚关系三元组)
分析案件中的具体索赔和赔偿关系，用三元组格式表达：
- 索赔关系：(原告/申请人, 要求赔偿, 被告/被申请人, 金额)
- 判决关系：(被告/被申请人, 需赔偿, 原告/申请人, 金额)
- 费用关系：(败诉方, 承担费用, 胜诉方, 金额或比例)

格式示例：
"(Plaintiff, claims damages from, 1st Defendant, HK$100,000); (2nd Defendant, ordered to pay, Plaintiff, HK$50,000); (1st Defendant, pay costs to, Plaintiff, 70%)"

## 输出格式:
返回标准JSON格式，不要任何解释：

{{
  "case_type": "",
  "judgment_result": "",
  "claim_amount": "",
  "judgment_amount": "",
  "plaintiff_lawyer": "",
  "defendant_lawyer": "",
  "judgment_relationships": ""
}}"""
        
        return prompt
    
    def create_batch_analysis_prompt(self, cases_batch: List[Dict[str, Any]]) -> str:
        """创建批量分析prompt"""
        prompt = """You are a professional Hong Kong legal document analyst. Analyze the following court documents and provide standardized information including lawyer analysis.

## Analysis Requirements:

### 1. case_type 
Choose the most appropriate type:
- "Contract Dispute", "Trust Dispute", "Appeal", "Setting Aside Application"
- "Security for Costs Application", "Mareva Injunction Discharge Application"
- "Commercial Dispute", "Debt Recovery", "Amendment Application"
- "Miscellaneous Proceedings", "Civil Action" (default)

### 2. judgment_result
Use EXACTLY one of these 5 labels:
- "Win": Plaintiff succeeds
- "Lose": Plaintiff application dismissed/refused  
- "Appeal Dismissed": Appeal rejected
- "Judgment Affirmed": Original judgment upheld
- "Plaintiff Withdrawn": Plaintiff withdraws

### 3. claim_amount & judgment_amount
- claim_amount: Total amount claimed against all defendants by plaintiff (HK$, USD, RMB)
- judgment_amount: Total amount defendants are ordered to pay by court (HK$, USD, RMB)
Use "unknown" if unclear.

### 4. plaintiff_lawyer & defendant_lawyer
From the lawyer information paragraph, extract lawyer names and law firms.
Format: "Lawyer Name (Law Firm)"

## Cases to Analyze:

"""
        
        for i, case_data in enumerate(cases_batch, 1):
            lawyer_segment = case_data.get('lawyer', '')
            lawyer_info = f"Lawyer Segment: {lawyer_segment}" if lawyer_segment else "Lawyer Segment: Not found"
            
            prompt += f"""### Case {i}:
- Case Number: {case_data.get('case_number', '')}
- Plaintiff: {case_data.get('plaintiff', '')}
- Defendant: {case_data.get('defendant', '')}
- Judge: {case_data.get('judge', '')}
- Case Type Text: {case_data.get('case_type', '')}
- Judgment Text: {case_data.get('judgment_result', '')}
- Claim Amount Text: {case_data.get('claim_amount', '')}
- Judgment Amount Text: {case_data.get('judgment_amount', '')}
- {lawyer_info}

"""

        prompt += """## Output Format:
Return ONLY a valid JSON array with one object for each case:

[
  {
    "case_type": "",
    "judgment_result": "",
    "claim_amount": "",
    "judgment_amount": "",
    "plaintiff_lawyer": "",
    "defendant_lawyer": "",
    "judgment_relationships": ""
  }
]"""
        
        return prompt
    
    def call_llm_api(self, prompt: str) -> Dict[str, Any]:
        """调用LLM API"""
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional Hong Kong legal document analyst. Always return valid JSON format. Pay special attention to lawyer information extraction from provided segments."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 1024,
            "temperature": 0.3,
            "top_p": 0.8
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            self.logger.info(f"API Response: {content[:100]}...")
            
            # 解析JSON响应
            try:
                if '```json' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.find('```', json_start)
                    json_content = content[json_start:json_end].strip()
                elif '```' in content:
                    json_start = content.find('```') + 3
                    json_end = content.find('```', json_start)
                    json_content = content[json_start:json_end].strip()
                elif '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_content = content[json_start:json_end]
                elif '[' in content and ']' in content:
                    json_start = content.find('[')
                    json_end = content.rfind(']') + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                parsed_result = json.loads(json_content)
                return parsed_result
                
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse JSON response: {e}")
                self.logger.error(f"Raw content: {content}")
                return {
                    "case_type": "Civil Action",
                    "judgment_result": "unknown",
                    "claim_amount": "unknown", 
                    "judgment_amount": "unknown",
                    "plaintiff_lawyer": "unknown",
                    "defendant_lawyer": "unknown",
                    "judgment_relationships": "unknown"
                }
                
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            return {
                "case_type": "Civil Action",
                "judgment_result": "unknown",
                "claim_amount": "unknown",
                "judgment_amount": "unknown",
                "plaintiff_lawyer": "unknown",
                "defendant_lawyer": "unknown",
                "judgment_relationships": "unknown"
            }
    
    def process_single_case(self, case_data: Dict[str, Any]) -> Dict[str, Any]:
        """处理单个案件"""
        self.logger.info(f"Processing case: {case_data.get('case_number', 'Unknown')}")
        
        # 创建prompt
        prompt = self.create_optimized_analysis_prompt(case_data)
        
        # 调用API
        llm_result = self.call_llm_api(prompt)
        
        # 获取文件名
        file_name = case_data.get('file_name', '')
        if file_name.endswith('.pdf'):
            file_name = file_name[:-4]
        
        # 构建最终结果（包含所有分层提取的字段）
        processed_result = {
            "file_name": file_name,
            "trial_date": case_data.get('trial_date', ''),
            "court_name": case_data.get('court_name', ''),
            "case_number": case_data.get('case_number', ''),
            "plaintiff": case_data.get('plaintiff', ''),
            "defendant": case_data.get('defendant', ''),
            "judge": case_data.get('judge', ''),
            "case_type": llm_result.get('case_type', 'Civil Action'),
            "judgment_result": llm_result.get('judgment_result', 'unknown'),
            "claim_amount": llm_result.get('claim_amount', 'unknown'),
            "judgment_amount": llm_result.get('judgment_amount', 'unknown'),
            "plaintiff_lawyer": llm_result.get('plaintiff_lawyer', 'unknown'),
            "defendant_lawyer": llm_result.get('defendant_lawyer', 'unknown'),
            "judgment_relationships": llm_result.get('judgment_relationships', 'unknown'),
            "lawyer_segment": case_data.get('lawyer', ''),  # 保留原始律师段落供参考
            "language": case_data.get('language', ''),
            "document_type": case_data.get('document_type', '')
        }
        
        return processed_result
    
    def process_batch(self, input_file: str, output_file: str, delay: float = 2.0, batch_size: int = 3):
        """批量处理案件 - 针对律师分析优化，减小批次大小"""
        self.logger.info(f"Starting optimized LLM processing (batch_size={batch_size}): {input_file} -> {output_file}")
        
        # 读取输入文件
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                cases = json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to read input file: {e}")
            return
        
        processed_cases = []
        total_cases = len(cases)
        total_batches = (total_cases + batch_size - 1) // batch_size
        
        self.logger.info(f"Total cases: {total_cases}, Processing in {total_batches} batches of {batch_size}")
        
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_cases)
            current_batch = cases[start_idx:end_idx]
            
            self.logger.info(f"Processing batch {batch_idx + 1}/{total_batches} (cases {start_idx + 1}-{end_idx})")
            
            try:
                # 逐个处理以确保律师信息分析质量
                for case_data in current_batch:
                    result = self.process_single_case(case_data)
                    processed_cases.append(result)
                
                completed_cases = len(processed_cases)
                self.logger.info(f"✅ Completed batch {batch_idx + 1}/{total_batches}, total processed: {completed_cases}/{total_cases}")
                
                # API调用间隔
                if batch_idx < total_batches - 1:
                    self.logger.info(f"Waiting {delay} seconds before next batch...")
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"Failed to process batch {batch_idx + 1}: {e}")
                # 添加失败处理
                for case in current_batch:
                    file_name = case.get('file_name', '')
                    if file_name.endswith('.pdf'):
                        file_name = file_name[:-4]
                    
                    fallback_case = {
                        "file_name": file_name,
                        "trial_date": case.get('trial_date', ''),
                        "court_name": case.get('court_name', ''),
                        "case_number": case.get('case_number', ''),
                        "plaintiff": case.get('plaintiff', ''),
                        "defendant": case.get('defendant', ''),
                        "judge": case.get('judge', ''),
                        "case_type": "Civil Action",
                        "judgment_result": "unknown",
                        "claim_amount": "unknown",
                        "judgment_amount": "unknown",
                        "plaintiff_lawyer": "unknown",
                        "defendant_lawyer": "unknown",
                        "judgment_relationships": "unknown",
                        "lawyer_segment": case.get('lawyer', ''),
                        "language": case.get('language', ''),
                        "document_type": case.get('document_type', '')
                    }
                    processed_cases.append(fallback_case)
        
        # 保存结果
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(processed_cases, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"✅ Optimized LLM processing completed! Results saved to: {output_file}")
            self.logger.info(f"📊 Total processed: {len(processed_cases)} cases")
            
            # 统计分析结果
            self._print_analysis_summary(processed_cases)
            
        except Exception as e:
            self.logger.error(f"Failed to save output file: {e}")
    
    def _print_analysis_summary(self, cases: List[Dict[str, Any]]):
        """打印分析摘要"""
        print("\n📊 优化版LLM分析结果摘要:")
        print("=" * 50)
        
        # 基本统计
        case_types = {}
        judgment_results = {}
        
        for case in cases:
            case_type = case.get('case_type', 'unknown')
            judgment_result = case.get('judgment_result', 'unknown')
            
            case_types[case_type] = case_types.get(case_type, 0) + 1
            judgment_results[judgment_result] = judgment_results.get(judgment_result, 0) + 1
        
        print("案件类型分布:")
        for case_type, count in sorted(case_types.items()):
            print(f"  {case_type}: {count}")
        
        print("\n判决结果分布:")
        for result, count in sorted(judgment_results.items()):
            print(f"  {result}: {count}")
        
        # 律师信息提取统计
        plaintiff_lawyer_extracted = sum(1 for case in cases if case.get('plaintiff_lawyer', 'unknown') not in ['unknown', ''])
        defendant_lawyer_extracted = sum(1 for case in cases if case.get('defendant_lawyer', 'unknown') not in ['unknown', ''])
        lawyer_segment_available = sum(1 for case in cases if case.get('lawyer_segment', '').strip())
        
        print(f"\n律师信息提取统计:")
        print(f"  律师段落可用: {lawyer_segment_available}/{len(cases)} ({lawyer_segment_available/len(cases)*100:.1f}%)")
        print(f"  原告律师提取: {plaintiff_lawyer_extracted}/{len(cases)} ({plaintiff_lawyer_extracted/len(cases)*100:.1f}%)")
        print(f"  被告律师提取: {defendant_lawyer_extracted}/{len(cases)} ({defendant_lawyer_extracted/len(cases)*100:.1f}%)")
        
        # 金额提取统计
        claim_extracted = sum(1 for case in cases if case.get('claim_amount', 'unknown') != 'unknown')
        judgment_extracted = sum(1 for case in cases if case.get('judgment_amount', 'unknown') != 'unknown')
        
        print(f"\n金额提取统计:")
        print(f"  申请金额提取: {claim_extracted}/{len(cases)} ({claim_extracted/len(cases)*100:.1f}%)")
        print(f"  判决金额提取: {judgment_extracted}/{len(cases)} ({judgment_extracted/len(cases)*100:.1f}%)")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='优化版LLM处理器 - 处理分层提取结果')
    parser.add_argument('--input', '-i', required=True, help='输入JSON文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出JSON文件路径')
    parser.add_argument('--delay', '-d', type=float, default=2.0, help='API调用间隔(秒), 默认2秒')
    parser.add_argument('--batch-size', '-b', type=int, default=3, help='批次大小, 默认3')
    
    args = parser.parse_args()
    
    processor = OptimizedLLMProcessor()
    processor.process_batch(args.input, args.output, args.delay, args.batch_size)

if __name__ == "__main__":
    main() 