#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 将当前目录添加到Python路径
sys.path.insert(0, os.path.dirname(__file__))

from enhanced_reports import enhanced_wechat_reports

# 替换原有的get_wechat_reports函数
def get_wechat_reports():
    """获取微信专栏的公司周报内容（增强版）"""
    return enhanced_wechat_reports()

# 测试增强版函数
if __name__ == "__main__":
    reports = get_wechat_reports()
    print(f"✅ 成功获取 {len(reports)} 篇公司周报")
    for i, report in enumerate(reports):
        print(f"周报 {i+1}: {report['title']}")