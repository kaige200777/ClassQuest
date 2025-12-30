# 题库管理功能修复

## 问题描述

### 用户报告
"重命名失败"

### 问题现象
- 点击题库的"重命名"按钮
- 输入新名称
- 显示"重命名失败"
- 同样，删除功能也无法使用

## 问题分析

### 根本原因
前端调用的 API 端点在后端没有实现：
- 重命名 API：`POST /api/bank/<bank_id>/rename`
- 删除 API：`DELETE /api/bank/<bank_id>`

### 前端代码
```javascript
// 重命名
fetch(`/api/bank/${bankId}/rename`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({name: newName})
})

// 删除
fetch(`/api/bank/${bankId}`, {
    method: 'DELETE'
})
```

### 后端缺失
搜索 `app.py` 发现没有这两个路由的实现。

## 修复方案

### 1. 实现重命名 API

#### 功能需求
- 验证教师权限
- 验证新名称不为空
- 检查题库是否存在
- 检查同类型题库是否已有相同名称
- 更新题库名称
- 返回成功/失败消息

#### 实现代码
```python
@app.route('/api/bank/<int:bank_id>/rename', methods=['POST'])
def rename_bank(bank_id):
    """重命名题库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    try:
        data = request.get_json()
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'message': '题库名称不能为空'}), 400
        
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return jsonify({'success': False, 'message': '题库不存在'}), 404
        
        # 检查同类型题库是否已存在相同名称
        existing = QuestionBank.query.filter_by(
            name=new_name,
            question_type=bank.question_type
        ).filter(QuestionBank.id != bank_id).first()
        
        if existing:
            return jsonify({'success': False, 'message': f'该题型下已存在名为"{new_name}"的题库'}), 400
        
        bank.name = new_name
        db.session.commit()
        
        return jsonify({'success': True, 'message': '重命名成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'重命名失败: {str(e)}'}), 500
```

### 2. 实现删除 API

#### 功能需求
- 验证教师权限
- 检查题库是否存在
- 删除题库（级联删除所有题目）
- 返回成功/失败消息

#### 实现代码
```python
@app.route('/api/bank/<int:bank_id>', methods=['DELETE'])
def delete_bank(bank_id):
    """删除题库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    try:
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return jsonify({'success': False, 'message': '题库不存在'}), 404
        
        # 删除题库（级联删除所有题目）
        db.session.delete(bank)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500
```

### 3. 改进前端错误处理

#### 修复前
```javascript
// 重命名
.then(r => {
    if (r.ok) loadBankList();
    else alert('重命名失败');  // ❌ 没有显示具体错误
});

// 删除
.then(r => {
    if (r.ok) loadBankList();
    else alert('删除失败');  // ❌ 没有显示具体错误
});
```

#### 修复后
```javascript
// 重命名
.then(r => r.json())
.then(data => {
    if (data.success) {
        alert('✅ ' + data.message);  // ✅ 显示成功消息
        loadBankList();
    } else {
        alert('❌ ' + data.message);  // ✅ 显示具体错误
    }
})
.catch(error => {
    alert('❌ 重命名失败: ' + error.message);  // ✅ 显示网络错误
});

// 删除
.then(r => r.json())
.then(data => {
    if (data.success) {
        alert('✅ ' + data.message);  // ✅ 显示成功消息
        loadBankList();
    } else {
        alert('❌ ' + data.message);  // ✅ 显示具体错误
    }
})
.catch(error => {
    alert('❌ 删除失败: ' + error.message);  // ✅ 显示网络错误
});
```

### 4. 改进删除确认提示

#### 修复前
```javascript
if (confirm('确定要删除这个题库吗？'))
```

#### 修复后
```javascript
if (confirm('确定要删除这个题库吗？此操作将删除题库中的所有题目，且无法恢复！'))
```

## 修改文件
- `app.py` - 添加重命名和删除 API
- `templates/teacher_dashboard.html` - 改进错误处理和确认提示

## 功能特性

### 重命名功能
1. **权限验证**：只有教师可以重命名
2. **名称验证**：不能为空
3. **存在性检查**：题库必须存在
4. **唯一性检查**：同类型题库不能有重名
5. **友好提示**：显示具体的成功/失败原因

### 删除功能
1. **权限验证**：只有教师可以删除
2. **存在性检查**：题库必须存在
3. **级联删除**：自动删除题库中的所有题目
4. **二次确认**：明确提示操作不可恢复
5. **友好提示**：显示具体的成功/失败原因

## 测试验证

### 测试重命名功能

#### 测试用例 1：正常重命名
1. 点击题库的"重命名"按钮
2. 输入新名称：`单选题库-修改版`
3. 点击"确定"
4. **预期结果**：
   ```
   ✅ 重命名成功
   ```
5. 题库列表自动更新，显示新名称

#### 测试用例 2：空名称
1. 点击"重命名"按钮
2. 清空输入框
3. 点击"确定"
4. **预期结果**：
   ```
   ❌ 题库名称不能为空
   ```

#### 测试用例 3：重名
1. 已有题库"单选题模板"
2. 尝试将另一个单选题库重命名为"单选题模板"
3. **预期结果**：
   ```
   ❌ 该题型下已存在名为"单选题模板"的题库
   ```

#### 测试用例 4：不同题型可以重名
1. 单选题库名为"基础题库"
2. 将多选题库重命名为"基础题库"
3. **预期结果**：
   ```
   ✅ 重命名成功
   ```
   （不同题型的题库可以同名）

### 测试删除功能

#### 测试用例 1：正常删除
1. 点击题库的"删除"按钮
2. 看到确认提示：
   ```
   确定要删除这个题库吗？此操作将删除题库中的所有题目，且无法恢复！
   ```
3. 点击"确定"
4. **预期结果**：
   ```
   ✅ 删除成功
   ```
5. 题库列表自动更新，该题库消失

#### 测试用例 2：取消删除
1. 点击"删除"按钮
2. 点击"取消"
3. **预期结果**：无操作，题库保持不变

#### 测试用例 3：验证级联删除
1. 创建一个包含 10 道题目的题库
2. 删除该题库
3. 使用数据库查询验证：
   ```bash
   python -c "from app import app, db, Question; app.app_context().push(); print(f'题目数量: {Question.query.count()}')"
   ```
4. **预期结果**：题目数量减少 10

## 安全考虑

### 权限控制
- ✅ 所有操作都需要教师权限
- ✅ 学生无法重命名或删除题库

### 数据完整性
- ✅ 使用事务确保操作原子性
- ✅ 失败时自动回滚
- ✅ 级联删除确保没有孤立数据

### 用户体验
- ✅ 删除前二次确认
- ✅ 明确提示操作不可恢复
- ✅ 显示具体的错误原因

## 边界情况处理

### 情况 1：题库不存在
- 返回 404 错误
- 提示"题库不存在"

### 情况 2：网络错误
- 捕获异常
- 显示网络错误提示

### 情况 3：数据库错误
- 自动回滚事务
- 显示具体错误信息

### 情况 4：并发操作
- 使用数据库事务保证一致性
- 后提交的操作会覆盖先提交的

## 后续改进建议

### 短期
1. ✅ 已实现：基本的重命名和删除功能
2. ✅ 已实现：友好的错误提示

### 中期
1. 添加操作日志（记录谁在什么时候删除了什么）
2. 添加软删除（标记为删除而不是真删除）
3. 添加恢复功能（从回收站恢复）

### 长期
1. 添加题库导出功能
2. 添加题库复制功能
3. 添加题库合并功能
4. 添加批量操作功能

## 相关修复
此修复是题库导入功能系列修复的第五个：
1. **TEMPLATE_IMPORT_FIX.md** - 列名映射修复
2. **FILE_UPLOAD_FIX.md** - 文件扩展名检测修复
3. **IMPORT_UI_FIX.md** - 用户界面修复
4. **BANK_LIST_DISPLAY_FIX.md** - 题库列表显示修复
5. **BANK_MANAGEMENT_FIX.md** - 题库管理功能修复（本文档）

## 总结
通过实现重命名和删除 API，并改进前端错误处理，成功修复了题库管理功能。现在教师可以方便地管理题库，包括重命名和删除操作，并能看到清晰的成功/失败提示。
