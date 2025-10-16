from app import app

# Vercel需要handler变量指向WSGI应用
# 直接使用Flask应用的WSGI接口
handler = app