# 修复导入路径，确保在Vercel环境中能正确导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app

# Vercel需要这个handler变量
handler = app