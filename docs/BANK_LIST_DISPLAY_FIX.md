# 题库列表显示问题修复

## 问题描述

### 用户报告
导入成功后，题库管理中单选题下方没有正确显示题库名称。

### 问题现象
- 导入提示显示成功：`✅ 成功导入 196 道题目到题库 "单选题模板"`
- 但在题库列表区域看不到题库名称
- 题库实际已经保存到数据库中

## 问题分析

### 数据流程
1. **后端 API** (`/api/question_banks`) 返回：
   ```json
   {
     "success": true,
     "banks": [
       {
         "id": 1,
         "name": "单选题模板",
         "question_type": "single_choice",
         "question_count": 196
       },
       ...
     ]
   }
   ```

2. **前端期望**的数据格式（按题型分组）：
   ```json
   {
     "single_choice": [
       {
         "id": 1,
         "name": "单选题模板",
         "question_count": 196
       }
     ],
     "multiple_choice": [...],
     ...
   }
   ```

3. **问题所在**：
   - `loadBankList()` 直接将 API 响应赋值给 `bankData`
   - `renderBankList()` 尝试访问 `bankData[currentType]`
   - 但 `bankData` 是 `{success: true, banks: [...]}`，没有按题型分组
   - 结果 `bankData[currentType]` 返回 `undefined`
   - 题库列表显示为空

### 根本原因
前端没有将 API 返回的扁平数组转换为按题型分组的对象结构。

## 修复方案

### 解决思路
在 `loadBankList()` 函数中，将 API 返回的题库列表按 `question_type` 字段分组。

### 修复代码

#### 修复前
```javascript
function loadBankList() {
    fetch('/api/question_banks').then(r=>r.json()).then(data => {
        bankData = data;  // ❌ 直接赋值，格式不匹配
        renderBankList();
        updateBankSelects();
    });
}
```

#### 修复后
```javascript
function loadBankList() {
    fetch('/api/question_banks').then(r=>r.json()).then(response => {
        // ✅ 将返回的题库列表按题型分组
        const grouped = {};
        if (response.success && response.banks) {
            response.banks.forEach(bank => {
                if (!grouped[bank.question_type]) {
                    grouped[bank.question_type] = [];
                }
                grouped[bank.question_type].push(bank);
            });
        }
        bankData = grouped;
        renderBankList();
        updateBankSelects();
    });
}
```

### 数据转换示例

**输入**（API 响应）：
```json
{
  "success": true,
  "banks": [
    {"id": 1, "name": "单选题模板", "question_type": "single_choice", "question_count": 196},
    {"id": 2, "name": "多选题模板", "question_type": "multiple_choice", "question_count": 8},
    {"id": 3, "name": "单选题库2", "question_type": "single_choice", "question_count": 50}
  ]
}
```

**输出**（分组后的 `bankData`）：
```json
{
  "single_choice": [
    {"id": 1, "name": "单选题模板", "question_type": "single_choice", "question_count": 196},
    {"id": 3, "name": "单选题库2", "question_type": "single_choice", "question_count": 50}
  ],
  "multiple_choice": [
    {"id": 2, "name": "多选题模板", "question_type": "multiple_choice", "question_count": 8}
  ]
}
```

## 修改文件
- `templates/teacher_dashboard.html` - `loadBankList()` 函数

## 测试验证

### 测试步骤
1. 刷新教师面板页面（Ctrl+F5）
2. 点击"单选题"标签
3. 查看题库列表区域

### 预期结果
✅ 应该能看到：
```
题库列表
┌─────────────────────────────────────┐
│ 单选题模板              [重命名] [删除] │
└─────────────────────────────────────┘
```

### 验证其他题型
1. 点击"多选题"标签 → 应该显示多选题题库
2. 点击"判断题"标签 → 应该显示判断题题库
3. 点击"填空题"标签 → 应该显示填空题题库
4. 点击"简答题"标签 → 应该显示简答题题库

## 相关功能

### 题库列表功能
修复后，以下功能应该正常工作：
- ✅ 显示题库名称
- ✅ 点击题库名称查看题目
- ✅ 重命名题库
- ✅ 删除题库
- ✅ 题库选择下拉列表（在测试配置中）

### 自动刷新
导入成功后，题库列表会自动刷新并显示新导入的题库。

## 边界情况处理

### 情况 1：没有题库
如果某个题型没有题库，显示：
```
暂无题库
```

### 情况 2：API 返回错误
如果 API 返回 `success: false`，`bankData` 将是空对象 `{}`，所有题型都显示"暂无题库"。

### 情况 3：网络错误
如果网络请求失败，题库列表不会更新，保持之前的状态。

## 性能考虑

### 数据量
- 分组操作的时间复杂度：O(n)，其中 n 是题库总数
- 对于典型场景（< 100 个题库），性能影响可忽略不计

### 优化建议
如果题库数量非常大（> 1000），可以考虑：
1. 后端直接返回分组后的数据
2. 使用虚拟滚动显示题库列表
3. 添加分页功能

## 替代方案

### 方案 A：修改后端 API
修改 `/api/question_banks` 返回分组后的数据：
```python
@app.route('/api/question_banks')
def get_question_banks():
    banks = QuestionBank.query.order_by(QuestionBank.created_at.desc()).all()
    grouped = {}
    for bank in banks:
        if bank.question_type not in grouped:
            grouped[bank.question_type] = []
        grouped[bank.question_type].append({
            'id': bank.id,
            'name': bank.name,
            'question_count': len(bank.questions),
            'created_at': to_bj(bank.created_at).strftime('%Y-%m-%d %H:%M:%S')
        })
    return jsonify(grouped)
```

**优点**：
- 前端代码更简单
- 减少前端计算

**缺点**：
- 修改后端 API
- 可能影响其他使用该 API 的地方

### 方案 B：当前方案（前端分组）
**优点**：
- 不修改后端 API
- 向后兼容
- 灵活性高

**缺点**：
- 前端需要额外的数据处理

**选择**：我们选择了方案 B，因为它不需要修改后端，更安全。

## 相关修复
此修复是题库导入功能系列修复的第四个：
1. **TEMPLATE_IMPORT_FIX.md** - 列名映射修复
2. **FILE_UPLOAD_FIX.md** - 文件扩展名检测修复
3. **IMPORT_UI_FIX.md** - 用户界面修复
4. **BANK_LIST_DISPLAY_FIX.md** - 题库列表显示修复（本文档）

## 总结
通过在前端添加数据分组逻辑，成功解决了题库列表不显示的问题。现在导入成功后，用户可以立即在题库列表中看到新导入的题库。
