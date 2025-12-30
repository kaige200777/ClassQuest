# 简答题显示"错"的问题修复

## 问题描述

学生完成测试后，在测试结果详情页面，简答题后面显示"错"的标记，这是不合理的，因为简答题需要教师人工评分，不应该自动判断对错。

同样，在教师控制面板的人工评分页面，也不应该显示"错"的标记。

## 问题原因

1. **在 `app.py` 的 `test_result` 路由中**：
   - 所有题目的 `is_correct` 初始值都设置为 `False`
   - 简答题没有自动判断对错的逻辑，所以 `is_correct` 保持为 `False`
   - 导致前端显示"错"的徽章

2. **在 `templates/test_result.html` 中**：
   - 所有题目都显示"对"或"错"的徽章
   - 没有针对简答题的特殊处理

## 修复方案

### 1. 修改后端逻辑 (`app.py`)

将简答题的 `is_correct` 设置为 `None`，而不是 `False`，表示"不判断对错"。

**修改前：**
```python
is_correct = False  # 所有题目默认为False
score = 0
comment = None

# ... 其他题型的判断 ...

elif question.question_type == 'short_answer':
    # 从ShortAnswerSubmission表中获取评分和评语
    submission = ShortAnswerSubmission.query.filter_by(
        result_id=result.id,
        question_id=question.id
    ).first()
    if submission:
        score = submission.score
        comment = submission.comment
```

**修改后：**
```python
is_correct = None  # 默认为None，简答题不判断对错
score = 0
comment = None

# ... 其他题型的判断 ...

elif question.question_type == 'short_answer':
    # 简答题不判断对错，保持is_correct为None
    # 从ShortAnswerSubmission表中获取评分和评语
    submission = ShortAnswerSubmission.query.filter_by(
        result_id=result.id,
        question_id=question.id
    ).first()
    if submission:
        score = submission.score
        comment = submission.comment
```

### 2. 修改前端显示 (`templates/test_result.html`)

针对简答题显示"待评分"或"已评分"状态，而不是"对"或"错"。

**修改前：**
```html
<div class="card-header">
    <div class="d-flex justify-content-between align-items-center">
        <span>第{{ loop.index }}题</span>
        <span class="badge {% if question.is_correct %}bg-success{% else %}bg-danger{% endif %}">
            {% if question.is_correct %}对{% else %}错{% endif %}
        </span>
    </div>
</div>
```

**修改后：**
```html
<div class="card-header">
    <div class="d-flex justify-content-between align-items-center">
        <span>第{{ loop.index }}题</span>
        {% if question.question_type == 'short_answer' %}
        <span class="badge bg-secondary">
            {% if question.score is not none %}已评分{% else %}待评分{% endif %}
        </span>
        {% else %}
        <span class="badge {% if question.is_correct %}bg-success{% else %}bg-danger{% endif %}">
            {% if question.is_correct %}对{% else %}错{% endif %}
        </span>
        {% endif %}
    </div>
</div>
```

## 修改效果

### 学生测试结果页面
- **其他题型**：显示绿色"对"或红色"错"徽章
- **简答题**：
  - 未评分时：显示灰色"待评分"徽章
  - 已评分时：显示灰色"已评分"徽章

### 教师评分页面
- 简答题不再显示"错"的标记
- 显示评分状态（待评分/已评分）

## 影响范围

- ✅ 学生查看测试结果时，简答题不再显示"错"
- ✅ 教师查看学生答题详情时，简答题显示评分状态
- ✅ 不影响其他题型的对错判断
- ✅ 向后兼容

## 测试建议

1. 学生完成包含简答题的测试
2. 查看测试结果详情页面
3. 验证简答题显示"待评分"而不是"错"
4. 教师评分后，验证显示"已评分"
5. 验证其他题型仍然正常显示"对"或"错"

## 修复日期

2024-12-03
