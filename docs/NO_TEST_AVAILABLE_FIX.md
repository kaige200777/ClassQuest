# 无可用测试时的提前检查修复

## 问题描述

当教师在面板中删除预设的某个测试后没有保存新的测试内容时：
1. 学生端登录后可以开始某次以前的测试
2. 但提交答案时才显示"当前没有可用的测试或测试已删除"
3. 这导致学生浪费时间答题，体验很差

## 问题原因

原有逻辑中：
- 学生登录时（`student_start` POST）没有检查测试可用性
- 直接重定向到 `test` 路由
- 只有在提交测试时（`submit_test`）才检查测试是否存在

## 解决方案

在学生登录时就检查测试可用性，如果没有可用的测试，立即显示警告信息，阻止学生进入测试页面。

## 实现细节

### 1. 修改 `student_start` 路由 (`app.py`)

在学生提交登录信息后，创建账户前，先检查测试可用性：

```python
@app.route('/student/start', methods=['GET', 'POST'])
def student_start():
    if request.method == 'POST':
        name = request.form.get('name')
        class_number = request.form.get('class_number')
        test_content = request.form.get('test_content')
        
        if not name or not class_number:
            flash('姓名和班级号不能为空')
            return render_template('student_start.html')
        
        # 在创建学生账户前，先检查是否有可用的测试
        if test_content:
            # 学生选择了预设
            preset = TestPreset.query.get(test_content)
            if not preset:
                flash('选择的测试内容不存在，请联系管理员')
                return render_template('student_start.html')
        else:
            # 学生没有选择，检查是否有激活的测试
            current_test = Test.query.filter_by(is_active=True).first()
            if not current_test:
                # 如果没有激活的测试，尝试获取最新的测试
                current_test = Test.query.order_by(Test.created_at.desc()).first()
            
            if not current_test:
                flash('当前没有可用的测试，请联系管理员')
                return render_template('student_start.html')
        
        # 检查通过后，才创建学生账户并进入测试
        username = f"{name}_{class_number}"
        student = User.query.filter_by(username=username, role='student').first()
        if not student:
            student = User(username=username, role='student')
            student.set_password(username)
            db.session.add(student)
            db.session.commit()
        
        session['student_id'] = student.id
        session['student_name'] = name
        session['class_number'] = class_number
        session['role'] = 'student'
        session['selected_preset_id'] = test_content if test_content else None
        
        return redirect(url_for('test'))
    return render_template('student_start.html')
```

### 2. 添加 Flash 消息显示 (`templates/student_start.html`)

在表单上方添加警告消息显示区域：

```html
<div class="card-body">
    {% with messages = get_flashed_messages() %}
        {% if messages %}
            {% for message in messages %}
            <div class="alert alert-warning alert-dismissible fade show" role="alert">
                <strong>⚠️ 提示：</strong> {{ message }}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form method="post">
        <!-- 表单内容 -->
    </form>
</div>
```

### 3. 同样修改首页 (`templates/index.html`)

在首页也添加相同的警告消息显示。

### 4. 保持 `test` 路由的检查

即使在 `student_start` 中已经检查，`test` 路由中仍然保留检查逻辑，作为双重保险：

```python
if not current_test:
    flash('当前没有可用的测试，请联系管理员')
    return redirect(url_for('student_start'))
```

## 用户体验改进

### 修复前

1. 学生输入姓名和班级号
2. 点击"开始测试"
3. 进入测试页面，看到题目
4. 花时间答题
5. 点击"提交测试"
6. **此时才显示错误**："当前没有可用的测试或测试已删除"
7. 学生的答题时间被浪费

### 修复后

1. 学生输入姓名和班级号
2. 点击"开始测试"
3. **立即显示警告**："当前没有可用的测试，请联系管理员"
4. 学生停留在登录页面，等待教师设置测试
5. 不会浪费时间答题

## 测试场景

### 场景1：有可用测试（正常流程）

1. 教师已设置测试
2. 学生登录
3. 成功进入测试页面
4. 完成答题并提交

### 场景2：无可用测试（修复后）

1. 教师删除了所有测试预设
2. 学生尝试登录
3. **立即看到警告**："当前没有可用的测试，请联系管理员"
4. 停留在登录页面
5. 等待教师重新设置测试

### 场景3：预设被删除（修复后）

1. 学生选择了某个预设
2. 但该预设已被教师删除
3. **立即看到警告**："选择的测试内容不存在，请联系管理员"
4. 停留在登录页面

## 优点

1. **提前检查**：在学生开始答题前就发现问题
2. **节省时间**：避免学生浪费时间答无效的题目
3. **清晰提示**：明确告知学生需要联系管理员
4. **双重保险**：在多个环节都有检查，确保安全
5. **用户友好**：警告消息醒目且可关闭

## 注意事项

1. **消息文案统一**：
   - 使用"请联系管理员"而不是"请联系教师"
   - 保持一致的用户体验

2. **不影响正常流程**：
   - 有可用测试时，流程完全不变
   - 只在异常情况下才显示警告

3. **兼容性**：
   - 支持预设选择和默认测试两种模式
   - 都会进行可用性检查

## 修复日期

2024-12-03
