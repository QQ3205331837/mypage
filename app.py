from flask import Flask, render_template, request, jsonify
from flask import Response, send_from_directory
import csv
import io
import requests
import os
import time
import random
from urllib.parse import quote_plus
from collections import defaultdict
from bs4 import BeautifulSoup
from datetime import datetime
import re
from markupsafe import Markup
import logging

# 配置日志 - 适配Vercel无服务器环境
def setup_logging():
    """Vercel环境适配的日志配置"""
    import os
    
    # Vercel环境变量
    is_vercel = os.environ.get('VERCEL') or os.environ.get('NOW_REGION')
    
    if is_vercel:
        # Vercel环境：简化日志，避免文件操作
        logging.basicConfig(
            level=logging.INFO,  # Vercel生产环境使用INFO级别
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )
    else:
        # 本地开发环境：详细日志
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[logging.StreamHandler()]
        )

setup_logging()
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='/static')

# Vercel适配：优化静态文件服务
@app.route('/static/image/<path:filename>')
def serve_static_image(filename):
    """直接服务static/image目录下的图片文件"""
    static_folder = app.static_folder or 'static'
    return send_from_directory(os.path.join(static_folder, 'image'), filename)

# 兼容旧路径：/image/ -> /static/image/
@app.route('/image/<path:filename>')
def serve_image(filename):
    """兼容旧图片路径，重定向到新的静态路径"""
    static_folder = app.static_folder or 'static'
    return send_from_directory(os.path.join(static_folder, 'image'), filename)

# 简单内存缓存：key=(website), value={"data": list, "ts": epoch_seconds}
CACHE_TTL_SECONDS = 60  # 1分钟，加快缓存刷新
_cache = {}

# 观测：抓取指标与错误日志（内存）
_metrics = {
    'last_fetch': {},  # website -> {ts, duration_ms, count}
}
_errors = []  # [{ts, website, stage, message}]

def _check_admin_key():
    expected = os.environ.get('ADMIN_KEY', '').strip()
    if not expected:
        return True  # 未设置即不鉴权
    supplied = request.args.get('key') or request.headers.get('X-Admin-Key')
    return supplied == expected

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

# 公司周报配置
WECHAT_ALBUM_URL = "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA4ODA2ODMzNA==&action=getalbum&album_id=4180740440766726147#wechat_redirect"

# 公司周报数据（从微信专栏实际抓取）
company_reports = []

def get_wechat_reports():
    """获取微信专栏的公司周报内容（增强版）"""
    try:
        from enhanced_reports import enhanced_wechat_reports
        reports = enhanced_wechat_reports()
        return reports
        
    except Exception as e:
        logger.error(f"获取微信专栏失败: {str(e)}")
        return []  # 返回空列表，不使用示例数据


ALL_SOURCES_LABEL = "全部来源"

@app.route('/')
def index():
    # 获取选项卡类型：news（国内新闻）或 reports（公司周报）
    tab_type = request.args.get('tab', 'news')
    
    # 如果是新闻选项卡，使用原有逻辑
    if tab_type == 'news':
        # 默认显示人民网旅游频道的新闻
        website = request.args.get('website', '人民网旅游频道')
        sources_str = request.args.get('sources', '').strip()
        selected_sources = [s for s in [x.strip() for x in sources_str.split(',')] if s] if sources_str else []
        search_text = request.args.get('search', '')
        
        # 支持强制刷新 ?refresh=1
        refresh = request.args.get('refresh', '0') == '1'
        # 获取新闻数据（带缓存），支持聚合与多来源选择
        if selected_sources:
            valid_sources = [s for s in selected_sources if s in websites]
            aggregated = []
            for site in valid_sources:
                aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
            # 去重（按链接）
            seen = set()
            deduped = []
            for item in aggregated:
                link = item.get('link')
                if link and link not in seen:
                    seen.add(link)
                    deduped.append(item)
            deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
            news_data = deduped
        elif website == ALL_SOURCES_LABEL:
            # 聚合所有来源
            aggregated = []
            for site in websites.keys():
                aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
            # 去重（按链接）
            seen = set()
            deduped = []
            for item in aggregated:
                link = item.get('link')
                if link and link not in seen:
                    seen.add(link)
                    deduped.append(item)
            # 按日期倒序
            deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
            news_data = deduped
        else:
            news_data = get_news_with_cache(website, force_refresh=refresh)

        # 去重（按链接），即使是单个网站也可能有重复
        seen = set()
        deduped = []
        for item in news_data:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        news_data = deduped

        # 公共过滤
        news_data = filter_news(news_data, search_text)
        
        # 获取当前时间
        now = datetime.now()
        
        # 分页参数
        try:
            page = int(request.args.get('page', '1'))
            page_size = int(request.args.get('page_size', '12'))
            page = max(page, 1)
            page_size = max(min(page_size, 30), 6)
        except Exception:
            page, page_size = 1, 12

        start = (page - 1) * page_size
        end = start + page_size
        paged_news = news_data[start:end]
        total_pages = max((len(news_data) + page_size - 1) // page_size, 1)

        return render_template('index.html', 
                              news_data=paged_news, 
                              websites=[ALL_SOURCES_LABEL] + list(websites.keys()), 
                              current_website=website,
                              search_text=search_text,
                              selected_sources=','.join(selected_sources),
                              news_count=len(news_data),
                              page=page,
                              page_size=page_size,
                              total_pages=total_pages,
                              now=now,
                              metrics=_metrics['last_fetch'].get(website if website != ALL_SOURCES_LABEL else '聚合', None),
                              tab_type=tab_type,
                              company_reports=[])
    
    # 如果是公司周报选项卡
    elif tab_type == 'reports':
        # 获取公司周报数据
        reports_data = get_wechat_reports()
        
        # 调试信息：打印实际抓取到的数据
        print("=== 公司周报数据调试信息 ===")
        print(f"抓取到的周报数量: {len(reports_data)}")
        for i, report in enumerate(reports_data[:3]):
            print(f"周报 {i+1}:")
            print(f"  标题: {repr(report.get('title', ''))}")
            print(f"  链接: {report.get('link', '')}")
            print(f"  日期: {report.get('date', '')}")
        print("==========================")
        
        # 获取当前时间
        now = datetime.now()
        
        # 分页参数
        try:
            page = int(request.args.get('page', '1'))
            page_size = int(request.args.get('page_size', '12'))
            page = max(page, 1)
            page_size = max(min(page_size, 30), 6)
        except Exception:
            page, page_size = 1, 12

        start = (page - 1) * page_size
        end = start + page_size
        paged_reports = reports_data[start:end]
        total_pages = max((len(reports_data) + page_size - 1) // page_size, 1)

        return render_template('index.html', 
                              news_data=[], 
                              websites=[ALL_SOURCES_LABEL] + list(websites.keys()), 
                              current_website='公司周报',
                              search_text='',
                              selected_sources='',
                              news_count=len(reports_data),
                              page=page,
                              page_size=page_size,
                              total_pages=total_pages,
                              now=now,
                              metrics=None,
                              tab_type=tab_type,
                              company_reports=paged_reports)

def filter_news(news_data, search_text):
    # 添加过滤前后的日志
    logger.debug(f"Before filter - News count: {len(news_data)}")
    
    # 过滤无效链接
    invalid_links = [
        "https://travel.cnr.cn/travel.cnr.cn/mlzgtgx",
        "https://travel.cnr.cn/travel.cnr.cn/hydt/"
    ]
    
    # 过滤无效链接
    filtered_news = []
    for news in news_data:
        link = news.get('link', '')
        # 跳过无效链接
        if link in invalid_links:
            logger.debug(f"Filtering invalid link: {link}")
            continue
        filtered_news.append(news)
    news_data = filtered_news
    logger.debug(f"After invalid link filter - News count: {len(news_data)}")
    
    # 关键词过滤
    if search_text:
        logger.debug(f"Applying search filter: '{search_text}'")
        filtered_news = []
        for news in news_data:
            if search_text.lower() in str(news.get('title','')).lower():
                filtered_news.append(news)
        news_data = filtered_news
        logger.debug(f"After text filter - News count: {len(news_data)}")
    
    # 若有搜索词，进行命中优先排序：完全命中 > 子串命中；同组按日期倒序
    if search_text:
        logger.debug(f"Sorting with search priority")
        s = search_text.lower()
        def score(item):
            title = str(item.get('title',''))
            tl = title.lower()
            exact = 1 if tl == s else 0
            contains = 1 if s in tl else 0
            # 更高的元组将排前（Python默认从前到后比较）
            return (exact, contains, str(item.get('date','')))
        news_data.sort(key=score, reverse=True)
    else:
        # 默认按日期倒序
        logger.debug("Sorting by date descending")
        news_data.sort(key=lambda x: str(x.get('date','')), reverse=True)
    
    # 记录前5条新闻的标题
    if len(news_data) > 0:
        logger.debug("Top 5 news after filter and sort:")
        for i in range(min(5, len(news_data))):
            logger.debug(f"{i+1}. {news_data[i].get('title', 'No title')}")
    
    return news_data

@app.route('/news_content')
def news_content():
    link = request.args.get('link')
    if not link:
        return "缺少链接参数", 400
    website = request.args.get('website', '人民网旅游频道')
    search_text = request.args.get('search', '')
    
    # 重新获取新闻数据以确保一致性，与index函数保持相同的逻辑
    sources_str = request.args.get('sources', '').strip()
    selected_sources = [s for s in [x.strip() for x in sources_str.split(',')] if s] if sources_str else []
    
    if selected_sources:
        # 多来源选择
        valid_sources = [s for s in selected_sources if s in websites]
        aggregated = []
        for site in valid_sources:
            aggregated.extend(get_news_with_cache(site))
        # 去重并排序
        seen = set()
        deduped = []
        for item in aggregated:
            item_link = item.get('link')
            if item_link and item_link not in seen:
                seen.add(item_link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        news_data = deduped
    elif website == ALL_SOURCES_LABEL:
        # 对于"全部来源"，需要聚合所有网站的新闻数据
        aggregated = []
        for site in websites.keys():
            aggregated.extend(get_news_with_cache(site))
        # 去重并排序
        seen = set()
        deduped = []
        for item in aggregated:
            item_link = item.get('link')
            if item_link and item_link not in seen:
                seen.add(item_link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        news_data = deduped
    else:
        # 对于单个网站，使用与index函数相同的方式获取数据
        news_data = get_news_with_cache(website)

    # 去重（按链接），即使是单个网站也可能有重复
    seen = set()
    deduped = []
    for item in news_data:
        item_link = item.get('link')
        if item_link and item_link not in seen:
            seen.add(item_link)
            deduped.append(item)
    news_data = deduped

    # 应用与index函数相同的过滤逻辑
    news_data = filter_news(news_data, search_text)
    
    # 支持分页参数
    page = request.args.get('page', '1')
    page_size = request.args.get('page_size', '12')
    try:
        page = int(page)
        page_size = int(page_size)
        page = max(page, 1)
        page_size = max(min(page_size, 30), 6)
    except Exception:
        page, page_size = 1, 12
        
    # 计算当前页的起始和结束索引
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    # 根据分页参数截取当前页的新闻数据
    paged_news_data = news_data[start_index:end_index]
    
    # Find the news item by link
    print(f"\n=== NEWS CONTENT DEBUG INFO ===")
    print(f"Searching for news with link: {link}")
    print(f"Total news items after filtering: {len(news_data)}")
    print(f"Current page: {page}, page size: {page_size}")
    print(f"Page range: {start_index}-{end_index}")
    print(f"News items on current page: {len(paged_news_data)}")
    print(f"=== END DEBUG INFO ===\n")
    
    news_item = None
    global_index = None
    
    # 直接在完整列表中查找匹配的新闻
    for i, item in enumerate(news_data):
        item_link = item.get('link')
        if item_link == link:
            logger.info(f"Found matching news at index {i}: {item.get('title', 'No title')}")
            news_item = item.copy()
            global_index = i
            # 计算这条新闻应该在第几页
            page = (i // page_size) + 1
            # 更新分页范围
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paged_news_data = news_data[start_index:end_index]
            break
    
    if news_item is None:
        print(f"Warning: News not found for link: {link}")
        return "新闻不存在", 404

    content = get_news_content(link, news_item['source'])
    news_item['content'] = content
    
    # 计算前后链接
    prev_link = None
    next_link = None
    
    if global_index is not None:
        # 使用全局索引计算前后链接，这是最可靠的方法
        if global_index > 0:
            prev_link = news_data[global_index - 1]['link']
            print(f"Using global index {global_index} to find previous link: {prev_link}")
        else:
            print(f"No previous link (global index is 0)")
        
        if global_index + 1 < len(news_data):
            next_link = news_data[global_index + 1]['link']
            print(f"Using global index {global_index} to find next link: {next_link}")
        else:
            print(f"No next link (global index is at end)")
    
    return render_template('news_content.html', 
                          news_item=news_item, 
                          websites=list(websites.keys()),
                          current_website=website,
                          prev_link=prev_link,
                          next_link=next_link,
                          page=page,
                          page_size=page_size,
                          sources=sources_str,
                          search=search_text)

@app.route('/fetch_news')
def api_fetch_news():
    website = request.args.get('website', '人民网旅游频道')
    refresh = request.args.get('refresh', '0') == '1'
    search_text = request.args.get('search', '')
    sources_str = request.args.get('sources', '').strip()
    selected_sources = [s for s in [x.strip() for x in sources_str.split(',')] if s] if sources_str else []
    if selected_sources:
        valid_sources = [s for s in selected_sources if s in websites]
        aggregated = []
        for site in valid_sources:
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        news_data = filter_news(deduped, search_text)
    elif website == ALL_SOURCES_LABEL:
        aggregated = []
        for site in websites.keys():
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        news_data = filter_news(deduped, search_text)
    else:
        news_data = filter_news(get_news_with_cache(website, force_refresh=refresh), search_text)
    return jsonify(news_data)

@app.route('/export')
def export_data():
    website = request.args.get('website', ALL_SOURCES_LABEL)
    fmt = request.args.get('format', 'json').lower()
    refresh = request.args.get('refresh', '0') == '1'
    search_text = request.args.get('search', '')
    sources_str = request.args.get('sources', '').strip()
    selected_sources = [s for s in [x.strip() for x in sources_str.split(',')] if s] if sources_str else []
    # 复用聚合逻辑
    if selected_sources:
        valid_sources = [s for s in selected_sources if s in websites]
        aggregated = []
        for site in valid_sources:
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        data = filter_news(deduped, search_text)
    elif website == ALL_SOURCES_LABEL:
        aggregated = []
        for site in websites.keys():
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        data = filter_news(deduped, search_text)
    else:
        data = filter_news(get_news_with_cache(website, force_refresh=refresh), search_text)

    if fmt == 'csv':
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=['title', 'link', 'source', 'date'])
        writer.writeheader()
        for row in data:
            writer.writerow({
                'title': row.get('title', ''),
                'link': row.get('link', ''),
                'source': row.get('source', ''),
                'date': row.get('date', ''),
            })
        resp = Response(output.getvalue(), mimetype='text/csv; charset=utf-8')
        resp.headers['Content-Disposition'] = 'attachment; filename="news.csv"'
        return resp
    else:
        return jsonify(data)

@app.route('/feed.xml')
def rss_feed():
    website = request.args.get('website', ALL_SOURCES_LABEL)
    refresh = request.args.get('refresh', '0') == '1'
    search_text = request.args.get('search', '')
    sources_str = request.args.get('sources', '').strip()
    selected_sources = [s for s in [x.strip() for x in sources_str.split(',')] if s] if sources_str else []

    # 数据获取与筛选（复用现有逻辑）
    if selected_sources:
        valid_sources = [s for s in selected_sources if s in websites]
        aggregated = []
        for site in valid_sources:
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        data = filter_news(deduped, search_text)
    elif website == ALL_SOURCES_LABEL:
        aggregated = []
        for site in websites.keys():
            aggregated.extend(get_news_with_cache(site, force_refresh=refresh))
        seen = set()
        deduped = []
        for item in aggregated:
            link = item.get('link')
            if link and link not in seen:
                seen.add(link)
                deduped.append(item)
        deduped.sort(key=lambda x: x.get('date', ''), reverse=True)
        data = filter_news(deduped, search_text)
    else:
        data = filter_news(get_news_with_cache(website, force_refresh=refresh), search_text)

    # 生成 RSS 2.0
    base = request.url_root.rstrip('/')
    title = f"国内旅游资讯 - {website if not selected_sources else ','.join(selected_sources)}"
    feed_items = []
    for item in data[:50]:
        t = (item.get('title') or '').replace('&', '&amp;')
        l = (item.get('link') or '').replace('&', '&amp;')
        d = (item.get('date') or '')
        feed_items.append(f"""
    <item>
      <title>{t}</title>
      <link>{l}</link>
      <guid isPermaLink="true">{l}</guid>
      <pubDate>{d}</pubDate>
      <description><![CDATA[{t}]]></description>
    </item>
""")
    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>{title}</title>
    <link>{base}/</link>
    <description>按当前筛选生成的资讯订阅</description>
    {''.join(feed_items)}
  </channel>
</rss>
"""
    return Response(rss, mimetype='application/rss+xml; charset=utf-8')

def get_news_with_cache(website, force_refresh=False):
    # 支持URL参数强制刷新
    if request.args.get('refresh') == 'true':
        force_refresh = True
    now = time.time()
    cache_entry = _cache.get(website)
    if not force_refresh and cache_entry and (now - cache_entry["ts"]) < CACHE_TTL_SECONDS:
        return cache_entry["data"]
    t0 = time.time()
    data = fetch_news(website)
    t1 = time.time()
    _cache[website] = {"data": data, "ts": now}
    # 记录指标
    _metrics['last_fetch'][website] = {
        'ts': int(now),
        'duration_ms': int((t1 - t0) * 1000),
        'count': len(data),
    }
    return data

def get_default_headers():
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }

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

def fetch_url_with_retries(url, headers=None, timeout=10, retries=3):
    last_exc = None
    for attempt in range(retries):
        try:
            resp = fetch_url(url, headers=headers or get_default_headers(), timeout=timeout)
            if resp.status_code == 200 and resp.text:
                return resp
            # 对于非常短的响应或临时错误，触发重试
        except Exception as exc:
            last_exc = exc
        # 指数退避 + 轻微抖动
        backoff_ms = (2 ** attempt) * 0.3 + random.uniform(0.05, 0.2)
        time.sleep(backoff_ms)
    # 最后一次尝试，直接抛出或返回占位响应
    if last_exc:
        raise last_exc
    return fetch_url(url, headers=headers or get_default_headers(), timeout=timeout)

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
        headers = get_default_headers()
        
        # 发送请求（对中国旅游新闻网增加回退URL以提升成功率）
        candidate_urls = [url]
        if website == "中国旅游新闻网":
            candidate_urls.extend([
                "https://www.ctnews.com.cn/jujiao/",  # 栏目页
                "https://www.ctnews.com.cn/",         # 首页
            ])
        response = None
        for cand in candidate_urls:
            try:
                response = fetch_url_with_retries(cand, headers=headers, timeout=10, retries=3)
                if response and response.status_code == 200 and response.text and len(response.text) > 1000:
                    print(f"成功抓取 {website} 从 {cand}, 内容长度: {len(response.text)}")
                    break
                else:
                    print(f"抓取失败 {website} 从 {cand}, 状态码: {response.status_code if response else 'None'}")
            except Exception as e:
                print(f"抓取异常 {website} 从 {cand}: {str(e)}")
                response = None
                continue
        if response is None:
            print(f"所有URL都失败 {website}")
            return []
        
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
        elif website == "中国旅游新闻网":
            # 中国旅游新闻网使用UTF-8编码
            response.encoding = "utf-8"
        else:
            # 其他网站使用UTF-8或自动检测
            response.encoding = response.apparent_encoding
        
        if response.status_code != 200:
            return []
        
        # 解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 获取标题和链接 - 支持单个选择器或选择器列表
        selectors = []
        if isinstance(link_css, list):
            selectors.extend(link_css)
        else:
            selectors.append(link_css)

        # 根据站点追加备用选择器以提升成功率
        if website == "人民网旅游频道":
            selectors.extend([
                'a[href*="/n1/"]',
                'div.ej_list_box a',
                'div.box a',
                'div.list_box a',
            ])
        if website == "中国旅游新闻网":
            selectors.extend([
                'a[href*="/content/"]',
                'div.list a[href*="/content/"]',
                'div.article-list a[href*="/content/"]',
                'ul li a[href*="/content/"]',
                'section a[href*="/content/"]',
            ])

        news_items = []
        for css in selectors:
            try:
                css_links = soup.select(css)
                if css_links:
                    print(f"选择器 {css} 匹配到 {len(css_links)} 个链接")
                    news_items.extend(css_links)
                else:
                    print(f"选择器 {css} 未匹配到链接")
            except Exception as e:
                print(f"选择器 {css} 异常: {str(e)}")
                continue
        
        print(f"总共找到 {len(news_items)} 个链接元素")
        
        # 去重处理，优先保留有文本内容的链接
        seen_hrefs = {}
        for item in news_items:
            href = item.get('href', '')
            if href:
                text = item.text.strip() if item.text else ""
                # 如果这个链接还没有记录，或者新链接有文本而旧链接没有文本
                if href not in seen_hrefs or (text and not seen_hrefs[href].text.strip()):
                    seen_hrefs[href] = item
        
        news_items = list(seen_hrefs.values())
        
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
                print(f"跳过无效项: 标题='{title[:30]}', 链接='{link[:50]}'")
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
                if isinstance(link, str) and isinstance(base_url, str) and link.startswith(base_url + base_url):
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
                # 修复双斜杠问题：只修复协议后的双斜杠，保留协议本身
                if link.startswith('http'):
                    # 将协议后的双斜杠替换为单斜杠
                    protocol_end = link.find('//') + 2
                    protocol_part = link[:protocol_end]
                    path_part = link[protocol_end:]
                    # 修复路径中的双斜杠
                    path_part = path_part.replace('//', '/')
                    link = protocol_part + path_part
                
                # 过滤明显无效的央广网链接模式（更精确的过滤）
                invalid_cnr_patterns = [
                    '/cnr_404/',      # 直接404页面
                    '//cnr.cn/',      # 跨域链接
                    '/2024zt/ai/',    # 特定的AI专题页面（已知404）
                    '/news.cnr.cn/2024zt/',  # 跨域专题页面
                    '/www.cnr.cn/2024zt/'    # 跨域专题页面
                ]
                
                if any(pattern in link for pattern in invalid_cnr_patterns):
                    print(f"过滤无效央广网链接: {link}")
                    continue
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
        
        print(f"处理完成后得到 {len(news_data)} 条新闻")
        
    except Exception as e:
        error_msg = str(e)
        print(f"获取资讯失败: {error_msg}")
        try:
            _errors.append({
                'ts': int(time.time()),
                'website': website,
                'stage': 'fetch_news',
                'message': error_msg,
            })
        except Exception:
            pass
        # 返回空列表而不是崩溃
        return []
        
    # 按日期排序，最新的在前
    news_data.sort(key=lambda x: x['date'], reverse=True)
    
    print(f"最终返回 {len(news_data)} 条新闻")
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
        # 验证链接格式，过滤无效链接
        if not link or not isinstance(link, str) or len(link.strip()) < 10:
            return "链接格式无效"
        
        # 修复链接中的双斜杠问题
        link = link.replace('//', '/').replace('https:/', 'https://').replace('http:/', 'http://')
        
        # 过滤明显无效的链接模式
        invalid_patterns = [
            'javascript:', '#', 'mailto:', 'tel:', 'ftp:', 'file:',
            '//news.cnr.cn//',  # 央广网特定的无效链接模式
            '//travel.cnr.cn//'  # 央广网特定的无效链接模式
        ]
        
        if any(pattern in link for pattern in invalid_patterns):
            return "链接格式无效"
        
        # 设置请求头，模拟浏览器
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        }
        
        # 请求新闻详情页
        response = fetch_url_with_retries(link, headers=headers, timeout=10, retries=3)
        
        # 检查响应状态，过滤404等错误页面
        if response.status_code != 200:
            if response.status_code == 404:
                return "页面不存在(404)"
            elif response.status_code >= 400:
                return f"页面访问失败({response.status_code})"
        
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
            main_content = soup.select_one('div.article-content, div#article_body, div.content, div.main-content, div.article-body')
        elif website == "人民网旅游频道":
            # 人民网旅游频道特定内容提取
            main_content = soup.select_one('div#rwb_zw, div#articleText, div.rm_txt_con, div.article-content, div.content, div.main')
        elif website == "央广网文旅频道":
            # 央广网文旅频道特定内容提取
            main_content = soup.select_one('div.article-content, div.content, div.main, div.article-body, div.article-text')
        
        # 如果没有找到特定内容，尝试通用选择器
        if not main_content:
            main_content = soup.select_one('div.content, div#article, div.article-content, div.content-main, div.main-content, div.article-body, div.article-text, div.text-content')
        
        # 如果仍然没有找到，尝试更通用的选择器
        if not main_content:
            # 查找包含大量文本的容器
            content_candidates = soup.select('div, article, section')
            for candidate in content_candidates:
                text_length = len(candidate.get_text(strip=True))
                if text_length > 200:  # 假设主要内容至少200字符
                    main_content = candidate
                    break
        
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

@app.route('/healthz')
def healthz():
    return jsonify({"status": "ok", "proxy": bool(os.environ.get('PROXY_BASE'))})

@app.route('/favicon.ico')
def favicon():
    # 避免日志里出现对favicon的错误请求
    return ('', 204)

@app.route('/metrics')
def metrics():
    if not _check_admin_key():
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify(_metrics)

@app.route('/logs')
def logs():
    if not _check_admin_key():
        return jsonify({'error': 'unauthorized'}), 401
    limit = int(request.args.get('limit', '100'))
    return jsonify(_errors[-limit:])

@app.route('/clear_cache', methods=['POST', 'GET'])
def clear_cache():
    if not _check_admin_key():
        return jsonify({'error': 'unauthorized'}), 401
    _cache.clear()
    return jsonify({'ok': True})

# --- UI helpers ---
@app.template_filter('highlight')
def highlight_filter(text, keyword):
    if not text or not keyword:
        return text
    try:
        pattern = re.compile(re.escape(keyword), re.IGNORECASE)
        return Markup(pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', str(text)))
    except Exception:
        return text

# --- SEO ---
@app.route('/robots.txt')
def robots_txt():
    base = request.url_root.rstrip('/')
    body = f"""User-agent: *
Allow: /
Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype='text/plain; charset=utf-8')

@app.route('/sitemap.xml')
def sitemap_xml():
    base = request.url_root.rstrip('/')
    urls = [
        f"{base}/",
        f"{base}/?website=全部来源",
    ]
    for site in websites.keys():
        urls.append(f"{base}/?website={site}")
    xml_urls = "".join([f"<url><loc>{u}</loc></url>" for u in urls])
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{xml_urls}
</urlset>"""
    return Response(xml, mimetype='application/xml; charset=utf-8')
# Vercel适配：标准Flask应用入口点
if __name__ == '__main__':
    # 确保中文正常显示
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # 本地运行入口点
    print("Running in local environment")
    app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
else:
    # Vercel环境使用
    application = app.wsgi_app