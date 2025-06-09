#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简易系统测试脚本
----------------
该脚本使用 ``DocumentExtractor`` 在一段模拟文本上运行，
验证核心提取流程是否正常工作。
"""

from src.extractor import DocumentExtractor

SAMPLE_TEXT = """IN THE HIGH COURT OF THE HONG KONG SPECIAL ADMINISTRATIVE REGION\n" \
"Action No: HCA 1234/2023\n" \
"BETWEEN\n" \
"ABC LIMITED\n" \
"Plaintiff\n" \
"AND\n" \
"XYZ LIMITED\n" \
"Defendant\n" \
"Before: Hon. Justice Smith\n" \
"Date of Hearing: 12 May 2023\n"""


def main() -> None:
    """运行测试并打印提取结果"""
    extractor = DocumentExtractor()
    result = extractor.extract_information(SAMPLE_TEXT, "sample.txt")
    for key, value in result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()

