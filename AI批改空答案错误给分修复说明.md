# AI批改空答案错误给分修复说明

## 问题描述
AI评分系统在处理未填写任何答案的情况时，错误地给出了分数，而不是应该的0分。

## 问题原因
在 `ai_grading_service.py` 文件的 `_parse_text_response` 方法中，存在一个逻辑错误：

```python
# 如果没有找到分数，给一个默认分数（满分的60%）
if score == 0:
    score = int(max_score * 0.6)
```

这段代码的意图是处理AI返回文本无法解析的情况，但错误地给出了默认分数（满分的60%），导致即使是空答案也会得分。

## 修复方案
将错误的默认给分逻辑修改为正确的0分处理：

**修复前：**
```python
# 如果没有找到分数，给一个默认分数（满分的60%）
if score == 0:
    score = int(max_score * 0.6)
```

**修复后：**
```python
# 如果没有找到分数，默认为0分
# 注意：不应该给默认分数，未找到分数说明AI评分失败，应该返回0分
```

## 现有的正确逻辑
系统已经有正确的空答案处理逻辑：

1. **完全空答案检查：**
```python
if not student_answer or not student_answer.strip():
    return True, {
        "score": 0,
        "feedback": "未作答，得分为0"
    }
```

2. **填空题空答案检查：**
```python
student_parts = split_answers(student_answer)
if not student_parts:  # 所有空格都为空
    return True, {
        "score": 0,
        "feedback": "所有空格均未填写，得分为0"
    }
```

## 测试验证
创建了测试文件 `test_ai_grading_fix.py` 验证修复效果：

- ✅ 完全空的答案 → 0分
- ✅ 只有空格的答案 → 0分  
- ✅ 填空题空答案 → 0分
- ✅ 填空题只有分隔符的答案 → 0分

## 影响范围
此修复影响所有使用AI批改功能的题目类型：
- 简答题
- 填空题

## 修复时间
2024年12月16日

## 状态
✅ 已修复并测试通过