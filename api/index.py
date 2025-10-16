# Vercel Python WSGI入口
# 使用最简单的WSGI应用格式

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

# Vercel需要handler变量指向WSGI应用
# 直接使用Flask应用的WSGI接口
handler = app