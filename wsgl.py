from app import app
import os

# 从环境变量或配置文件读取端口
try:
    from config import HOST, PORT
except ImportError:
    HOST = os.environ.get('APP_HOST', '0.0.0.0')
    PORT = int(os.environ.get('APP_PORT', 8000))

if __name__ == '__main__':
    from waitress import serve
    print(f"Starting server on http://{HOST}:{PORT}")
    serve(app, host=HOST, port=PORT)