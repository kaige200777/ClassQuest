# 学习任务单系统

一个基于 Flask 的在线学习任务单评估系统，支持多种题型、题库管理、测试统计和简答题批改等功能。

## 📋 项目简介

学习任务单系统是一个功能完善的在线测试系统，主要用于教育场景中的学习任务单和评估。系统支持教师端和学生端，提供了完整的题库管理、测试设置、在线测试、成绩统计等功能。

## ✨ 功能特点

### 教师端功能

#### 1. 题库管理
- **多题型支持**：支持单选题、多选题、判断题、填空题、简答题
- **题库分类**：按题型分类管理，支持创建多个题库
- **批量导入**：支持 CSV 和 Excel 格式批量导入题目
- **题目编辑**：支持在线编辑题目内容、选项、答案和配图
- **题目删除**：支持删除单个题目或清空整个题库
- **题库导出**：支持导出题库为 Excel 格式

#### 2. 测试设置
- **灵活配置**：可设置各题型的题目数量和分值（也可在测试配置时设置题目分数）
- **题库选择**：为每种题型选择题库
- **预设管理**：支持创建和管理测试预设，方便快速设置
- **学生自选**：支持允许学生自主选择测试内容
- **自动计算**：自动计算总分

#### 3. 测试统计
- **成绩统计**：查看所有学生的测试成绩
- **详细分析**：查看单个学生的详细答题情况
- **数据分析**：统计平均分、最高分、最低分等数据
- **导出功能**：支持导出测试统计数据

#### 4. 简答题批改
- **人工批改**：支持在线批改学生的简答题答案
- **AI批改**：支持使用AI自动批改简答题（需配置AI服务）
- **图片上传**：学生可上传图片作为答案
- **评分注释**：支持添加评分和评语
- **批量处理**：支持批量查看未批改的简答题
- **批改方式选择**：可在测试设置时选择人工批改或AI批改

#### 5. 系统管理
- **用户管理**：教师登录、修改密码
- **数据初始化**：支持初始化系统数据
- **题库重命名**：支持重命名题库

### 学生端功能

#### 1. 在线测试
- **自动登录**：通过姓名和班级号自动创建账号
- **测试内容选择**：支持选择预设的测试内容（教师端设置允许时）
- **随机抽题**：系统随机从题库中抽取题目
- **实时答题**：支持在线答题，自动保存答案
- **图片上传**：简答题支持上传图片答案

#### 2. 成绩查看
- **测试结果**：查看测试成绩和正确答案
- **历史记录**：查看历史测试记录
- **成绩统计**：查看个人测试统计信息

## 🛠️ 技术栈

### 后端
- **Python 3.10+**
- **Flask 3.0.2** - Web 框架
- **SQLAlchemy 2.0.27** - ORM 框架
- **Flask-SQLAlchemy 3.1.1** - Flask SQLAlchemy 集成
- **Waitress 2.1.2** - WSGI 服务器

### 前端
- **Bootstrap 5.3.0** - UI 框架
- **Bootstrap Icons** - 图标库
- **JavaScript** - 交互逻辑

### 数据处理
- **Pandas 2.0.3** - 数据处理
- **OpenPyXL 3.1.2** - Excel 文件处理
- **NumPy 1.24.3** - 数值计算

### AI服务（可选）
- **OpenAI API** - 支持 OpenAI 兼容的 API 服务
- **DeepSeek** - 支持 DeepSeek AI 服务
- 其他兼容 OpenAI API 格式的服务

### 数据库
- **SQLite** - 轻量级数据库（默认）
- 支持迁移到 MySQL、PostgreSQL 等数据库

## 📦 系统要求

- Python 3.10 或更高版本
- pip 包管理器
- 现代浏览器（Chrome、Firefox、Edge 等）
- 至少 500MB 可用磁盘空间

## 🚀 安装部署

### 1. 环境准备

#### Windows 系统

```bash
# 1. 下载并安装 Python 3.10+
# 从 https://www.python.org/downloads/ 下载

# 2. 验证 Python 安装
python --version

# 3. 验证 pip 安装
pip --version
```

#### Linux 系统

```bash
# 1. 安装 Python 3.10+
sudo apt update
sudo apt install python3 python3-pip

# 2. 验证安装
python3 --version
pip3 --version
```

#### macOS 系统

```bash
# 1. 使用 Homebrew 安装 Python
brew install python3

# 2. 验证安装
python3 --version
pip3 --version
```

### 2. 克隆项目

```bash
# 使用 Git 克隆项目
git clone <repository-url>
cd 学习任务单系统

# 或者直接下载项目文件
```

### 3. 创建虚拟环境

#### Windows

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate
```

#### Linux/macOS

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate
```

### 4. 安装依赖

```bash
# 安装项目依赖
pip install -r requirements.txt

# 如果使用国内镜像，可以使用：
# pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5. 配置数据库

系统使用 SQLite 数据库，首次运行时会自动创建数据库文件。

数据库文件位置：`instance/test_system.db`

### 6. 初始化数据库

```bash
# 方式1：直接运行应用（会自动初始化）
python app.py

# 方式2：使用初始化脚本
python run.py
```

### 7. 启动应用

#### 开发模式

```bash
# 使用 Flask 开发服务器
python app.py

# 应用将在 http://localhost:8000 启动
```

#### 生产模式

```bash
# 使用 Waitress 服务器
python run.py

# 或者使用 wsgl.py
python wsgl.py

# 应用将在 http://0.0.0.0:8000 启动
```

#### 使用 Gunicorn (Linux/macOS)

```bash
# 安装 Gunicorn
pip install gunicorn

# 启动应用
gunicorn -w 4 -b 0.0.0.0:8000 wsgl:app
```

#### 使用 Docker (可选)

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "run.py"]
```

```bash
# 构建镜像
docker build -t test-system .

# 运行容器
docker run -d -p 8000:8000 test-system
```

### 8. 访问应用

- **首页**：http://localhost:8000
- **教师登录**：http://localhost:8000/teacher/login
- **学生测试**：http://localhost:8000/student/start

### 9. 默认账号

- **教师账号**：admin
- **教师密码**：admin

**⚠️ 首次登录后请立即修改密码！**

## 📖 使用说明

### 教师端使用

#### 1. 登录系统

1. 访问教师登录页面
2. 输入用户名和密码
3. 点击登录

#### 2. 导入题库

1. 在教师控制面板选择题型（单选题、多选题等，题库目录下的题型就是模板。）
2. 点击"导入题库"按钮
3. 选择 CSV 或 Excel 文件
4. 系统自动识别文件格式并导入

**CSV 格式要求：**（以单选为例）
- 第一行为表头
- 包含以下列：题目、选项A、选项B、选项C、选项D、正确答案、分值、解析
- 编码格式：UTF-8

**Excel 格式要求：**
- 第一行为表头
- 包含以下列：题目、选项A、选项B、选项C、选项D、正确答案、分值、解析
- 支持 .xlsx 格式

#### 3. 设置测试参数

1. 在"设置测试参数"区域配置各题型的题目数量和分值
2. 为每种题型选择题库
3. 设置测试标题
4. 选择简答题批改方式：
   - **人工批改**：教师手动批改简答题
   - **AI批改**：使用AI自动批改简答题（需先配置AI服务）
5. 选择是否允许学生自选测试内容（勾选之后，学生端测试时可以选择已设定的测试内容）
6. 点击"保存设置"

#### 4. 创建测试预设

1. 在"选择预设"下拉框中选择"创建新预设"
2. 设置预设名称和参数
3. 点击"保存设置"
4. 预设将自动保存，可在下拉框中选择

#### 5. 查看测试统计

1. 点击"测试统计"菜单
2. 查看所有测试记录
3. 点击测试记录查看详细信息
4. 查看学生答题情况和成绩分布

### 学生端使用

#### 1. 开始测试

1. 访问首页
2. 输入姓名和班级号
3. 如果教师端已勾选允许自选内容，可以选择测试内容
4. 点击"开始测试"

#### 2. 答题

1. 系统随机抽取题目
2. 选择题和判断题：点击选项
3. 多选题：可选择多个选项
4. 填空题：在输入框中填写答案
5. 简答题：在文本框中填写答案，可上传图片

#### 3. 提交测试

1. 完成所有题目后点击"提交测试"
2. 系统自动评分（简答题需教师批改）
3. 查看测试结果和正确答案

#### 4. 查看成绩

1. 在学生面板查看测试成绩
2. 查看历史测试记录
3. 查看个人统计信息

## 📁 项目结构

```
学习任务单系统/
├── app.py                  # 主应用程序文件
├── run.py                  # 运行脚本
├── wsgl.py                 # WSGI 入口文件
├── config.py               # 配置文件（包含AI配置）
├── ai_grading_service.py   # AI批改服务
├── requirements.txt        # 项目依赖
├── README.md              # 项目说明文档
├── instance/              # 实例文件夹
│   └── test_system.db     # SQLite 数据库文件
├── templates/             # HTML 模板
│   ├── index.html         # 首页
│   ├── teacher_login.html # 教师登录页
│   ├── teacher_dashboard.html # 教师控制面板
│   ├── student_start.html # 学生开始测试页
│   ├── test.html          # 测试页面
│   ├── test_result.html   # 测试结果页
│   ├── test_statistics.html # 测试统计页
│   └── ...
├── static/                # 静态资源
│   ├── bootstrap/         # Bootstrap 文件
│   ├── bootstrap-icons/   # Bootstrap Icons
│   ├── js/                # JavaScript 文件
│   └── uploads/           # 上传文件目录
├── models/                # 数据模型
│   ├── __init__.py
│   └── user.py
├── models.py              # 数据模型定义
└── 题库/                  # 题库文件目录
    ├── *.csv             # CSV 格式题库
    ├── *.xlsx            # Excel 格式题库
    └── ...
```

## 🔌 API 接口

### 公开 API

#### 获取当前测试设置
```
GET /api/current_test_settings
返回：{"allow_student_choice": true/false}
```

#### 获取测试预设列表
```
GET /api/test_presets_public
返回：[{"id": 1, "title": "预设名称"}, ...]
```

### 教师 API（需要登录）

#### 获取题库列表
```
GET /api/question_banks
返回：题库列表
```

#### 获取题目数量
```
GET /api/question_count/<question_type>
返回：{"count": 10}
```

#### 管理测试预设
```
GET /api/test_presets
DELETE /api/test_presets/<preset_id>
GET /api/test_presets/<preset_id>
```

#### 上传图片
```
POST /api/upload_image
返回：{"url": "/static/uploads/..."}
```

## ⚙️ 配置说明

### AI批改配置（可选）

如果需要使用AI批改简答题功能，需要在 `config.py` 中配置AI服务：

```python
# AI批改配置
AI_GRADING_CONFIG = {
    'enabled': True,  # 是否启用AI批改
    'provider': 'openai',  # AI服务提供商：openai, deepseek 等
    'api_key': 'your-api-key-here',  # API密钥
    'base_url': 'https://api.deepseek.com',  # API基础URL（可选）
    'model': 'deepseek-chat',  # 使用的模型
    'timeout': 30,  # 请求超时时间（秒）
    'max_retries': 2  # 最大重试次数
}
```

**支持的AI服务提供商：**

1. **OpenAI**
   ```python
   AI_GRADING_CONFIG = {
       'enabled': True,
       'provider': 'openai',
       'api_key': 'sk-...',
       'model': 'gpt-3.5-turbo'
   }
   ```

2. **DeepSeek**
   ```python
   AI_GRADING_CONFIG = {
       'enabled': True,
       'provider': 'openai',  # DeepSeek兼容OpenAI API
       'api_key': 'sk-...',
       'base_url': 'https://api.deepseek.com',
       'model': 'deepseek-chat'
   }
   ```

3. **其他兼容OpenAI API的服务**
   ```python
   AI_GRADING_CONFIG = {
       'enabled': True,
       'provider': 'openai',
       'api_key': 'your-api-key',
       'base_url': 'https://your-api-endpoint.com',
       'model': 'your-model-name'
   }
   ```

**配置说明：**
- `enabled`: 是否启用AI批改功能
- `provider`: AI服务提供商标识
- `api_key`: API密钥（必需）
- `base_url`: API基础URL（可选，默认使用OpenAI官方地址）
- `model`: 使用的AI模型名称
- `timeout`: API请求超时时间（秒）
- `max_retries`: 请求失败时的最大重试次数

**注意事项：**
- 如果不配置或配置错误，AI批改选项将自动禁用
- 系统会在教师控制面板自动检测AI配置状态
- AI批改需要消耗API调用额度，请注意成本控制
- 建议先在测试环境验证AI批改效果

### 数据库配置

在 `app.py` 中修改数据库配置：

```python
# SQLite（默认）
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///test_system.db'

# MySQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://user:password@localhost/dbname'

# PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/dbname'
```

### 服务器配置

在 `run.py` 或 `wsgl.py` 中修改服务器配置：

```python
# 修改端口
serve(app, host='0.0.0.0', port=8000)

# 修改绑定地址
serve(app, host='127.0.0.1', port=8000)
```

### 文件上传配置

在 `app.py` 中修改上传配置：

```python
# 允许的图片格式
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

# 最大文件大小（字节）
MAX_IMG_SIZE = 2 * 1024 * 1024  # 2MB
```

## 🔒 安全建议

1. **修改默认密码**：首次登录后立即修改默认密码
2. **使用 HTTPS**：生产环境建议使用 HTTPS
3. **设置强密码**：使用复杂的密码
4. **定期备份**：定期备份数据库文件
5. **限制访问**：使用防火墙限制访问
6. **更新依赖**：定期更新项目依赖包

## 🐛 常见问题

### 1. 数据库初始化失败

**问题**：数据库文件无法创建

**解决**：
- 检查 `instance` 目录是否存在
- 检查文件写入权限
- 手动创建 `instance` 目录

### 2. 导入题库失败

**问题**：CSV 或 Excel 文件导入失败

**解决**：
- 检查文件格式是否正确
- 检查文件编码是否为 UTF-8
- 检查文件列名是否正确
- 检查文件大小是否超过限制

### 3. 图片上传失败

**问题**：学生上传图片失败

**解决**：
- 检查 `static/uploads` 目录是否存在
- 检查文件写入权限
- 检查文件大小是否超过限制
- 检查文件格式是否支持

### 4. 测试提交失败

**问题**：学生提交测试时出错

**解决**：
- 检查数据库连接
- 检查测试配置是否正确
- 检查题库是否有足够的题目
- 查看服务器日志

### 5. 端口被占用

**问题**：启动时提示端口被占用

**解决**：
- 修改 `run.py` 中的端口号
- 关闭占用端口的程序
- 使用其他端口

### 6. AI批改不可用

**问题**：AI批改选项显示为灰色或禁用状态

**解决**：
- 检查 `config.py` 中的 `AI_GRADING_CONFIG` 配置
- 确认 `enabled` 设置为 `True`
- 确认 `api_key` 已正确配置
- 检查 `base_url` 和 `model` 配置是否正确
- 查看服务器日志中的错误信息

### 7. AI批改超时

**问题**：AI批改时出现超时错误

**解决**：
- 增加 `timeout` 配置值（默认30秒）
- 检查网络连接
- 检查API服务是否正常
- 尝试使用其他AI模型

### 8. AI批改结果不准确

**问题**：AI批改的分数或评语不合理

**解决**：
- 检查题目的标准答案是否清晰
- 尝试使用更强大的AI模型
- 考虑使用人工批改进行复核
- 调整题目描述使其更明确

## 📝 更新日志

### v1.1.0 (2025-12-12)
- ✅ 新增简答题AI批改功能
- ✅ 支持OpenAI、DeepSeek等AI服务
- ✅ AI配置状态自动检测
- ✅ 批改方式可选（人工/AI）
- ✅ AI批改超时处理和重试机制
- ✅ 优化教师控制面板布局

### v1.0.0 (2025-08-28)
- ✅ 初始版本发布
- ✅ 支持多种题型（单选、多选、判断、填空、简答）
- ✅ 题库管理功能
- ✅ 测试设置和预设功能
- ✅ 学生自选测试内容功能
- ✅ 测试统计功能
- ✅ 简答题人工批改功能
- ✅ 图片上传功能

## 📧 联系方式

如有问题或建议，请联系项目维护者 QQ:59083992。

## 🙏 致谢

感谢cursor

**注意**：本项目仅供学习和教育使用，请勿用于商业用途。

