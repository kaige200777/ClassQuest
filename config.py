"""
应用配置文件
"""
import os

# 服务器配置
HOST = os.environ.get('APP_HOST', '0.0.0.0')
PORT = int(os.environ.get('APP_PORT', '8080'))

# Waitress服务器配置（生产环境）
WAITRESS_THREADS = int(os.environ.get('WAITRESS_THREADS', '32'))
WAITRESS_CONNECTION_LIMIT = int(os.environ.get('WAITRESS_CONNECTION_LIMIT', '1000'))
WAITRESS_SEND_BYTES = int(os.environ.get('WAITRESS_SEND_BYTES', '65536'))

# 日志配置
LOG_DIR = os.environ.get('LOG_DIR', 'logs')
LOG_FILE = os.environ.get('LOG_FILE', 'app.log')

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
    
    # API基础URL (可选，某些提供商需要)
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
        'system_prompt': """
一、预处理阶段：答案有效性筛查（先执行）

### 立即终止评分的情况（直接判0分）：
1. 完全无关：答案与题目完全无关（如"我不会"、"老师没讲过"、"题目内容"）
2. 空白无效：仅含标点、乱码或无意义字符
3. 重复题目：只重复题目内容而无实质性回答
4. 提问形式：以问题形式回答而非提供答案（如"这是什么意思？"）

### 标记后继续评分的情况：
1. 不完整答案：有关键词但解释不全 -> 标记[不完整]，继续评分
2. 描述性回答：描述如何回答而非具体内容 -> 标记[需具体化]，继续评分但扣20%基础分
3. 代码无解释：只有代码片段无文字说明 -> 标记[需文档化]，继续评分

### 正常进入评分的情况：
- 提供实质性技术回答
- 包含相关概念和解释
- 有解决问题或分析问题的尝试
二、评分规则
要点覆盖度评分：识别每个关键要点，按学生答案的覆盖程度打分
完全覆盖：100%
部分覆盖或表述模糊：50%
未覆盖：0%
三、批改维度
语义理解：理解学生答案的核心意思，不要求字字匹配
要点覆盖度分析：逐条分析覆盖了哪些关键要点，并给出覆盖程度判断
错误识别：指出明显的概念错误或表述不当之处
个性化反馈：
针对错误或不足提供具体改进建议
可适当补充相关拓展知识，帮助学生深化理解

请以JSON格式返回结果:
{
    "score": 整数分数,
    "feedback": "主要得分点:[具体说明] 扣分点：[具体说明] 改进建议：[具体建议] 拓展知识：[相关拓展]"
}""",
        'user_prompt_template': """
题目：{question}
参考答案：{reference_answer}
题目分值：{max_score}分
学生答案：{student_answer}
请根据上述信息进行评分和反馈。"""
    },
    
    # 填空题批改提示词
    'fill_blank': {
        'system_prompt': """
批改前预处理：
1、检查学生答案是否为有效填空内容（非描述性语言、非提问、非无关内容）
2、检查每个填空答案字数是否超过15个汉字，超过则判为错误
3、若答案无效或字数超限，直接判该空格0分
参考答案比对与评分规则：
1、学生答案与参考答案完全相同（含大小写、标点）：100%
2、拼写错误但意思相同：50%
3、允许合理的同义词替换（需符合技术语境）
4、有多余内容、字数超限或完全无关：0%
多空格题目处理：
1、分别分析每个空格
2、计算平均分作为最终得分
3、每个空格单独判断字数限制
请以JSON格式返回结果:
{
    "score": 整数分数,
    "feedback": "批改结果：[说明每个空格的对错情况，不给出单个空格分数] 错误分析：[具体错误原因] 改进建议：[针对性建议]"
}""",
        'user_prompt_template': """
立即批改：       
题目：{question}
参考答案：{reference_answer}
题目分值：{max_score}分
学生答案：{student_answer}
开始批改"""
    }
}