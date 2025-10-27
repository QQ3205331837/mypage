#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
from datetime import datetime, timedelta

def debug_wechat_reports():
    """调试微信专栏公司周报数据抓取"""
    try:
        reports = []
        
        # 方法1：直接使用wechat_album.html文件中的数据
        try:
            file_path = 'c:\\Users\\zhao\\Desktop\\pyLy\\news_web\\wechat_album.html'
            print(f"1. 尝试读取文件: {file_path}")
            
            # 检查文件是否存在
            if not os.path.exists(file_path):
                print(f"❌ 文件不存在: {file_path}")
                return []
            
            print("✅ 文件存在")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                local_html = f.read()
            
            print(f"✅ 文件读取成功，长度: {len(local_html)} 字符")
            
            # 检查是否包含公司周报数据
            if "公司周报" in local_html:
                print("✅ 文件中包含'公司周报'关键词")
            else:
                print("❌ 文件中不包含'公司周报'关键词")
            
            # 检查是否包含data-title
            if "data-title" in local_html:
                print("✅ 文件中包含'data-title'属性")
                
                # 统计data-title出现的次数
                title_count = local_html.count("data-title")
                print(f"📊 data-title出现次数: {title_count}")
            else:
                print("❌ 文件中不包含'data-title'属性")
            
            # 使用更精确的正则表达式匹配
            # 先找到所有li元素，然后在每个li元素中提取data-title和data-link
            li_pattern = r'<li[^>]*?class="album__list-item[\s\S]*?</li>'
            li_matches = re.findall(li_pattern, local_html)
            
            print(f"📊 找到 {len(li_matches)} 个li元素")
            
            matches = []
            for li_content in li_matches:
                # 在每个li元素中提取data-title和data-link
                title_match = re.search(r'data-title="([^"]+)"', li_content)
                link_match = re.search(r'data-link="([^"]+)"', li_content)
                
                if title_match and link_match:
                    matches.append((title_match.group(1), link_match.group(1)))
            
            print(f"\n2. 正则表达式匹配结果:")
            print(f"📊 找到 {len(matches)} 个匹配项")
            
            # 显示所有匹配项
            for i, match in enumerate(matches):
                print(f"  匹配项 {i+1}:")
                print(f"    标题: '{match[0]}'")
                print(f"    链接: '{match[1]}'")
            
            # 处理匹配结果
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
            
            print(f"\n3. 最终抓取结果:")
            print(f"✅ 成功抓取 {len(reports)} 篇公司周报")
            for i, report in enumerate(reports):
                print(f"  周报 {i+1}: {report['title']}")
            
        except Exception as e:
            print(f"❌ 读取本地HTML文件失败: {str(e)}")
            import traceback
            traceback.print_exc()
        
        return reports
        
    except Exception as e:
        print(f"❌ 调试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    debug_wechat_reports()