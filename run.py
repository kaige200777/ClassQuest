from app import init_db, app
from waitress import serve
import os

# 从环境变量或配置文件读取端口
try:
    from config import HOST, PORT
except ImportError:
    HOST = os.environ.get('APP_HOST', '0.0.0.0')
    PORT = int(os.environ.get('APP_PORT', 8000))

def check_ai_config():
    """检查AI配置状态"""
    try:
        from ai_grading_service import AIGradingService
        ai_service = AIGradingService()
        
        # 先检查配置项
        enabled, message = ai_service.get_config_status()
        
        if not enabled:
            print(f"✗ AI批改功能未配置: {message}")
            print("  提示: 请在config.py中正确配置AI_GRADING_CONFIG")
            return
        
        # 配置项正确，测试API连接
        provider = ai_service.config.get('provider', 'unknown')
        model = ai_service.config.get('model', 'unknown')
        
        print(f"正在测试AI API连接 ({provider}/{model})...", end='', flush=True)
        connection_ok, connection_msg = ai_service.test_connection()
        
        if connection_ok:
            print(f"\r✓ AI批改功能已配置并测试通过 ({provider}/{model})")
        else:
            print(f"\r✗ AI API连接失败: {connection_msg}")
            print(f"  配置: {provider}/{model}")
            print("  提示: 请检查API密钥是否正确，或网络连接是否正常")
            
    except Exception as e:
        print(f"✗ AI配置检测失败: {str(e)}")

if __name__ == "__main__":
    # 初始化数据库
    init_db()
    
    # 检查AI配置
    check_ai_config()
    
    # 启动Waitress服务器
    print(f"\nStarting server on http://{HOST}:{PORT}")
    print(f"访问地址: http://localhost:{PORT}")
    print("按 Ctrl+C 停止服务器\n")
    serve(app, host=HOST, port=PORT) 