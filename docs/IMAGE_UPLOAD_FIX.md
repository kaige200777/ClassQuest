# 图片上传功能修复

## 问题描述

### 用户报告
"编辑题目时显示图片上传异常"

### 问题现象
- 在题目编辑框中粘贴图片
- 显示"图片上传异常"错误
- 图片无法插入到题目中

## 问题分析

### 前端实现
前端已经实现了图片粘贴功能（`static/js/paste_image.js`）：
1. 监听 textarea 的 paste 事件
2. 检测剪贴板中的图片
3. 上传图片到 `/api/upload_image`
4. 将返回的 URL 插入到文本框中

### 后端缺失
搜索 `app.py` 发现 `/api/upload_image` API 没有实现。

## 修复方案

### 实现图片上传 API

#### 功能需求
1. 验证教师权限
2. 验证文件类型（只允许图片格式）
3. 验证文件大小（限制 2MB）
4. 生成唯一文件名
5. 保存文件到 `static/uploads` 目录
6. 返回图片 URL

#### 实现代码
```python
@app.route('/api/upload_image', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    try:
        # 检查文件类型
        if '.' not in file.filename:
            return jsonify({'success': False, 'message': '文件名无效'}), 400
        
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        if file_ext not in ALLOWED_IMG_EXT:
            return jsonify({'success': False, 'message': f'不支持的图片格式: {file_ext}'}), 400
        
        # 检查文件大小
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_IMG_SIZE:
            return jsonify({'success': False, 'message': f'图片大小超过限制（最大 {MAX_IMG_SIZE // 1024 // 1024}MB）'}), 400
        
        # 生成唯一文件名
        filename = f"{uuid.uuid4().hex}.{file_ext}"
        
        # 确保上传目录存在
        upload_dir = os.path.join('static', 'uploads')
        os.makedirs(upload_dir, exist_ok=True)
        
        # 保存文件
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)
        
        # 返回URL
        url = f"/static/uploads/{filename}"
        return jsonify({'success': True, 'url': url})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500
```

### 配置常量
在 `app.py` 顶部已经定义了相关常量：
```python
# 允许的扩展名
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
# 限制大小（字节）2MB
MAX_IMG_SIZE = 2 * 1024 * 1024
```

## 修改文件
- `app.py` - 添加图片上传 API

## 功能特性

### 图片上传
1. **权限验证**：只有教师可以上传
2. **格式验证**：支持 png, jpg, jpeg, gif, bmp, webp
3. **大小限制**：最大 2MB
4. **唯一文件名**：使用 UUID 避免冲突
5. **自动创建目录**：确保上传目录存在
6. **返回 URL**：返回可访问的图片 URL

### 图片粘贴
1. **监听粘贴事件**：自动检测剪贴板中的图片
2. **自动上传**：粘贴后自动上传到服务器
3. **插入标签**：上传成功后插入 `<img>` 标签
4. **错误提示**：上传失败时显示友好提示

## 使用流程

### 在题目中插入图片
1. 打开题库编辑页面
2. 点击"编辑"或"添加题目"
3. 在题目内容输入框中：
   - 方法1：复制图片，然后粘贴（Ctrl+V）
   - 方法2：截图后直接粘贴
4. 图片自动上传并插入
5. 保存题目

### 支持的场景
- ✅ 题目内容中插入图片
- ✅ 选项中插入图片
- ✅ 解析中插入图片
- ✅ 支持多张图片

## 测试验证

### 测试用例 1：正常上传
1. 复制一张图片（< 2MB）
2. 在题目输入框中粘贴
3. **预期结果**：
   - 图片自动上传
   - 输入框中插入 `<img src="/static/uploads/xxx.png"/>`
   - 保存后可以正常显示

### 测试用例 2：文件过大
1. 复制一张大图片（> 2MB）
2. 粘贴到输入框
3. **预期结果**：
   - 显示"图片大小超过限制（最大 2MB）"
   - 图片未插入

### 测试用例 3：不支持的格式
1. 尝试上传非图片文件
2. **预期结果**：
   - 显示"不支持的图片格式"
   - 文件未上传

### 测试用例 4：权限验证
1. 未登录或学生身份
2. 尝试上传图片
3. **预期结果**：
   - 返回 403 未授权错误

## 安全考虑

### 文件类型验证
- ✅ 只允许图片格式
- ✅ 检查文件扩展名
- ✅ 防止上传可执行文件

### 文件大小限制
- ✅ 限制最大 2MB
- ✅ 防止磁盘空间耗尽
- ✅ 提高上传速度

### 文件名安全
- ✅ 使用 UUID 生成唯一文件名
- ✅ 避免文件名冲突
- ✅ 防止路径遍历攻击

### 权限控制
- ✅ 只有教师可以上传
- ✅ 学生无法上传图片

## 存储管理

### 上传目录
- 位置：`static/uploads/`
- 自动创建：如果目录不存在会自动创建
- 访问方式：通过 `/static/uploads/filename` 访问

### 文件命名
- 格式：`{uuid}.{ext}`
- 示例：`a1b2c3d4e5f6.png`
- 优点：唯一、安全、无冲突

### 清理建议
1. 定期清理未使用的图片
2. 实现图片引用计数
3. 删除题目时同时删除关联图片

## 已知限制

### 当前实现
1. **无图片管理**：没有图片列表和管理界面
2. **无引用追踪**：不知道哪些图片被哪些题目使用
3. **无自动清理**：删除题目时不会删除图片
4. **无压缩**：不会自动压缩大图片

### 未来改进
1. 添加图片管理界面
2. 实现图片引用追踪
3. 删除题目时清理关联图片
4. 自动压缩大图片
5. 支持图片裁剪和编辑
6. 添加图片预览功能

## 相关修复
此修复是题库导入功能系列修复的第七个：
1. **TEMPLATE_IMPORT_FIX.md** - 列名映射修复
2. **FILE_UPLOAD_FIX.md** - 文件扩展名检测修复
3. **IMPORT_UI_FIX.md** - 用户界面修复
4. **BANK_LIST_DISPLAY_FIX.md** - 题库列表显示修复
5. **BANK_MANAGEMENT_FIX.md** - 题库管理功能修复
6. **BANK_EDIT_FIX.md** - 题库编辑功能修复
7. **IMAGE_UPLOAD_FIX.md** - 图片上传功能修复（本文档）

## 总结
通过实现图片上传 API，成功修复了题目编辑时的图片上传功能。现在教师可以通过粘贴的方式在题目中插入图片，支持多种图片格式，并有完善的安全验证机制。
