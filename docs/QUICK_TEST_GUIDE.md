# 快速测试指南 - 题库导入功能

## 测试目的
验证题库导入功能是否能正确处理中文文件名

## 测试步骤

### 1. 启动应用
```bash
python run.py
```

### 2. 登录教师账户
- 访问：http://localhost:5000/teacher/login
- 用户名：admin
- 密码：admin

### 3. 测试导入功能

#### 测试用例 1：单选题模板
1. 在教师面板，点击"单选题"标签
2. 点击"导入题库"按钮
3. 选择文件：`题库/单选题模板.xlsx`
4. **预期结果**：✅ 成功导入 196 道题目

#### 测试用例 2：多选题模板
1. 点击"多选题"标签
2. 点击"导入题库"按钮
3. 选择文件：`题库/多选题模板.xlsx`
4. **预期结果**：✅ 成功导入 8 道题目

#### 测试用例 3：判断题模板
1. 点击"判断题"标签
2. 点击"导入题库"按钮
3. 选择文件：`题库/判断题模板.xlsx`
4. **预期结果**：✅ 成功导入 114 道题目

#### 测试用例 4：填空题模板
1. 点击"填空题"标签
2. 点击"导入题库"按钮
3. 选择文件：`题库/填空题模板.xlsx`
4. **预期结果**：✅ 成功导入 5 道题目

#### 测试用例 5：简答题模板
1. 点击"简答题"标签
2. 点击"导入题库"按钮
3. 选择文件：`题库/简答题模板.xlsx`
4. **预期结果**：✅ 成功导入 1 道题目

## 成功标志

### 导入成功的提示
- 页面顶部显示绿色成功消息
- 消息内容类似：`成功导入 X 道题目到题库 "XXX"`
- 题库列表中出现新的题库

### 导入失败的提示（修复前）
- 页面顶部显示红色错误消息
- 消息内容：`不支持的文件格式: 。仅支持 CSV 和 Excel 文件`

## 验证导入结果

### 方法 1：查看题库列表
1. 在对应题型标签下
2. 查看"题库列表"区域
3. 应该能看到新导入的题库

### 方法 2：查看题库内容
1. 点击题库名称
2. 查看题目列表
3. 验证题目数量和内容

### 方法 3：使用数据库查询
```bash
python -c "from app import app, db, QuestionBank, Question; app.app_context().push(); print(f'题库数量: {QuestionBank.query.count()}'); print(f'题目数量: {Question.query.count()}')"
```

## 常见问题

### Q1: 导入后没有反应
**可能原因**：
- 文件格式不正确
- 文件内容为空
- 列名不匹配

**解决方法**：
- 检查浏览器控制台的错误信息
- 确认使用的是标准模板文件
- 查看服务器日志

### Q2: 导入部分成功
**可能原因**：
- 某些行的数据格式不正确
- 必填字段为空

**解决方法**：
- 查看导入结果消息中的错误详情
- 修正数据后重新导入

### Q3: 中文乱码
**可能原因**：
- CSV 文件编码不是 UTF-8 或 GBK

**解决方法**：
- 使用 Excel 文件（.xlsx）
- 或确保 CSV 文件使用 UTF-8 编码

## 自动化测试

### 运行单元测试
```bash
python -m pytest tests/test_import.py -v
```

### 运行验证脚本
```bash
# 验证模板文件
python test_template_import.py

# 验证文件名处理
python test_file_upload.py

# 验证完整导入流程
python test_import_fix.py
```

## 回滚方案

如果修复后出现问题，可以回滚到之前的版本：

```bash
git checkout HEAD~1 app.py
```

## 技术细节

### 修复的代码位置
- 文件：`app.py`
- 函数：`import_questions()`
- 行号：约 1027-1038

### 关键改动
```python
# 修复前
filename = secure_filename(file.filename)
file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

# 修复后
original_filename = file.filename
file_ext = original_filename.rsplit('.', 1)[1].lower()
filename = secure_filename(original_filename)
```

## 联系支持

如果遇到问题，请提供：
1. 错误消息截图
2. 浏览器控制台日志
3. 服务器日志
4. 使用的文件名和文件大小
