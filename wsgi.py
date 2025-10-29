from app import app

# WSGI入口点
application = app.wsgi_app

if __name__ == "__main__":
    app.run()