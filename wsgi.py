import os
from app import app

# WSGI入口点 - Vercel兼容
application = app.wsgi_app

# 配置Vercel环境下的端口
if __name__ == "__main__":
    # 获取端口，Vercel环境会自动设置PORT变量
    port = int(os.environ.get('PORT', 5000))
    # 设置host为0.0.0.0以允许外部访问
    app.run(host='0.0.0.0', port=port)