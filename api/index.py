from app import app

# Vercel需要handler变量指向WSGI应用
# 对于Python Flask应用，使用app.wsgi_app
handler = app.wsgi_app