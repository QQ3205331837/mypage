# Vercel Python WSGI入口
# 使用Vercel官方推荐的最简单格式

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 导入Flask应用
from app import app

# Vercel需要handler变量
# 直接使用Flask应用对象（Vercel会自动处理WSGI转换）
handler = app