# 文件上传扩展名检测问题修复

## 问题描述

### 错误信息
```json
{
  "message": "不支持的文件格式: 。仅支持 CSV 和 Excel 文件",
  "success": false
}
```

### 问题原因
当用户上传中文文件名的题库模板（如 `单选题模板.xlsx`）时，系统无法正确识别文件扩展名。

**根本原因**：
1. 代码先使用 `secure_filename()` 处理文件名
2. `secure_filename()` 会移除所有非 ASCII 字符（包括中文）
3. 中文文件名 `单选题模板.xlsx` 被处理成 `xlsx`（只剩扩展名）
4. 然后尝试从 `xlsx` 中提取扩展名，结果为空字符串
5. 空字符串不在允许的扩展名列表中，导致错误

### 问题代码
```python
# 错误的处理顺序
filename = secure_filename(file.filename)  # '单选题模板.xlsx' -> 'xlsx'
file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''  # 'xlsx' -> ''
```

## 修复方案

### 解决思路
在调用 `secure_filename()` 之前先提取文件扩展名，避免中文字符被移除后无法识别扩展名。

### 修复代码
```python
# 正确的处理顺序
# 1. 先从原始文件名获取扩展名
original_filename = file.filename
if '.' not in original_filename:
    return jsonify({'success': False, 'message': '文件名缺少扩展名。请使用 .csv、.xlsx 或 .xls 文件'}), 400

file_ext = original_filename.rsplit('.', 1)[1].lower()

# 2. 验证扩展名
if file_ext not in ['csv', 'xlsx', 'xls']:
    return jsonify({'success': False, 'message': f'不支持的文件格式: {file_ext}。仅支持 CSV 和 Excel 文件'}), 400

# 3. 最后使用 secure_filename 处理（用于日志和显示）
filename = secure_filename(original_filename)
```

## 修改文件
- `app.py` - `import_questions()` 函数（第1027-1038行）

## 测试验证

### 测试用例
| 文件名 | 扩展名检测 | 结果 |
|--------|-----------|------|
| 单选题模板.xlsx | xlsx | ✅ 通过 |
| 多选题模板.xlsx | xlsx | ✅ 通过 |
| 判断题模板.xlsx | xlsx | ✅ 通过 |
| 填空题模板.xlsx | xlsx | ✅ 通过 |
| 简答题模板.xlsx | xlsx | ✅ 通过 |
| test.csv | csv | ✅ 通过 |
| test.xls | xls | ✅ 通过 |
| test | (无) | ❌ 正确拒绝 |
| test.txt | txt | ❌ 正确拒绝 |

### 测试脚本
创建了以下测试脚本：
- `test_file_upload.py` - 测试文件名处理逻辑
- `test_import_fix.py` - 测试完整的导入流程

## 影响范围
✅ 修复了中文文件名的题库导入功能
✅ 保持了对英文文件名的兼容性
✅ 改进了错误提示信息
✅ 不影响其他功能

## 使用说明

### 教师使用
1. 在教师面板点击"导入题库"按钮
2. 选择题库模板文件（支持中文文件名）
3. 系统会自动识别文件类型并导入

### 支持的文件格式
- ✅ CSV 文件 (.csv)
- ✅ Excel 文件 (.xlsx, .xls)
- ✅ 中文文件名
- ✅ 英文文件名

### 不支持的情况
- ❌ 没有扩展名的文件
- ❌ 其他格式的文件（如 .txt, .doc 等）

## 相关问题

### secure_filename() 的作用
`secure_filename()` 是 Werkzeug 提供的安全函数，用于：
- 移除路径分隔符（防止目录遍历攻击）
- 移除非 ASCII 字符（包括中文）
- 规范化文件名

### 为什么不完全移除 secure_filename()？
虽然我们在提取扩展名时不使用它，但仍然保留它用于：
- 日志记录
- 文件名显示
- 安全性考虑（如果将来需要保存文件）

## 后续建议

### 短期
1. ✅ 已修复：在提取扩展名前不使用 secure_filename()
2. ✅ 已改进：提供更清晰的错误提示

### 长期
1. 考虑添加文件内容验证（不仅依赖扩展名）
2. 考虑支持更多文件格式（如 .ods）
3. 添加文件大小限制检查
4. 添加导入预览功能

## 总结
通过调整文件名处理的顺序，成功修复了中文文件名导入失败的问题。修复后的代码能够正确处理各种文件名格式，同时保持了安全性和兼容性。
