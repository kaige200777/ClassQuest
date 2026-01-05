"""
测试填空题分隔符处理
"""

def split_answers(text):
    """分割答案，支持顿号和逗号"""
    # 先统一替换为顿号
    text = text.replace(',', '、')
    return [f.strip().lower() for f in text.split('、') if f.strip()]

# 测试用例
test_cases = [
    # (学生答案, 正确答案, 期望结果)
    ('114、3.5、-3', '114,3.5,-3', True),
    ('114、 3.5、 -3', '114,3.5,-3', True),  # 有空格
    ('114 、 3.5 、 -3', '114,3.5,-3', True),  # 空格在顿号前后
    ('True、False、True、True', 'True,False,True,True', True),
    ('True、 False、 True、 True', 'True,False,True,True', True),  # 有空格
]

print("=" * 60)
print("填空题分隔符处理测试")
print("=" * 60)
print()

for student, correct, expected in test_cases:
    student_list = split_answers(student)
    correct_list = split_answers(correct)
    
    is_match = student_list == correct_list
    status = "✓" if is_match == expected else "✗"
    
    print(f"{status} 学生答案: {student}")
    print(f"  正确答案: {correct}")
    print(f"  学生列表: {student_list}")
    print(f"  正确列表: {correct_list}")
    print(f"  匹配结果: {is_match} (期望: {expected})")
    print()

print("=" * 60)
