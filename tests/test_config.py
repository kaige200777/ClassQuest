"""
测试配置管理功能的属性测试

使用 Hypothesis 进行属性测试，验证测试配置的正确性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import tempfile
import os
from app import app, db, Test, TestPreset, Question, QuestionBank, User


@pytest.fixture
def test_app():
    """创建测试应用实例"""
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        # 创建测试教师账户
        teacher = User(username='test_teacher', role='teacher')
        teacher.set_password('test')
        db.session.add(teacher)
        
        # 创建测试题库和题目
        for q_type in ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer']:
            bank = QuestionBank(name=f'{q_type}_bank', question_type=q_type)
            db.session.add(bank)
            db.session.flush()
            
            # 为每个题库添加50道题
            for i in range(50):
                question = Question(
                    question_type=q_type,
                    content=f'测试题目 {i}',
                    correct_answer='A' if q_type in ['single_choice', 'multiple_choice'] else '正确',
                    score=5,
                    bank_id=bank.id
                )
                if q_type in ['single_choice', 'multiple_choice']:
                    question.option_a = 'A选项'
                    question.option_b = 'B选项'
                    question.option_c = 'C选项'
                    question.option_d = 'D选项'
                db.session.add(question)
        
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


# Feature: debug-test-system, Property 6: 测试配置必填字段验证
@settings(max_examples=100)
@given(
    missing_field=st.sampled_from(['title', 'all_counts_zero'])
)
def test_config_required_fields_validation(test_app, missing_field):
    """
    属性测试：测试配置必填字段验证
    
    验证：对于任何缺少必填字段的测试配置，系统应该拒绝保存并返回验证错误
    
    测试策略：
    1. 创建缺少必填字段的配置
    2. 尝试保存
    3. 验证返回错误
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 获取题库ID
        with test_app.app_context():
            bank = QuestionBank.query.filter_by(question_type='single_choice').first()
            bank_id = bank.id
        
        # 构建配置数据
        config_data = {
            'title': '测试配置',
            'single_choice_count': 10,
            'single_choice_score': 5,
            'single_choice_bank_id': bank_id,
            'multiple_choice_count': 0,
            'true_false_count': 0,
            'fill_blank_count': 0,
            'short_answer_count': 0,
            'allow_student_choice': 'false',
            'save_as_preset': 'false'
        }
        
        # 根据测试参数移除必填字段
        if missing_field == 'title':
            config_data['title'] = ''
        elif missing_field == 'all_counts_zero':
            config_data['single_choice_count'] = 0
        
        # 尝试保存
        response = client.post('/save_test_settings', data=config_data)
        
        # 验证返回错误
        assert response.status_code == 400, "应该返回 400 错误"
        result = response.get_json()
        assert result['success'] is False, "success 应该为 False"
        assert 'message' in result, "应该包含错误信息"


# Feature: debug-test-system, Property 7: 题库题目数量验证
@settings(max_examples=100)
@given(
    requested_count=st.integers(min_value=51, max_value=100)
)
def test_config_question_count_validation(test_app, requested_count):
    """
    属性测试：题库题目数量验证
    
    验证：对于任何测试配置，如果某题型要求的题目数量超过对应题库中的可用题目数量，
         系统应该拒绝该配置
    
    测试策略：
    1. 题库中有50道题
    2. 请求超过50道题（51-100）
    3. 验证返回错误
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 获取题库ID
        with test_app.app_context():
            bank = QuestionBank.query.filter_by(question_type='single_choice').first()
            bank_id = bank.id
        
        # 构建配置数据，请求的题目数量超过可用数量
        config_data = {
            'title': '测试配置',
            'single_choice_count': requested_count,  # 超过50
            'single_choice_score': 5,
            'single_choice_bank_id': bank_id,
            'multiple_choice_count': 0,
            'true_false_count': 0,
            'fill_blank_count': 0,
            'short_answer_count': 0,
            'allow_student_choice': 'false',
            'save_as_preset': 'false'
        }
        
        # 尝试保存
        response = client.post('/save_test_settings', data=config_data)
        
        # 验证返回错误
        assert response.status_code == 400, "应该返回 400 错误"
        result = response.get_json()
        assert result['success'] is False, "success 应该为 False"
        assert 'errors' in result or '题库' in result.get('message', ''), \
            "应该提示题库题目不足"


# Feature: debug-test-system, Property 8: 测试总分自动计算
@settings(max_examples=100)
@given(
    single_count=st.integers(min_value=0, max_value=10),
    single_score=st.integers(min_value=1, max_value=10),
    multiple_count=st.integers(min_value=0, max_value=10),
    multiple_score=st.integers(min_value=1, max_value=10),
    true_false_count=st.integers(min_value=0, max_value=10),
    true_false_score=st.integers(min_value=1, max_value=10)
)
def test_config_total_score_calculation(test_app, single_count, single_score, 
                                        multiple_count, multiple_score,
                                        true_false_count, true_false_score):
    """
    属性测试：测试总分自动计算
    
    验证：对于任何测试配置，总分应该等于所有题型的（题目数量 × 单题分值）之和
    
    测试策略：
    1. 生成随机的题型配置
    2. 保存配置
    3. 验证返回的总分等于计算值
    """
    # 确保至少有一种题型
    assume(single_count + multiple_count + true_false_count > 0)
    
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 获取题库ID
        with test_app.app_context():
            single_bank = QuestionBank.query.filter_by(question_type='single_choice').first()
            multiple_bank = QuestionBank.query.filter_by(question_type='multiple_choice').first()
            tf_bank = QuestionBank.query.filter_by(question_type='true_false').first()
        
        # 构建配置数据
        config_data = {
            'title': '测试配置',
            'single_choice_count': single_count,
            'single_choice_score': single_score,
            'single_choice_bank_id': single_bank.id if single_count > 0 else '',
            'multiple_choice_count': multiple_count,
            'multiple_choice_score': multiple_score,
            'multiple_choice_bank_id': multiple_bank.id if multiple_count > 0 else '',
            'true_false_count': true_false_count,
            'true_false_score': true_false_score,
            'true_false_bank_id': tf_bank.id if true_false_count > 0 else '',
            'fill_blank_count': 0,
            'short_answer_count': 0,
            'allow_student_choice': 'false',
            'save_as_preset': 'false'
        }
        
        # 计算期望的总分
        expected_total = (
            single_count * single_score +
            multiple_count * multiple_score +
            true_false_count * true_false_score
        )
        
        # 保存配置
        response = client.post('/save_test_settings', data=config_data)
        
        # 验证响应
        assert response.status_code == 200, f"保存失败: {response.get_json()}"
        result = response.get_json()
        assert result['success'] is True, f"保存失败: {result.get('message')}"
        
        # 验证总分
        assert result['total_score'] == expected_total, \
            f"总分计算错误: 期望 {expected_total}, 实际 {result['total_score']}"


# Feature: debug-test-system, Property 9: 测试预设往返一致性
@settings(max_examples=100)
@given(
    preset_name=st.text(min_size=1, max_size=50, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters=' -_'
    )),
    single_count=st.integers(min_value=1, max_value=10),
    single_score=st.integers(min_value=1, max_value=10)
)
def test_preset_round_trip_consistency(test_app, preset_name, single_count, single_score):
    """
    属性测试：测试预设往返一致性
    
    验证：对于任何测试预设，保存后再读取，应该得到相同的配置参数
    
    测试策略：
    1. 创建预设配置
    2. 保存预设
    3. 读取预设
    4. 验证所有参数一致
    """
    assume(len(preset_name.strip()) > 0)
    
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 获取题库ID
        with test_app.app_context():
            bank = QuestionBank.query.filter_by(question_type='single_choice').first()
            bank_id = bank.id
        
        # 构建预设数据
        preset_data = {
            'title': '临时标题',  # 预设不使用这个
            'preset_name': preset_name,
            'single_choice_count': single_count,
            'single_choice_score': single_score,
            'single_choice_bank_id': bank_id,
            'multiple_choice_count': 0,
            'true_false_count': 0,
            'fill_blank_count': 0,
            'short_answer_count': 0,
            'allow_student_choice': 'true',
            'save_as_preset': 'true'
        }
        
        # 保存预设
        response = client.post('/save_test_settings', data=preset_data)
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        preset_id = result['preset_id']
        
        # 读取预设
        response = client.get(f'/api/test_presets/{preset_id}')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        preset = result['preset']
        
        # 验证所有参数一致
        assert preset['single_choice_count'] == single_count, \
            f"单选题数量不匹配: 期望 {single_count}, 实际 {preset['single_choice_count']}"
        assert preset['single_choice_score'] == single_score, \
            f"单选题分值不匹配: 期望 {single_score}, 实际 {preset['single_choice_score']}"
        assert preset['single_choice_bank_id'] == bank_id, \
            f"单选题题库ID不匹配: 期望 {bank_id}, 实际 {preset['single_choice_bank_id']}"
        assert preset['allow_student_choice'] is True, \
            "学生自选设置不匹配"


def test_config_missing_bank_selection(test_app):
    """
    单元测试：验证未选择题库时的错误处理
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 构建配置数据，有题目数量但没有选择题库
        config_data = {
            'title': '测试配置',
            'single_choice_count': 10,
            'single_choice_score': 5,
            # 缺少 single_choice_bank_id
            'multiple_choice_count': 0,
            'true_false_count': 0,
            'fill_blank_count': 0,
            'short_answer_count': 0,
            'allow_student_choice': 'false',
            'save_as_preset': 'false'
        }
        
        # 尝试保存
        response = client.post('/save_test_settings', data=config_data)
        
        # 验证返回错误
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert '未选择题库' in str(result.get('errors', []))


def test_config_unauthorized_access(test_app):
    """
    单元测试：验证未授权访问的处理
    """
    with test_app.test_client() as client:
        # 不登录，直接尝试保存配置
        config_data = {
            'title': '测试配置',
            'single_choice_count': 10
        }
        
        response = client.post('/save_test_settings', data=config_data)
        
        # 验证返回 403 错误
        assert response.status_code == 403
        result = response.get_json()
        assert result['success'] is False
        assert '未授权' in result['message']


def test_preset_delete(test_app):
    """
    单元测试：验证预设删除功能
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 创建预设
        with test_app.app_context():
            bank = QuestionBank.query.filter_by(question_type='single_choice').first()
            preset = TestPreset(
                title='测试预设',
                single_choice_count=10,
                single_choice_score=5,
                single_choice_bank_id=bank.id
            )
            db.session.add(preset)
            db.session.commit()
            preset_id = preset.id
        
        # 删除预设
        response = client.delete(f'/api/test_presets/{preset_id}')
        assert response.status_code == 200
        result = response.get_json()
        assert result['success'] is True
        
        # 验证预设已删除
        with test_app.app_context():
            preset = TestPreset.query.get(preset_id)
            assert preset is None, "预设应该已被删除"
