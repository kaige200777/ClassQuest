# 快速推送到 GitHub

## 一键推送命令

### 首次推送

```bash
# 1. 检查 Git 状态
git status

# 2. 添加所有文件
git add .

# 3. 提交
git commit -m "Initial commit: 课堂测试系统 v1.1.0 - 支持AI批改功能"

# 4. 添加远程仓库（替换为你的仓库地址）
git remote add origin https://github.com/你的用户名/classroom-test-system.git

# 5. 推送
git push -u origin main
```

### 后续更新

```bash
# 1. 添加修改
git add .

# 2. 提交
git commit -m "更新说明"

# 3. 推送
git push
```

## 推送前检查清单

- [ ] 已创建 config.example.py 模板
- [ ] config.py 已添加到 .gitignore
- [ ] 数据库文件不会被推送（instance/ 在 .gitignore 中）
- [ ] API 密钥未暴露
- [ ] 虚拟环境不会被推送（venv/ 在 .gitignore 中）
- [ ] 上传文件不会被推送（static/uploads/ 在 .gitignore 中）

## 验证推送

推送后访问你的 GitHub 仓库，确认：
1. config.py 未出现在文件列表中
2. instance/ 目录未出现
3. venv/ 目录未出现
4. config.example.py 存在
5. README.md 正确显示

## 如果推送了敏感信息

立即执行：

```bash
# 1. 从 Git 历史中删除文件
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch config.py" \
  --prune-empty --tag-name-filter cat -- --all

# 2. 强制推送
git push origin --force --all

# 3. 修改所有暴露的密钥和密码
```

## 创建 GitHub 仓库步骤

1. 访问 https://github.com/new
2. 填写信息：
   - Repository name: `classroom-test-system`
   - Description: `课堂测试系统 - 支持多题型、AI批改的在线测试平台`
   - 选择 Public 或 Private
   - 不要勾选 "Initialize this repository with a README"
3. 点击 "Create repository"
4. 复制仓库 URL
5. 执行上面的推送命令

## 完整示例

```bash
# 假设你的 GitHub 用户名是 zhangsan
# 仓库名是 classroom-test-system

# 1. 初始化（如果还没有）
git init

# 2. 添加文件
git add .

# 3. 提交
git commit -m "Initial commit: 课堂测试系统 v1.1.0"

# 4. 添加远程仓库
git remote add origin https://github.com/zhangsan/classroom-test-system.git

# 5. 推送
git push -u origin main

# 完成！访问 https://github.com/zhangsan/classroom-test-system
```

## 常用 Git 命令

```bash
# 查看状态
git status

# 查看修改
git diff

# 查看提交历史
git log --oneline

# 撤销修改
git checkout -- <文件名>

# 查看远程仓库
git remote -v

# 拉取更新
git pull

# 创建分支
git branch <分支名>

# 切换分支
git checkout <分支名>

# 合并分支
git merge <分支名>
```

## 需要帮助？

详细指南请查看：`GITHUB_PUSH_GUIDE.md`
