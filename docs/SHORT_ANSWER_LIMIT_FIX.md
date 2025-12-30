# 简答题字数和图片限制功能

## 功能描述

为简答题添加以下限制：
1. **字数限制**：答案不超过200个汉字（不包括HTML标签）
2. **图片限制**：如果粘贴了多张图片，只保留最后一张

## 实现细节

### 1. 前端限制 (`templates/test.html`)

#### 添加字数提示和限制
```html
<textarea class="form-control allow-img-paste" 
          name="answer_{{ question.id }}" 
          rows="4" 
          placeholder="请输入答案（可粘贴图片，限200字）" 
          maxlength="200" 
          data-question-id="{{ question.id }}">
</textarea>
<small class="text-muted">已输入 <span id="charCount_{{ question.id }}">0</span>/200 字</small>
```

特点：
- `maxlength="200"` - HTML原生字数限制
- `data-question-id` - 用于JavaScript识别
- 实时显示字数统计

### 2. JavaScript功能 (`static/js/paste_image.js`)

#### 字数统计功能
```javascript
function updateCharCount(textarea) {
    const questionId = textarea.dataset.questionId;
    if (!questionId) return;
    
    // 计算纯文本字数（排除HTML标签）
    const textOnly = textarea.value.replace(/<[^>]*>/g, '');
    const charCount = textOnly.length;
    
    const countSpan = document.getElementById('charCount_' + questionId);
    if (countSpan) {
        countSpan.textContent = charCount;
        
        // 颜色提示
        if (charCount >= 200) {
            countSpan.style.color = 'red';
            countSpan.style.fontWeight = 'bold';
        } else if (charCount >= 180) {
            countSpan.style.color = 'orange';
        } else {
            countSpan.style.color = '';
            countSpan.style.fontWeight = '';
        }
    }
}
```

#### 图片限制功能
```javascript
function insertAtCursor(textarea, text) {
    // 如果是图片标签，先移除所有现有的图片标签（只保留最后一张）
    if (text.includes('<img')) {
        textarea.value = textarea.value.replace(/<img[^>]*>/g, '');
    }
    
    // ... 插入新图片
    
    // 更新字数统计
    updateCharCount(textarea);
}
```

#### 实时监听
```javascript
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('textarea.allow-img-paste').forEach(el => {
        attachImagePaste(el);
        
        // 添加输入事件监听，实时更新字数统计
        el.addEventListener('input', function() {
            updateCharCount(this);
        });
        
        // 初始化字数统计
        updateCharCount(el);
    });
});
```

### 3. 后端验证 (`app.py`)

在 `submit_test` 路由中添加服务器端验证：

```python
elif question.question_type == 'short_answer':
    student_answer = request.form.get(f'answer_{question_id}', '').strip()
    
    # 限制字数：移除HTML标签后不超过200字
    import re
    text_only = re.sub(r'<[^>]*>', '', student_answer)
    if len(text_only) > 200:
        text_only = text_only[:200]
        # 重新组合答案（保留图片但截断文本）
        img_tags = re.findall(r'<img[^>]*>', student_answer)
        if img_tags:
            # 只保留最后一张图片
            student_answer = text_only + img_tags[-1]
        else:
            student_answer = text_only
    else:
        # 限制图片数量：只保留最后一张
        img_tags = re.findall(r'<img[^>]*>', student_answer)
        if len(img_tags) > 1:
            # 移除所有图片，只保留最后一张
            text_without_imgs = re.sub(r'<img[^>]*>', '', student_answer)
            student_answer = text_without_imgs + img_tags[-1]
    
    answers[question_id] = student_answer
```

## 用户体验

### 字数统计显示

1. **正常状态**（0-179字）：
   ```
   已输入 50/200 字  （灰色）
   ```

2. **接近上限**（180-199字）：
   ```
   已输入 185/200 字  （橙色）
   ```

3. **达到上限**（200字）：
   ```
   已输入 200/200 字  （红色加粗）
   ```

### 图片粘贴行为

1. **粘贴第一张图片**：
   - 图片正常插入
   - 显示在答案框中

2. **粘贴第二张图片**：
   - 自动删除第一张图片
   - 只保留第二张图片

3. **粘贴第三张图片**：
   - 自动删除前两张图片
   - 只保留第三张图片

### 字数限制行为

1. **输入文本**：
   - 实时统计字数
   - 达到200字后无法继续输入

2. **粘贴文本**：
   - 如果超过200字，自动截断
   - 保留前200个字符

3. **包含图片的答案**：
   - 只统计纯文本字数
   - 图片标签不计入字数

## 技术细节

### 字数计算规则

- **包含**：所有可见文本字符（汉字、字母、数字、标点）
- **不包含**：HTML标签（如 `<img>`, `<br>` 等）
- **计算方式**：`text.replace(/<[^>]*>/g, '').length`

### 图片处理规则

- **识别**：通过正则表达式 `/<img[^>]*>/g` 识别图片标签
- **保留**：只保留数组中的最后一个元素 `img_tags[-1]`
- **位置**：图片始终添加在文本末尾

### 前后端双重验证

1. **前端验证**：
   - 提供即时反馈
   - 改善用户体验
   - 可被绕过

2. **后端验证**：
   - 确保数据安全
   - 防止恶意提交
   - 最终保障

## 测试场景

### 场景1：正常输入文本
1. 输入50个字
2. 显示"已输入 50/200 字"
3. 可以继续输入

### 场景2：达到字数上限
1. 输入200个字
2. 显示"已输入 200/200 字"（红色）
3. 无法继续输入

### 场景3：粘贴单张图片
1. 粘贴一张图片
2. 图片正常显示
3. 字数统计不变

### 场景4：粘贴多张图片
1. 粘贴第一张图片 → 显示图片1
2. 粘贴第二张图片 → 图片1消失，显示图片2
3. 粘贴第三张图片 → 图片2消失，显示图片3

### 场景5：文本+图片
1. 输入100个字
2. 粘贴一张图片
3. 显示"已输入 100/200 字"
4. 继续输入文本
5. 粘贴第二张图片 → 第一张图片消失

### 场景6：超长文本提交
1. 前端输入200字
2. 通过开发者工具修改为300字
3. 提交后，后端自动截断为200字

## 优点

1. **用户友好**：
   - 实时字数提示
   - 颜色警告
   - 自动限制

2. **数据安全**：
   - 前后端双重验证
   - 防止恶意提交
   - 确保数据一致性

3. **性能优化**：
   - 限制图片数量
   - 减少存储空间
   - 提高加载速度

4. **易于维护**：
   - 代码清晰
   - 逻辑简单
   - 易于调试

## 注意事项

1. **字数计算**：
   - 汉字、字母、数字都算1个字符
   - 不区分全角半角

2. **图片大小**：
   - 仍受上传接口的2MB限制
   - 建议提示用户压缩图片

3. **浏览器兼容性**：
   - 需要支持ES6语法
   - 需要支持正则表达式

## 修复日期

2024-12-03

## 影响范围

- ✅ 简答题输入限制
- ✅ 字数统计显示
- ✅ 图片数量限制
- ✅ 不影响其他题型
