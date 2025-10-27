#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
from datetime import datetime, timedelta

def test_wechat_reports():
    """测试微信专栏公司周报数据抓取"""
    try:
        reports = []
        
        # 方法1：直接使用wechat_album.html文件中的数据
        try:
            file_path = 'c:\\Users\\zhao\\Desktop\\pyLy\\news_web\\wechat_album.html'
            print(f"尝试读取文件: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                local_html = f.read()
            
            print("=== 文件读取成功 ===")
            print(f"文件长度: {len(local_html)} 字符")
            
            # 调试：打印文件内容片段
            print("=== 微信专栏HTML文件内容片段 ===")
            print(local_html[:500])
            print("==============================")
            
            # 使用正则表达式匹配 - 考虑多行情况
            pattern = r'data-title="([^"]+)".*?data-link="([^"]+)"'
            matches = re.findall(pattern, local_html, re.DOTALL)
            
            print(f"=== 正则表达式匹配结果 ===")
            print(f"找到 {len(matches)} 个匹配项")
            
            # 显示前几个匹配项
            for i, match in enumerate(matches[:5]):
                print(f"匹配项 {i+1}: 标题='{match[0]}', 链接='{match[1]}'")
            print("========================")
            
            for match in matches:
                if len(match) >= 2:
                    title = str(match[0])
                    link = str(match[1])
                    
                    # 修复编码问题
                    title = title.replace('\x26amp;', '&').replace('&amp;', '&')
                    
                    # 确保链接是完整的URL
                    if link and not link.startswith('http'):
                        link = 'https:' + link if link.startswith('//') else 'https://' + link
                    
                    if title and link and len(title) > 5:
                        # 生成合理的发布日期
                        base_date = datetime.now()
                        date_offset = len(reports) * 7
                        report_date = (base_date - timedelta(days=date_offset)).strftime('%Y-%m-%d')
                        
                        reports.append({
                            "title": title.strip(),
                            "link": link.strip(),
                            "date": report_date,
                            "source": "公司周报"
                        })
            
            print(f"=== 最终抓取结果 ===")
            print(f"成功抓取 {len(reports)} 篇公司周报")
            for i, report in enumerate(reports):
                print(f"周报 {i+1}: {report['title']}")
            print("==================")
            
        except Exception as e:
            print(f"读取本地HTML文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return reports
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    test_wechat_reports()