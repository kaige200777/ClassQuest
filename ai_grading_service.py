"""
AI批改服务模块
提供简答题的AI自动批改功能
"""

import json
import requests
import time
import logging
from typing import Dict, Optional, Tuple
from config import AI_GRADING_CONFIG, AI_GRADING_PROMPTS

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIGradingService:
    """AI批改服务类"""
    
    def __init__(self):
        self.config = AI_GRADING_CONFIG
        self.prompts = AI_GRADING_PROMPTS
        self.enabled, self.config_message = self._check_config()
    
    def _check_config(self) -> Tuple[bool, str]:
        """检查AI配置是否完整（仅检查配置项，不测试连接）"""
        # 检查是否启用
        if not self.config.get('enabled', False):
            return False, "AI批改功能未启用"
        
        # 检查API密钥
        api_key = self.config.get('api_key', '').strip()
        if not api_key:
            return False, "缺少API密钥"
        
        # 检查API密钥格式（基本验证）
        if len(api_key) < 10:
            return False, "API密钥格式不正确"
        
        # 检查提供商
        provider = self.config.get('provider', '').strip()
        if not provider:
            return False, "未配置API提供商"
        
        # 检查模型名称
        model = self.config.get('model', '').strip()
        if not model:
            return False, "未配置模型名称"
        
        # 检查基础URL（某些提供商需要）
        if provider in ['azure', 'qianfan', 'tongyi']:
            base_url = self.config.get('base_url', '').strip()
            if not base_url:
                return False, f"{provider}提供商需要配置base_url"
        
        return True, "配置正确"
    
    def test_connection(self) -> Tuple[bool, str]:
        """测试API连接是否有效"""
        if not self.enabled:
            return False, self.config_message
        
        try:
            # 发送一个简单的测试请求
            test_prompt = "请回复'OK'"
            provider = self.config.get('provider', 'openai').lower()
            
            # 构建测试请求
            if provider == 'openai':
                url = self.config.get('base_url', 'https://api.openai.com/v1') + '/chat/completions'
                headers = {
                    'Authorization': f'Bearer {self.config["api_key"]}',
                    'Content-Type': 'application/json'
                }
                data = {
                    'model': self.config.get('model', 'gpt-3.5-turbo'),
                    'messages': [{'role': 'user', 'content': test_prompt}],
                    'max_tokens': 10
                }
            else:
                # 其他提供商暂时跳过实际测试
                return True, "配置正确（未测试连接）"
            
            # 发送请求，设置较短的超时时间
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return True, "API连接测试成功"
            elif response.status_code == 401:
                return False, "API密钥无效或已过期"
            elif response.status_code == 403:
                return False, "API密钥无权限访问"
            elif response.status_code == 429:
                return False, "API请求频率超限"
            else:
                return False, f"API连接失败 (状态码: {response.status_code})"
                
        except requests.exceptions.Timeout:
            return False, "API连接超时"
        except requests.exceptions.ConnectionError:
            return False, "无法连接到API服务器"
        except Exception as e:
            return False, f"连接测试失败: {str(e)}"
    
    def is_enabled(self) -> bool:
        """检查AI批改功能是否可用"""
        return self.enabled
    
    def get_config_status(self) -> Tuple[bool, str]:
        """获取配置状态和消息"""
        return self.enabled, self.config_message
    
    def grade_answer(self, question: str, reference_answer: str, 
                    student_answer: str, max_score: int, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """
        批改学生答案
        
        Args:
            question: 题目内容
            reference_answer: 参考答案
            student_answer: 学生答案
            max_score: 题目满分
            question_type: 题目类型 ('short_answer' 或 'fill_blank')
            
        Returns:
            Tuple[bool, Dict]: (是否成功, 结果字典)
            结果字典包含: score, feedback, error_message
        """
        if not self.enabled:
            return False, {"error_message": "AI批改功能未启用"}
        
        try:
            # 检查学生答案是否为空
            if not student_answer or student_answer.strip() == '':
                # 学生未作答，直接给0分
                return True, {
                    'score': 0,
                    'feedback': '主要得分点: 学生未作答，无法评分。\n扣分点: 无作答内容。\n改进建议: 请根据题目要求提供答案。\n拓展知识: 无'
                }
            
            # 根据题目类型选择不同的批改策略
            if question_type == 'fill_blank':
                return self._grade_fill_blank(question, reference_answer, student_answer, max_score)
            else:
                return self._grade_short_answer(question, reference_answer, student_answer, max_score)
            
        except Exception as e:
            logger.error(f"AI批改过程中发生错误: {str(e)}")
            return False, {"error_message": f"批改失败: {str(e)}"}
    
    def _grade_short_answer(self, question: str, reference_answer: str, 
                           student_answer: str, max_score: int) -> Tuple[bool, Dict]:
        """批改简答题"""
        # 构建请求消息
        user_prompt = self.prompts['short_answer']['user_prompt_template'].format(
            question=question,
            reference_answer=reference_answer or "无参考答案",
            max_score=max_score,
            student_answer=student_answer
        )
        
        # 根据不同的API提供商构建请求
        success, result = self._make_api_request(user_prompt, 'short_answer')
        
        if not success:
            return False, result
        
        # 解析AI返回的结果
        return self._parse_ai_response(result, max_score)
    
    def _grade_fill_blank(self, question: str, reference_answer: str, 
                         student_answer: str, max_score: int) -> Tuple[bool, Dict]:
        """批改填空题"""
        # 构建请求消息
        user_prompt = self.prompts['fill_blank']['user_prompt_template'].format(
            question=question,
            reference_answer=reference_answer,
            max_score=max_score,
            student_answer=student_answer
        )
        
        # 发送API请求
        success, result = self._make_api_request(user_prompt, 'fill_blank')
        
        if not success:
            return False, result
        
        # 解析AI返回的结果
        return self._parse_ai_response(result, max_score)
    
    def _make_api_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """发送API请求"""
        provider = self.config.get('provider', 'openai').lower()
        
        if provider == 'openai':
            return self._openai_request(user_prompt, question_type)
        elif provider == 'azure':
            return self._azure_request(user_prompt, question_type)
        elif provider == 'anthropic':
            return self._anthropic_request(user_prompt, question_type)
        elif provider == 'qianfan':
            return self._qianfan_request(user_prompt, question_type)
        elif provider == 'tongyi':
            return self._tongyi_request(user_prompt, question_type)
        else:
            return False, {"error_message": f"不支持的API提供商: {provider}"}
    
    def _openai_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """OpenAI API请求"""
        url = self.config.get('base_url', 'https://api.openai.com/v1') + '/chat/completions'
        
        headers = {
            'Authorization': f'Bearer {self.config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.config.get('model', 'gpt-3.5-turbo'),
            'messages': [{'role': 'system', 'content': self.prompts[question_type]['system_prompt']},
                        {'role': 'user', 'content': user_prompt}],
            'temperature': self.config.get('temperature', 0.3),
            'max_tokens': self.config.get('max_tokens', 1000)
        }
        
        return self._send_request(url, headers, data)
    
    def _azure_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """Azure OpenAI API请求"""
        # Azure OpenAI的URL格式通常是：
        # https://{resource}.openai.azure.com/openai/deployments/{deployment}/chat/completions?api-version=2023-12-01-preview
        base_url = self.config.get('base_url', '')
        if not base_url:
            return False, {"error_message": "Azure OpenAI需要配置base_url"}
        
        headers = {
            'api-key': self.config["api_key"],
            'Content-Type': 'application/json'
        }
        
        data = {
            'messages': [{'role': 'system', 'content': self.prompts[question_type]['system_prompt']},
                        {'role': 'user', 'content': user_prompt}],
            'temperature': self.config.get('temperature', 0.3),
            'max_tokens': self.config.get('max_tokens', 1000)
        }
        
        return self._send_request(base_url, headers, data)
    
    def _anthropic_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """Anthropic Claude API请求"""
        url = self.config.get('base_url', 'https://api.anthropic.com/v1') + '/messages'
        
        headers = {
            'x-api-key': self.config["api_key"],
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        data = {
            'model': self.config.get('model', 'claude-3-sonnet-20240229'),
            'max_tokens': self.config.get('max_tokens', 1000),
            'messages': [{'role': 'user', 'content': f"{self.prompts[question_type]['system_prompt']}\n\n{user_prompt}"}]
        }
        
        return self._send_request(url, headers, data)
    
    def _qianfan_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """百度千帆API请求"""
        # 千帆API需要access_token，这里简化处理
        # 实际使用时需要先获取access_token
        url = self.config.get('base_url', 'https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions')
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'messages': [{'role': 'user', 'content': f"{self.prompts[question_type]['system_prompt']}\n\n{user_prompt}"}],
            'temperature': self.config.get('temperature', 0.3),
            'max_output_tokens': self.config.get('max_tokens', 1000)
        }
        
        # 添加access_token到URL
        url += f"?access_token={self.config['api_key']}"
        
        return self._send_request(url, headers, data)
    
    def _tongyi_request(self, user_prompt: str, question_type: str = 'short_answer') -> Tuple[bool, Dict]:
        """阿里通义千问API请求"""
        url = self.config.get('base_url', 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation')
        
        headers = {
            'Authorization': f'Bearer {self.config["api_key"]}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': self.config.get('model', 'qwen-turbo'),
            'input': {
                'messages': [{'role': 'system', 'content': self.prompts[question_type]['system_prompt']},
                            {'role': 'user', 'content': user_prompt}]
            },
            'parameters': {
                'temperature': self.config.get('temperature', 0.3),
                'max_tokens': self.config.get('max_tokens', 1000)
            }
        }
        
        return self._send_request(url, headers, data)
    
    def _send_request(self, url: str, headers: Dict, data: Dict) -> Tuple[bool, Dict]:
        """发送HTTP请求"""
        max_retries = self.config.get('max_retries', 3)
        timeout = self.config.get('timeout', 30)
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    url, 
                    headers=headers, 
                    json=data, 
                    timeout=timeout
                )
                
                if response.status_code == 200:
                    return True, response.json()
                else:
                    logger.warning(f"API请求失败 (尝试 {attempt + 1}/{max_retries}): {response.status_code} - {response.text}")
                    if attempt == max_retries - 1:
                        return False, {"error_message": f"API请求失败: {response.status_code} - {response.text}"}
                    
            except requests.exceptions.Timeout:
                logger.warning(f"API请求超时 (尝试 {attempt + 1}/{max_retries})")
                if attempt == max_retries - 1:
                    return False, {"error_message": "API请求超时"}
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"API请求异常 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                if attempt == max_retries - 1:
                    return False, {"error_message": f"API请求异常: {str(e)}"}
            
            # 重试前等待
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # 指数退避
        
        return False, {"error_message": "达到最大重试次数"}
    
    def _parse_ai_response(self, response: Dict, max_score: int) -> Tuple[bool, Dict]:
        """解析AI返回的响应"""
        try:
            provider = self.config.get('provider', 'openai').lower()
            
            # 根据不同提供商提取内容
            if provider == 'openai' or provider == 'azure':
                content = response['choices'][0]['message']['content']
            elif provider == 'anthropic':
                content = response['content'][0]['text']
            elif provider == 'qianfan':
                content = response['result']
            elif provider == 'tongyi':
                content = response['output']['text']
            else:
                return False, {"error_message": "不支持的API提供商响应格式"}
            
            # 尝试解析JSON格式的回答
            try:
                # 提取JSON部分（可能包含在markdown代码块中）
                if '```json' in content:
                    json_start = content.find('```json') + 7
                    json_end = content.find('```', json_start)
                    json_content = content[json_start:json_end].strip()
                elif '{' in content and '}' in content:
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_content = content[json_start:json_end]
                else:
                    json_content = content
                
                result = json.loads(json_content)
                
                # 验证和调整分数
                score = int(result.get('score', 0))
                score = max(0, min(score, max_score))  # 确保分数在0到满分之间
                
                feedback = result.get('feedback', '').strip()
                if not feedback:
                    feedback = "答案已评分，请参考参考答案进行对比学习。"
                
                # 构建返回结果
                ai_result = {
                    'score': score,
                    'feedback': feedback
                }
                
                # 如果是填空题，添加额外信息
                if 'order_required' in result:
                    ai_result['order_required'] = result.get('order_required', False)
                if 'correct_count' in result:
                    ai_result['correct_count'] = result.get('correct_count', 0)
                if 'total_count' in result:
                    ai_result['total_count'] = result.get('total_count', 0)
                if 'analysis' in result:
                    ai_result['analysis'] = result.get('analysis', '')
                if 'short_reason' in result:
                    ai_result['short_reason'] = result.get('short_reason', '')
                
                return True, ai_result
                
            except json.JSONDecodeError:
                # 如果无法解析JSON，尝试从文本中提取信息
                logger.warning("无法解析AI返回的JSON格式，尝试文本解析")
                return self._parse_text_response(content, max_score)
                
        except Exception as e:
            logger.error(f"解析AI响应时发生错误: {str(e)}")
            return False, {"error_message": f"解析AI响应失败: {str(e)}"}
    
    def _parse_text_response(self, content: str, max_score: int) -> Tuple[bool, Dict]:
        """从文本响应中提取评分信息"""
        try:
            # 简单的文本解析逻辑
            lines = content.split('\n')
            score = 0
            feedback = content
            
            # 尝试从文本中提取分数
            for line in lines:
                line = line.strip()
                if '分数' in line or 'score' in line.lower():
                    # 提取数字
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        score = int(numbers[0])
                        break
            
            # 确保分数在合理范围内
            score = max(0, min(score, max_score))
            
            # 如果没有找到分数，给一个默认分数（满分的60%）
            if score == 0:
                score = int(max_score * 0.6)
            
            return True, {
                'score': score,
                'feedback': feedback
            }
            
        except Exception as e:
            logger.error(f"文本解析失败: {str(e)}")
            return False, {"error_message": f"文本解析失败: {str(e)}"}

# 全局AI批改服务实例
ai_grading_service = AIGradingService()

def get_ai_grading_service() -> AIGradingService:
    """获取AI批改服务实例"""
    return ai_grading_service