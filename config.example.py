"""
应用配置文件模板
复制此文件为 config.py 并填写实际配置
"""
import os

# 服务器配置
HOST = os.environ.get('APP_HOST', '0.0.0.0')
PORT = int(os.environ.get('APP_PORT', 8080))

# 数据库配置
DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///test_system.db')

# 密钥配置（生产环境请使用环境变量设置）
# 生成随机密钥: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-this')

# 调试模式
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# 图片上传配置
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
MAX_IMG_SIZE = 2 * 1024 * 1024  # 2MB

# 时区配置
TIMEZONE_OFFSET = 8  # 北京时间 UTC+8

# AI批改配置
# 请在下方填写您的AI API配置信息
AI_GRADING_CONFIG = {
    # API提供商选择: 'openai', 'azure', 'anthropic', 'qianfan', 'tongyi' 等
    'provider': 'openai',
    
    # API密钥 - 请填写您的API Key
    'api_key': 'your-api-key-here',  # 例如: 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    
    # API基础URL (可选，某些提供商需要)
    'base_url': '',  # 例如: 'https://api.openai.com/v1' 或 'https://api.deepseek.com'
    
    # 模型名称
    'model': 'gpt-3.5-turbo',  # 例如: 'gpt-4', 'deepseek-chat', 'claude-3-sonnet' 等
    
    # 请求超时时间（秒）
    'timeout': 30,
    
    # 最大重试次数
    'max_retries': 3,
    
    # 温度参数（0-1，控制回答的随机性）
    'temperature': 0.3,
    
    # 最大token数
    'max_tokens': 1000,
    
    # 是否启用AI批改（当api_key为空时自动禁用）
    'enabled': False  # 配置好API密钥后改为True
}

# AI批改提示词模板
AI_GRADING_PROMPTS = {
    'system_prompt': """你是一位专业的教师，负责批改学生的简答题答案。请根据以下要求进行评分：

1. 语义理解：理解学生答案的核心意思，不要求字字匹配
2. 要点覆盖度分析：分析学生答案覆盖了哪些关键要点
3. 错误识别：识别明显的错误概念或表述
4. 个性化反馈：提供具体的改进建议和拓展知识

评分规则：
- 每个要点按覆盖程度给分(完全覆盖100%,部分覆盖50%)
- 合理但不在参考答案中的内容，可适当加分
- 错误陈述不扣分，但需要在反馈中指出

请以JSON格式返回结果:
{
    "score": 分数(整数),
    "feedback": "主要得分点:[具体说明] 扣分点：[具体说明] 改进建议：[具体建议] 拓展知识：[相关拓展]"
}""",
    
    'user_prompt_template': """题目：{question}

参考答案：{reference_answer}

题目分值：{max_score}分

学生答案：{student_answer}

请根据上述信息进行评分和反馈。"""
}
