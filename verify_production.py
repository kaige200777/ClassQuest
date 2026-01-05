"""
生产环境验证脚本
验证所有核心文件和功能是否就绪
"""

import os
import sys

def check_file(filepath, description):
    """检查文件是否存在"""
    if os.path.exists(filepath):
        print(f"  ✓ {description}: {filepath}")
        return True
    else:
        print(f"  ✗ {description}: {filepath} (缺失!)")
        return False

def check_import(module_name, description):
    """检查模块是否可导入"""
    try:
        __import__(module_name)
        print(f"  ✓ {description}: {module_name}")
        return True
    except Exception as e:
        print(f"  ✗ {description}: {module_name} - {str(e)}")
        return False

def verify_production():
    """验证生产环境"""
    print("=" * 60)
    print("生产环境验证")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # 检查核心应用文件
    print("【核心应用文件】")
    core_files = [
        ('app.py', '主应用程序'),
        ('run.py', '启动脚本'),
        ('wsgl.py', 'WSGI入口'),
        ('config.py', '配置文件'),
        ('models.py', '数据模型'),
        ('ai_grading_service.py', 'AI批改服务'),
        ('version.py', '版本信息'),
        ('requirements.txt', '依赖列表'),
    ]
    
    for filepath, desc in core_files:
        if not check_file(filepath, desc):
            all_ok = False
    
    print()
    
    # 检查文档文件
    print("【文档文件】")
    doc_files = [
        ('README.md', '项目说明'),
        ('CHANGELOG.md', '更新日志'),
        ('DEPLOYMENT_GUIDE.md', '部署指南'),
        ('PRODUCTION_DEPLOYMENT.md', '生产部署清单'),
        ('PRODUCTION_READY_REPORT.md', '生产就绪报告'),
    ]
    
    for filepath, desc in doc_files:
        if not check_file(filepath, desc):
            all_ok = False
    
    print()
    
    # 检查目录
    print("【必要目录】")
    dirs = [
        ('templates', 'HTML模板'),
        ('static', '静态资源'),
        ('models', '数据模型模块'),
        ('tests', '单元测试'),
        ('题库', '题库文件'),
    ]
    
    for dirname, desc in dirs:
        if not check_file(dirname, desc):
            all_ok = False
    
    print()
    
    # 检查模块导入
    print("【模块导入测试】")
    modules = [
        ('config', '配置模块'),
        ('models', '数据模型'),
        ('ai_grading_service', 'AI批改服务'),
        ('version', '版本信息'),
    ]
    
    for module, desc in modules:
        if not check_import(module, desc):
            all_ok = False
    
    print()
    
    # 检查配置
    print("【配置检查】")
    try:
        import config
        
        # 检查SECRET_KEY
        if config.SECRET_KEY == 'your-secret-key':
            print("  ⚠ SECRET_KEY 仍使用默认值，建议修改")
        else:
            print("  ✓ SECRET_KEY 已自定义")
        
        # 检查AI配置
        if hasattr(config, 'AI_GRADING_CONFIG'):
            ai_config = config.AI_GRADING_CONFIG
            if ai_config.get('enabled'):
                if ai_config.get('api_key'):
                    print("  ✓ AI批改已配置")
                else:
                    print("  ⚠ AI批改已启用但缺少API密钥")
            else:
                print("  - AI批改未启用")
        
        # 检查端口配置
        print(f"  ✓ 服务器配置: {config.HOST}:{config.PORT}")
        
    except Exception as e:
        print(f"  ✗ 配置检查失败: {str(e)}")
        all_ok = False
    
    print()
    
    # 检查是否有测试文件残留
    print("【清理验证】")
    test_files = [
        'test_ai_config_validation.py',
        'test_ai_grading.py',
        'test_full_ai_grading.py',
        'cleanup_production.py',
        'preview_cleanup.py',
    ]
    
    clean = True
    for test_file in test_files:
        if os.path.exists(test_file):
            print(f"  ⚠ 发现测试文件: {test_file}")
            clean = False
    
    if clean:
        print("  ✓ 所有测试文件已清理")
    
    print()
    print("=" * 60)
    
    if all_ok:
        print("✅ 生产环境验证通过！")
        print()
        print("下一步:")
        print("1. 阅读 PRODUCTION_DEPLOYMENT.md")
        print("2. 修改 config.py 中的配置")
        print("3. 运行 python run.py 启动服务")
        print("4. 访问 http://localhost:8080")
        print("5. 使用 admin/admin 登录并修改密码")
    else:
        print("❌ 生产环境验证失败！")
        print("请检查上述错误并修复")
        sys.exit(1)
    
    print("=" * 60)

if __name__ == "__main__":
    verify_production()
