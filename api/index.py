# Vercel Python WSGI入口
# 符合Vercel Python运行时要求的类格式

import sys
import os
from http.server import BaseHTTPRequestHandler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

# Vercel需要handler继承自BaseHTTPRequestHandler
class VercelWSGIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.app = app
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        self.handle_request('GET')
    
    def do_POST(self):
        self.handle_request('POST')
    
    def handle_request(self, method):
        # 简单的响应处理
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b'Hello from Vercel Python Runtime')

# Vercel需要handler是一个类
handler = VercelWSGIHandler