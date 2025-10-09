from flask import Flask, render_template, request, jsonify
import requests
import os
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from datetime import datetime
import re

app = Flask(__name__)

# 网站配置信息
websites = {
    "中国旅游新闻网": {
        "url": "https://www.ctnews.com.cn/jujiao/node_1823.html",
        "link_css": 'a[href*="/content/"]',
        "base_url": "https://www.ctnews.com.cn",
        "date_pattern": r"/content/(\\d{4}-\\d{2})/(\\d{2})/"
    },
    "人民网旅游频道": {
        "url": "http://travel.people.com.cn/",
        "link_css": [
            "ul.list_16 a"
        ],
        "content_css": ".article-content, #article_body",
        "base_url": "http://travel.people.com.cn/",
        "date_pattern": "(\\d{4})-(\\d{2})-(\\d{2})",
        "special_handler": False
    },
    "央广网文旅频道": {
        "url": "https://travel.cnr.cn/",
        "link_css": 'a[href]:not([href*="javascript"]):not([href*="#"])',  # 宽松选择器
        "base_url": "https://travel.cnr.cn",
        "date_pattern": None
    }
}

@app.route('/')
def index():
    # 默认显示人民网旅游频道的新闻
    website = request.args.get('website', '人民网旅游频道')
    search_text = request.args.get('search', '')
    
    # 获取新闻数据
    news_data = fetch_news(website)
    
    # 如果有搜索关键词，过滤新闻
    if search_text:
        filtered_news = []
        for news in news_data:
            if search_text.lower() in news['title'].lower():
                filtered_news.append(news)
        news_data = filtered_news
    
    # 获取当前时间
    now = datetime.now()
    
    return render_template('index.html', 
                          news_data=news_data, 
                          websites=list(websites.keys()), 
                          current_website=website,
                          search_text=search_text,
                          news_count=len(news_data),
                          now=now)

@app.route('/news_content/<int:news_id>')
def news_content(news_id):
    website = request.args.get('website', '人民网旅游频道')
    
    # 重新获取新闻数据以确保一致性
    news_data = fetch_news(website)
    
    if 0 <= news_id < len(news_data):
        news_item = news_data[news_id]
        # 获取详细内容
        content = get_news_content(news_item['link'], website)
        news_item['content'] = content
        return render_template('news_content.html', 
                              news_item=news_item, 
                              websites=list(websites.keys()),
                              current_website=website)
    else:
        return "新闻不存在", 404

@app.route('/fetch_news')
def api_fetch_news():
    website = request.args.get('website', '人民网旅游频道')
    news_data = fetch_news(website)
    return jsonify(news_data)

def fetch_url(url, headers=None, timeout=10):
    """统一的HTTP获取函数；如设置了PROXY_BASE则经由代理。

    PROXY_BASE 示例: https://your-worker-subdomain.workers.dev
    实际请求为: PROXY_BASE + '?url=' + urlencode(original_url)
    """
    proxy_base = os.environ.get('PROXY_BASE', '').strip()
    target = url
    if proxy_base:
        # 确保末尾没有多余斜杠，避免 //
        proxy_base = proxy_base.rstrip('/')
        target = f"{proxy_base}?url={quote_plus(url)}"
    return requests.get(target, headers=headers, timeout=timeout)

def fetch_news(website):
    """获取选定网站的最新资讯"""
    website_config = websites.get(website)
    if not website_config:
        return []
    
    url = website_config["url"]
    link_css = website_config["link_css"]  # 使用CSS选择器替代XPath
    base_url = website_config["base_url"]
    
    # 存储处理后的链接集合，用于去重
    processed_links = set()
    news_data = []
    
    try:
        # 设置请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        }
        
        # 发送请求
        response = fetch_url(url, headers=headers, timeout=10)
        
        # 根据不同网站设置不同的编码策略
        if website == "央广网文旅频道":
            # 央广网可能使用GBK编码
            try:
                # 先尝试自动检测编码
                response.encoding = response.apparent_encoding
                
                # 测试解码是否正常
                test_content = response.text
                # 如果有乱码特征，尝试GBK编码
                if any(ch in test_content for ch in ['锟斤拷', '烫烫烫', '????']):
                    response.encoding = "gbk"
            except Exception:
                response.encoding = "gbk"  # 默认为GBK
        else:
            # 其他网站使用UTF-8或自动检测
            response.encoding = response.apparent_encoding
        
        if response.status_code != 200:
            return []
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取标题和链接 - 支持单个选择器或选择器列表
        news_items = []
        if isinstance(link_css, list):
            for css in link_css:
                css_links = soup.select(css)
                news_items.extend(css_links)
        else:
            news_items = soup.select(link_css)
        
        # 去重处理
        seen_hrefs = set()
        unique_items = []
        for item in news_items:
            href = item.get('href', '')
            if href and href not in seen_hrefs:
                seen_hrefs.add(href)
                unique_items.append(item)
        news_items = unique_items
        
        # 根据不同网站调整过滤策略
        if website == "中国旅游新闻网":
            filter_words = ['无标题', '详情', '视频', '图片', '更多', '相关', '推荐']
        elif website == "环球网旅游频道":
            filter_words = ['无标题', '详情', '视频', '图片', '更多', '相关', '推荐', '首页', '返回']
        elif website == "人民网旅游频道":
            filter_words = ['无标题', '详情', '视频', '图片', '更多', '相关', '推荐', '首页']
        else:  # 其他网站
            filter_words = ['无标题', '详情', '视频', '图片', '更多', '相关', '推荐', '首页']
        
        for item in news_items:
            title = ""
            link = ""
            
            # 检查item的类型
            if isinstance(item, str):
                link = item.strip()
                # 尝试从URL中提取标题信息
                if link:
                    try:
                        # 适配人民网的URL格式
                        title_match = re.search(r'/(\d{4})/(\d{2})(\d{2})/([\w-]+)\.html', link)
                        if title_match:
                            title = title_match.group(4)  # 使用URL中的最后部分作为临时标题
                    except:
                        pass
            else:
                # 原有的元素节点处理逻辑
                title = item.text.strip() if item.text else ""
                
                # 环球网特定的标题提取逻辑
                if website == "环球网旅游频道" and not title:
                    # 尝试获取alt属性
                    title = item.get('alt', '').strip()
                    # 尝试获取title属性
                    if not title:
                        title = item.get('title', '').strip()
                    # 尝试获取父元素的文本
                    if not title:
                        parent = item.findparent()
                        if parent and parent.text:
                            title = parent.text.strip()
                    # 尝试获取兄弟元素的文本
                    if not title:
                        next_sibling = item.getnext()
                        if next_sibling and next_sibling.text:
                            title = next_sibling.text.strip()
                    # 尝试获取子元素的文本
                    if not title:
                        for child in item.iter():
                            if child.text and len(child.text.strip()) > 0:
                                title = child.text.strip()
                                break
                
                link = item.get('href') if item.get('href') else ""
            
            # 跳过无效标题和链接
            if not title or len(title) < 5 or not link:
                continue
            
            # 确保链接不是None
            if link is None:
                continue
            
            # 将链接转换为字符串
            link = str(link)
            
            # 清理链接中的特殊字符
            link = link.strip()
            
            # 修复可能的重复base_url问题
            try:
                # 处理多种可能的重复格式
                if link.startswith(base_url + base_url):
                    link = link.replace(base_url + base_url, base_url)
                # 处理可能的双斜杠问题
                if '//' in link and link.startswith('http'):
                    parts = link.split('//')
                    if len(parts) > 2:
                        # 保留协议部分，合并后面的部分
                        link = parts[0] + '//' + '/'.join(parts[1:])
            except Exception:
                pass
            
            # 根据不同网站进行特定的链接过滤
            if website == "央广网文旅频道":
                # 央广网特定过滤
                if "javascript" in link.lower() or "#" in link:
                    continue
                # 检查是否为绝对链接，如果不是则添加基础URL
                if not link.startswith('http'):
                    if link.startswith('/'):
                        link = f"https://travel.cnr.cn{link}"
                    else:
                        link = f"https://travel.cnr.cn/{link}"
            elif website == "人民网旅游频道":
                # 人民网旅游频道特定过滤
                if "javascript" in link.lower() or "#" in link:
                    continue
            
            # 跳过包含过滤关键词的标题
            if any(word in title for word in filter_words):
                continue
            
            # 确保链接是完整的
            if not link.startswith('http'):
                # 根据不同网站处理相对链接
                if website == "中国旅游新闻网":
                    link = f"https://www.ctnews.com.cn{link}"
                elif website == "人民网旅游频道":
                    # 人民网旅游频道相对链接处理
                    if link.startswith('/'):
                        link = f"http://travel.people.com.cn{link}"
                    else:
                        link = f"http://travel.people.com.cn/{link}"
                else:  # 央广网文旅频道
                      if link.startswith('/'):
                          link = f"https://travel.cnr.cn{link}"
                      else:
                          link = f"https://travel.cnr.cn/{link}"
            
            # 检查链接是否已处理过（防止内容重复）
            if link in processed_links:
                continue
            
            # 添加链接到已处理集合
            processed_links.add(link)
            
            # 从链接中提取日期信息或设置默认日期
            date_str = extract_date_from_link(link, website)
            
            # 保存新闻数据
            news_data.append({
                'title': title,
                'link': link,
                'source': website,
                'date': date_str
            })
            
            # 限制新闻数量，防止过多
            if len(news_data) >= 50:
                break
        
    except Exception as e:
        print(f"获取资讯失败: {str(e)}")
        
    # 按日期排序，最新的在前
    news_data.sort(key=lambda x: x['date'], reverse=True)
    
    return news_data

def extract_date_from_link(link, website):
    """从链接中提取日期信息"""
    try:
        # 人民网旅游频道 URL格式: http://travel.people.com.cn/n1/2024/0925/c41570-40567332.html
        if website == "人民网旅游频道":
            date_match = re.search(r'/n1/(\d{4})/(\d{2})(\d{2})/', link)
            if date_match:
                year = date_match.group(1)
                month = date_match.group(2)
                day = date_match.group(3)
                return f"{year}-{month}-{day}"
        # 中国旅游新闻网 URL格式: https://www.ctnews.com.cn/content/2024-09/25/content_13044816.htm
        elif website == "中国旅游新闻网":
            date_match = re.search(r'/content/(\d{4}-\d{2})/(\d{2})/', link)
            if date_match:
                return f"{date_match.group(1)}-{date_match.group(2)}"
        # 央广网文旅频道 URL格式可能不统一，尝试通用提取
        elif website == "央广网文旅频道":
            # 尝试从链接中提取任何可能的日期格式
            date_patterns = [
                r'(\d{4})-(\d{2})-(\d{2})',
                r'(\d{4})/(\d{2})/(\d{2})',
                r'(\d{4})(\d{2})(\d{2})'
            ]
            for pattern in date_patterns:
                date_match = re.search(pattern, link)
                if date_match and len(date_match.group(1)) == 4:
                    if len(date_match.groups()) == 3:
                        return f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
        
        # 如果无法从链接提取日期，返回当前日期
        return datetime.now().strftime('%Y-%m-%d')
    except Exception:
        # 出错时返回当前日期
        return datetime.now().strftime('%Y-%m-%d')

def get_news_content(link, website):
    """获取新闻的详细内容"""
    try:
        # 设置请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        }
        
        # 请求新闻详情页
        response = fetch_url(link, headers=headers, timeout=10)
        
        # 尝试不同的编码方式解决乱码问题
        if website == "央广网文旅频道":
            # 央广网详情页编码处理
            try:
                # 先尝试GBK编码，这是央广网常用的编码
                response.encoding = "gbk"
                test_content = response.text
                # 检查是否有乱码特征
                if any(ch in test_content for ch in ['锟斤拷', '烫烫烫', '????']):
                    response.encoding = response.apparent_encoding
            except Exception:
                response.encoding = "utf-8"  # 默认使用UTF-8
        else:
            # 其他网站使用自动检测编码
            response.encoding = response.apparent_encoding
        
        # 解析内容
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 根据不同网站使用不同的内容提取策略
        main_paragraphs = []
        
        # 1. 查找主要内容容器 - 使用网站特定策略
        main_content = None
        if website == "中国旅游新闻网":
            # 中国旅游新闻网特定内容提取
            main_content = soup.select_one('div.article-content, div#article_body')
        elif website == "环球网旅游频道":
            # 环球网旅游频道特定内容提取，增加更多可能的容器选择器
            main_content = soup.select_one('div.article-content, div#text_content, div.article-text, div.content')
        elif website == "人民网旅游频道":
            # 人民网旅游频道特定内容提取
            main_content = soup.select_one('div#rwb_zw, div#articleText, div.rm_txt_con')
        
        # 如果没有找到特定内容，尝试通用选择器
        if not main_content:
            main_content = soup.select_one('div.content, div#article, div.article-content, div.content-main')
        
        if main_content:
            # 2. 首先尝试提取p标签内容
            paragraphs = main_content.find_all('p')
            
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text and len(text) > 5:
                    main_paragraphs.append(text)
            
            # 如果p标签内容不足，再尝试提取其他标签内容
            if len(main_paragraphs) < 3:
                # 尝试提取div标签内的文本内容
                divs = main_content.find_all('div')
                for div in divs:
                    text = div.get_text(strip=True)
                    if text and len(text) > 5 and text not in main_paragraphs:
                        main_paragraphs.append(text)
                
                # 尝试提取span标签内容
                spans = main_content.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and len(text) > 5 and text not in main_paragraphs:
                        main_paragraphs.append(text)
                
                # 尝试提取section标签内容
                sections = main_content.find_all('section')
                for section in sections:
                    text = section.get_text(strip=True)
                    if text and len(text) > 5 and text not in main_paragraphs:
                        main_paragraphs.append(text)
                
                # 尝试提取article标签内容
                articles = main_content.find_all('article')
                for article in articles:
                    text = article.get_text(strip=True)
                    if text and len(text) > 5 and text not in main_paragraphs:
                        main_paragraphs.append(text)
        
        # 如果找到正文段落，返回它们
        if main_paragraphs:
            return "\n\n".join(main_paragraphs)
        else:
            # 备用策略：使用网站特定的备用提取策略
            if website == "环球网旅游频道":
                # 环球网备用策略 - 尝试更多的容器选择器
                content_elements = soup.select('div[class*="article"], div[id*="content"], div[class*="main"], div[class*="text-main"]')
            elif website == "央广网文旅频道":
                # 央广网备用策略 - 尝试更多的容器选择器
                content_elements = soup.select('div[class*="article"], div[id*="article"], div[class*="article-body"], div[class*="article-content"]')
            else:
                # 通用备用策略
                content_elements = soup.select('div[class*="article-content"], div[class*="content-main"], div[id*="content"], div[class*="content"]')
            
            all_text = "\n\n".join([elem.get_text(separator='\n', strip=True) for elem in content_elements])
            
            # 清理可能的乱码
            if website == "央广网文旅频道" and all_text:
                # 尝试替换可能的乱码字符
                all_text = all_text.replace("锟斤拷", "").replace("烫烫烫", "").strip()
            
            if all_text and len(all_text.strip()) > 20:
                return all_text
            else:
                return "无法提取内容，请点击上方链接在浏览器中查看完整内容。"
        
    except Exception as e:
        return f"加载内容失败: {str(e)}"
# 本地运行入口点
if __name__ == '__main__':
    # 确保中文正常显示
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    app.run(debug=False)