# 端口配置说明

## 快速修改端口

### 方法1：修改 config.py（推荐）✅

编辑 `config.py` 文件：
```python
PORT = 8000  # 改为你想要的端口，如 5000, 8080 等
```

### 方法2：使用环境变量

#### Windows (CMD)
```cmd
set APP_PORT=5000
python run.py
```

#### Windows (PowerShell)
```powershell
$env:APP_PORT=5000
python run.py
```

#### Linux/Mac
```bash
export APP_PORT=5000
python run.py
```

### 方法3：直接修改 run.py

编辑 `run.py` 文件，找到：
```python
PORT = int(os.environ.get('APP_PORT', 8000))
```
改为：
```python
PORT = int(os.environ.get('APP_PORT', 5000))  # 改为你想要的端口
```

## 文件说明

### 1. run.py（主启动文件）⭐
- **用途**：生产环境启动脚本
- **服务器**：Waitress（生产级WSGI服务器）
- **推荐使用**：✅ 是
- **端口配置**：从 config.py 或环境变量读取

### 2. wsgl.py（备用启动文件）
- **用途**：备用启动脚本（功能与run.py相同）
- **服务器**：Waitress
- **推荐使用**：可选
- **端口配置**：从 config.py 或环境变量读取

### 3. app.py（应用主文件）
- **用途**：Flask应用定义
- **端口配置**：仅在直接运行 `python app.py` 时使用
- **推荐使用**：❌ 不推荐（仅用于开发调试）
- **说明**：生产环境不应该直接运行 app.py

## 启动方式对比

### 生产环境（推荐）✅
```bash
python run.py
```
- 使用 Waitress 服务器
- 性能好，稳定
- 支持并发
- 端口：从 config.py 读取（默认8000）

### 开发环境（调试用）
```bash
python app.py
```
- 使用 Flask 内置服务器
- 支持热重载
- 仅用于开发
- 端口：硬编码为8000

## 常见端口选择

| 端口 | 说明 | 推荐 |
|------|------|------|
| 80 | HTTP默认端口 | 需要管理员权限 |
| 443 | HTTPS默认端口 | 需要管理员权限 + SSL证书 |
| 5000 | Flask默认端口 | ✅ 开发环境 |
| 8000 | 常用Web端口 | ✅ 生产环境（当前默认） |
| 8080 | 备用Web端口 | ✅ 生产环境 |
| 3000 | Node.js常用 | 可用 |

## 端口冲突解决

### 检查端口占用

#### Windows
```cmd
netstat -ano | findstr :8000
```

#### Linux/Mac
```bash
lsof -i :8000
```

### 解决方案
1. 修改为其他端口（推荐）
2. 停止占用端口的程序
3. 使用端口转发

## 配置优先级

端口配置的读取优先级（从高到低）：

1. **环境变量** `APP_PORT`
2. **config.py** 中的 `PORT`
3. **默认值** `8000`

示例：
```python
# 优先级1: 环境变量
APP_PORT=5000 python run.py  # 使用5000

# 优先级2: config.py
# config.py: PORT = 6000
python run.py  # 使用6000

# 优先级3: 默认值
# 没有环境变量，没有config.py
python run.py  # 使用8000
```

## 生产环境部署

### 使用 Nginx 反向代理（推荐）

应用运行在内部端口（如8000），Nginx监听80/443：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;  # 应用端口
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

优点：
- 应用使用非特权端口（8000）
- Nginx处理SSL、静态文件、负载均衡
- 更安全、更高效

### 直接监听80端口

需要管理员权限：

```bash
# Linux
sudo python run.py

# 或修改 config.py
PORT = 80
```

## 多实例部署

运行多个实例，使用不同端口：

```bash
# 实例1
APP_PORT=8001 python run.py &

# 实例2
APP_PORT=8002 python run.py &

# 实例3
APP_PORT=8003 python run.py &
```

然后使用 Nginx 负载均衡：
```nginx
upstream app_servers {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    location / {
        proxy_pass http://app_servers;
    }
}
```

## 故障排查

### 问题1：端口被占用
```
OSError: [Errno 98] Address already in use
```

**解决**：
1. 修改为其他端口
2. 或停止占用端口的程序

### 问题2：无法访问
```
无法连接到 localhost:8000
```

**检查**：
1. 应用是否正常启动
2. 防火墙是否阻止
3. 端口是否正确

### 问题3：权限不足
```
Permission denied: port 80
```

**解决**：
1. 使用非特权端口（>1024）
2. 或使用管理员权限运行

## 总结

### 推荐配置方式

1. **开发环境**：
   ```python
   # config.py
   PORT = 5000
   DEBUG = True
   ```

2. **生产环境**：
   ```python
   # config.py
   PORT = 8000
   DEBUG = False
   ```

3. **使用环境变量**（最灵活）：
   ```bash
   APP_PORT=8000 python run.py
   ```

### 最佳实践

✅ **推荐**：
- 使用 `config.py` 统一管理配置
- 生产环境使用环境变量
- 使用 Nginx 反向代理
- 应用使用非特权端口（8000）

❌ **不推荐**：
- 直接运行 `python app.py`
- 在代码中硬编码端口
- 直接监听80端口（除非必要）

---

**配置文件**：`config.py`  
**启动文件**：`run.py`  
**默认端口**：8000  
**修改方式**：编辑 config.py 或设置环境变量
