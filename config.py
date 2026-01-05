"""
应用配置文件
"""
import os

# 服务器配置
HOST = os.environ.get('APP_HOST', '0.0.0.0')
PORT = int(os.environ.get('APP_PORT', 8080))

# 数据库配置
DATABASE_URI = os.environ.get('DATABASE_URI', 'sqlite:///test_system.db')

# 密钥配置（生产环境请使用环境变量设置）
SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key')

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
    'api_key': 'sk-e8de4f86a5b54ed7a17f338e1db658db',  # 例如: 'sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
    
    # API基础URL (可选，某些提供商需要)f338e1db658db
    'base_url': 'https://api.deepseek.com',  # 例如: 'https://api.openai.com/v1' 或自定义代理地址
    
    # 模型名称
    'model': 'deepseek-chat',  # 例如: 'gpt-4', 'claude-3-sonnet', 'qianfan-chinese-llama-2-7b' 等
    
    # 请求超时时间（秒）
    'timeout': 30,
    
    # 最大重试次数
    'max_retries': 3,
    
    # 温度参数（0-1，控制回答的随机性）
    'temperature': 0.3,
    
    # 最大token数
    'max_tokens': 1000,
    
    # 是否启用AI批改（当api_key为空时自动禁用）
    'enabled': True  # 当api_key配置正确后，请改为True
}

# AI批改提示词模板
AI_GRADING_PROMPTS = {
    # 简答题批改提示词
    'short_answer': {
        'system_prompt': """你是一位专业的教师，负责批改学生的简答题答案。请根据以下流程和要求进行评分：
一、批改流程
如果有参考答案，先以参考答案为准，分析学生答案的得分情况；
如果没有参考答案，则仔细阅读题目，基于你的专业知识和对题目意图的理解，自行判断关键要点并评分。
二、评分规则
要点覆盖度评分：识别每个关键要点，按学生答案的覆盖程度打分
完全覆盖：100%
部分覆盖或表述模糊：50%
未覆盖：0%
合理额外内容：若学生写出合理但参考答案中未提到的内容，可适当加分（不超过该要点对应分值）
错误陈述：不扣分，须在反馈中指出并纠正
三、批改维度
语义理解：理解学生答案的核心意思，不要求字字匹配
要点覆盖度分析：逐条分析覆盖了哪些关键要点，并给出覆盖程度判断
错误识别：指出明显的概念错误或表述不当之处
个性化反馈：
针对错误或不足提供具体改进建议
可适当补充相关拓展知识，帮助学生深化理解

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
    },
    
    # 填空题批改提示词
    'fill_blank': {
        'system_prompt': """你是一位专业的教师，负责批改学生的填空题答案。请根据以下流程和要求进行评分：
一、批改流程
1. 仔细对比学生答案与参考答案
2. 严格按照参考答案进行评分，注重准确性和完整性
3. 对每个空格单独评分
二、评分规则
完全正确：100%
拼写错误但意思相同：50%
部分正确：根据匹配程度适当扣分
完全错误：0%
三、评分注意事项
- 填空题要求精准匹配，注重关键词的正确性
- 允许合理的同义词替换
- 注意大小写、标点符号等细节
- 对于多个空格的题目，要分别分析每个空格的对错情况

请以JSON格式返回结果:
{
    "score": 分数(整数),
    "feedback": "批改结果：[对每个空格的对错情况，不要明确给出单个空格的具体分数] 错误分析：[具体说明错误原因] 改进建议：[针对性建议]"
}""",
        'user_prompt_template': """题目：{question}

参考答案：{reference_answer}

题目分值：{max_score}分

学生答案：{student_answer}

请根据上述信息进行评分和反馈，在批改结果中只说明每个空格的对错情况，不要明确给出单个空格的具体分数。"""
    }
}
