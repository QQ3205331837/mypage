import re
import requests
from datetime import datetime, timedelta

def enhanced_wechat_reports():
    """增强版微信专栏公司周报内容获取函数"""
    try:
        reports = []
        
        # 方法1：直接使用wechat_album.html文件中的数据
        try:
            with open('c:\\Users\\zhao\\Desktop\\pyLy\\news_web\\wechat_album.html', 'r', encoding='utf-8') as f:
                local_html = f.read()
            
            print("=== 微信专栏HTML文件内容片段 ===")
            print(local_html[:1000])
            print("==============================")
            
            # 使用更精确的正则表达式匹配，同时提取标题、链接和创建时间
            # 先找到所有li元素，然后在每个li元素中提取data-title、data-link和create_time
            li_pattern = r'<li[^>]*?class="album__list-item[\s\S]*?</li>'
            li_matches = re.findall(li_pattern, local_html)
            
            print(f"📊 找到 {len(li_matches)} 个li元素")
            
            matches = []
            for li_content in li_matches:
                # 在每个li元素中提取data-title、data-link和create_time
                title_match = re.search(r'data-title="([^"]+)"', li_content)
                link_match = re.search(r'data-link="([^"]+)"', li_content)
                
                # 尝试从JavaScript数据中提取create_time
                create_time_match = None
                
                # 方法1：从JavaScript的articleList中提取
                js_pattern = r"title:\s*'([^']+)'[\s\S]*?create_time:\s*'(\\d+)'"
                js_matches = re.findall(js_pattern, li_content)
                if js_matches:
                    for js_title, js_time in js_matches:
                        if title_match and js_title in title_match.group(1):
                            create_time_match = js_time
                            break
                
                # 方法2：从HTML的span元素中提取
                if not create_time_match:
                    time_span_match = re.search(r'<span[^>]*class="js_article_create_time[^>]*>([^<]+)</span>', li_content)
                    if time_span_match:
                        create_time_match = time_span_match.group(1)
                
                if title_match and link_match:
                    matches.append((title_match.group(1), link_match.group(1), create_time_match))
            
            print(f"=== 正则表达式匹配结果 ===")
            print(f"找到 {len(matches)} 个匹配项")
            for i, match in enumerate(matches[:3]):
                print(f"匹配项 {i+1}: 标题='{match[0]}', 链接='{match[1]}', 时间戳='{match[2]}'")
            print("========================")
            
            for match in matches:
                if len(match) >= 2:
                    title = str(match[0])  # 确保title是字符串类型
                    link = str(match[1])     # 确保link是字符串类型
                    create_time = match[2] if len(match) > 2 else None
                    
                    # 修复编码问题：将 \x26amp; 和 &amp; 替换为 &
                    title = title.replace('\x26amp;', '&').replace('&amp;', '&')
                    
                    # 确保链接是完整的URL
                    if link and not link.startswith('http'):
                        link = 'https:' + link if link.startswith('//') else 'https://' + link
                    
                    if title and link and len(title) > 5:
                        # 处理发布日期
                        if create_time and create_time.isdigit():
                            # 使用真实的创建时间戳
                            timestamp = int(create_time)
                            # 将Unix时间戳转换为日期格式
                            report_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                            print(f"使用真实日期: {report_date} (时间戳: {timestamp})")
                        else:
                            # 如果没有找到真实时间戳，使用合理的发布日期（从最新到最旧）
                            base_date = datetime.now()
                            date_offset = len(reports) * 7  # 每周一篇
                            report_date = (base_date - timedelta(days=date_offset)).strftime('%Y-%m-%d')
                            print(f"使用估算日期: {report_date}")
                        
                        reports.append({
                            "title": title.strip(),
                            "link": link.strip(),
                            "date": report_date,
                            "source": "公司周报"
                        })
        except Exception as e:
            print(f"读取本地HTML文件失败: {str(e)}")
        
        # 方法2：如果方法1失败，使用在线抓取
        if not reports:
            try:
                url = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA4ODA2ODMzNA==&action=getalbum&album_id=4180740440766726147#wechat_redirect"
                response = requests.get(url, timeout=10)
                html_content = response.text
                
                # 从在线HTML中提取标题、链接和创建时间
                article_patterns = [
                    r'data-title="([^"]+)".*?data-link="([^"]+)".*?create_time:\s*\'(\\d+)\'',
                    r'data-title="([^"]+)"[^>]*data-link="([^"]+)"[^>]*create_time:\s*\'(\\d+)\'',
                ]
                
                for pattern in article_patterns:
                    matches = re.findall(pattern, html_content, re.DOTALL)
                    if matches:
                        for match in matches:
                            if len(match) >= 3:
                                title = str(match[0])  # 确保title是字符串类型
                                link = str(match[1])     # 确保link是字符串类型
                                create_time = str(match[2])  # 创建时间戳
                                
                                # 修复编码问题：将 \x26amp; 和 &amp; 替换为 &
                                title = title.replace('\x26amp;', '&').replace('&amp;', '&')
                                
                                # 确保链接是完整的URL
                                if link and not link.startswith('http'):
                                    link = 'https:' + link if link.startswith('//') else 'https://' + link
                                
                                if title and link and len(title) > 5:
                                    # 处理发布日期
                                    if create_time and create_time.isdigit():
                                        # 使用真实的创建时间戳
                                        timestamp = int(create_time)
                                        # 将Unix时间戳转换为日期格式
                                        report_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
                                        print(f"使用真实日期: {report_date} (时间戳: {timestamp})")
                                    else:
                                        # 如果没有找到真实时间戳，使用合理的发布日期
                                        base_date = datetime.now()
                                        date_offset = len(reports) * 7  # 每周一篇
                                        report_date = (base_date - timedelta(days=date_offset)).strftime('%Y-%m-%d')
                                        print(f"使用估算日期: {report_date}")
                                    
                                    reports.append({
                                        "title": title.strip(),
                                        "link": link.strip(),
                                        "date": report_date,
                                        "source": "公司周报"
                                    })
                        
                        if reports:
                            break
            except Exception as e:
                print(f"在线抓取失败: {str(e)}")
        
        # 如果所有方法都失败，返回空列表
        if not reports:
            reports = []
        
        # 按日期排序，最新的在前
        reports.sort(key=lambda x: x['date'], reverse=True)
        
        # 打印调试信息
        print("=== 公司周报数据抓取结果 ===")
        print(f"抓取到的周报数量: {len(reports)}")
        for i, report in enumerate(reports):
            print(f"周报 {i+1}: {repr(report.get('title', ''))}")
            print(f"     链接: {report.get('link', '')}")
            print(f"     日期: {report.get('date', '')}")
        print("==========================")
        
        return reports
        
    except Exception as e:
        print(f"获取微信专栏失败: {str(e)}")
        return []  # 返回空列表，不使用示例数据

# 测试函数
if __name__ == "__main__":
    result = enhanced_wechat_reports()
    print(f"最终结果: {len(result)} 篇周报")