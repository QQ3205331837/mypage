#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from enhanced_reports import enhanced_wechat_reports

print("=== 测试增强版公司周报函数 ===")
result = enhanced_wechat_reports()

print(f"\n=== 测试结果 ===")
print(f"总共抓取到 {len(result)} 篇公司周报")

for i, report in enumerate(result):
    print(f"周报 {i+1}: {report['title']}")
    print(f"     日期: {report['date']}")
    print(f"     链接: {report['link']}")
    print()

print("=== 测试完成 ===")