# 启动时AI配置检测功能说明

## 功能概述

在服务启动时自动检测AI批改功能的配置状态，并在控制台输出检测结果。

## 启动输出示例

### 1. AI配置正确且连接测试通过

```
PS D:\python\Test system - trae> python run.py
✓ 数据库表创建成功
✓ 默认教师账户已存在
✓ 数据库初始化完成
正在测试AI API连接 (openai/deepseek-chat)...
✓ AI批改功能已配置并测试通过 (openai/deepseek-chat)

Starting server on http://0.0.0.0:8080
访问地址: http://localhost:8080
按 Ctrl+C 停止服务器

INFO:waitress:Serving on http://0.0.0.0:8080
```

### 2. API key未配置

```
PS D:\python\Test system - trae> python run.py
✓ 数据库表创建成功
✓ 默认教师账户已存在
✓ 数据库初始化完成
✗ AI批改功能未配置: 缺少API密钥
  提示: 请在config.py中正确配置AI_GRADING_CONFIG

Starting server on http://0.0.0.0:8080
访问地址: http://localhost:8080
按 Ctrl+C 停止服务器

INFO:waitress:Serving on http://0.0.0.0:8080
```

### 3. API key无效或已过期

```
PS D:\python\Test system - trae> python run.py
✓ 数据库表创建成功
✓ 默认教师账户已存在
✓ 数据库初始化完成
正在测试AI API连接 (openai/deepseek-chat)...
✗ AI API连接失败: API密钥无效或已过期
  配置: openai/deepseek-chat
  提示: 请检查API密钥是否正确，或网络连接是否正常

Starting server on http://0.0.0.0:8080
访问地址: http://localhost:8080
按 Ctrl+C 停止服务器

INFO:waitress:Serving on http://0.0.0.0:8080
```

### 4. 其他配置错误

```
PS D:\python\Test system - trae> python run.py
✓ 数据库表创建成功
✓ 默认教师账户已存在
✓ 数据库初始化完成
✗ AI批改功能未配置: 未配置模型名称
  提示: 请在config.py中正确配置AI_GRADING_CONFIG

Starting server on http://0.0.0.0:8080
访问地址: http://localhost:8080
按 Ctrl+C 停止服务器

INFO:waitress:Serving on http://0.0.0.0:8080
```

### 5. API连接超时或网络错误

```
PS D:\python\Test system - trae> python run.py
✓ 数据库表创建成功
✓ 默认教师账户已存在
✓ 数据库初始化完成
正在测试AI API连接 (openai/deepseek-chat)...
✗ AI API连接失败: API连接超时
  配置: openai/deepseek-chat
  提示: 请检查API密钥是否正确，或网络连接是否正常

Starting server on http://0.0.0.0:8080
访问地址: http://localhost:8080
按 Ctrl+C 停止服务器

INFO:waitress:Serving on http://0.0.0.0:8080
```

## 检测内容

AI配置检测分为两个阶段：

### 阶段1：配置项检查
验证配置文件中的必要项是否填写：

1. **启用状态** - `enabled` 是否为 `True`
2. **API密钥** - `api_key` 是否已配置且格式正确（长度检查）
3. **提供商** - `provider` 是否已配置
4. **模型名称** - `model` 是否已配置
5. **基础URL** - 某些提供商需要配置 `base_url`

### 阶段2：API连接测试（仅当配置项检查通过）
实际测试API连接是否有效：

1. **发送测试请求** - 向API服务器发送简单的测试请求
2. **验证响应** - 检查API密钥是否有效
3. **错误识别** - 识别常见错误（401无效密钥、403无权限、429超限等）
4. **网络检测** - 检测网络连接问题

## 与教师面板的联动

- **AI配置正确时**：教师控制面板中的"AI批改"单选按钮为可选状态
- **AI配置错误时**：教师控制面板中的"AI批改"单选按钮为禁用状态（灰色）

**注意**：启动时的连接测试失败不会影响教师面板的AI选项可用性。教师面板会在运行时再次检测配置状态。这样设计是为了：
1. 避免因临时网络问题导致功能完全不可用
2. 允许在服务启动后网络恢复时仍能使用AI功能
3. 给用户更灵活的使用体验

## 实现细节

### 代码位置

- **启动检测**：`run.py` 中的 `check_ai_config()` 函数
- **配置验证**：`ai_grading_service.py` 中的 `_check_config()` 方法
- **前端检测**：`templates/teacher_dashboard.html` 中的 `checkAIGradingStatus()` 函数

### 检测流程

```
启动服务
    ↓
初始化数据库
    ↓
检测AI配置
    ↓
输出检测结果
    ↓
启动Web服务器
```

## 配置修复建议

### 配置项错误

如果看到"AI批改功能未配置"提示，请按以下步骤修复：

1. 打开 `config.py` 文件
2. 找到 `AI_GRADING_CONFIG` 配置项
3. 根据错误提示修复相应的配置：
   - 缺少API密钥：填写 `api_key`
   - 未配置提供商：填写 `provider`
   - 未配置模型：填写 `model`
   - 需要base_url：填写 `base_url`
4. 保存文件并重启服务

### API连接错误

如果看到"API连接失败"提示，请检查：

1. **API密钥无效或已过期**
   - 检查API密钥是否正确复制（没有多余空格）
   - 确认API密钥是否已过期
   - 验证API密钥是否有足够的额度
   - 确认API密钥对应的服务商是否正确

2. **API连接超时**
   - 检查网络连接是否正常
   - 确认是否需要代理访问
   - 尝试增加 `timeout` 配置值

3. **无法连接到API服务器**
   - 检查 `base_url` 配置是否正确
   - 确认防火墙是否阻止了连接
   - 验证DNS解析是否正常

4. **API请求频率超限**
   - 等待一段时间后重试
   - 检查是否有其他程序在使用同一API密钥
   - 考虑升级API服务套餐

## 注意事项

1. AI配置检测不会阻止服务启动，即使配置错误也能正常启动
2. 配置错误时，AI批改功能将自动禁用，不影响其他功能
3. 可以在服务运行时修改配置，但需要重启服务才能生效
4. 前端会实时检测AI配置状态，无需刷新页面
