# Vercel Python WSGI入口
# 符合Vercel Python运行时要求的类格式

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

# Vercel需要handler是一个类
# 创建一个WSGI应用类来满足Vercel的要求
class WSGIHandler:
    def __init__(self, app):
        self.app = app
    
    def __call__(self, environ, start_response):
        return self.app(environ, start_response)

# 创建处理程序实例
handler = WSGIHandler(app.wsgi_app)