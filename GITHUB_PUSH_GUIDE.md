# GitHub 推送指南

## 前提条件

1. 已安装 Git
2. 拥有 GitHub 账号
3. 已配置 Git 用户信息

## 步骤一：检查 Git 配置

### 1. 检查 Git 是否已安装
```bash
git --version
```

如果未安装，请访问 https://git-scm.com/downloads 下载安装。

### 2. 配置 Git 用户信息（首次使用）
```bash
git config --global user.name "你的用户名"
git config --global user.email "你的邮箱@example.com"
```

### 3. 验证配置
```bash
git config --global user.name
git config --global user.email
```

## 步骤二：准备推送前的清理

### 1. 检查 .gitignore 文件
确保 `.gitignore` 文件包含以下内容：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/

# 数据库
instance/
*.db
*.sqlite
*.sqlite3

# 配置文件（包含敏感信息）
config.py

# 日志
*.log
logs/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# 操作系统
.DS_Store
Thumbs.db

# 上传文件
static/uploads/*
!static/uploads/.gitkeep

# 临时文件
*.tmp
*.bak
*.backup

# 测试
.pytest_cache/
.coverage
htmlcov/

# 构建
build/
dist/
*.egg-info/
```

### 2. 创建配置文件模板
为了不暴露敏感信息，创建一个配置模板：

```bash
# 复制 config.py 为模板
cp config.py config.example.py
```

然后编辑 `config.example.py`，将敏感信息替换为占位符：

```python
# config.example.py
SECRET_KEY = 'your-secret-key-here'
AI_GRADING_CONFIG = {
    'api_key': 'your-api-key-here',
    # ...
}
```

## 步骤三：初始化 Git 仓库（如果还没有）

### 1. 检查是否已初始化
```bash
git status
```

如果显示 "not a git repository"，则需要初始化：

```bash
git init
```

### 2. 查看当前状态
```bash
git status
```

## 步骤四：添加文件到 Git

### 1. 添加所有文件
```bash
git add .
```

### 2. 查看将要提交的文件
```bash
git status
```

### 3. 如果需要排除某些文件
```bash
# 取消添加某个文件
git reset HEAD <文件名>

# 或者添加到 .gitignore
echo "文件名" >> .gitignore
```

## 步骤五：提交更改

### 1. 提交到本地仓库
```bash
git commit -m "Initial commit: 课堂测试系统 v1.1.0"
```

### 2. 查看提交历史
```bash
git log --oneline
```

## 步骤六：在 GitHub 创建仓库

### 1. 登录 GitHub
访问 https://github.com 并登录

### 2. 创建新仓库
- 点击右上角的 "+" 号
- 选择 "New repository"
- 填写仓库信息：
  - Repository name: `classroom-test-system`（或其他名称）
  - Description: `课堂测试系统 - 支持多题型、AI批改的在线测试平台`
  - 选择 Public 或 Private
  - **不要**勾选 "Initialize this repository with a README"
- 点击 "Create repository"

## 步骤七：连接远程仓库

### 1. 添加远程仓库
```bash
git remote add origin https://github.com/你的用户名/classroom-test-system.git
```

### 2. 验证远程仓库
```bash
git remote -v
```

应该显示：
```
origin  https://github.com/你的用户名/classroom-test-system.git (fetch)
origin  https://github.com/你的用户名/classroom-test-system.git (push)
```

## 步骤八：推送到 GitHub

### 方式一：使用 HTTPS（推荐新手）

#### 1. 推送主分支
```bash
git push -u origin main
```

或者如果分支名是 master：
```bash
git push -u origin master
```

#### 2. 输入 GitHub 凭据
- 用户名：你的 GitHub 用户名
- 密码：使用 Personal Access Token（不是账号密码）

#### 3. 创建 Personal Access Token
如果还没有 Token：
1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token" → "Generate new token (classic)"
3. 设置名称：`classroom-test-system`
4. 选择权限：勾选 `repo`
5. 点击 "Generate token"
6. **复制并保存 Token**（只显示一次）
7. 使用 Token 作为密码推送

### 方式二：使用 SSH（推荐熟练用户）

#### 1. 生成 SSH 密钥（如果还没有）
```bash
ssh-keygen -t ed25519 -C "你的邮箱@example.com"
```

按 Enter 使用默认路径，可以设置密码或留空。

#### 2. 添加 SSH 密钥到 GitHub
```bash
# Windows (PowerShell)
Get-Content ~/.ssh/id_ed25519.pub | clip

# Linux/macOS
cat ~/.ssh/id_ed25519.pub
```

复制输出的内容，然后：
1. 访问 https://github.com/settings/keys
2. 点击 "New SSH key"
3. 粘贴公钥内容
4. 点击 "Add SSH key"

#### 3. 修改远程仓库 URL
```bash
git remote set-url origin git@github.com:你的用户名/classroom-test-system.git
```

#### 4. 推送
```bash
git push -u origin main
```

## 步骤九：验证推送

### 1. 访问 GitHub 仓库
打开浏览器访问：
```
https://github.com/你的用户名/classroom-test-system
```

### 2. 检查文件
确认所有文件都已上传，敏感信息未泄露。

## 步骤十：后续更新

### 1. 修改文件后提交
```bash
# 查看修改
git status

# 添加修改的文件
git add .

# 提交
git commit -m "描述你的修改"

# 推送
git push
```

### 2. 创建标签（版本发布）
```bash
# 创建标签
git tag -a v1.1.0 -m "版本 1.1.0 - 新增AI批改功能"

# 推送标签
git push origin v1.1.0

# 推送所有标签
git push --tags
```

## 常见问题

### 1. 推送被拒绝（rejected）
```bash
# 先拉取远程更改
git pull origin main --rebase

# 再推送
git push
```

### 2. 忘记添加 .gitignore
```bash
# 删除已跟踪的文件（但保留本地文件）
git rm --cached config.py
git rm -r --cached instance/

# 提交更改
git commit -m "Remove sensitive files"
git push
```

### 3. 修改最后一次提交
```bash
# 修改提交信息
git commit --amend -m "新的提交信息"

# 强制推送（谨慎使用）
git push -f
```

### 4. 撤销推送的敏感信息
如果不小心推送了敏感信息：
1. 立即修改密码/密钥
2. 使用 `git filter-branch` 或 BFG Repo-Cleaner 清理历史
3. 强制推送清理后的历史

### 5. 分支名称问题
如果 Git 默认分支是 master 而不是 main：
```bash
# 重命名分支
git branch -M main

# 推送
git push -u origin main
```

## 推荐的 README.md 结构

在 GitHub 上，README.md 会自动显示。确保你的 README.md 包含：

- 项目简介
- 功能特点
- 安装步骤
- 使用说明
- 配置说明
- 截图（可选）
- 技术栈
- 贡献指南
- 许可证
- 联系方式

## 添加 LICENSE 文件

建议添加开源许可证：

```bash
# 创建 LICENSE 文件
# 访问 https://choosealicense.com/ 选择合适的许可证
```

常用许可证：
- MIT License（最宽松）
- Apache License 2.0
- GPL v3（要求衍生作品开源）

## 完整推送命令总结

```bash
# 1. 初始化（如果需要）
git init

# 2. 添加文件
git add .

# 3. 提交
git commit -m "Initial commit: 课堂测试系统 v1.1.0"

# 4. 添加远程仓库
git remote add origin https://github.com/你的用户名/classroom-test-system.git

# 5. 推送
git push -u origin main

# 6. 后续更新
git add .
git commit -m "更新说明"
git push
```

## 安全提示

⚠️ **推送前务必检查：**
1. config.py 已添加到 .gitignore
2. 数据库文件未包含
3. API 密钥未暴露
4. 上传的文件未包含
5. 日志文件未包含

✅ **推送后验证：**
1. 在 GitHub 上检查文件列表
2. 搜索敏感信息（API key、密码等）
3. 确认 .gitignore 生效

## 参考资源

- Git 官方文档: https://git-scm.com/doc
- GitHub 文档: https://docs.github.com
- Git 教程: https://www.liaoxuefeng.com/wiki/896043488029600

---
**最后更新**: 2025-12-12
