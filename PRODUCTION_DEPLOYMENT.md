# 生产环境部署清单

## 版本信息
- **版本**: v1.1.0
- **发布日期**: 2025-12-12
- **Python版本**: 3.10+

## 部署前检查

### 1. 环境准备
- [ ] Python 3.10+ 已安装
- [ ] pip 包管理器可用
- [ ] 虚拟环境已创建
- [ ] 所有依赖已安装 (`pip install -r requirements.txt`)

### 2. 配置检查
- [ ] `config.py` 中的 `SECRET_KEY` 已修改（不使用默认值）
- [ ] `config.py` 中的 `HOST` 和 `PORT` 已配置
- [ ] 数据库路径已确认
- [ ] AI批改配置已设置（如需使用）

### 3. 安全检查
- [ ] 默认教师密码已修改（admin/admin）
- [ ] 文件上传目录权限已设置
- [ ] 数据库文件权限已设置
- [ ] 敏感信息未提交到版本控制

### 4. 功能测试
- [ ] 教师登录功能正常
- [ ] 题库导入功能正常
- [ ] 测试创建功能正常
- [ ] 学生答题功能正常
- [ ] 成绩统计功能正常
- [ ] AI批改功能正常（如已配置）

## 部署步骤

### 1. 克隆或下载项目
```bash
git clone <repository-url>
cd 课堂测试系统
```

### 2. 创建虚拟环境
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置应用
编辑 `config.py` 文件：
```python
# 修改密钥
SECRET_KEY = 'your-production-secret-key-here'

# 配置服务器
HOST = '0.0.0.0'
PORT = 8080

# 配置AI批改（可选）
AI_GRADING_CONFIG = {
    'enabled': True,
    'api_key': 'your-api-key',
    # ... 其他配置
}
```

### 5. 初始化数据库
```bash
python run.py
# 首次运行会自动创建数据库和默认账户
# 按 Ctrl+C 停止
```

### 6. 修改默认密码
1. 访问 http://localhost:8080/teacher/login
2. 使用 admin/admin 登录
3. 点击"修改密码"修改默认密码

### 7. 导入题库
1. 准备题库文件（CSV或Excel格式）
2. 在教师控制面板导入题库
3. 验证题库导入成功

### 8. 启动生产服务
```bash
python run.py
```

## 生产环境优化

### 1. 使用进程管理器
推荐使用 systemd、supervisor 或 PM2 管理应用进程

#### systemd 示例
创建 `/etc/systemd/system/test-system.service`:
```ini
[Unit]
Description=Test System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/test-system
Environment="PATH=/path/to/test-system/venv/bin"
ExecStart=/path/to/test-system/venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable test-system
sudo systemctl start test-system
sudo systemctl status test-system
```

### 2. 使用反向代理
推荐使用 Nginx 作为反向代理

#### Nginx 配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/test-system/static;
        expires 30d;
    }
}
```

### 3. 配置HTTPS
使用 Let's Encrypt 获取免费SSL证书：
```bash
sudo certbot --nginx -d your-domain.com
```

### 4. 数据库备份
创建定时备份脚本：
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp /path/to/instance/test_system.db /path/to/backups/test_system_$DATE.db
# 保留最近30天的备份
find /path/to/backups -name "test_system_*.db" -mtime +30 -delete
```

添加到 crontab：
```bash
# 每天凌晨2点备份
0 2 * * * /path/to/backup.sh
```

### 5. 日志管理
配置日志轮转 `/etc/logrotate.d/test-system`:
```
/path/to/test-system/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
}
```

## 监控和维护

### 1. 性能监控
- 监控CPU和内存使用
- 监控磁盘空间
- 监控数据库大小
- 监控API调用次数（如使用AI批改）

### 2. 定期维护
- [ ] 每周检查系统日志
- [ ] 每月检查数据库大小
- [ ] 每月检查备份完整性
- [ ] 每季度更新依赖包
- [ ] 每半年审查安全配置

### 3. 故障处理
常见问题和解决方案请参考 README.md 中的"常见问题"章节

## 升级指南

### 1. 备份数据
```bash
# 备份数据库
cp instance/test_system.db instance/test_system.db.backup

# 备份配置
cp config.py config.py.backup

# 备份上传文件
cp -r static/uploads static/uploads.backup
```

### 2. 更新代码
```bash
git pull origin main
# 或下载新版本文件
```

### 3. 更新依赖
```bash
pip install -r requirements.txt --upgrade
```

### 4. 数据库迁移
如有数据库结构变更，运行迁移脚本

### 5. 重启服务
```bash
sudo systemctl restart test-system
```

### 6. 验证功能
测试关键功能是否正常

## 回滚计划

如果升级出现问题：

1. 停止服务
```bash
sudo systemctl stop test-system
```

2. 恢复备份
```bash
cp instance/test_system.db.backup instance/test_system.db
cp config.py.backup config.py
```

3. 恢复代码
```bash
git checkout <previous-version>
```

4. 重启服务
```bash
sudo systemctl start test-system
```

## 安全建议

1. **定期更新**
   - 及时更新Python和依赖包
   - 关注安全公告

2. **访问控制**
   - 使用防火墙限制访问
   - 配置IP白名单（如适用）
   - 使用强密码策略

3. **数据保护**
   - 定期备份数据
   - 加密敏感数据
   - 限制文件上传大小和类型

4. **监控审计**
   - 启用访问日志
   - 监控异常登录
   - 定期审查用户活动

## 联系支持

如遇到问题，请：
1. 查看 README.md 中的常见问题
2. 查看系统日志
3. 联系技术支持 QQ: 59083992

## 文档版本
- v1.0 - 2025-12-12 - 初始版本
