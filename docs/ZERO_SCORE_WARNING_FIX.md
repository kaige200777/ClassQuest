# 零分警告功能添加

## 问题背景

在测试结果中发现，学生答对了多选题（答案 ABD，正确答案也是 ABD），但得分为 0。

经过调试发现：
- 评分逻辑正确
- 答案判断正确
- 问题根源：**教师在设置测试时，将多选题的每题分数设置为了 0**

这导致学生答对了题目，但因为该题型分数为 0，所以不得分。

## 解决方案

添加警告功能，在教师保存测试设置时，如果某个题型有题目但分数为 0，给出警告提示。

## 实现细节

### 1. 后端验证 (`app.py` - `save_test_settings` 路由)

在验证逻辑后添加分数检查：

```python
# 检查分数设置警告
warnings = []
if single_choice_count > 0 and single_choice_score == 0:
    warnings.append('单选题：题目数量大于0，但每题分数为0')
if multiple_choice_count > 0 and multiple_choice_score == 0:
    warnings.append('多选题：题目数量大于0，但每题分数为0')
if true_false_count > 0 and true_false_score == 0:
    warnings.append('判断题：题目数量大于0，但每题分数为0')
if fill_blank_count > 0 and fill_blank_score == 0:
    warnings.append('填空题：题目数量大于0，但每题分数为0')
if short_answer_count > 0 and short_answer_score == 0:
    warnings.append('简答题：题目数量大于0，但每题分数为0')
```

在返回响应时包含警告信息：

```python
response_data = {
    'success': True,
    'message': message,
    'preset_id': preset.id,
    'total_score': total_score
}

# 如果有警告，添加到响应中
if warnings:
    response_data['warnings'] = warnings

return jsonify(response_data)
```

### 2. 前端显示 (`templates/teacher_dashboard.html`)

修改表单提交成功后的处理逻辑：

```javascript
.then(data => {
    if (data.success) {
        let successMsg = '✅ ' + data.message + '\n\n总分: ' + data.total_score;
        
        // 如果有警告信息，显示出来
        if (data.warnings && data.warnings.length > 0) {
            successMsg += '\n\n⚠️ 警告：\n' + data.warnings.join('\n');
            successMsg += '\n\n建议：请检查分数设置，确保每个题型的分数大于0';
        }
        
        alert(successMsg);
        loadPresets();
    }
})
```

## 使用场景

### 场景1：正常设置（无警告）

教师设置：
- 单选题：10道，每题4分
- 多选题：5道，每题5分
- 判断题：10道，每题3分

保存后显示：
```
✅ 预设 "期末考试" 保存成功

总分: 115
```

### 场景2：分数设置为0（有警告）

教师设置：
- 单选题：10道，每题4分
- 多选题：5道，每题0分  ← 问题
- 判断题：10道，每题3分

保存后显示：
```
✅ 预设 "期末考试" 保存成功

总分: 70

⚠️ 警告：
多选题：题目数量大于0，但每题分数为0

建议：请检查分数设置，确保每个题型的分数大于0
```

## 优点

1. **及时提醒**：在保存设置时立即发现问题
2. **不阻止保存**：警告不会阻止保存，给教师灵活性
3. **清晰明确**：明确指出哪个题型有问题
4. **用户友好**：提供建议，帮助教师修正

## 注意事项

1. **这是警告，不是错误**：
   - 系统仍然允许保存分数为 0 的设置
   - 某些情况下，教师可能确实想设置分数为 0（如练习模式）

2. **不影响现有数据**：
   - 已经提交的测试结果不会被修改
   - 只影响新保存的测试设置

3. **建议教师操作**：
   - 如果看到警告，检查分数设置
   - 如果是误设置，重新保存正确的分数
   - 如果是有意为之，可以忽略警告

## 测试验证

1. **测试警告功能**：
   - 登录教师面板
   - 设置测试时，将某个题型的分数设为 0
   - 保存后应该看到警告信息

2. **测试正常流程**：
   - 设置所有题型的分数都大于 0
   - 保存后不应该看到警告

## 修复日期

2024-12-03
