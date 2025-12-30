# 课堂练习评估系统 - 生产环境部署指南

## 系统概述

课堂练习评估系统是一个基于 Flask 的 Web 应用，用于创建、管理和评估学生测试。

### 主要功能

- 教师端：题库管理、测试配置、成绩统计、简答题评分
- 学生端：在线测试、成绩查看、历史记录
- 支持多种题型：单选、多选、判断、填空、简答
- 支持图片上传（题目和答案）
- 测试预设管理
- Excel 批量导入题目

## 系统要求

### 硬件要求
- CPU: 2核心或以上
- 内存: 2GB 或以上
- 磁盘: 10GB 可用空间（用于数据库和上传文件）

### 软件要求
- Python 3.8 或以上
- SQLite 3（Python 自带）
- 现代浏览器（Chrome、Firefox、Edge、Safari）

## 部署步骤

### 1. 准备环境

```bash
# 克隆或复制项目文件到服务器
cd /path/to/project

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 初始化数据库

```bash
# 运行数据库初始化脚本
python init_database.py
```

这将创建：
- 所有必要的数据库表
- 默认管理员账户（用户名: admin, 密码: admin）

**重要：首次登录后请立即修改默认密码！**

### 3. 创建管理员账户（可选）

如果需要创建额外的管理员账户：

```bash
python create_teacher.py
```

按提示输入用户名和密码。

### 4. 配置应用

编辑 `app.py` 中的配置（如需要）：

```python
# 密钥（生产环境请使用强随机密钥）
app.config['SECRET_KEY'] = 'your-secret-key-here'

# 数据库路径
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_system.db'

# 上传文件配置
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_IMG_SIZE = 2 * 1024 * 1024  # 2MB
```

### 5. 启动应用

#### 开发模式（仅用于测试）

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动。

#### 生产模式（推荐）

使用 Gunicorn（Linux/Mac）：

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用（4个工作进程）
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

使用 Waitress（Windows）：

```bash
# 安装 Waitress
pip install waitress

# 启动应用
waitress-serve --host=0.0.0.0 --port=8000 app:app
```

### 6. 配置反向代理（可选但推荐）

使用 Nginx 作为反向代理：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /static {
        alias /path/to/project/static;
    }

    client_max_body_size 10M;
}
```

## 目录结构

```
project/
├── app.py                  # 主应用文件
├── models.py              # 数据库模型（如果分离）
├── run.py                 # 启动脚本
├── init_database.py       # 数据库初始化
├── create_teacher.py      # 创建教师账户
├── requirements.txt       # Python 依赖
├── README.md             # 项目说明
├── CHANGELOG.md          # 更新日志
├── DEPLOYMENT_GUIDE.md   # 本文件
├── instance/             # 数据库文件目录
│   └── test_system.db
├── static/               # 静态文件
│   ├── bootstrap/
│   ├── uploads/         # 上传的图片
│   └── ...
├── templates/            # HTML 模板
│   ├── index.html
│   ├── teacher_dashboard.html
│   ├── student_start.html
│   └── ...
├── tests/                # 单元测试（可选）
├── docs/                 # 文档目录
└── venv/                 # 虚拟环境（不要提交到版本控制）
```

## 安全建议

### 1. 修改默认密码
首次登录后立即修改默认管理员密码。

### 2. 使用强密钥
在 `app.py` 中设置强随机密钥：

```python
import secrets
app.config['SECRET_KEY'] = secrets.token_hex(32)
```

### 3. 限制文件上传
已配置文件类型和大小限制：
- 允许的图片格式：png, jpg, jpeg, gif, bmp, webp
- 最大文件大小：2MB

### 4. 定期备份数据库

```bash
# 备份数据库
cp instance/test_system.db instance/test_system.db.backup.$(date +%Y%m%d)

# 或使用 SQLite 命令
sqlite3 instance/test_system.db ".backup instance/test_system.db.backup"
```

### 5. 使用 HTTPS
在生产环境中，强烈建议使用 HTTPS。可以使用 Let's Encrypt 免费证书。

### 6. 防火墙配置
只开放必要的端口（如 80、443），限制对数据库文件的直接访问。

## 维护操作

### 查看日志

应用日志会输出到控制台。在生产环境中，建议重定向到文件：

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app >> logs/app.log 2>&1
```

### 数据库备份

建议设置定时任务（cron）自动备份：

```bash
# 每天凌晨2点备份
0 2 * * * cp /path/to/instance/test_system.db /path/to/backups/test_system.db.$(date +\%Y\%m\%d)
```

### 清理旧数据

如需清理旧的测试记录：

```python
# 在 Python 交互式环境中
from app import app, db, TestResult
from datetime import datetime, timedelta

with app.app_context():
    # 删除30天前的测试记录
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    old_results = TestResult.query.filter(TestResult.created_at < cutoff_date).all()
    for result in old_results:
        db.session.delete(result)
    db.session.commit()
    print(f"已删除 {len(old_results)} 条旧记录")
```

### 更新应用

```bash
# 1. 备份数据库
cp instance/test_system.db instance/test_system.db.backup

# 2. 拉取最新代码
git pull

# 3. 更新依赖
pip install -r requirements.txt

# 4. 重启应用
# 如果使用 systemd:
sudo systemctl restart test-system

# 如果手动运行:
# 停止旧进程，然后重新启动
```

## 故障排查

### 问题：无法启动应用

**检查：**
1. Python 版本是否正确（3.8+）
2. 所有依赖是否已安装
3. 端口是否被占用
4. 数据库文件是否存在且有读写权限

### 问题：无法上传图片

**检查：**
1. `static/uploads` 目录是否存在
2. 目录是否有写权限
3. 文件大小是否超过限制（2MB）
4. 文件格式是否支持

### 问题：学生无法登录

**检查：**
1. 是否有激活的测试
2. 测试配置是否正确
3. 题库中是否有足够的题目

### 问题：数据库错误

**解决：**
```bash
# 重新初始化数据库（警告：会清空所有数据）
rm instance/test_system.db
python init_database.py
```

## 性能优化

### 1. 使用多个工作进程

```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

工作进程数建议为 `(2 × CPU核心数) + 1`

### 2. 启用静态文件缓存

在 Nginx 配置中：

```nginx
location /static {
    alias /path/to/project/static;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

### 3. 数据库优化

定期执行 VACUUM 命令优化数据库：

```bash
sqlite3 instance/test_system.db "VACUUM;"
```

## 监控建议

### 1. 应用监控
- 使用 Supervisor 或 systemd 管理进程
- 配置自动重启
- 监控内存和CPU使用

### 2. 日志监控
- 定期检查错误日志
- 设置日志轮转
- 监控异常访问

### 3. 数据库监控
- 监控数据库大小
- 定期检查数据完整性
- 监控查询性能

## 联系支持

如遇到问题，请查看：
1. `docs/` 目录中的修复文档
2. `CHANGELOG.md` 了解最新更新
3. `README.md` 了解基本使用

## 版本信息

- 当前版本：见 `version.py`
- 最后更新：2024-12-03
- Python 版本要求：3.8+
- Flask 版本：见 `requirements.txt`

## 许可证

请查看项目根目录的 LICENSE 文件。
