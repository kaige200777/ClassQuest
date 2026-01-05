"""
题库导入功能的属性测试

使用 Hypothesis 进行属性测试，验证 CSV 和 Excel 文件导入的正确性
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import tempfile
import os
import pandas as pd
from io import BytesIO, StringIO
from app import app, db, Question, QuestionBank
from werkzeug.datastructures import FileStorage


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
        from app import User
        teacher = User(username='test_teacher', role='teacher')
        teacher.set_password('test')
        db.session.add(teacher)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


# 生成测试数据的策略
@st.composite
def question_data(draw, question_type='single_choice'):
    """生成随机题目数据"""
    content = draw(st.text(min_size=5, max_size=200, alphabet=st.characters(blacklist_categories=('Cs',))))
    score = draw(st.integers(min_value=1, max_value=10))
    correct_answer = draw(st.sampled_from(['A', 'B', 'C', 'D']))
    
    data = {
        '题目': content,
        '正确答案': correct_answer,
        '分值': score
    }
    
    if question_type in ['single_choice', 'multiple_choice']:
        data['选项A'] = draw(st.text(min_size=1, max_size=50))
        data['选项B'] = draw(st.text(min_size=1, max_size=50))
        data['选项C'] = draw(st.text(min_size=1, max_size=50))
        data['选项D'] = draw(st.text(min_size=1, max_size=50))
    
    return data


# Feature: debug-test-system, Property 2: CSV 文件解析正确性
@settings(max_examples=100)
@given(
    question_count=st.integers(min_value=1, max_value=20),
    question_type=st.sampled_from(['single_choice', 'multiple_choice', 'true_false', 'fill_blank'])
)
def test_csv_import_correctness(test_app, question_count, question_type):
    """
    属性测试：CSV 文件解析正确性
    
    验证：对于任何符合格式要求的 UTF-8 编码 CSV 文件，
         解析后的题目数量应该等于文件中的数据行数
    
    测试策略：
    1. 生成随机数量的题目数据
    2. 创建 CSV 文件
    3. 导入文件
    4. 验证导入的题目数量等于生成的数量
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 生成测试数据
        questions_data = []
        for _ in range(question_count):
            if question_type in ['single_choice', 'multiple_choice']:
                q_data = {
                    '题目': f'测试题目{_}',
                    '选项A': 'A选项',
                    '选项B': 'B选项',
                    '选项C': 'C选项',
                    '选项D': 'D选项',
                    '正确答案': 'A',
                    '分值': 5
                }
            else:
                q_data = {
                    '题目': f'测试题目{_}',
                    '正确答案': '正确' if question_type == 'true_false' else '答案',
                    '分值': 5
                }
            questions_data.append(q_data)
        
        # 创建 CSV 文件
        df = pd.DataFrame(questions_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        
        # 创建 FileStorage 对象
        csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
        file_storage = FileStorage(
            stream=csv_bytes,
            filename='test_questions.csv',
            content_type='text/csv'
        )
        
        # 导入文件
        response = client.post(
            f'/import_questions/{question_type}',
            data={
                'file': file_storage,
                'bank_name': f'test_bank_{question_type}'
            },
            content_type='multipart/form-data'
        )
        
        # 验证响应
        assert response.status_code == 200, f"导入失败: {response.get_json()}"
        result = response.get_json()
        assert result['success'] is True, f"导入失败: {result.get('message')}"
        
        # 验证导入的题目数量
        with test_app.app_context():
            imported_count = Question.query.filter_by(question_type=question_type).count()
            assert imported_count == question_count, \
                f"导入的题目数量不匹配: 期望 {question_count}, 实际 {imported_count}"


# Feature: debug-test-system, Property 3: Excel 文件解析正确性
@settings(max_examples=100)
@given(
    question_count=st.integers(min_value=1, max_value=20),
    question_type=st.sampled_from(['single_choice', 'multiple_choice', 'true_false', 'fill_blank'])
)
def test_excel_import_correctness(test_app, question_count, question_type):
    """
    属性测试：Excel 文件解析正确性
    
    验证：对于任何符合格式要求的 .xlsx 文件，
         解析后的题目数量应该等于文件中的数据行数
    
    测试策略：
    1. 生成随机数量的题目数据
    2. 创建 Excel 文件
    3. 导入文件
    4. 验证导入的题目数量等于生成的数量
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 生成测试数据
        questions_data = []
        for _ in range(question_count):
            if question_type in ['single_choice', 'multiple_choice']:
                q_data = {
                    '题目': f'测试题目{_}',
                    '选项A': 'A选项',
                    '选项B': 'B选项',
                    '选项C': 'C选项',
                    '选项D': 'D选项',
                    '正确答案': 'A',
                    '分值': 5
                }
            else:
                q_data = {
                    '题目': f'测试题目{_}',
                    '正确答案': '正确' if question_type == 'true_false' else '答案',
                    '分值': 5
                }
            questions_data.append(q_data)
        
        # 创建 Excel 文件
        df = pd.DataFrame(questions_data)
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)
        
        # 创建 FileStorage 对象
        file_storage = FileStorage(
            stream=excel_buffer,
            filename='test_questions.xlsx',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
        # 导入文件
        response = client.post(
            f'/import_questions/{question_type}',
            data={
                'file': file_storage,
                'bank_name': f'test_bank_{question_type}_excel'
            },
            content_type='multipart/form-data'
        )
        
        # 验证响应
        assert response.status_code == 200, f"导入失败: {response.get_json()}"
        result = response.get_json()
        assert result['success'] is True, f"导入失败: {result.get('message')}"
        
        # 验证导入的题目数量
        with test_app.app_context():
            imported_count = Question.query.filter_by(question_type=question_type).count()
            assert imported_count == question_count, \
                f"导入的题目数量不匹配: 期望 {question_count}, 实际 {imported_count}"


# Feature: debug-test-system, Property 4: 文件导入错误处理
@settings(max_examples=50)
@given(
    invalid_format=st.sampled_from(['txt', 'pdf', 'doc', 'json', 'xml'])
)
def test_import_invalid_file_format(test_app, invalid_format):
    """
    属性测试：文件导入错误处理
    
    验证：对于任何格式不正确的文件，系统应该返回包含具体错误信息的响应
    
    测试策略：
    1. 创建不支持格式的文件
    2. 尝试导入
    3. 验证返回错误信息
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 创建无效格式的文件
        invalid_content = BytesIO(b'invalid content')
        file_storage = FileStorage(
            stream=invalid_content,
            filename=f'test_file.{invalid_format}',
            content_type='application/octet-stream'
        )
        
        # 尝试导入
        response = client.post(
            '/import_questions/single_choice',
            data={
                'file': file_storage,
                'bank_name': 'test_bank'
            },
            content_type='multipart/form-data'
        )
        
        # 验证返回错误
        assert response.status_code == 400, "应该返回 400 错误"
        result = response.get_json()
        assert result['success'] is False, "success 应该为 False"
        assert '不支持的文件格式' in result['message'] or 'format' in result['message'].lower(), \
            f"错误信息应该提到文件格式问题: {result['message']}"


# Feature: debug-test-system, Property 5: 图片路径存储往返一致性
@settings(max_examples=100)
@given(
    image_path=st.text(min_size=5, max_size=100, alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd'),
        whitelist_characters='/-_.'
    ))
)
def test_image_path_round_trip(test_app, image_path):
    """
    属性测试：图片路径存储往返一致性
    
    验证：对于任何包含图片路径的题目，存储到数据库后再读取，应该得到相同的图片路径
    
    测试策略：
    1. 创建包含图片路径的题目数据
    2. 导入到数据库
    3. 读取题目
    4. 验证图片路径一致
    """
    assume(len(image_path.strip()) > 0)  # 确保路径不为空
    
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 创建包含图片路径的题目数据
        questions_data = [{
            '题目': '测试题目',
            '选项A': 'A选项',
            '选项B': 'B选项',
            '选项C': 'C选项',
            '选项D': 'D选项',
            '正确答案': 'A',
            '分值': 5,
            '图片': image_path
        }]
        
        # 创建 CSV 文件
        df = pd.DataFrame(questions_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        
        csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
        file_storage = FileStorage(
            stream=csv_bytes,
            filename='test_questions.csv',
            content_type='text/csv'
        )
        
        # 导入文件
        response = client.post(
            '/import_questions/single_choice',
            data={
                'file': file_storage,
                'bank_name': 'test_bank_image'
            },
            content_type='multipart/form-data'
        )
        
        assert response.status_code == 200
        
        # 读取题目并验证图片路径
        with test_app.app_context():
            question = Question.query.filter_by(content='测试题目').first()
            assert question is not None, "题目应该被导入"
            assert question.image_path == image_path, \
                f"图片路径不匹配: 期望 '{image_path}', 实际 '{question.image_path}'"


def test_import_missing_required_columns(test_app):
    """
    单元测试：验证缺少必需列时的错误处理
    """
    with test_app.test_client() as client:
        # 登录
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'teacher'
        
        # 创建缺少必需列的数据
        questions_data = [{
            '题目': '测试题目',
            # 缺少 '正确答案' 和 '分值'
        }]
        
        df = pd.DataFrame(questions_data)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_buffer.seek(0)
        
        csv_bytes = BytesIO(csv_buffer.getvalue().encode('utf-8'))
        file_storage = FileStorage(
            stream=csv_bytes,
            filename='test_questions.csv',
            content_type='text/csv'
        )
        
        # 尝试导入
        response = client.post(
            '/import_questions/single_choice',
            data={
                'file': file_storage,
                'bank_name': 'test_bank'
            },
            content_type='multipart/form-data'
        )
        
        # 验证返回错误
        assert response.status_code == 400
        result = response.get_json()
        assert result['success'] is False
        assert '缺少必需的列' in result['message']


def test_import_unauthorized(test_app):
    """
    单元测试：验证未授权访问的处理
    """
    with test_app.test_client() as client:
        # 不登录，直接尝试导入
        csv_bytes = BytesIO(b'test')
        file_storage = FileStorage(
            stream=csv_bytes,
            filename='test.csv',
            content_type='text/csv'
        )
        
        response = client.post(
            '/import_questions/single_choice',
            data={'file': file_storage},
            content_type='multipart/form-data'
        )
        
        # 验证返回 403 错误
        assert response.status_code == 403
        result = response.get_json()
        assert result['success'] is False
        assert '未授权' in result['message']
