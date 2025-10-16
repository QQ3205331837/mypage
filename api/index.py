from http.server import BaseHTTPRequestHandler
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 设置响应头
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # 调用Flask应用的WSGI接口
        def start_response(status, headers):
            self.send_response(int(status.split()[0]))
            for header, value in headers:
                self.send_header(header, value)
            self.end_headers()
        
        # 创建WSGI环境
        environ = {
            'REQUEST_METHOD': self.command,
            'PATH_INFO': self.path,
            'QUERY_STRING': self.path.split('?', 1)[1] if '?' in self.path else '',
            'SERVER_NAME': self.server.server_address[0],
            'SERVER_PORT': str(self.server.server_address[1]),
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.input': self.rfile,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }
        
        # 调用Flask应用
        result = app(environ, start_response)
        try:
            for data in result:
                self.wfile.write(data)
        finally:
            if hasattr(result, 'close'):
                result.close()

# Vercel需要这个变量
handler = Handler