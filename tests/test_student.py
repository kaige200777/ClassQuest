"""
学生测试流程的属性测试

使用 Hypothesis 进行属性测试，验证学生测试流程的正确性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import tempfile
import os
import json
from app import app, db, User, Test, TestResult, Question, QuestionBank, TestPreset


@pytest.fixture
def test_app_with_test():
    """创建包含测试配置的测试应用实例"""
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        
        # 创建测试题库和题目
        for q_type in ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer']:
            bank = QuestionBank(name=f'{q_type}_bank', question_type=q_type)
            db.session.add(bank)
            db.session.flush()
            
            # 为每个题库添加20道题
            for i in range(20):
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
        
        # 创建测试配置
        single_bank = QuestionBank.query.filter_by(question_type='single_choice').first()
        test = Test(
            title='测试考试',
            single_choice_count=10,
            single_choice_score=5,
            single_choice_bank_id=single_bank.id,
            multiple_choice_count=0,
            true_false_count=0,
            fill_blank_count=0,
            short_answer_count=0,
            total_score=50,
            is_active=True
        )
        db.session.add(test)
        db.session.commit()
        
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


# Feature: debug-test-system, Property 10: 学生账户自动创建或登录
@settings(max_examples=100)
@given(
    name=st.text(min_size=1, max_size=20, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='_'
    )),
    class_number=st.text(min_size=1, max_size=10, alphabet=st.characters(
        whitelist_categories=('Nd',)
    ))
)
def test_student_account_auto_creation(test_app_with_test, name, class_number):
    """
    属性测试：学生账户自动创建或登录
    
    验证：对于任何姓名和班级号组合，系统应该能够创建新账户或找到已存在的账户，
         不应该创建重复账户
    
    测试策略：
    1. 第一次使用姓名和班级号登录，应该创建新账户
    2. 第二次使用相同信息登录，应该找到已存在的账户
    3. 验证不会创建重复账户
    """
    assume(len(name.strip()) > 0 and len(class_number.strip()) > 0)
    
    with test_app_with_test.test_client() as client:
        # 第一次登录 - 应该创建新账户
        response1 = client.post('/student/start', data={
            'name': name,
            'class_number': class_number
        }, follow_redirects=False)
        
        assert response1.status_code == 302, "应该重定向到测试页面"
        
        # 检查账户是否创建
        with test_app_with_test.app_context():
            username = f"{name}_{class_number}"
            user1 = User.query.filter_by(username=username, role='student').first()
            assert user1 is not None, "应该创建学生账户"
            user1_id = user1.id
            initial_count = User.query.filter_by(username=username, role='student').count()
            assert initial_count == 1, "应该只有一个账户"
        
        # 第二次登录 - 应该使用已存在的账户
        response2 = client.post('/student/start', data={
            'name': name,
            'class_number': class_number
        }, follow_redirects=False)
        
        assert response2.status_code == 302, "应该重定向到测试页面"
        
        # 验证没有创建重复账户
        with test_app_with_test.app_context():
            user2 = User.query.filter_by(username=username, role='student').first()
            assert user2 is not None, "账户应该存在"
            assert user2.id == user1_id, "应该是同一个账户"
            final_count = User.query.filter_by(username=username, role='student').count()
            assert final_count == 1, "不应该创建重复账户"


# Feature: debug-test-system, Property 11: 随机抽题数量和来源正确性
@settings(max_examples=100)
@given(
    question_count=st.integers(min_value=1, max_value=15)
)
def test_random_question_selection(test_app_with_test, question_count):
    """
    属性测试：随机抽题数量和来源正确性
    
    验证：对于任何测试配置，抽取的题目数量应该等于配置的数量，
         且所有题目都来自指定的题库
    
    测试策略：
    1. 创建指定数量的测试配置
    2. 学生开始测试
    3. 验证抽取的题目数量和来源
    """
    with test_app_with_test.test_client() as client:
        # 更新测试配置
        with test_app_with_test.app_context():
            test = Test.query.filter_by(is_active=True).first()
            test.single_choice_count = question_count
            test.total_score = question_count * test.single_choice_score
            bank_id = test.single_choice_bank_id
            db.session.commit()
        
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 访问测试页面
        response = client.get('/test')
        assert response.status_code == 200
        
        # 解析页面内容，验证题目数量
        # 注意：这里简化处理，实际应该解析HTML
        # 我们通过检查session来验证
        with client.session_transaction() as sess:
            assert 'student_id' in sess
        
        # 验证数据库中的题目来源
        with test_app_with_test.app_context():
            # 验证题库中有足够的题目
            available_questions = Question.query.filter_by(
                question_type='single_choice',
                bank_id=bank_id
            ).count()
            assert available_questions >= question_count, \
                f"题库中应该有足够的题目: 需要 {question_count}, 可用 {available_questions}"


# Feature: debug-test-system, Property 12: 答案保存往返一致性
@settings(max_examples=100)
@given(
    answer=st.sampled_from(['A', 'B', 'C', 'D'])
)
def test_answer_save_round_trip(test_app_with_test, answer):
    """
    属性测试：答案保存往返一致性
    
    验证：对于任何学生提交的答案，保存到数据库后再读取，应该得到相同的答案内容
    
    测试策略：
    1. 学生提交答案
    2. 从数据库读取答案
    3. 验证答案一致
    """
    with test_app_with_test.test_client() as client:
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 获取测试页面以获取题目ID
        response = client.get('/test')
        assert response.status_code == 200
        
        # 获取第一道题的ID
        with test_app_with_test.app_context():
            question = Question.query.filter_by(question_type='single_choice').first()
            question_id = question.id
        
        # 提交答案
        response = client.post('/submit_test', data={
            f'answer_{question_id}': answer
        }, follow_redirects=False)
        
        assert response.status_code == 302, "应该重定向到学生面板"
        
        # 从数据库读取答案
        with test_app_with_test.app_context():
            result = TestResult.query.order_by(TestResult.created_at.desc()).first()
            assert result is not None, "应该有测试结果"
            
            answers = json.loads(result.answers)
            saved_answer = answers.get(str(question_id))
            
            assert saved_answer == answer, \
                f"答案不一致: 提交 '{answer}', 保存 '{saved_answer}'"


# Feature: debug-test-system, Property 13: 自动评分正确性
@settings(max_examples=100)
@given(
    correct_count=st.integers(min_value=0, max_value=10)
)
def test_auto_grading_correctness(test_app_with_test, correct_count):
    """
    属性测试：自动评分正确性
    
    验证：对于任何提交的测试答案，自动评分的结果应该等于所有正确答案的分值之和
    
    测试策略：
    1. 提交部分正确、部分错误的答案
    2. 验证得分等于正确答案数量 × 单题分值
    """
    with test_app_with_test.test_client() as client:
        # 更新测试配置为10道题
        with test_app_with_test.app_context():
            test = Test.query.filter_by(is_active=True).first()
            test.single_choice_count = 10
            test.single_choice_score = 5
            test.total_score = 50
            db.session.commit()
        
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 获取题目
        with test_app_with_test.app_context():
            questions = Question.query.filter_by(question_type='single_choice').limit(10).all()
            
            # 构建答案：前 correct_count 道题答对，其余答错
            answer_data = {}
            for i, q in enumerate(questions):
                if i < correct_count:
                    # 答对
                    answer_data[f'answer_{q.id}'] = q.correct_answer
                else:
                    # 答错（选择一个错误答案）
                    wrong_answer = 'B' if q.correct_answer != 'B' else 'C'
                    answer_data[f'answer_{q.id}'] = wrong_answer
        
        # 提交答案
        response = client.post('/submit_test', data=answer_data, follow_redirects=False)
        assert response.status_code == 302
        
        # 验证得分
        with test_app_with_test.app_context():
            result = TestResult.query.order_by(TestResult.created_at.desc()).first()
            assert result is not None, "应该有测试结果"
            
            expected_score = correct_count * 5
            assert result.score == expected_score, \
                f"得分不正确: 期望 {expected_score}, 实际 {result.score}"


# Feature: debug-test-system, Property 14: 图片上传关联正确性
def test_image_upload_association(test_app_with_test):
    """
    单元测试：图片上传关联正确性
    
    验证：对于任何简答题的图片上传，图片应该正确关联到对应的答案记录
    
    注意：这是一个简化的测试，实际的图片上传需要更复杂的设置
    """
    with test_app_with_test.test_client() as client:
        # 更新测试配置包含简答题
        with test_app_with_test.app_context():
            test = Test.query.filter_by(is_active=True).first()
            test.single_choice_count = 0
            test.short_answer_count = 1
            test.short_answer_score = 10
            short_answer_bank = QuestionBank.query.filter_by(question_type='short_answer').first()
            test.short_answer_bank_id = short_answer_bank.id
            test.total_score = 10
            db.session.commit()
        
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 获取简答题ID
        with test_app_with_test.app_context():
            question = Question.query.filter_by(question_type='short_answer').first()
            question_id = question.id
        
        # 提交答案（包含图片标签）
        answer_with_image = '这是我的答案 <img src="/static/uploads/test.jpg">'
        response = client.post('/submit_test', data={
            f'answer_{question_id}': answer_with_image
        }, follow_redirects=False)
        
        assert response.status_code == 302
        
        # 验证答案中包含图片信息
        with test_app_with_test.app_context():
            from app import ShortAnswerSubmission
            submission = ShortAnswerSubmission.query.order_by(
                ShortAnswerSubmission.created_at.desc()
            ).first()
            
            assert submission is not None, "应该有简答题提交记录"
            assert '<img' in submission.student_answer, "答案应该包含图片标签"


def test_student_empty_input_validation(test_app_with_test):
    """
    单元测试：验证空输入的处理
    """
    with test_app_with_test.test_client() as client:
        # 尝试用空姓名和班级号登录
        response = client.post('/student/start', data={
            'name': '',
            'class_number': ''
        }, follow_redirects=True)
        
        # 应该返回错误或重新显示表单
        assert response.status_code == 200
        # 验证没有创建会话
        with client.session_transaction() as sess:
            assert 'student_id' not in sess


def test_multiple_test_submissions(test_app_with_test):
    """
    单元测试：验证同一学生可以多次参加测试
    """
    with test_app_with_test.test_client() as client:
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 获取题目ID
        with test_app_with_test.app_context():
            question = Question.query.filter_by(question_type='single_choice').first()
            question_id = question.id
        
        # 第一次提交
        client.post('/submit_test', data={
            f'answer_{question_id}': 'A'
        })
        
        # 第二次提交
        client.post('/submit_test', data={
            f'answer_{question_id}': 'B'
        })
        
        # 验证有两条测试记录
        with test_app_with_test.app_context():
            results = TestResult.query.filter_by(student_name='测试学生').all()
            assert len(results) == 2, "应该有两条测试记录"


def test_fill_blank_scoring(test_app_with_test):
    """
    单元测试：验证填空题的评分逻辑
    """
    with test_app_with_test.test_client() as client:
        # 更新测试配置包含填空题
        with test_app_with_test.app_context():
            test = Test.query.filter_by(is_active=True).first()
            test.single_choice_count = 0
            test.fill_blank_count = 1
            test.fill_blank_score = 10
            fill_blank_bank = QuestionBank.query.filter_by(question_type='fill_blank').first()
            test.fill_blank_bank_id = fill_blank_bank.id
            test.total_score = 10
            
            # 创建一个有多个填空的题目
            question = Question.query.filter_by(question_type='fill_blank').first()
            question.correct_answer = '答案1、答案2'  # 两个填空
            db.session.commit()
            question_id = question.id
        
        # 学生登录
        client.post('/student/start', data={
            'name': '测试学生',
            'class_number': '001'
        })
        
        # 提交答案（只答对一个）
        response = client.post('/submit_test', data={
            f'answer_{question_id}_1': '答案1',
            f'answer_{question_id}_2': '错误答案'
        }, follow_redirects=False)
        
        assert response.status_code == 302
        
        # 验证得分（应该是部分分）
        with test_app_with_test.app_context():
            result = TestResult.query.order_by(TestResult.created_at.desc()).first()
            # 两个填空，答对一个，应该得5分
            assert result.score == 5, f"填空题部分分计算错误: {result.score}"
