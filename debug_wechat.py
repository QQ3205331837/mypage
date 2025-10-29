import requests
import re

url = 'https://mp.weixin.qq.com/mp/appmsgalbum?__biz=MzA4ODA2ODMzNA==&action=getalbum&album_id=4180740440766726147#wechat_redirect'
response = requests.get(url, timeout=10)
html = response.text

print("=== 分析微信专栏页面结构 ===")
print(f"页面长度: {len(html)} 字符")
print(f"状态码: {response.status_code}")

# 搜索常见的数据模式
patterns = [
    r'data-title=[\"\']([^\"\']+)[\"\']',
    r'title[\"\']?\s*:\s*[\"\']([^\"\']+)[\"\']',
    r'data-link=[\"\']([^\"\']+)[\"\']',
    r'link[\"\']?\s*:\s*[\"\']([^\"\']+)[\"\']',
    r'create_time[\"\']?\s*:\s*[\"\']?(\\d+)[\"\']?',
    r'album__list-item',
]

for pattern in patterns:
    matches = re.findall(pattern, html, re.IGNORECASE)
    if matches:
        print(f'模式 {pattern}: 找到 {len(matches)} 个匹配')
        if len(matches) > 0:
            print('示例:', matches[:3])

# 搜索包含文章信息的script标签
script_pattern = r'<script[^>]*>([^<]*article[^<]*)</script>'
script_matches = re.findall(script_pattern, html, re.IGNORECASE)
if script_matches:
    print('找到包含article的script标签')
    for i, match in enumerate(script_matches[:2]):
        print(f'script {i+1} 内容片段: {match[:200]}')

# 搜索li元素
li_pattern = r'<li[^>]*>.*?</li>'
li_matches = re.findall(li_pattern, html, re.DOTALL)
print(f'找到 {len(li_matches)} 个li元素')

# 搜索包含数据的JavaScript变量
js_patterns = [
    r'var\s+\w+\s*=\s*\{[^}]*title[^}]*\}',
    r'window\.\w+\s*=\s*\{[^}]*title[^}]*\}',
    r'articleList\s*:\s*\[[^]]*\]',
]

for pattern in js_patterns:
    matches = re.findall(pattern, html, re.DOTALL)
    if matches:
        print(f'找到JavaScript数据模式: {pattern[:50]}...')
        for i, match in enumerate(matches[:1]):
            print(f'数据 {i+1}: {match[:300]}')

# 保存HTML内容到文件以便分析
with open('wechat_debug.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("HTML内容已保存到 wechat_debug.html")