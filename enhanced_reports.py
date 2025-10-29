import re
import requests
from datetime import datetime, timedelta

def enhanced_wechat_reports():
    """动态抓取微信专栏公司周报内容函数"""
    try:
        reports = []
        
        # 在线动态抓取微信专栏数据
        try:
            url = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA4ODA2ODMzNA==&action=getalbum&album_id=4180740440766726147#wechat_redirect"
            response = requests.get(url, timeout=10)
            html_content = response.text
            
            print("=== 开始动态抓取微信专栏数据 ===")
            
            # 从JavaScript的articleList数组中提取数据
            # 匹配articleList数组中的对象
            article_list_pattern = r'articleList\s*:\s*\[(.*?)\]'
            article_list_match = re.search(article_list_pattern, html_content, re.DOTALL)
            
            if article_list_match:
                article_list_content = article_list_match.group(1)
                print(f"找到articleList内容，长度: {len(article_list_content)}")
                
                # 匹配每个文章对象
                article_pattern = r'\{\s*title:\s*\'([^\']+)\'\s*,\s*create_time:\s*\'(\d+)\'\s*,\s*[^}]*url:\s*\'([^\']+)\'[^}]*\}'
                matches = re.findall(article_pattern, article_list_content)
                
                if matches:
                    print(f"找到 {len(matches)} 个匹配项")
                    for match in matches:
                        if len(match) >= 3:
                            title = str(match[0])  # 确保title是字符串类型
                            create_time = str(match[1])  # 创建时间戳
                            link = str(match[2])     # 确保link是字符串类型
                            
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
                else:
                    print("未找到匹配的文章数据")
            else:
                print("未找到articleList数组")
        except Exception as e:
            print(f"在线抓取失败: {str(e)}")
        
        # 如果抓取失败，返回空列表
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
        return []  # 返回空列表

# 测试函数
if __name__ == "__main__":
    result = enhanced_wechat_reports()
    print(f"最终结果: {len(result)} 篇周报")