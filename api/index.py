# Vercel Python WSGI入口
# 符合Vercel Python运行时要求的类格式

import sys
import os
from http.server import BaseHTTPRequestHandler

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

# Vercel需要handler是一个继承自BaseHTTPRequestHandler的类
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 处理GET请求
        environ = {
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': self.path,
            'QUERY_STRING': '',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': None,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False
        }
        
        def start_response(status, headers):
            self.send_response(int(status.split()[0]))
            for header, value in headers:
                self.send_header(header, value)
            self.end_headers()
        
        # 调用Flask应用
        result = app.wsgi_app(environ, start_response)
        for data in result:
            self.wfile.write(data)
        if hasattr(result, 'close'):
            result.close()

# Vercel需要handler变量指向这个类
handler = Handler