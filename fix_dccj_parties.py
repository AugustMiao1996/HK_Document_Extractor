#!/usr/bin/env python3
# -*- coding: utf-8 -*-

def fix_dccj_parties():
    """修复DCCJ原告被告提取逻辑"""
    
    file_path = "src/extractor.py"
    
    # 读取文件
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 修复_extract_plaintiff_improved方法
    old_plaintiff_method = '''    def _extract_plaintiff_improved(self, text: str) -> str:
        """改进的英文原告提取方法"""
        # 查找BETWEEN段落
        between_match = re.search(r'BETWEEN\\s*(.*?)\\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
        if not between_match:
            return ""
        
        between_content = between_match.group(1).strip()
        
        # 找到"AND"的位置，提取"AND"之前的所有内容作为原告段落
        and_match = re.search(r'\\s+AND\\s+', between_content, re.IGNORECASE)
        if not and_match:
            return ""
        
        plaintiff_section = between_content[:and_match.start()].strip()
        
        # 提取原告信息
        plaintiffs = self._extract_parties_robust(plaintiff_section, 'Plaintiff')
        
        # 智能格式化
        return self._format_parties_smart(plaintiffs, 'Plaintiff')'''
    
    new_plaintiff_method = '''    def _extract_plaintiff_improved(self, text: str) -> str:
        """改进的英文原告提取方法 - 支持DCCJ格式"""
        
        # 策略1：DCCJ格式 - 直接搜索"XXX Plaintiff"格式
        dccj_patterns = [
            r'([A-Z][A-Za-z\\s,\\.\\(\\)&\\-\\'（）]+?)\\s+Plaintiff',
            r'([A-Z][A-Za-z\\s,\\.\\(\\)&\\-\\'（）]+?)\\s*\\n\\s*Plaintiff',
        ]
        
        for pattern in dccj_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                plaintiffs = []
                for match in matches:
                    clean_name = re.sub(r'\\s+', ' ', match.strip())
                    # 移除常见的格式干扰
                    clean_name = re.sub(r'^\\s*and\\s+', '', clean_name, flags=re.IGNORECASE)
                    if len(clean_name) > 3 and len(clean_name) < 200:
                        plaintiffs.append(clean_name)
                
                if plaintiffs:
                    return ' | '.join(plaintiffs) if len(plaintiffs) > 1 else plaintiffs[0]
        
        # 策略2：标准BETWEEN段落格式（HCA文档）
        between_match = re.search(r'BETWEEN\\s*(.*?)\\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
        if between_match:
            between_content = between_match.group(1).strip()
            
            # 找到"AND"的位置，提取"AND"之前的所有内容作为原告段落
            and_match = re.search(r'\\s+AND\\s+', between_content, re.IGNORECASE)
            if and_match:
                plaintiff_section = between_content[:and_match.start()].strip()
                
                # 提取原告信息
                plaintiffs = self._extract_parties_robust(plaintiff_section, 'Plaintiff')
                
                # 智能格式化
                return self._format_parties_smart(plaintiffs, 'Plaintiff')
        
        return ""'''
    
    # 修复_extract_defendant_improved方法
    old_defendant_method = '''    def _extract_defendant_improved(self, text: str) -> str:
        """改进的英文被告提取方法"""
        # 查找BETWEEN段落
        between_match = re.search(r'BETWEEN\\s*(.*?)\\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
        if not between_match:
            return ""
        
        between_content = between_match.group(1).strip()
        
        # 找到"AND"的位置，提取"AND"之后的所有内容作为被告段落
        and_match = re.search(r'\\s+AND\\s+', between_content, re.IGNORECASE)
        if not and_match:
            return ""
        
        defendant_section = between_content[and_match.end():].strip()
        
        # 清理被告段落，移除下划线等无关内容
        defendant_section = re.sub(r'_{5,}.*$', '', defendant_section, flags=re.DOTALL).strip()
        
        # 提取被告信息
        defendants = self._extract_parties_robust(defendant_section, 'Defendant')
        
        # 智能格式化
        return self._format_parties_smart(defendants, 'Defendant')'''
    
    new_defendant_method = '''    def _extract_defendant_improved(self, text: str) -> str:
        """改进的英文被告提取方法 - 支持DCCJ格式"""
        
        # 策略1：DCCJ格式 - 直接搜索"XXX Defendant"格式
        dccj_patterns = [
            r'([A-Z][A-Za-z\\s,\\.\\(\\)&\\-\\'（）]+?)\\s+Defendant',
            r'([A-Z][A-Za-z\\s,\\.\\(\\)&\\-\\'（）]+?)\\s*\\n\\s*Defendant',
        ]
        
        for pattern in dccj_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            if matches:
                defendants = []
                for match in matches:
                    clean_name = re.sub(r'\\s+', ' ', match.strip())
                    # 移除常见的格式干扰
                    clean_name = re.sub(r'^\\s*and\\s+', '', clean_name, flags=re.IGNORECASE)
                    if len(clean_name) > 3 and len(clean_name) < 200:
                        defendants.append(clean_name)
                
                if defendants:
                    return ' | '.join(defendants) if len(defendants) > 1 else defendants[0]
        
        # 策略2：标准BETWEEN段落格式（HCA文档）
        between_match = re.search(r'BETWEEN\\s*(.*?)\\s*(?=Before:|__________|Date|主審)', text, re.DOTALL | re.IGNORECASE)
        if between_match:
            between_content = between_match.group(1).strip()
            
            # 找到"AND"的位置，提取"AND"之后的所有内容作为被告段落
            and_match = re.search(r'\\s+AND\\s+', between_content, re.IGNORECASE)
            if and_match:
                defendant_section = between_content[and_match.end():].strip()
                
                # 清理被告段落，移除下划线等无关内容
                defendant_section = re.sub(r'_{5,}.*$', '', defendant_section, flags=re.DOTALL).strip()
                
                # 提取被告信息
                defendants = self._extract_parties_robust(defendant_section, 'Defendant')
                
                # 智能格式化
                return self._format_parties_smart(defendants, 'Defendant')
        
        return ""'''
    
    # 应用修复
    if old_plaintiff_method in content:
        content = content.replace(old_plaintiff_method, new_plaintiff_method)
        print("✅ 成功修复原告提取方法")
    else:
        print("❌ 未找到原告提取方法")
    
    if old_defendant_method in content:
        content = content.replace(old_defendant_method, new_defendant_method)
        print("✅ 成功修复被告提取方法")
    else:
        print("❌ 未找到被告提取方法")
    
    # 写回文件
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("DCCJ原告被告提取逻辑修复完成")

if __name__ == "__main__":
    fix_dccj_parties() 