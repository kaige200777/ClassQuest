# 测试内容下拉列表显示逻辑修复

## 问题描述

需要确保测试内容下拉列表的显示逻辑正确：
- 当教师在面板中勾选"允许学生自选测试内容"并保存时，学生端应显示预设下拉列表
- 当教师未勾选"允许学生自选测试内容"时，学生端应隐藏预设下拉列表

## 正确逻辑

测试内容下拉列表的显示应该依赖于当前激活测试的 `allow_student_choice` 设置：

1. **教师勾选"允许学生自选测试内容"**：
   - 保存时，`Test.allow_student_choice` 设置为 `True`
   - API `/api/current_test_settings` 返回 `allow_student_choice: true`
   - 前端显示下拉列表并加载预设

2. **教师未勾选"允许学生自选测试内容"**：
   - 保存时，`Test.allow_student_choice` 设置为 `False`
   - API `/api/current_test_settings` 返回 `allow_student_choice: false`
   - 前端隐藏下拉列表

这样可以让教师完全控制学生是否能自选测试内容。

## 实现细节

### 1. `app.py` - `/api/current_test_settings` 路由

```python
@app.route('/api/current_test_settings')
def get_current_test_settings():
    """获取当前测试设置（公开API，学生可访问）"""
    # 获取当前激活的测试
    current_test = Test.query.filter_by(is_active=True).first()
    if not current_test:
        return jsonify({'allow_student_choice': False})
    
    # 返回当前测试的allow_student_choice设置
    return jsonify({'allow_student_choice': current_test.allow_student_choice})
```

### 2. `app.py` - `/api/test_presets_public` 路由

```python
@app.route('/api/test_presets_public')
def get_test_presets_public():
    """获取可供学生选择的测试预设列表（公开API）"""
    # 检查当前测试是否允许学生自选
    current_test = Test.query.filter_by(is_active=True).first()
    if not current_test or not current_test.allow_student_choice:
        return jsonify({'presets': []})
    
    # 如果允许，返回所有预设
    presets = TestPreset.query.order_by(TestPreset.created_at.desc()).all()
    return jsonify({
        'presets': [{
            'id': preset.id,
            'title': preset.title
        } for preset in presets]
    })
```

### 3. `app.py` - `/save_test_settings` 路由

保存测试设置时，会同时：
1. 保存/更新预设（`TestPreset`）
2. 创建新的活跃测试（`Test`），并设置 `allow_student_choice` 字段
3. 将之前的测试设为非活跃状态

```python
# 创建新的测试配置
test = Test(
    title=title,
    # ... 其他字段 ...
    allow_student_choice=allow_student_choice,  # 从表单获取
    is_active=True
)
```

### 4. 前端逻辑 (`templates/index.html` 和 `templates/student_start.html`)

前端通过两个步骤控制下拉列表的显示：

1. **检查是否允许学生自选**：
```javascript
function checkTestSettings() {
    fetch('/api/current_test_settings')
        .then(response => response.json())
        .then(data => {
            if (data.allow_student_choice) {
                // 显示下拉框并加载预设
                document.getElementById('testContentDiv').style.display = 'block';
                loadTestPresets();
            } else {
                // 隐藏下拉框
                document.getElementById('testContentDiv').style.display = 'none';
            }
        });
}
```

2. **加载预设列表**：
```javascript
function loadTestPresets() {
    fetch('/api/test_presets_public')
        .then(response => response.json())
        .then(data => {
            const select = document.getElementById('test_content');
            select.innerHTML = '<option value="">-- 请选择测试内容 --</option>';
            
            if (data.presets && Array.isArray(data.presets)) {
                data.presets.forEach(preset => {
                    const option = document.createElement('option');
                    option.value = preset.id;
                    option.textContent = preset.title;
                    select.appendChild(option);
                });
            }
        });
}
```

## 测试验证

### 测试步骤

1. **教师端操作**：
   - 登录教师面板
   - 创建一些测试预设
   - 保存测试设置时，勾选"允许学生自选测试内容"
   - 验证设置已保存

2. **学生端验证（允许自选）**：
   - 访问学生登录页面
   - 应该看到"测试内容"下拉列表
   - 下拉列表中应该有可选的预设项

3. **教师端修改**：
   - 返回教师面板
   - 保存测试设置时，取消勾选"允许学生自选测试内容"
   - 验证设置已保存

4. **学生端验证（不允许自选）**：
   - 刷新学生登录页面
   - "测试内容"下拉列表应该被隐藏
   - 学生只能使用默认测试配置

### API 测试

运行测试脚本：
```bash
python test_preset_display.py
```

预期结果：
- 当 `allow_student_choice = True` 时：
  - `/api/current_test_settings` 返回 `{"allow_student_choice": true}`
  - `/api/test_presets_public` 返回预设列表
- 当 `allow_student_choice = False` 时：
  - `/api/current_test_settings` 返回 `{"allow_student_choice": false}`
  - `/api/test_presets_public` 返回空列表 `{"presets": []}`

## 影响范围

- ✅ 教师可以完全控制学生是否能自选测试内容
- ✅ 学生端根据教师设置动态显示/隐藏下拉列表
- ✅ 不影响现有测试流程
- ✅ 向后兼容

## 修复日期

2024-12-03
