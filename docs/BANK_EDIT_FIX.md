# 题库编辑功能修复

## 问题描述

### 用户报告
"单击题库名称时无法打开题库进行题目的编辑"

### 问题现象
- 点击题库名称链接
- 浏览器显示 404 错误
- 无法查看或编辑题库中的题目

## 问题分析

### 前端链接
题库列表中的链接指向：
```html
<a href="/teacher/bank/${bank.id}" target="_blank">${bank.name}</a>
```

### 后端缺失
搜索 `app.py` 发现以下路由和 API 都没有实现：
1. `GET /teacher/bank/<bank_id>` - 题库详情页面
2. `GET /api/question_bank/<bank_id>/questions` - 获取题库内容
3. `POST /api/question_bank/<bank_id>/questions` - 保存题库内容

### 模板文件
虽然模板文件 `templates/teacher_bank.html` 已经存在，但缺少对应的路由。

## 修复方案

### 1. 实现题库详情页面路由

#### 功能需求
- 验证教师权限
- 检查题库是否存在
- 渲染题库编辑页面

#### 实现代码
```python
@app.route('/teacher/bank/<int:bank_id>')
def teacher_bank(bank_id):
    """题库详情页面 - 查看和编辑题库中的题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    bank = QuestionBank.query.get_or_404(bank_id)
    return render_template('teacher_bank.html', bank_id=bank_id)
```

### 2. 实现题库内容管理 API

#### 功能需求
- **GET 请求**：获取题库中的所有题目
- **POST 请求**：更新题库中的所有题目
- 验证教师权限
- 检查题库是否存在
- 支持批量更新

#### 实现代码
```python
@app.route('/api/question_bank/<int:bank_id>/questions', methods=['GET', 'POST'])
def manage_bank_questions(bank_id):
    """获取或更新题库中的题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        return jsonify({'success': False, 'message': '题库不存在'}), 404
    
    if request.method == 'GET':
        # 获取题库内容
        questions = Question.query.filter_by(bank_id=bank_id).order_by(Question.id).all()
        return jsonify({
            'success': True,
            'bank_id': bank.id,
            'bank_name': bank.name,
            'question_type': bank.question_type,
            'questions': [{
                'id': q.id,
                'content': q.content,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'option_e': q.option_e,
                'correct_answer': q.correct_answer,
                'score': q.score,
                'explanation': q.explanation,
                'image_path': q.image_path
            } for q in questions]
        })
    
    else:  # POST - 更新题库内容
        try:
            data = request.get_json()
            questions_data = data.get('questions', [])
            
            # 删除现有题目
            Question.query.filter_by(bank_id=bank_id).delete()
            
            # 添加新题目
            for q_data in questions_data:
                # 跳过空题目
                if not q_data.get('content', '').strip():
                    continue
                
                question = Question(
                    question_type=bank.question_type,
                    content=q_data.get('content', '').strip(),
                    option_a=q_data.get('option_a', '').strip() if q_data.get('option_a') else None,
                    option_b=q_data.get('option_b', '').strip() if q_data.get('option_b') else None,
                    option_c=q_data.get('option_c', '').strip() if q_data.get('option_c') else None,
                    option_d=q_data.get('option_d', '').strip() if q_data.get('option_d') else None,
                    option_e=q_data.get('option_e', '').strip() if q_data.get('option_e') else None,
                    correct_answer=q_data.get('correct_answer', '').strip(),
                    score=int(q_data.get('score', 0)) if q_data.get('score') else 0,
                    explanation=q_data.get('explanation', '').strip() if q_data.get('explanation') else None,
                    bank_id=bank_id
                )
                db.session.add(question)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': '保存成功'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500
```

## 修改文件
- `app.py` - 添加题库详情页面路由和内容管理 API

## 功能特性

### 题库编辑页面
1. **权限验证**：只有教师可以访问
2. **题库验证**：题库必须存在（404 错误）
3. **新窗口打开**：使用 `target="_blank"`，不影响主页面
4. **响应式表格**：支持不同题型的字段显示

### 获取题库内容（GET）
1. **完整数据**：返回题库信息和所有题目
2. **有序排列**：按题目 ID 排序
3. **字段完整**：包含所有题目字段

### 保存题库内容（POST）
1. **批量更新**：一次性更新所有题目
2. **删除重建**：先删除旧题目，再添加新题目
3. **空题目过滤**：自动跳过内容为空的题目
4. **事务保证**：失败时自动回滚
5. **友好提示**：显示成功/失败消息

## 使用流程

### 查看和编辑题库
1. 在教师面板，点击题库名称
2. 新窗口打开题库编辑页面
3. 页面显示题库中的所有题目
4. 可以编辑题目内容、选项、答案、分值、解析
5. 点击"保存修改"按钮
6. 看到提示：`保存成功` 或 `保存失败: 原因`

### 支持的题型
- ✅ 单选题：题干、选项A/B/C/D、答案、分值、解析
- ✅ 多选题：题干、选项A/B/C/D/E、答案、分值、解析
- ✅ 判断题：题干、答案、分值、解析
- ✅ 填空题：题干、答案、分值、解析
- ✅ 简答题：题干、答案、分值、解析

## 测试验证

### 测试用例 1：查看题库
1. 点击题库名称"单选题模板"
2. **预期结果**：
   - 新窗口打开
   - 显示题库标题："单选题模板（单选题）"
   - 显示表格，包含所有题目
   - 每道题目显示完整信息

### 测试用例 2：编辑题目
1. 打开题库编辑页面
2. 修改第一道题的题干
3. 点击"保存修改"
4. **预期结果**：
   - 显示"保存成功"
   - 刷新页面，修改已保存

### 测试用例 3：添加题目
1. 打开题库编辑页面
2. 在表格末尾添加新行（需要修改模板支持）
3. 填写新题目信息
4. 点击"保存修改"
5. **预期结果**：
   - 显示"保存成功"
   - 新题目已添加

### 测试用例 4：删除题目
1. 打开题库编辑页面
2. 清空某道题的题干
3. 点击"保存修改"
4. **预期结果**：
   - 显示"保存成功"
   - 该题目被删除（因为题干为空）

### 测试用例 5：权限验证
1. 未登录或学生身份
2. 尝试访问 `/teacher/bank/1`
3. **预期结果**：
   - 重定向到教师登录页面

## 安全考虑

### 权限控制
- ✅ 所有操作都需要教师权限
- ✅ 学生无法访问题库编辑页面
- ✅ 未登录用户被重定向到登录页面

### 数据验证
- ✅ 验证题库是否存在
- ✅ 过滤空题目
- ✅ 验证数据类型（分值必须是整数）

### 事务安全
- ✅ 使用数据库事务
- ✅ 失败时自动回滚
- ✅ 避免部分更新导致的数据不一致

## 已知限制

### 当前实现
1. **批量更新**：保存时会删除所有旧题目，再添加新题目
   - 优点：实现简单，不会有遗留数据
   - 缺点：题目 ID 会改变

2. **无增量更新**：不支持只更新修改的题目
   - 影响：每次保存都会重建所有题目

3. **无添加/删除按钮**：模板中没有动态添加/删除行的功能
   - 解决方法：可以通过清空题干来删除题目

### 未来改进
1. 实现增量更新（只更新修改的题目）
2. 添加"添加题目"按钮
3. 添加"删除题目"按钮
4. 添加题目排序功能
5. 添加批量导入/导出功能

## 相关修复
此修复是题库导入功能系列修复的第六个：
1. **TEMPLATE_IMPORT_FIX.md** - 列名映射修复
2. **FILE_UPLOAD_FIX.md** - 文件扩展名检测修复
3. **IMPORT_UI_FIX.md** - 用户界面修复
4. **BANK_LIST_DISPLAY_FIX.md** - 题库列表显示修复
5. **BANK_MANAGEMENT_FIX.md** - 题库管理功能修复
6. **BANK_EDIT_FIX.md** - 题库编辑功能修复（本文档）

## 更新：使用正确的模板

### 发现
实际的编辑页面使用的是 `bank_content.html` 模板，而不是 `teacher_bank.html`。

### 额外实现的 API
为了支持 `bank_content.html` 模板，还需要实现以下 API：

1. **GET /api/question/<question_id>** - 获取单个题目详情
2. **POST /api/question/<question_id>** - 创建或更新题目
3. **DELETE /api/question/<question_id>** - 删除题目

### 更新后的路由
```python
@app.route('/teacher/bank/<int:bank_id>')
def teacher_bank(bank_id):
    """题库详情页面 - 查看和编辑题库中的题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    bank = QuestionBank.query.get_or_404(bank_id)
    questions = Question.query.filter_by(bank_id=bank_id).order_by(Question.id).all()
    
    # 添加题型显示名称
    type_display_map = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'true_false': '判断题',
        'fill_blank': '填空题',
        'short_answer': '简答题'
    }
    bank.question_type_display = type_display_map.get(bank.question_type, bank.question_type)
    
    return render_template('bank_content.html', bank=bank, questions=questions)
```

### 题目管理 API
```python
@app.route('/api/question/<question_id>', methods=['GET', 'POST', 'DELETE'])
def manage_question(question_id):
    """获取、更新或删除单个题目"""
    # GET: 获取题目详情
    # POST: 创建或更新题目（question_id='new' 表示创建）
    # DELETE: 删除题目
```

### 功能特性
- ✅ 查看题库中的所有题目（表格形式）
- ✅ 添加新题目（弹窗表单）
- ✅ 编辑题目（弹窗表单）
- ✅ 删除题目（确认后删除）
- ✅ 导出题库（如果实现了导出功能）
- ✅ 返回教师面板

## 总结
通过实现题库详情页面路由和完整的题目管理 API，成功修复了题库编辑功能。现在教师可以点击题库名称查看和编辑题库中的所有题目，支持添加、编辑、删除操作，实现了完整的题库管理功能。
