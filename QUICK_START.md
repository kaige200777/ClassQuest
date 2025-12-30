# 快速开始指南

## 5分钟快速部署

### 1. 环境准备
```bash
# 确保已安装 Python 3.10+
python --version

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置应用
编辑 `config.py`：
```python
# 修改密钥（必须）
SECRET_KEY = 'your-random-secret-key-here'

# 配置AI批改（可选）
AI_GRADING_CONFIG = {
    'enabled': True,
    'api_key': 'your-api-key',
    'base_url': 'https://api.deepseek.com',
    'model': 'deepseek-chat',
    # ...
}
```

### 3. 启动服务
```bash
python run.py
```

### 4. 访问系统
- 打开浏览器访问: http://localhost:8080
- 教师登录: admin / admin
- **立即修改默认密码！**

### 5. 导入题库
1. 登录教师控制面板
2. 选择题型
3. 点击"导入题库"
4. 上传CSV或Excel文件

### 6. 创建测试
1. 设置各题型的数量和分值
2. 选择题库
3. 点击"保存设置"

## 验证部署

运行验证脚本：
```bash
python verify_production.py
```

## 常见问题

### 端口被占用
修改 `config.py` 中的 `PORT` 值

### 数据库错误
删除 `instance/test_system.db` 重新启动

### AI批改不可用
检查 `config.py` 中的 AI 配置

## 详细文档

- **完整说明**: README.md
- **部署指南**: PRODUCTION_DEPLOYMENT.md
- **AI功能**: AI批改功能使用指南.md

## 技术支持

QQ: 59083992
