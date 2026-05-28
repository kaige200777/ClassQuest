from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import pandas as pd
import os
from datetime import datetime
from datetime import timedelta
import random
import json
from sqlalchemy import func
from sqlalchemy import text
from collections import defaultdict
from io import BytesIO
from werkzeug.utils import secure_filename
import uuid
from ai_grading_service import get_ai_grading_service
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 图片上传配置 ---
# 允许的扩展名
ALLOWED_IMG_EXT = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
# 限制大小（字节）2MB
MAX_IMG_SIZE = 2 * 1024 * 1024

# ---- 时间工具 ----
BJ_OFFSET = timedelta(hours=8)

def to_bj(dt: datetime):
    """
    Convert naive UTC datetime stored in DB to Beijing time
    """
    return (dt + BJ_OFFSET) if dt else dt

# Jinja 过滤器函数
def bjtime_filter(value, fmt='%Y-%m-%d %H:%M'):
    if not value:
        return ''
    return to_bj(value).strftime(fmt)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'test_system.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)

# 请求去重装饰器
def prevent_duplicate_requests(timeout=5):
    """
    防止短时间内重复请求的装饰器
    timeout: 请求间隔时间（秒）
    """
    def decorator(f):
        def wrapper(*args, **kwargs):
            if request.method == 'POST':
                request_key = f'last_request_{request.endpoint}'
                current_time = datetime.utcnow().timestamp()
                
                if request_key in session:
                    last_request_time = session[request_key]
                    if current_time - last_request_time < timeout:
                        logger.warning(f"检测到重复请求: {request.endpoint}, 间隔: {current_time - last_request_time:.2f}秒")
                        flash('请求过于频繁，请稍后再试', 'error')
                        if request.is_json:
                            return jsonify({'error': '请求过于频繁，请稍后再试'}), 429
                        return redirect(request.referrer or '/')
                
                session[request_key] = current_time
            
            return f(*args, **kwargs)
        wrapper.__name__ = f.__name__
        return wrapper
    return decorator

# 注册过滤器
app.jinja_env.filters['bjtime'] = bjtime_filter

# 数据库模型
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'teacher' or 'student'

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuestionBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # 'single_choice', 'multiple_choice', ...
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='bank', lazy=True, cascade="all, delete-orphan")

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_type = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200))  # 题目配图
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    option_e = db.Column(db.String(200))
    correct_answer = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    explanation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    single_choice_count = db.Column(db.Integer, default=0)
    multiple_choice_count = db.Column(db.Integer, default=0)
    true_false_count = db.Column(db.Integer, default=0)
    fill_blank_count = db.Column(db.Integer, default=0)
    short_answer_count = db.Column(db.Integer, default=0)
    single_choice_score = db.Column(db.Integer, default=0)
    multiple_choice_score = db.Column(db.Integer, default=0)
    true_false_score = db.Column(db.Integer, default=0)
    fill_blank_score = db.Column(db.Integer, default=0)
    short_answer_score = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # 新增：题库选择
    single_choice_bank_id = db.Column(db.Integer)
    multiple_choice_bank_id = db.Column(db.Integer)
    true_false_bank_id = db.Column(db.Integer)
    fill_blank_bank_id = db.Column(db.Integer)
    short_answer_bank_id = db.Column(db.Integer)
    
    # 新增：简答题指定题号（JSON格式存储，如 [{"id": 1, "score": 20}, {"id": 3, "score": 15}]）
    short_answer_questions = db.Column(db.Text)
    
    # 新增：是否允许学生自选测试内容
    allow_student_choice = db.Column(db.Boolean, default=False)
    
    # AI批改配置
    short_answer_grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    fill_blank_grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    
    # 新增：关联预设ID（用于学生自选测试内容）
    preset_id = db.Column(db.Integer, db.ForeignKey('test_preset.id'))

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_name = db.Column(db.String(100), nullable=False)
    class_number = db.Column(db.String(50), nullable=False)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    answers = db.Column(db.Text)
    ip_address = db.Column(db.String(15), nullable=True) # Added ip_address column
    test = db.relationship('Test', backref=db.backref('results', lazy=True))

class StudentTestHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student_name = db.Column(db.String(100), nullable=False)
    class_number = db.Column(db.String(50), nullable=False)
    test_count = db.Column(db.Integer, default=0)  # 总测试次数
    total_score = db.Column(db.Integer, default=0)  # 总分
    average_score = db.Column(db.Float, default=0.0)  # 平均分
    highest_score = db.Column(db.Integer, default=0)  # 最高分
    lowest_score = db.Column(db.Integer, default=0)  # 最低分
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- 新增：测试参数预设模型 ---
class TestPreset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    # 题量
    single_choice_count = db.Column(db.Integer, default=0)
    multiple_choice_count = db.Column(db.Integer, default=0)
    true_false_count = db.Column(db.Integer, default=0)
    fill_blank_count = db.Column(db.Integer, default=0)
    short_answer_count = db.Column(db.Integer, default=0)
    # 分值
    single_choice_score = db.Column(db.Integer, default=0)
    multiple_choice_score = db.Column(db.Integer, default=0)
    true_false_score = db.Column(db.Integer, default=0)
    fill_blank_score = db.Column(db.Integer, default=0)
    short_answer_score = db.Column(db.Integer, default=0)
    # 题库ID
    single_choice_bank_id = db.Column(db.Integer)
    multiple_choice_bank_id = db.Column(db.Integer)
    true_false_bank_id = db.Column(db.Integer)
    fill_blank_bank_id = db.Column(db.Integer)
    short_answer_bank_id = db.Column(db.Integer)
    
    # 新增：简答题指定题号（JSON格式存储）
    short_answer_questions = db.Column(db.Text)
    
    # 新增：是否允许学生自选测试内容
    allow_student_choice = db.Column(db.Boolean, default=False)
    
    # AI批改配置
    short_answer_grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    fill_blank_grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    
    # 试卷模式字段
    test_mode = db.Column(db.String(20), default='question_bank')  # 'question_bank' 或 'paper'
    paper_id = db.Column(db.Integer, db.ForeignKey('paper_bank.id'))
    duration_minutes = db.Column(db.Integer)  # 考试时长（分钟）
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ShortAnswerSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_answer = db.Column(db.Text, nullable=False)
    image_path = db.Column(db.String(200))
    score = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    graded_bool = db.Column(db.Boolean, default=False)
    # AI批改相关字段
    grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    ai_original_score = db.Column(db.Integer, nullable=True)  # AI原始评分
    ai_feedback = db.Column(db.Text, nullable=True)  # AI反馈
    manual_reviewed = db.Column(db.Boolean, default=False)  # 是否经过人工复核
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FillBlankSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    result_id = db.Column(db.Integer, db.ForeignKey('test_result.id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    student_answer = db.Column(db.Text, nullable=False)
    score = db.Column(db.Integer, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    graded_bool = db.Column(db.Boolean, default=False)
    # AI批改相关字段
    grading_method = db.Column(db.String(20), default='manual')  # 'manual' 或 'ai'
    ai_original_score = db.Column(db.Integer, nullable=True)  # AI原始评分
    ai_feedback = db.Column(db.Text, nullable=True)  # AI反馈
    manual_reviewed = db.Column(db.Boolean, default=False)  # 是否经过人工复核
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# --- 试卷模式相关模型 ---
class PaperBank(db.Model):
    """试卷库"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    paper_path = db.Column(db.String(500))  # 试卷文件路径
    answer_path = db.Column(db.String(500))  # 参考答案PDF路径
    excel_path = db.Column(db.String(500))  # 答题卡Excel配置文件路径
    answer_config = db.Column(db.Text)  # Excel答题卡配置JSON
    question_positions = db.Column(db.Text)  # PDF题号定位信息JSON: [{num, page, y}, ...]
    file_type = db.Column(db.String(20), default='pdf')  # 'pdf' 或 'image'
    page_count = db.Column(db.Integer, default=0)
    total_questions = db.Column(db.Integer, default=0)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class PaperExamRecord(db.Model):
    """试卷模式考试记录"""
    id = db.Column(db.Integer, primary_key=True)
    preset_id = db.Column(db.Integer, db.ForeignKey('test_preset.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    class_number = db.Column(db.String(50), nullable=False)
    answers_json = db.Column(db.Text)  # 学生作答JSON: {question_num: answer, ...}
    ai_grading_results = db.Column(db.Text)  # AI批改结果JSON
    total_score = db.Column(db.Float, default=0.0)
    is_submitted = db.Column(db.Boolean, default=False)
    submitted_at = db.Column(db.DateTime)
    auto_save_at = db.Column(db.DateTime)
    duration_used = db.Column(db.Integer)  # 实际用时（秒）
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    preset = db.relationship('TestPreset', backref=db.backref('paper_exams', lazy=True))
    student = db.relationship('User', backref=db.backref('paper_exams', lazy=True))

def shuffle_options(question):
    """
    返回题目选项的原始顺序
    """
    return {
        'content': question.content,
        'id': question.id,
        'score': question.score,
        'option_a': question.option_a,
        'option_b': question.option_b,
        'option_c': question.option_c,
        'option_d': question.option_d,
        'correct_answer': question.correct_answer,
        'original_correct_answer': question.correct_answer
    }

# 初始化数据库
def init_db():
    """
    初始化数据库，创建所有表和默认数据
    
    功能：
    1. 创建所有数据库表
    2. 创建默认教师账户（如果不存在）
    3. 提供错误处理和日志记录
    
    Returns:
        bool: 初始化是否成功
    """
    try:
        with app.app_context():
            # 创建所有表
            db.create_all()
            print("[OK] 数据库表创建成功")
            
            # 数据库迁移：添加新列到现有表
            try:
                # 检查并添加 test_preset 表的新列
                import sqlalchemy as sa
                inspector = sa.inspect(db.engine)
                
                # 获取 test_preset 表的列名
                preset_columns = [col['name'] for col in inspector.get_columns('test_preset')]
                
                # 添加 test_mode 列
                if 'test_mode' not in preset_columns:
                    db.session.execute(sa.text('ALTER TABLE test_preset ADD COLUMN test_mode VARCHAR(20) DEFAULT "question_bank"'))
                    print("[OK] 添加 test_preset.test_mode 列")
                
                # 添加 paper_id 列
                if 'paper_id' not in preset_columns:
                    db.session.execute(sa.text('ALTER TABLE test_preset ADD COLUMN paper_id INTEGER'))
                    print("[OK] 添加 test_preset.paper_id 列")
                
                # 添加 duration_minutes 列
                if 'duration_minutes' not in preset_columns:
                    db.session.execute(sa.text('ALTER TABLE test_preset ADD COLUMN duration_minutes INTEGER DEFAULT 120'))
                    print("[OK] 添加 test_preset.duration_minutes 列")
                
                # 检查 paper_bank 表
                paper_columns = [col['name'] for col in inspector.get_columns('paper_bank')]
                
                # 添加 paper_bank 表的新列
                if 'total_questions' not in paper_columns:
                    db.session.execute(sa.text('ALTER TABLE paper_bank ADD COLUMN total_questions INTEGER DEFAULT 0'))
                    print("[OK] 添加 paper_bank.total_questions 列")
                if 'page_count' not in paper_columns:
                    db.session.execute(sa.text('ALTER TABLE paper_bank ADD COLUMN page_count INTEGER DEFAULT 0'))
                    print("[OK] 添加 paper_bank.page_count 列")
                if 'excel_path' not in paper_columns:
                    db.session.execute(sa.text('ALTER TABLE paper_bank ADD COLUMN excel_path VARCHAR(500)'))
                    print("[OK] 添加 paper_bank.excel_path 列")
                
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"[WARN] 数据库迁移警告（可忽略）: {str(e)}")
            
            # 检查并创建默认教师账户
            admin = User.query.filter_by(username='admin', role='teacher').first()
            if not admin:
                admin = User(username='admin', role='teacher')
                admin.set_password('admin')
                db.session.add(admin)
                db.session.commit()
                print("[OK] 默认教师账户创建成功 (用户名: admin, 密码: admin)")
                print("[WARN] 请在首次登录后立即修改默认密码！")
            else:
                print("[OK] 默认教师账户已存在")
            
            print("[OK] 数据库初始化完成")
            return True
            
    except Exception as e:
        print(f"[ERR] 数据库初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

# 路由
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/teacher/login', methods=['GET', 'POST'])
@prevent_duplicate_requests(timeout=3)
def teacher_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 添加调试信息
        print(f"登录尝试：用户名={username}, 密码={password}")
        
        user = User.query.filter_by(username=username, role='teacher').first()
        print(f"查询到的用户：{user}")
        
        if user:
            print(f"用户存在，密码验证：{user.check_password(password)}")
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = 'teacher'
            print(f"登录成功，重定向到teacher_dashboard")
            return redirect(url_for('teacher_dashboard'))
        flash('用户名或密码错误', 'login_error')
        print(f"登录失败，用户名或密码错误")
    return render_template('teacher_login.html')

@app.route('/teacher/dashboard')
def teacher_dashboard():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    # 获取最新的测试设置
    last_test = Test.query.order_by(Test.created_at.desc()).first()
    
    # 获取各类型的题目
    single_choice_questions = Question.query.filter_by(question_type='single_choice').all()
    multiple_choice_questions = Question.query.filter_by(question_type='multiple_choice').all()
    true_false_questions = Question.query.filter_by(question_type='true_false').all()
    fill_blank_questions = Question.query.filter_by(question_type='fill_blank').all()
    short_answer_questions = Question.query.filter_by(question_type='short_answer').all()
    
    return render_template('teacher_dashboard.html',
                         last_test=last_test,
                         single_choice_questions=single_choice_questions,
                         multiple_choice_questions=multiple_choice_questions,
                         true_false_questions=true_false_questions,
                         fill_blank_questions=fill_blank_questions,
                         short_answer_questions=short_answer_questions,
                         last_import_filename=session.get('last_import_filename'),
                         last_import_filepath=session.get('last_import_filepath'))


@app.route('/teacher/bank/<int:bank_id>')
def teacher_bank(bank_id):
    """题库详情页面 - 查看和编辑题库中的题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    bank = QuestionBank.query.get_or_404(bank_id)
    questions = Question.query.filter_by(bank_id=bank_id).order_by(Question.id).all()
    
    # 添加题型显示名称
    type_display_map = {
        'single_choice': '单选题',
        'multiple_choice': '多选题',
        'true_false': '判断题',
        'fill_blank': '填空题',
        'short_answer': '简答题'
    }
    bank.question_type_display = type_display_map.get(bank.question_type, bank.question_type)
    
    return render_template('bank_content.html', bank=bank, questions=questions)


@app.route('/student/start', methods=['GET', 'POST'])
@prevent_duplicate_requests(timeout=3)
def student_start():
    if request.method == 'POST':
        name = request.form.get('name')
        class_number = request.form.get('class_number')
        test_content = request.form.get('test_content')  # 新增：获取学生选择的测试内容
        
        if not name or not class_number:
            flash('姓名和班级号不能为空')
            return render_template('student_start.html')
        
        # 验证姓名：只能是2-4个汉字
        import re
        if not re.match(r'^[\u4e00-\u9fa5]{2,4}$', name):
            flash('姓名只能是2-4个汉字')
            return render_template('student_start.html')
        
        # 验证班级号：只能是3位阿拉伯数字
        if not re.match(r'^\d{3}$', class_number):
            flash('班级号只能是3位阿拉伯数字')
            return render_template('student_start.html')
        
        # 标准化班级号：去除"班"字和前后空格，统一格式
        class_number = class_number.strip().replace('班', '').strip()
        
        # 获取当前测试设置
        current_test = Test.query.filter_by(is_active=True).first()
        allow_student_choice = current_test.allow_student_choice if current_test else False
        
        # 在创建学生账户前，先检查是否有可用的测试
        if test_content:
            # 学生选择了预设
            preset = TestPreset.query.get(test_content)
            if not preset:
                flash('选择的测试内容不存在，请联系管理员')
                return render_template('student_start.html')
        else:
            # 学生没有选择测试内容
            if allow_student_choice:
                # 如果设置了允许学生自选，但学生没有选择，提示错误
                flash('请选择测试内容后开始')
                return render_template('student_start.html')
            else:
                # 如果没有设置允许学生自选，自动查找最新保存的测试内容
                # 优先查找同名的试卷模式预设
                if current_test:
                    paper_preset = TestPreset.query.filter_by(title=current_test.title, test_mode='paper').first()
                    if paper_preset:
                        test_content = str(paper_preset.id)
                        preset = paper_preset
                    else:
                        # 查找最新的试卷模式预设
                        paper_preset = TestPreset.query.filter_by(test_mode='paper').order_by(TestPreset.created_at.desc()).first()
                        if paper_preset:
                            test_content = str(paper_preset.id)
                            preset = paper_preset
            
            # 如果还是没有找到预设，检查激活的测试是否有题目
            if not test_content and current_test:
                has_questions = (current_test.single_choice_count or 0) + \
                               (current_test.multiple_choice_count or 0) + \
                               (current_test.true_false_count or 0) + \
                               (current_test.fill_blank_count or 0) + \
                               (current_test.short_answer_count or 0) > 0
                
                if not has_questions:
                    # 如果激活的测试没有题目，查找可用的测试预设
                    latest_preset = TestPreset.query.order_by(TestPreset.created_at.desc()).first()
                    if latest_preset:
                        test_content = str(latest_preset.id)
                        preset = latest_preset
                    else:
                        flash('当前没有可用的测试，请联系管理员')
                        return render_template('student_start.html')
        
        # 试卷模式不需要检查 active test
        if test_content and getattr(preset, 'test_mode', 'question_bank') != 'paper':
            if not current_test:
                current_test = Test.query.order_by(Test.created_at.desc()).first()
            if not current_test:
                flash('当前没有可用的测试，请联系管理员')
                return render_template('student_start.html')
        
        username = f"{name}_{class_number}"
        student = User.query.filter_by(username=username, role='student').first()
        if not student:
            student = User(username=username, role='student')
            student.set_password(username)
            db.session.add(student)
            db.session.commit()
        
        session['student_id'] = student.id
        session['student_name'] = name
        session['class_number'] = class_number
        session['role'] = 'student'  # 明确设置学生角色
        session['selected_preset_id'] = test_content if test_content else None  # 新增：存储选择的预设ID
        
        # 检查是否为试卷模式
        if test_content:
            preset = TestPreset.query.get(int(test_content))
            if preset and getattr(preset, 'test_mode', 'question_bank') == 'paper':
                session['user_id'] = student.id
                # 直接跳转到试卷测试页面
                return redirect(url_for('student_paper_test', preset_id=test_content))
        
        return redirect(url_for('test'))
    return render_template('student_start.html')

@app.route('/api/check_student_history', methods=['POST'])
def check_student_history():
    """检查学生是否有历史记录"""
    data = request.get_json()
    name = data.get('name')
    class_number = data.get('class_number')
    
    # 验证姓名：只能是2-4个汉字
    import re
    if not name or not class_number or not re.match(r'^[\u4e00-\u9fa5]{2,4}$', name) or not re.match(r'^\d{3}$', class_number):
        return jsonify({'has_history': False})
    
    # 生成学生用户名
    username = f"{name}_{class_number}"
    # 检查是否存在学生记录
    student = User.query.filter_by(username=username, role='student').first()
    
    if not student:
        return jsonify({'has_history': False})
    
    # 检查是否有测试结果
    has_history = TestResult.query.filter_by(student_id=student.id).count() > 0
    
    return jsonify({'has_history': has_history})

@app.route('/student/history_login', methods=['POST'])
def student_history_login():
    """通过历史记录登录学生账户"""
    name = request.form.get('name')
    class_number = request.form.get('class_number')
    
    if not name or not class_number:
        flash('姓名和班级号不能为空')
        return redirect(url_for('index'))
    
    # 验证姓名：只能是2-4个汉字
    import re
    if not re.match(r'^[\u4e00-\u9fa5]{2,4}$', name):
        flash('姓名只能是2-4个汉字')
        return redirect(url_for('index'))
    
    # 验证班级号：只能是3位阿拉伯数字
    if not re.match(r'^\d{3}$', class_number):
        flash('班级号只能是3位阿拉伯数字')
        return redirect(url_for('index'))
    
    # 标准化班级号：去除"班"字和前后空格，统一格式
    class_number = class_number.strip().replace('班', '').strip()
    
    # 生成学生用户名
    username = f"{name}_{class_number}"
    # 检查是否存在学生记录
    student = User.query.filter_by(username=username, role='student').first()
    
    if not student:
        flash('未找到历史记录')
        return redirect(url_for('index'))
    
    # 检查是否有测试结果
    has_history = TestResult.query.filter_by(student_id=student.id).count() > 0
    
    if not has_history:
        flash('未找到历史记录')
        return redirect(url_for('index'))
    
    # 设置会话
    session['student_id'] = student.id
    session['user_id'] = student.id  # 新增：保持与student_start一致
    session['student_name'] = name
    session['class_number'] = class_number
    session['role'] = 'student'
    
    return redirect(url_for('student_dashboard'))

@app.route('/test')
def test():
    if 'student_id' not in session:
        return redirect(url_for('student_start'))
    
    # 获取学生选择的预设ID
    selected_preset_id = session.get('selected_preset_id')
    
    # 根据选择决定使用哪个测试配置
    if selected_preset_id:
        # 学生选择了预设，使用预设配置
        preset = TestPreset.query.get(selected_preset_id)
        if not preset:
            flash('选择的测试内容不存在')
            return redirect(url_for('student_start'))
        
        # 获取简答题指定题号配置
        short_answer_questions_config = None
        if preset.short_answer_questions:
            try:
                short_answer_questions_config = json.loads(preset.short_answer_questions)
            except:
                short_answer_questions_config = None
        
        # 使用预设配置创建临时测试对象
        test_config = {
            'title': preset.title,
            'single_choice_count': preset.single_choice_count or 0,
            'multiple_choice_count': preset.multiple_choice_count or 0,
            'true_false_count': preset.true_false_count or 0,
            'fill_blank_count': preset.fill_blank_count or 0,
            'short_answer_count': preset.short_answer_count or 0,
            'single_choice_score': preset.single_choice_score or 0,
            'multiple_choice_score': preset.multiple_choice_score or 0,
            'true_false_score': preset.true_false_score or 0,
            'fill_blank_score': preset.fill_blank_score or 0,
            'short_answer_score': preset.short_answer_score or 0,
            'single_choice_bank_id': preset.single_choice_bank_id,
            'multiple_choice_bank_id': preset.multiple_choice_bank_id,
            'true_false_bank_id': preset.true_false_bank_id,
            'fill_blank_bank_id': preset.fill_blank_bank_id,
            'short_answer_bank_id': preset.short_answer_bank_id,
            'short_answer_questions': short_answer_questions_config,
            'total_score': ((preset.single_choice_count or 0) * (preset.single_choice_score or 0) +
                          (preset.multiple_choice_count or 0) * (preset.multiple_choice_score or 0) +
                          (preset.true_false_count or 0) * (preset.true_false_score or 0) +
                          (preset.fill_blank_count or 0) * (preset.fill_blank_score or 0) +
                          (preset.short_answer_score or 0))
        }
    else:
        # 学生没有选择，使用当前激活的测试
        current_test = Test.query.filter_by(is_active=True).first()
        if not current_test:
            # 如果没有激活的测试，尝试获取最新的测试
            current_test = Test.query.order_by(Test.created_at.desc()).first()
            
        if not current_test:
            flash('当前没有可用的测试，请联系管理员')
            return redirect(url_for('student_start'))
        
        # 检查激活的测试是否有题目
        has_questions = (current_test.single_choice_count or 0) + \
                       (current_test.multiple_choice_count or 0) + \
                       (current_test.true_false_count or 0) + \
                       (current_test.fill_blank_count or 0) + \
                       (current_test.short_answer_count or 0) > 0
        
        # 如果激活的测试没有题目，尝试查找同名的试卷模式预设
        if not has_questions:
            paper_preset = TestPreset.query.filter(
                TestPreset.test_mode == 'paper',
                TestPreset.title == current_test.title
            ).first()
            
            if not paper_preset:
                # 尝试查找任意试卷模式预设
                paper_preset = TestPreset.query.filter_by(test_mode='paper').first()
            
            if paper_preset:
                # 找到试卷预设，直接跳转到试卷测试页面
                session['selected_preset_id'] = paper_preset.id
                return redirect(url_for('student_paper_test', preset_id=paper_preset.id))
            else:
                flash('当前测试没有题目，请选择测试内容后开始')
                return redirect(url_for('student_start'))
        
        # 获取简答题指定题号配置
        short_answer_questions_config = None
        if current_test.short_answer_questions:
            try:
                short_answer_questions_config = json.loads(current_test.short_answer_questions)
            except:
                short_answer_questions_config = None
        
        # 确保所有必要的字段都有默认值
        test_config = {
            'title': current_test.title or '默认测试',
            'single_choice_count': current_test.single_choice_count or 0,
            'multiple_choice_count': current_test.multiple_choice_count or 0,
            'true_false_count': current_test.true_false_count or 0,
            'fill_blank_count': current_test.fill_blank_count or 0,
            'short_answer_count': current_test.short_answer_count or 0,
            'single_choice_score': current_test.single_choice_score or 0,
            'multiple_choice_score': current_test.multiple_choice_score or 0,
            'true_false_score': current_test.true_false_score or 0,
            'fill_blank_score': current_test.fill_blank_score or 0,
            'short_answer_score': current_test.short_answer_score or 0,
            'single_choice_bank_id': current_test.single_choice_bank_id,
            'multiple_choice_bank_id': current_test.multiple_choice_bank_id,
            'true_false_bank_id': current_test.true_false_bank_id,
            'fill_blank_bank_id': current_test.fill_blank_bank_id,
            'short_answer_bank_id': current_test.short_answer_bank_id,
            'short_answer_questions': short_answer_questions_config,
            'total_score': current_test.total_score or 0
        }
    
    # 每次都重新抽题，不再判断是否已参加过
    def pick_questions(q_type, count, bank_id, specific_ids=None):
        # 如果有指定题号，优先使用指定题号获取题目
        if specific_ids and len(specific_ids) > 0:
            questions = []
            for item in specific_ids:
                q_id = item['id']
                q = Question.query.filter_by(id=q_id, question_type=q_type).first()
                if q:
                    # 将分值信息附加到题目对象上
                    q.custom_score = item['score']
                    questions.append(q)
            return questions
        
        # 如果没有指定题号，则检查count是否大于0
        if count <= 0:
            return []
        
        # 随机抽题（旧方式）
        q = Question.query.filter_by(question_type=q_type)
        if bank_id:
            q = q.filter_by(bank_id=bank_id)
        return q.order_by(func.random()).limit(count).all()

    single_choice_questions  = pick_questions('single_choice',  test_config['single_choice_count'],  test_config['single_choice_bank_id'])
    multiple_choice_questions = pick_questions('multiple_choice', test_config['multiple_choice_count'], test_config['multiple_choice_bank_id'])
    true_false_questions      = pick_questions('true_false',   test_config['true_false_count'],     test_config['true_false_bank_id'])
    fill_blank_questions      = pick_questions('fill_blank',   test_config['fill_blank_count'],     test_config['fill_blank_bank_id'])
    # 简答题使用指定题号
    short_answer_questions    = pick_questions('short_answer', test_config['short_answer_count'],   test_config['short_answer_bank_id'], test_config['short_answer_questions'])
    
    # 考试时长：预设优先，否则默认60分钟
    duration_minutes = 60
    if selected_preset_id:
        preset = TestPreset.query.get(selected_preset_id)
        if preset and getattr(preset, 'duration_minutes', None):
            duration_minutes = preset.duration_minutes
    
    return render_template('test.html', 
                         test=test_config,
                         test_title=test_config['title'],
                         duration_minutes=duration_minutes,
                         single_choice_questions=single_choice_questions,
                         multiple_choice_questions=multiple_choice_questions,
                         true_false_questions=true_false_questions,
                         fill_blank_questions=fill_blank_questions,
                         short_answer_questions=short_answer_questions)

@app.route('/api/test_auto_save', methods=['POST'])
def test_auto_save():
    """题库模式实时自动保存作答到本地session"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    data = request.get_json()
    if data and 'answers' in data:
        session['auto_saved_answers'] = data['answers']
        session.modified = True
        return jsonify({'success': True, 'message': '已保存'})
    return jsonify({'success': False, 'message': '无数据'}), 400

@app.route('/api/test_load_answers', methods=['GET'])
def test_load_answers():
    """加载题库模式自动保存的作答"""
    if 'student_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    answers = session.get('auto_saved_answers', {})
    return jsonify({'success': True, 'answers': answers})

@app.route('/submit_test', methods=['POST'])
def submit_test():
    if 'student_id' not in session:
        return redirect(url_for('student_start'))
    
    # 获取学生选择的预设ID
    selected_preset_id = session.get('selected_preset_id')
    
    # 根据选择决定使用哪个测试配置
    if selected_preset_id:
        # 学生选择了预设，使用预设配置
        preset = TestPreset.query.get(selected_preset_id)
        if not preset:
            flash('选择的测试内容不存在')
            return redirect(url_for('student_start'))
        
        # 使用预设配置创建临时测试对象
        test_config = {
            'single_choice_score': preset.single_choice_score,
            'multiple_choice_score': preset.multiple_choice_score,
            'true_false_score': preset.true_false_score,
            'fill_blank_score': preset.fill_blank_score,
            'short_answer_score': preset.short_answer_score
        }
    else:
        # 学生没有选择，使用当前激活的测试
        current_test = Test.query.filter_by(is_active=True).first()
        if not current_test:
            flash('当前没有进行中的测试')
            return redirect(url_for('student_dashboard'))
        test_config = current_test
        
    # 获取所有答案
    answers = {}
    fill_blank_questions_ids = set()  # 记录填空题的ID
    ai_scores = {}  # 存储AI批改的分数，提前初始化避免UnboundLocalError
    
    for key in request.form:
        if key.startswith('answer_'):
            parts = key.split('_')
            # 识别填空题的子字段（如 answer_123_1）
            if len(parts) > 2 and parts[2].isdigit():
                # 这是填空题的子字段，记录question_id但不处理
                question_id = int(parts[1])
                fill_blank_questions_ids.add(question_id)
                continue
            if parts[-1] == 'img' and parts[-2] == 'url':
                continue  # 图片URL字段，跳过
            question_id = int(parts[1])
            question = Question.query.get(question_id)
            values = request.form.getlist(key)
            if question and question.question_type == 'short_answer':
                # 简答题：直接保存原始内容（可能包含图片标签），不做大写转换，保留原始格式
                answers[question_id] = values[0] if values else ''
            elif len(values) == 1:
                answers[question_id] = values[0].strip().upper()
            else:
                # 多选题，拼接为逗号分隔的大写字母，顺序统一
                answers[question_id] = ','.join(sorted([v.strip().upper() for v in values if v.strip()]))
    
    # 处理填空题：从request.form中收集填空题答案
    for question_id in fill_blank_questions_ids:
        student_fill_ins = []
        for i in range(1, 5):  # 假设最多4个填空输入框
            student_answer = request.form.get(f'answer_{question_id}_{i}', '').strip()
            if student_answer:
                student_fill_ins.append(student_answer)
        # 将填空题答案添加到answers字典
        if student_fill_ins:
            answers[question_id] = '、'.join(student_fill_ins)
        else:
            answers[question_id] = ''  # 即使没有答案也要记录，以便显示
    
    # 计算得分
    total_score = 0
    
    # 获取批改方式配置，用于判断哪些题目需要AI批改
    short_answer_grading_method = 'manual'  # 默认人工批改
    fill_blank_grading_method = 'manual'  # 默认人工批改
    if selected_preset_id:
        preset = TestPreset.query.get(selected_preset_id)
        if preset:
            short_answer_grading_method = preset.short_answer_grading_method or 'manual'
            fill_blank_grading_method = preset.fill_blank_grading_method or 'manual'
    else:
        current_test = Test.query.filter_by(is_active=True).first()
        if current_test:
            short_answer_grading_method = current_test.short_answer_grading_method or 'manual'
            fill_blank_grading_method = current_test.fill_blank_grading_method or 'manual'
    
    for question_id, answer in answers.items():
        question = Question.query.get(question_id)
        if not question:
            continue
        
        # 判断是否需要AI批改
        need_ai_grading = False
        if question.question_type == 'short_answer' and short_answer_grading_method == 'ai':
            need_ai_grading = True
        elif question.question_type == 'fill_blank' and fill_blank_grading_method == 'ai':
            need_ai_grading = True
        
        if question.question_type == 'single_choice':
            # 选择题对比答案时忽略大小写
            if answer.strip().upper() == question.correct_answer.strip().upper():
                score = test_config.get('single_choice_score') if isinstance(test_config, dict) else test_config.single_choice_score
                total_score += score or 0
        elif question.question_type == 'multiple_choice':
            # 多选题忽略参考答案与填写答案之间间隔符号，忽略大小写
            def normalize(ans):
                # 支持多种分隔符：逗号、顿号、空格、斜杠等
                ans = ans.replace(',', '').replace('，', '').replace('、', '').replace(' ', '').replace('/', '').replace('\\', '')
                return ''.join(sorted([c for c in ans.upper() if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ']))
            is_correct = normalize(answer) == normalize(question.correct_answer)
            if is_correct:
                score = test_config.get('multiple_choice_score') if isinstance(test_config, dict) else test_config.multiple_choice_score
                total_score += score or 0
        elif question.question_type == 'true_false':
            # 判断题参考答案为对和错，支持多种表示方式
            def normalize_tf(ans):
                ans = ans.strip().lower()
                # 认为正确的答案：对、正确、是、√、true、1、对的、是的
                true_values = {'对', '正确', '是', '√', 'true', '1', '对的', '是的', '真', 't'}
                # 认为错误的答案：错、错误、否、×、false、0、错的、不是
                false_values = {'错', '错误', '否', '×', 'false', '0', '错的', '不是', '假', 'f'}
                if ans in true_values:
                    return '对'
                elif ans in false_values:
                    return '错'
                return ans
            
            if normalize_tf(answer) == normalize_tf(question.correct_answer):
                score = test_config.get('true_false_score') if isinstance(test_config, dict) else test_config.true_false_score
                total_score += score or 0
        elif question.question_type == 'fill_blank':
            # 只计算不需要AI批改的填空题分数
            if not need_ai_grading:
                # 处理填空题多个答案（仅用于非AI批改的情况）
                # 统一处理分隔符：支持顿号（、）、逗号（,）、斜杠（/）
                def split_fill_answers(text):
                    """分割答案，支持多种分隔符"""
                    # 先统一替换为顿号
                    text = text.replace(',', '、').replace('，', '、').replace('/', '、').replace('\\', '、')
                    return [f.strip().lower() for f in text.split('、') if f.strip()]
                
                correct_fill_ins = split_fill_answers(question.correct_answer)
                student_fill_ins = split_fill_answers(answer)
                num_fill_ins = len(correct_fill_ins)
                
                if num_fill_ins > 0:
                    score = test_config.get('fill_blank_score') if isinstance(test_config, dict) else test_config.fill_blank_score
                    score_per_fill_in = round((score or 0) / num_fill_ins, 1)
                    fill_blank_score = 0
                    
                    # 比较每个填空，忽略大小写
                    for i in range(min(len(student_fill_ins), num_fill_ins)):
                        if student_fill_ins[i] == correct_fill_ins[i]:
                            fill_blank_score += score_per_fill_in
                    
                    # 对填空题分数进行四舍五入
                    fill_blank_score = round(fill_blank_score)
                    total_score += fill_blank_score
        elif question.question_type == 'short_answer':
            # 简答题字数限制处理，无论是否AI批改都需要做
            student_answer = answers.get(question_id, '')
            
            # 限制字数：移除HTML标签后不超过600字
            import re
            text_only = re.sub(r'<[^>]*>', '', student_answer)
            if len(text_only) > 600:
                # 只处理文本部分，保留原始格式和图片
                img_tags = re.findall(r'<img[^>]*>', student_answer)
                if img_tags:
                    # 只保留最后一张图片
                    answers[question_id] = text_only[:600] + img_tags[-1]
                else:
                    answers[question_id] = text_only[:600]
            else:
                # 限制图片数量：只保留最后一张
                img_tags = re.findall(r'<img[^>]*>', student_answer)
                if len(img_tags) > 1:
                    # 移除所有图片，只保留最后一张，保留原始文本格式
                    text_without_imgs = re.sub(r'<img[^>]*>', '', student_answer)
                    answers[question_id] = text_without_imgs + img_tags[-1]
    # 题目循环结束后，只插入一次TestResult
    ip_addr = request.headers.get('X-Forwarded-For', request.remote_addr)
    
    # 确定test_id
    if selected_preset_id:
        # 使用预设时，需要创建一个特殊的测试记录
        preset = TestPreset.query.get(selected_preset_id)
        if preset:
            try:
                # 尝试查找是否已存在相同预设ID的测试记录
                existing_test = Test.query.filter_by(
                    preset_id=selected_preset_id,
                    is_active=False
                ).first()
                
                if existing_test:
                    # 如果存在相同预设ID的测试记录，直接复用
                    temp_test = existing_test
                    test_id = temp_test.id
                else:
                    # 如果不存在，创建新的测试记录
                    temp_test = Test(
                        title=preset.title,
                        single_choice_count=preset.single_choice_count or 0,
                        multiple_choice_count=preset.multiple_choice_count or 0,
                        true_false_count=preset.true_false_count or 0,
                        fill_blank_count=preset.fill_blank_count or 0,
                        short_answer_count=preset.short_answer_count or 0,
                        single_choice_score=preset.single_choice_score or 0,
                        multiple_choice_score=preset.multiple_choice_score or 0,
                        true_false_score=preset.true_false_score or 0,
                        fill_blank_score=preset.fill_blank_score or 0,
                        short_answer_score=preset.short_answer_score or 0,
                        total_score=((preset.single_choice_count or 0) * (preset.single_choice_score or 0) +
                                   (preset.multiple_choice_count or 0) * (preset.multiple_choice_score or 0) +
                                   (preset.true_false_count or 0) * (preset.true_false_score or 0) +
                                   (preset.fill_blank_count or 0) * (preset.fill_blank_score or 0) +
                                   (preset.short_answer_count or 0) * (preset.short_answer_score or 0)),
                        single_choice_bank_id=preset.single_choice_bank_id,
                        multiple_choice_bank_id=preset.multiple_choice_bank_id,
                        true_false_bank_id=preset.true_false_bank_id,
                        fill_blank_bank_id=preset.fill_blank_bank_id,
                        short_answer_bank_id=preset.short_answer_bank_id,
                        is_active=False,  # 标记为非活跃，避免影响正常测试
                        preset_id=selected_preset_id  # 关联预设ID
                    )
                    db.session.add(temp_test)
                    db.session.flush()  # 获取ID但不提交
                    test_id = temp_test.id
            except Exception as e:
                # 如果创建临时测试失败，记录错误并重定向
                print(f"创建临时测试失败: {e}")
                flash('创建测试记录失败，请重试')
                return redirect(url_for('student_start'))
        else:
            flash('选择的测试内容不存在')
            return redirect(url_for('student_start'))
    else:
        # 使用默认测试时，test_id为当前测试的ID
        if isinstance(test_config, dict):
            # 如果是字典格式，需要从数据库重新获取Test对象
            current_test = Test.query.filter_by(is_active=True).first()
            if not current_test:
                current_test = Test.query.order_by(Test.created_at.desc()).first()
            test_id = current_test.id if current_test else None
        else:
            # 如果是对象格式，直接获取ID
            test_id = test_config.id
    
    # 确保test_id不为None
    if test_id is None:
        flash('无法获取测试ID，请重试')
        return redirect(url_for('student_start'))
    
    # 获取批改方式配置
    short_answer_grading_method = 'manual'  # 默认人工批改
    fill_blank_grading_method = 'manual'  # 默认人工批改
    if selected_preset_id:
        preset = TestPreset.query.get(selected_preset_id)
        if preset:
            short_answer_grading_method = preset.short_answer_grading_method or 'manual'
            fill_blank_grading_method = preset.fill_blank_grading_method or 'manual'
    else:
        current_test = Test.query.filter_by(is_active=True).first()
        if current_test:
            short_answer_grading_method = current_test.short_answer_grading_method or 'manual'
            fill_blank_grading_method = current_test.fill_blank_grading_method or 'manual'
    
    # 准备AI批改服务
    ai_service = get_ai_grading_service()
    
    # 先进行AI批改（在数据库事务外）
    if ai_service.is_enabled():
        for question_id, answer in answers.items():
            question = Question.query.get(question_id)
            # 检查是否需要AI批改
            should_ai_grade = False
            if question.question_type == 'short_answer' and short_answer_grading_method == 'ai':
                should_ai_grade = True
            elif question.question_type == 'fill_blank' and fill_blank_grading_method == 'ai':
                should_ai_grade = True
            
            if question and should_ai_grade:
                try:
                    # 获取题目分值（优先使用自定义分数，否则使用配置中的分数）
                    question_score = 0
                    if question.question_type == 'short_answer':
                        # 优先从 short_answer_questions 配置中获取当前题目的自定义分值
                        question_score = 0
                        if isinstance(test_config, dict) and test_config.get('short_answer_questions'):
                            for q in test_config['short_answer_questions']:
                                if q['id'] == question_id:
                                    question_score = q['score']
                                    break
                        elif hasattr(test_config, 'short_answer_questions') and test_config.short_answer_questions:
                            try:
                                import json
                                short_answer_config = json.loads(test_config.short_answer_questions)
                                for q in short_answer_config:
                                    if q['id'] == question_id:
                                        question_score = q['score']
                                        break
                            except:
                                pass
                        
                        # 如果没有找到自定义分值，使用默认分值
                        if question_score == 0:
                            if isinstance(test_config, dict):
                                question_score = test_config.get('short_answer_score', 0)
                            else:
                                question_score = test_config.short_answer_score or 0
                    elif question.question_type == 'fill_blank':
                        if isinstance(test_config, dict):
                            question_score = test_config.get('fill_blank_score', 0)
                        else:
                            question_score = test_config.fill_blank_score or 0
                    
                    # 注意：不再使用题目本身的分值，严格按照教师面板设置计算
                    
                    # 调用AI批改服务
                    success, ai_result = ai_service.grade_answer(
                        question=question.content,
                        reference_answer=question.correct_answer,
                        student_answer=answer,
                        max_score=question_score,
                        question_type=question.question_type
                    )
                    
                    if success:
                        # 确保AI给出的分数不超过教师设置的分值
                        actual_score = min(ai_result['score'], question_score)
                        if actual_score != ai_result['score']:
                            logger.warning(f"AI给出的分数({ai_result['score']})超过设定分值({question_score})，已调整为{actual_score}")
                        
                        ai_scores[question_id] = {
                            'score': actual_score,
                            'feedback': ai_result['feedback'],
                            'success': True
                        }
                        # 将调整后的AI评分加入总分
                        total_score += actual_score
                        logger.info(f"AI批改成功 - 题目ID: {question_id}, 得分: {actual_score}/{question_score}")
                    else:
                        ai_scores[question_id] = {
                            'score': 0,
                            'feedback': f"AI批改失败: {ai_result.get('error_message', '未知错误')}",
                            'success': False
                        }
                        logger.error(f"AI批改失败 - 题目ID: {question_id}, 错误: {ai_result.get('error_message')}")
                        
                except Exception as e:
                    ai_scores[question_id] = {
                        'score': 0,
                        'feedback': f"AI批改异常: {str(e)}",
                        'success': False
                    }
                    logger.error(f"AI批改异常 - 题目ID: {question_id}, 异常: {str(e)}")
    
    # 使用单个事务保存所有数据
    try:
        # 对总分进行四舍五入，不保留小数
        final_score = round(total_score)
        
        # 创建测试结果记录
        result = TestResult(
            student_id=session['student_id'],
            student_name=session.get('student_name', ''),
            class_number=session.get('class_number', ''),
            test_id=test_id,
            score=final_score,
            answers=json.dumps(answers),
            ip_address=ip_addr
        )
        db.session.add(result)
        db.session.flush()  # 获取result.id但不提交
        
        # 创建简答题和填空题提交记录
        for question_id, answer in answers.items():
            question = Question.query.get(question_id)
            if question and question.question_type == 'short_answer':
                sa = ShortAnswerSubmission(
                    result_id=result.id,
                    question_id=question_id,
                    student_answer=answer,
                    image_path=None,
                    grading_method=short_answer_grading_method
                )
                
                # 如果有AI批改结果，使用它
                if question_id in ai_scores:
                    ai_result = ai_scores[question_id]
                    sa.score = ai_result['score']
                    sa.comment = ai_result['feedback']
                    sa.graded_bool = True
                    
                    if ai_result['success']:
                        sa.ai_original_score = ai_result['score']
                        sa.ai_feedback = ai_result['feedback']
                
                db.session.add(sa)
            elif question and question.question_type == 'fill_blank':
                fb = FillBlankSubmission(
                    result_id=result.id,
                    question_id=question_id,
                    student_answer=answer,
                    grading_method=fill_blank_grading_method
                )
                
                # 如果有AI批改结果，使用它
                if question_id in ai_scores:
                    ai_result = ai_scores[question_id]
                    fb.score = ai_result['score']
                    fb.comment = ai_result['feedback']
                    fb.graded_bool = True
                    
                    if ai_result['success']:
                        fb.ai_original_score = ai_result['score']
                        fb.ai_feedback = ai_result['feedback']
                        # 如果有简短理由，将其保存到comment字段的开头
                        if 'short_reason' in ai_result and ai_result['short_reason']:
                            short_reason = ai_result['short_reason'].strip()
                            if short_reason:
                                fb.comment = f"扣分理由：{short_reason}。{ai_result['feedback']}"
                else:
                    # 如果没有AI批改，使用传统的填空题评分逻辑
                    # 这里需要计算填空题的分数
                    def split_fill_answers(text):
                        """分割答案，支持顿号和逗号"""
                        text = text.replace(',', '、')
                        return [f.strip().lower() for f in text.split('、') if f.strip()]
                    
                    correct_fill_ins = split_fill_answers(question.correct_answer)
                    student_fill_ins = split_fill_answers(answer)
                    num_fill_ins = len(correct_fill_ins)
                    
                    if num_fill_ins > 0:
                        if isinstance(test_config, dict):
                            total_fill_score = test_config.get('fill_blank_score', 0)
                        else:
                            total_fill_score = test_config.fill_blank_score or 0
                        
                        score_per_fill_in = round((total_fill_score or 0) / num_fill_ins, 1)
                        fill_blank_score = 0
                        
                        # 比较每个填空
                        for i in range(min(len(student_fill_ins), num_fill_ins)):
                            if student_fill_ins[i] == correct_fill_ins[i]:
                                fill_blank_score += score_per_fill_in
                        
                        fb.score = round(fill_blank_score)
                        fb.graded_bool = True
                
                db.session.add(fb)
        
        # 一次性提交所有更改
        db.session.commit()
        logger.info(f"测试提交成功 - 学生: {session.get('student_name')}, 总分: {total_score}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"数据库保存失败: {str(e)}")
        flash('提交失败，请重试')
        return redirect(url_for('test'))

    # 统计历史
    all_results = TestResult.query.filter_by(student_id=session['student_id']).all()
    test_count = len(all_results)
    total_score_sum = sum(r.score for r in all_results)
    average_score = round(total_score_sum / test_count) if test_count > 0 else 0
    highest_score = max((r.score for r in all_results), default=0)
    lowest_score = min((r.score for r in all_results), default=0)

    history = StudentTestHistory.query.filter_by(student_id=session['student_id']).first()
    if not history:
        history = StudentTestHistory(
            student_id=session['student_id'],
            student_name=session.get('student_name', ''),
            class_number=session.get('class_number', ''),
        )
        db.session.add(history)

    history.test_count = test_count
    history.total_score = total_score_sum
    history.average_score = average_score
    history.highest_score = highest_score
    history.lowest_score = lowest_score

    db.session.commit()
        
    flash('测试提交成功！')
    
    return redirect(url_for('student_dashboard'))

@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' not in session:
        return redirect(url_for('student_start'))
    
    # 获取学生信息
    student = User.query.get(session['student_id'])
    
    # 获取当前测试
    current_test = Test.query.filter_by(is_active=True).first()
    
    # 如果激活的测试没有题目，尝试查找同名的试卷模式预设
    if current_test:
        has_questions = (current_test.single_choice_count or 0) + \
                       (current_test.multiple_choice_count or 0) + \
                       (current_test.true_false_count or 0) + \
                       (current_test.fill_blank_count or 0) + \
                       (current_test.short_answer_count or 0) > 0
        
        if not has_questions:
            paper_preset = TestPreset.query.filter(
                TestPreset.test_mode == 'paper',
                TestPreset.title == current_test.title
            ).first()
            
            if paper_preset and paper_preset.paper_id:
                paper_bank = PaperBank.query.get(paper_preset.paper_id)
                if paper_bank and paper_bank.answer_config:
                    single_count = multi_count = tf_count = fb_count = sa_count = 0
                    single_score = multi_score = tf_score = fb_score = sa_score = 0
                    total_score_val = 0
                    try:
                        answer_config = json.loads(paper_bank.answer_config) if isinstance(paper_bank.answer_config, str) else paper_bank.answer_config
                        
                        for q in answer_config:
                            q_type = q.get('type', '')
                            q_score = q.get('score', 0)
                            total_score_val += q_score
                            
                            if q_type in ['单选', 'single_choice']:
                                single_count += 1
                                single_score = q_score
                            elif q_type in ['多选', 'multiple_choice']:
                                multi_count += 1
                                multi_score = q_score
                            elif q_type in ['判断', 'true_false', '判断题']:
                                tf_count += 1
                                tf_score = q_score
                            elif q_type in ['填空', 'fill_blank', '填空题']:
                                fb_count += 1
                                fb_score = q_score
                            elif q_type in ['简答', 'short_answer', '简答题', '问答', '问答题']:
                                sa_count += 1
                                sa_score = q_score
                        
                        # 创建模拟的测试对象
                        class MockTest:
                            title = current_test.title
                            single_choice_count = single_count
                            multiple_choice_count = multi_count
                            true_false_count = tf_count
                            fill_blank_count = fb_count
                            short_answer_count = sa_count
                            single_choice_score = single_score
                            multiple_choice_score = multi_score
                            true_false_score = tf_score
                            fill_blank_score = fb_score
                            short_answer_score = sa_score
                            total_score = total_score_val
                        
                        current_test = MockTest()
                        current_test.is_paper_mode = True
                        current_test.paper_preset_id = paper_preset.id
                    except Exception as e:
                        print(f"解析试卷配置失败: {e}")
    
    # 获取学生历史记录
    history = StudentTestHistory.query.filter_by(
        student_id=session['student_id']
    ).first()
    
    if not history:
        history = StudentTestHistory(
            student_id=session['student_id'],
            student_name=session.get('student_name', ''),
            class_number=session.get('class_number', ''),
            test_count=0,
            total_score=0,
            average_score=0.0,
            highest_score=0,
            lowest_score=0
        )
        db.session.add(history)
        db.session.commit()
    
    # 获取学生的测试结果（题库模式）
    test_results = TestResult.query.filter_by(
        student_id=session['student_id']
    ).order_by(TestResult.created_at.desc()).all()
    
    # 获取学生的试卷模式考试记录
    paper_exam_records = PaperExamRecord.query.filter_by(
        student_id=session['student_id'],
        is_submitted=True
    ).order_by(PaperExamRecord.submitted_at.desc()).all()
    
    # 组装试卷历史数据
    paper_history = []
    for record in paper_exam_records:
        preset = TestPreset.query.get(record.preset_id)
        paper_bank = PaperBank.query.get(preset.paper_id) if preset and preset.paper_id else None
        
        # 从答题卡配置中读取各题型信息
        question_stats = {'单选题': 0, '多选题': 0, '判断题': 0, '填空题': 0, '简答题': 0}
        single_score = multi_score = tf_score = fb_score = sa_score = 0
        total_possible = 0
        
        if paper_bank and paper_bank.answer_config:
            try:
                answer_config = json.loads(paper_bank.answer_config) if isinstance(paper_bank.answer_config, str) else paper_bank.answer_config
                for q in answer_config:
                    q_type = q.get('type', '')
                    q_score = q.get('score', 0)
                    total_possible += q_score
                    
                    if q_type in ['单选', 'single_choice']:
                        question_stats['单选题'] += 1
                        single_score = q_score
                    elif q_type in ['多选', 'multiple_choice']:
                        question_stats['多选题'] += 1
                        multi_score = q_score
                    elif q_type in ['判断', 'true_false', '判断题']:
                        question_stats['判断题'] += 1
                        tf_score = q_score
                    elif q_type in ['填空', 'fill_blank', '填空题']:
                        question_stats['填空题'] += 1
                        fb_score = q_score
                    elif q_type in ['简答', 'short_answer', '简答题', '问答', '问答题']:
                        question_stats['简答题'] += 1
                        sa_score = q_score
            except Exception as e:
                print(f"解析答题卡配置失败: {e}")
        
        # 时区转换：UTC转北京时间(UTC+8)
        local_submitted_at = '未知'
        if record.submitted_at:
            # 保存的是UTC时间，需要加8小时转换为北京时间
            import time
            timestamp = time.mktime(record.submitted_at.timetuple()) + 8 * 3600  # 加8小时
            beijing_time = datetime.fromtimestamp(timestamp)
            local_submitted_at = beijing_time.strftime('%Y-%m-%d %H:%M:%S')
        
        paper_history.append({
            'exam_id': record.id,
            'preset_id': record.preset_id,
            'title': preset.title if preset else ('试卷#' + str(record.preset_id)),
            'total_score': record.total_score or 0,
            'total_possible': total_possible,
            'submitted_at': local_submitted_at,
            'duration_used': record.duration_used or 0,
        })
    
    # 合并统计到 history
    paper_count = len(paper_exam_records)
    if paper_count > 0:
        paper_scores = [r['total_score'] for r in paper_history]
        history.test_count += paper_count
        combined_total = (history.total_score or 0) + sum(paper_scores)
        combined_count = history.test_count
        history.average_score = round(combined_total / combined_count, 1) if combined_count > 0 else 0
        history.highest_score = max(history.highest_score or 0, max(paper_scores))
    
    return render_template('student_dashboard.html',
                         student=student,
                         current_test=current_test,
                         history=history,
                         test_results=test_results,
                         paper_history=paper_history)

@app.route('/test_statistics')
def test_statistics():
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    # 获取所有考试及人次
    tests = Test.query.order_by(Test.created_at.desc()).all()
    
    # 统一按标题合并测试
    merged_tests = {}
    
    for t in tests:
        key = t.title
        
        if key not in merged_tests:
            merged_tests[key] = {
                'test': t,
                'count': 0,
                'test_ids': []
            }
        merged_tests[key]['test_ids'].append(t.id)
        cnt = TestResult.query.filter_by(test_id=t.id).count()
        merged_tests[key]['count'] += cnt
    
    # 转换为列表并按创建时间排序
    data = list(merged_tests.values())
    data.sort(key=lambda x: x['test'].created_at, reverse=True)
    
    return render_template('test_statistics.html', tests=data) 

@app.route('/test_statistics/<int:test_id>')
def get_test_statistics(test_id):
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    # 获取测试信息
    test = Test.query.get(test_id)
    if not test:
        flash('测试不存在', 'error')
        return redirect(url_for('test_statistics'))
    
    # 获取所有相同标题的测试ID
    test_ids = [t.id for t in Test.query.filter_by(title=test.title).all()]
    
    # 获取所有相关测试结果
    results = TestResult.query.filter(TestResult.test_id.in_(test_ids)).order_by(TestResult.class_number, TestResult.student_name, TestResult.created_at).all()
    
    # 按班级分组统计
    class_stats = {}
    class_students = {}
    for result in results:
        # 统计数据
        if result.class_number not in class_stats:
            class_stats[result.class_number] = {
                'student_count': 0,
                'total_score': 0,
                'scores': [],
                'pass_count': 0
            }
        stats = class_stats[result.class_number]
        stats['student_count'] += 1
        stats['total_score'] += result.score
        stats['scores'].append(result.score)
        if result.score >= 60:
            stats['pass_count'] += 1
        # 学生成绩明细
        if result.class_number not in class_students:
            class_students[result.class_number] = []
        class_students[result.class_number].append({
            'name': result.student_name,
            'score': result.score,
            'submit_time': to_bj(result.created_at).strftime('%Y-%m-%d %H:%M:%S'),
            'ip': result.ip_address,
            'result_id': result.id
        })
    # 计算每个班级的统计数据
    statistics = []
    for class_number, stats in class_stats.items():
        if stats['student_count'] > 0:
            statistics.append({
                'class_number': class_number,
                'student_count': stats['student_count'],
                'average_score': stats['total_score'] / stats['student_count'],
                'max_score': max(stats['scores']),
                'min_score': min(stats['scores']),
                'pass_rate': stats['pass_count'] / stats['student_count']
            })
    statistics.sort(key=lambda x: x['class_number'])
    # 按班级号排序
    class_students = dict(sorted(class_students.items(), key=lambda x: x[0]))
    # 统计每道题的错误率
    question_stats = defaultdict(lambda: {'total': 0, 'wrong': 0, 'content': '', 'question_type': '', 'correct_answer': ''})
    for result in results:
        answers = json.loads(result.answers)
        for qid_str, stu_ans in answers.items():
            qid = int(qid_str)
            question = Question.query.get(qid)
            if not question:
                continue
            question_stats[qid]['total'] += 1
            question_stats[qid]['content'] = question.content
            question_stats[qid]['question_type'] = question.question_type
            question_stats[qid]['correct_answer'] = question.correct_answer
            # 判定正误（与 test_result 逻辑一致）
            is_wrong = False
            if question.question_type == 'single_choice':
                is_wrong = stu_ans != question.correct_answer
            elif question.question_type == 'multiple_choice':
                def normalize(ans):
                    return ''.join(sorted([c for c in ans.replace(',', '').replace(' ', '').upper() if c in 'ABCDE']))
                is_wrong = normalize(stu_ans) != normalize(question.correct_answer)
            elif question.question_type == 'true_false':
                is_wrong = stu_ans != question.correct_answer
            elif question.question_type == 'fill_blank':
                def norm_fill(s):
                    parts = [p.strip().lower() for p in s.replace('、', ',').split(',') if p.strip()]
                    return ','.join(parts)
                is_wrong = norm_fill(stu_ans) != norm_fill(question.correct_answer)
            # 简答题暂不统计
            if is_wrong:
                question_stats[qid]['wrong'] += 1
    # 计算错误率并排序
    error_questions = []
    for qid, stat in question_stats.items():
        if stat['total'] > 0:
            error_rate = stat['wrong'] / stat['total']
            question = Question.query.get(qid) # 重新获取question对象以访问选项
            if question:
                q_data = {
                    'id': qid,
                    'content': stat['content'],
                    'question_type': stat['question_type'],
                    'correct_answer': stat['correct_answer'],
                    'error_rate': error_rate,
                    'wrong_count': stat['wrong'],
                    'total_count': stat['total']
                }
                if question.question_type in ['single_choice', 'multiple_choice']:
                    q_data['option_a'] = question.option_a
                    q_data['option_b'] = question.option_b
                    q_data['option_c'] = question.option_c
                    q_data['option_d'] = question.option_d
                    if question.question_type == 'multiple_choice':
                        q_data['option_e'] = question.option_e
                error_questions.append(q_data)
    error_questions.sort(key=lambda x: x['error_rate'], reverse=True)
    top_error_questions = error_questions[:10]
    return render_template('test_statistics_detail.html', statistics=statistics, class_students=class_students, top_error_questions=top_error_questions)


@app.route('/delete_test/<int:test_id>', methods=['POST'])
def delete_test(test_id):
    """删除测试及其所有相关数据"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    try:
        test = Test.query.get(test_id)
        if not test:
            flash('测试不存在', 'error')
            return redirect(url_for('test_statistics'))
        
        # 获取所有相同标题的测试ID
        same_title_tests = Test.query.filter_by(title=test.title).all()
        test_ids_to_delete = [t.id for t in same_title_tests]
        
        # 删除测试相关的所有数据
        for tid in test_ids_to_delete:
            # 1. 删除简答题提交记录
            for result in TestResult.query.filter_by(test_id=tid).all():
                ShortAnswerSubmission.query.filter_by(result_id=result.id).delete()
                FillBlankSubmission.query.filter_by(result_id=result.id).delete()
            
            # 2. 删除测试结果
            TestResult.query.filter_by(test_id=tid).delete()
            
            # 3. 删除测试配置
            test_to_delete = Test.query.get(tid)
            if test_to_delete:
                db.session.delete(test_to_delete)
        
        db.session.commit()
        # flash('测试及其所有成绩已删除', 'success')  # 移除成功提示
        
    except Exception as e:
        db.session.rollback()
        flash(f'删除失败: {str(e)}', 'error')
    
    return redirect(url_for('test_statistics'))


@app.route('/test_result/<int:result_id>')
def test_result(result_id):
    # 获取测试结果
    result = TestResult.query.get_or_404(result_id)
    
    # 检查权限：学生只能查看自己的，教师可以查看所有
    if 'role' not in session:
        return redirect(url_for('student_start'))
    
    if session.get('role') == 'teacher':
        # 教师可以查看所有学生的答题详情
        pass
    elif session.get('role') == 'student':
        # 学生只能查看自己的
        if 'student_id' not in session or result.student_id != session['student_id']:
            flash('无权访问此测试结果')
            return redirect(url_for('student_dashboard'))
    else:
        flash('无权访问此测试结果')
        return redirect(url_for('student_start'))
    
    # 获取测试信息
    test = Test.query.get(result.test_id)
    
    # 获取学生信息
    if session.get('role') == 'teacher':
        # 教师查看时，从 result 中获取学生信息
        student_id = result.student_id
        student = User.query.get(student_id)
        # 教师查看时也获取学生历史记录
        history = StudentTestHistory.query.filter_by(
            student_id=student_id
        ).first()
    else:
        # 学生查看自己的
        student = User.query.get(session['student_id'])
        history = StudentTestHistory.query.filter_by(
            student_id=session['student_id']
        ).first()
    
    # 获取题目详情
    questions = []
    answers = json.loads(result.answers)
    
    for question_id, answer in answers.items():
        question = Question.query.get(int(question_id))
        if question:
            is_correct = None  # 默认为None，简答题不判断对错
            score = 0
            comment = None
            
            if question.question_type == 'single_choice':
                is_correct = answer == question.correct_answer
                score = test.single_choice_score if is_correct else 0
            elif question.question_type == 'multiple_choice':
                def normalize(ans):
                    return ''.join(sorted([c for c in ans.replace(',', '').replace(' ', '').upper() if c in 'ABCDE']))
                is_correct = normalize(answer) == normalize(question.correct_answer)
                score = test.multiple_choice_score if is_correct else 0
            elif question.question_type == 'true_false':
                is_correct = answer == question.correct_answer
                score = test.true_false_score if is_correct else 0
            elif question.question_type == 'fill_blank':
                # 首先尝试从FillBlankSubmission表中获取评分信息
                fill_blank_submission = FillBlankSubmission.query.filter_by(
                    result_id=result.id,
                    question_id=question.id
                ).first()
                
                if fill_blank_submission:
                    # 如果有提交记录，使用记录中的分数
                    score = fill_blank_submission.score or 0
                    comment = fill_blank_submission.comment
                    is_correct = (score == test.fill_blank_score)
                else:
                    # 如果没有提交记录，使用传统的填空题评分逻辑
                    # 统一处理分隔符：支持顿号（、）和逗号（,）
                    def split_answers(text):
                        """分割答案，支持顿号和逗号"""
                        # 先统一替换为顿号
                        text = text.replace(',', '、')
                        return [f.strip().lower() for f in text.split('、') if f.strip()]
                    
                    correct_fill_ins = split_answers(question.correct_answer)
                    student_fill_ins = split_answers(answer)
                    num_fill_ins = len(correct_fill_ins)
                    
                    if num_fill_ins > 0:
                        score_per_fill_in = round(test.fill_blank_score / num_fill_ins, 1)
                        score = 0
                        
                        # 比较每个填空
                        for i in range(min(len(student_fill_ins), num_fill_ins)):
                            if student_fill_ins[i] == correct_fill_ins[i]:
                                score += score_per_fill_in
                        
                        # 判断是否全对
                        is_correct = (score == test.fill_blank_score)
                    else:
                        score = 0
                        is_correct = False
            elif question.question_type == 'short_answer':
                # 简答题不判断对错，保持is_correct为None
                # 从ShortAnswerSubmission表中获取评分和评语
                submission = ShortAnswerSubmission.query.filter_by(
                    result_id=result.id,
                    question_id=question.id
                ).first()
                if submission:
                    score = submission.score
                    comment = submission.comment
            
            # 为简答题和填空题添加AI批改相关信息
            grading_method = None
            ai_original_score = None
            ai_feedback = None
            manual_reviewed = False
            
            if question.question_type == 'short_answer' and submission:
                grading_method = submission.grading_method
                ai_original_score = submission.ai_original_score
                ai_feedback = submission.ai_feedback
                manual_reviewed = submission.manual_reviewed
            elif question.question_type == 'fill_blank' and fill_blank_submission:
                grading_method = fill_blank_submission.grading_method
                ai_original_score = fill_blank_submission.ai_original_score
                ai_feedback = fill_blank_submission.ai_feedback
                manual_reviewed = fill_blank_submission.manual_reviewed
            
            questions.append({
                'id': question.id,
                'content': question.content,
                'question_type': question.question_type,
                'option_a': question.option_a,
                'option_b': question.option_b,
                'option_c': question.option_c,
                'option_d': question.option_d,
                'student_answer': answer,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct,
                'score': score,
                'comment': comment,
                'explanation': question.explanation,
                # AI批改相关字段
                'grading_method': grading_method,
                'ai_original_score': ai_original_score,
                'ai_feedback': ai_feedback,
                'manual_reviewed': manual_reviewed
            })
    
    return render_template('test_result.html',
                         test=test,
                         result=result,
                         student=student,
                         history=history,
                         questions=questions,
                         is_teacher=session.get('role') == 'teacher',
                         test_id=test.id if test else None)

@app.route('/grade_short_answer_by_result', methods=['POST'])
def grade_short_answer_by_result():
    if 'role' not in session or session['role'] != 'teacher':
        flash('未授权')
        return redirect(url_for('teacher_login'))
    
    result_id = request.form.get('result_id')
    question_id = request.form.get('question_id')
    score = int(request.form.get('score'))
    comment = request.form.get('comment')
    
    try:
        # 更新简答题评分
        submission = ShortAnswerSubmission.query.filter_by(
            result_id=result_id,
            question_id=question_id
        ).first()
        
        if not submission:
            # 如果没有找到记录，创建一个新的
            submission = ShortAnswerSubmission(
                result_id=result_id,
                question_id=question_id,
                student_answer='',  # 这里不需要学生答案，因为已经在answers字段中
                score=score,
                comment=comment,
                graded_bool=True
            )
            db.session.add(submission)
        else:
            submission.score = score
            submission.comment = comment
            submission.graded_bool = True
            # 如果是AI批改的题目，标记为已人工复核
            if submission.grading_method == 'ai':
                submission.manual_reviewed = True
        
        # 重新计算测试结果的总分
        result = TestResult.query.get(result_id)
        test = Test.query.get(result.test_id)
        answers = json.loads(result.answers)
        
        total_score = 0
        for qid_str, answer in answers.items():
            qid = int(qid_str)
            question = Question.query.get(qid)
            if not question:
                continue
            
            if question.question_type == 'single_choice':
                if answer == question.correct_answer:
                    total_score += test.single_choice_score
            elif question.question_type == 'multiple_choice':
                def normalize(ans):
                    return ''.join(sorted([c for c in ans.replace(',', '').replace(' ', '').upper() if c in 'ABCDE']))
                if normalize(answer) == normalize(question.correct_answer):
                    total_score += test.multiple_choice_score
            elif question.question_type == 'true_false':
                if answer == question.correct_answer:
                    total_score += test.true_false_score
            elif question.question_type == 'fill_blank':
                def norm_fill(s):
                    parts = [p.strip().lower() for p in s.replace('、', ',').split(',') if p.strip()]
                    return ','.join(parts)
                if norm_fill(answer) == norm_fill(question.correct_answer):
                    total_score += test.fill_blank_score
            elif question.question_type == 'short_answer':
                # 从ShortAnswerSubmission表中获取评分
                sa_submission = ShortAnswerSubmission.query.filter_by(
                    result_id=result_id,
                    question_id=qid
                ).first()
                if sa_submission and sa_submission.score is not None:
                    total_score += sa_submission.score
        
        # 更新测试结果的总分（四舍五入）
        result.score = round(total_score)
        db.session.commit()
        
        # 更新学生历史记录
        student_id = result.student_id
        all_results = TestResult.query.filter_by(student_id=student_id).all()
        test_count = len(all_results)
        total_score_sum = sum(r.score for r in all_results)
        average_score = round(total_score_sum / test_count) if test_count > 0 else 0
        highest_score = max((r.score for r in all_results), default=0)
        lowest_score = min((r.score for r in all_results), default=0)
        
        history = StudentTestHistory.query.filter_by(student_id=student_id).first()
        if history:
            history.test_count = test_count
            history.total_score = total_score_sum
            history.average_score = average_score
            history.highest_score = highest_score
            history.lowest_score = lowest_score
            db.session.commit()
        

    except Exception as e:
        db.session.rollback()
        flash(f'评分失败：{str(e)}')
    
    return redirect(url_for('test_result', result_id=result_id))

@app.route('/grade_fill_blank/<int:question_id>/<int:result_id>', methods=['POST'])
def grade_fill_blank(question_id, result_id):
    """填空题评分路由"""
    if 'role' not in session or session['role'] != 'teacher':
        flash('未授权')
        return redirect(url_for('teacher_login'))
    
    score = int(request.form.get('score'))
    comment = request.form.get('comment')
    
    try:
        # 更新填空题评分
        submission = FillBlankSubmission.query.filter_by(
            result_id=result_id,
            question_id=question_id
        ).first()
        
        if not submission:
            # 如果没有找到记录，创建一个新的
            submission = FillBlankSubmission(
                result_id=result_id,
                question_id=question_id,
                student_answer='',  # 这里不需要学生答案，因为已经在answers字段中
                score=score,
                comment=comment,
                graded_bool=True
            )
            db.session.add(submission)
        else:
            submission.score = score
            submission.comment = comment
            submission.graded_bool = True
            # 如果是AI批改的题目，标记为已人工复核
            if submission.grading_method == 'ai':
                submission.manual_reviewed = True
        
        # 重新计算测试结果的总分
        result = TestResult.query.get(result_id)
        test = Test.query.get(result.test_id)
        answers = json.loads(result.answers)
        
        total_score = 0
        for qid_str, answer in answers.items():
            qid = int(qid_str)
            question = Question.query.get(qid)
            if not question:
                continue
            
            if question.question_type == 'single_choice':
                if answer == question.correct_answer:
                    total_score += test.single_choice_score
            elif question.question_type == 'multiple_choice':
                def normalize(ans):
                    return ''.join(sorted([c for c in ans.replace(',', '').replace(' ', '').upper() if c in 'ABCDE']))
                if normalize(answer) == normalize(question.correct_answer):
                    total_score += test.multiple_choice_score
            elif question.question_type == 'true_false':
                if answer == question.correct_answer:
                    total_score += test.true_false_score
            elif question.question_type == 'fill_blank':
                # 从FillBlankSubmission表中获取评分
                fb_submission = FillBlankSubmission.query.filter_by(
                    result_id=result_id,
                    question_id=qid
                ).first()
                if fb_submission and fb_submission.score is not None:
                    total_score += fb_submission.score
                else:
                    # 如果没有提交记录，使用传统评分
                    def norm_fill(s):
                        parts = [p.strip().lower() for p in s.replace('、', ',').split(',') if p.strip()]
                        return ','.join(parts)
                    if norm_fill(answer) == norm_fill(question.correct_answer):
                        total_score += test.fill_blank_score
            elif question.question_type == 'short_answer':
                # 从ShortAnswerSubmission表中获取评分
                sa_submission = ShortAnswerSubmission.query.filter_by(
                    result_id=result_id,
                    question_id=qid
                ).first()
                if sa_submission and sa_submission.score is not None:
                    total_score += sa_submission.score
        
        # 更新测试结果的总分（四舍五入）
        result.score = round(total_score)
        db.session.commit()
        
        # 更新学生历史记录
        student_id = result.student_id
        all_results = TestResult.query.filter_by(student_id=student_id).all()
        test_count = len(all_results)
        total_score_sum = sum(r.score for r in all_results)
        average_score = round(total_score_sum / test_count) if test_count > 0 else 0
        highest_score = max((r.score for r in all_results), default=0)
        lowest_score = min((r.score for r in all_results), default=0)
        
        history = StudentTestHistory.query.filter_by(student_id=student_id).first()
        if history:
            history.test_count = test_count
            history.total_score = total_score_sum
            history.average_score = average_score
            history.highest_score = highest_score
        history.lowest_score = lowest_score
        db.session.commit()
        

    
    except Exception as e:
        db.session.rollback()
        flash(f'评分失败：{str(e)}')
    
    return redirect(url_for('test_result', result_id=result_id))

@app.route('/import_questions/<question_type>', methods=['POST'])
def import_questions(question_type):
    """
    导入题库文件（CSV 或 Excel 格式）
    
    Args:
        question_type: 题目类型 (single_choice, multiple_choice, true_false, fill_blank, short_answer)
    
    Returns:
        JSON 响应，包含导入结果
    """
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    # 验证题目类型
    valid_types = ['single_choice', 'multiple_choice', 'true_false', 'fill_blank', 'short_answer']
    if question_type not in valid_types:
        return jsonify({'success': False, 'message': f'无效的题目类型: {question_type}'}), 400
    
    # 检查文件是否存在
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': '未找到上传文件'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': '未选择文件'}), 400
    
    # 获取题库名称
    bank_name = request.form.get('bank_name', f'{question_type}_bank_{datetime.utcnow().strftime("%Y%m%d_%H%M%S")}')
    
    try:
        # 根据文件扩展名判断文件类型
        # 先从原始文件名获取扩展名，避免 secure_filename 处理后丢失
        original_filename = file.filename
        if '.' not in original_filename:
            return jsonify({'success': False, 'message': '文件名缺少扩展名。请使用 .csv、.xlsx 或 .xls 文件'}), 400
        
        file_ext = original_filename.rsplit('.', 1)[1].lower()
        
        if file_ext not in ['csv', 'xlsx', 'xls']:
            return jsonify({'success': False, 'message': f'不支持的文件格式: {file_ext}。仅支持 CSV 和 Excel 文件'}), 400
        
        # 使用 secure_filename 处理文件名（用于日志和显示）
        filename = secure_filename(original_filename)
        
        # 读取文件内容
        if file_ext == 'csv':
            try:
                df = pd.read_csv(file, encoding='utf-8')
            except UnicodeDecodeError:
                try:
                    df = pd.read_csv(file, encoding='gbk')
                except Exception as e:
                    return jsonify({'success': False, 'message': f'CSV 文件编码错误，请使用 UTF-8 或 GBK 编码: {str(e)}'}), 400
        else:  # xlsx or xls
            try:
                df = pd.read_excel(file)
            except Exception as e:
                return jsonify({'success': False, 'message': f'Excel 文件读取失败: {str(e)}'}), 400
        
        # 根据题型定义不同的列名要求（用于选项验证）
        if question_type == 'single_choice':
            # 单选题需要验证选项A/B/C/D
            required_options = ['选项A', '选项B', '选项C', '选项D']
        elif question_type == 'multiple_choice':
            # 多选题需要验证选项A/B/C/D，选项E可选
            required_options = ['选项A', '选项B', '选项C', '选项D']
        else:
            required_options = []
        
        # 验证选择题的选项列
        if required_options:
            missing_options = [opt for opt in required_options if opt not in df.columns]
            if missing_options:
                available_cols = ', '.join(df.columns.tolist())
                return jsonify({
                    'success': False,
                    'message': f'缺少必需的选项列: {", ".join(missing_options)}。文件中的列: {available_cols}'
                }), 400
        
        # 验证必需的列 - 支持灵活的列名映射
        def find_column_mapping(df_columns, possible_names):
            """查找列名映射，支持多种可能的列名"""
            for possible_name in possible_names:
                if possible_name in df_columns:
                    return possible_name
            return None
        
        # 创建列名映射
        column_mapping = {}
        
        # 根据题型定义可能的列名
        if question_type == 'single_choice':
            content_possibilities = ['题干', '题目', '题目内容']
            answer_possibilities = ['正确答案', '答案']
            score_possibilities = ['分值', '分数']
            explanation_possibilities = ['答案解析', '解析', '说明']
        elif question_type == 'multiple_choice':
            content_possibilities = ['题干', '题目', '题目内容']
            answer_possibilities = ['正确答案', '答案']
            score_possibilities = ['分值', '分数']
            explanation_possibilities = ['解析', '答案解析', '说明']
        elif question_type == 'true_false':
            content_possibilities = ['题干', '题目', '题目内容']
            answer_possibilities = ['正确答案', '答案']
            score_possibilities = ['分值', '分数']
            explanation_possibilities = ['解析', '答案解析', '说明']
        elif question_type == 'fill_blank':
            content_possibilities = ['题干', '题目', '题目内容']
            answer_possibilities = ['正确答案', '答案']
            score_possibilities = ['分值', '分数']
            explanation_possibilities = ['解析', '答案解析', '说明']
        elif question_type == 'short_answer':
            content_possibilities = ['题目', '题干', '题目内容']
            answer_possibilities = ['答题要求', '参考答案', '正确答案', '答案']
            score_possibilities = ['分值', '分数']
            explanation_possibilities = ['解析', '答案解析', '说明']
        
        # 查找实际的列名
        content_col = find_column_mapping(df.columns, content_possibilities)
        answer_col = find_column_mapping(df.columns, answer_possibilities)
        score_col = find_column_mapping(df.columns, score_possibilities)
        explanation_col = find_column_mapping(df.columns, explanation_possibilities)
        
        # 验证必需的列是否存在
        missing_columns = []
        if not content_col:
            missing_columns.append(f"题目内容列（支持：{', '.join(content_possibilities)}）")
        
        # 对于简答题，答案和分值是可选的
        if question_type != 'short_answer':
            if not answer_col:
                missing_columns.append(f"答案列（支持：{', '.join(answer_possibilities)}）")
            if not score_col:
                missing_columns.append(f"分值列（支持：{', '.join(score_possibilities)}）")
        else:
            # 简答题的答案和分值列是可选的，但如果存在就使用
            if not answer_col:
                # 如果没有找到答案列，使用空字符串作为默认值
                answer_col = None
            if not score_col:
                # 如果没有找到分值列，使用0作为默认值
                score_col = None
        
        if missing_columns:
            available_cols = ', '.join(df.columns.tolist())
            return jsonify({
                'success': False,
                'message': f'缺少必需的列: {"; ".join(missing_columns)}。文件中的列: {available_cols}'
            }), 400
        
        # 创建或获取题库
        question_bank = QuestionBank.query.filter_by(name=bank_name, question_type=question_type).first()
        if not question_bank:
            question_bank = QuestionBank(name=bank_name, question_type=question_type)
            db.session.add(question_bank)
            db.session.flush()  # 获取 ID
        
        # 导入题目
        imported_count = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # 验证必填字段 - 题目内容始终必填
                if pd.isna(row[content_col]) or str(row[content_col]).strip() == '':
                    errors.append(f'第 {index + 2} 行：题目内容不能为空')
                    continue
                
                # 对于简答题，允许参考答案、分值、解析为空
                if question_type == 'short_answer':
                    # 简答题只要求题目内容不为空
                    content = str(row[content_col]).strip()
                    
                    # 处理答案列：如果列不存在或为空，使用空字符串
                    if answer_col and not pd.isna(row[answer_col]):
                        answer = str(row[answer_col]).strip()
                    else:
                        answer = ''
                    
                    # 处理分值列：如果列不存在或为空，使用0
                    if score_col and not pd.isna(row[score_col]) and str(row[score_col]).strip() != '':
                        try:
                            score = int(row[score_col])
                            if score < 0:
                                score = 0  # 负数分值设为0
                        except (ValueError, TypeError):
                            score = 0  # 无效分值设为0
                    else:
                        score = 0
                else:
                    # 其他题型要求答案和分值不为空
                    if pd.isna(row[answer_col]) or str(row[answer_col]).strip() == '':
                        errors.append(f'第 {index + 2} 行：正确答案不能为空')
                        continue
                    
                    if pd.isna(row[score_col]):
                        errors.append(f'第 {index + 2} 行：分值不能为空')
                        continue
                    
                    try:
                        score = int(row[score_col])
                        if score < 0:
                            errors.append(f'第 {index + 2} 行：分值不能为负数')
                            continue
                    except (ValueError, TypeError):
                        errors.append(f'第 {index + 2} 行：分值必须为有效数字')
                        continue
                    
                    content = str(row[content_col]).strip()
                    answer = str(row[answer_col]).strip()
                
                # 创建题目对象
                question = Question(
                    question_type=question_type,
                    content=content,
                    correct_answer=answer,
                    score=score,
                    bank_id=question_bank.id
                )
                
                # 设置选项（如果有）
                if question_type in ['single_choice', 'multiple_choice']:
                    question.option_a = str(row.get('选项A', '')).strip() if not pd.isna(row.get('选项A')) else ''
                    question.option_b = str(row.get('选项B', '')).strip() if not pd.isna(row.get('选项B')) else ''
                    question.option_c = str(row.get('选项C', '')).strip() if not pd.isna(row.get('选项C')) else ''
                    question.option_d = str(row.get('选项D', '')).strip() if not pd.isna(row.get('选项D')) else ''
                    if question_type == 'multiple_choice':
                        question.option_e = str(row.get('选项E', '')).strip() if not pd.isna(row.get('选项E')) else ''
                
                # 设置解析（可选）
                if explanation_col and explanation_col in df.columns and not pd.isna(row[explanation_col]):
                    question.explanation = str(row[explanation_col]).strip()
                
                # 设置图片路径（可选）
                if '图片' in df.columns and not pd.isna(row['图片']):
                    question.image_path = str(row['图片']).strip()
                
                db.session.add(question)
                imported_count += 1
                
            except Exception as e:
                errors.append(f'第 {index + 2} 行导入失败: {str(e)}')
                continue
        
        # 提交事务
        db.session.commit()
        
        # 构建响应消息
        message = f'成功导入 {imported_count} 道题目到题库 "{bank_name}"'
        if errors:
            message += f'\n\n遇到 {len(errors)} 个错误：\n' + '\n'.join(errors[:10])
            if len(errors) > 10:
                message += f'\n... 还有 {len(errors) - 10} 个错误'
        
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'error_count': len(errors),
            'bank_id': question_bank.id,
            'bank_name': bank_name
        })
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_detail = traceback.format_exc()
        print(f"导入失败: {error_detail}")
        return jsonify({'success': False, 'message': f'导入失败: {str(e)}'}), 500


@app.route('/api/question_banks')
def get_question_banks():
    """获取所有题库列表"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    banks = QuestionBank.query.order_by(QuestionBank.created_at.desc()).all()
    return jsonify({
        'success': True,
        'banks': [{
            'id': bank.id,
            'name': bank.name,
            'question_type': bank.question_type,
            'question_count': len(bank.questions),
            'created_at': to_bj(bank.created_at).strftime('%Y-%m-%d %H:%M:%S')
        } for bank in banks]
    })


@app.route('/api/question_count/<question_type>')
def get_question_count(question_type):
    """获取指定类型的题目总数"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    count = Question.query.filter_by(question_type=question_type).count()
    return jsonify({'success': True, 'count': count})


@app.route('/api/bank/<int:bank_id>/rename', methods=['POST'])
def rename_bank(bank_id):
    """重命名题库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    try:
        data = request.get_json()
        new_name = data.get('name', '').strip()
        
        if not new_name:
            return jsonify({'success': False, 'message': '题库名称不能为空'}), 400
        
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return jsonify({'success': False, 'message': '题库不存在'}), 404
        
        # 检查同类型题库是否已存在相同名称
        existing = QuestionBank.query.filter_by(
            name=new_name,
            question_type=bank.question_type
        ).filter(QuestionBank.id != bank_id).first()
        
        if existing:
            return jsonify({'success': False, 'message': f'该题型下已存在名为"{new_name}"的题库'}), 400
        
        bank.name = new_name
        db.session.commit()
        
        return jsonify({'success': True, 'message': '重命名成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'重命名失败: {str(e)}'}), 500


@app.route('/api/bank/<int:bank_id>', methods=['DELETE'])
def delete_bank(bank_id):
    """删除题库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    try:
        bank = QuestionBank.query.get(bank_id)
        if not bank:
            return jsonify({'success': False, 'message': '题库不存在'}), 404
        
        # 删除题库（级联删除所有题目）
        db.session.delete(bank)
        db.session.commit()
        
        return jsonify({'success': True, 'message': '删除成功'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@app.route('/export_bank/<int:bank_id>')
def export_bank(bank_id):
    """导出题库为Excel文件"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('teacher_login'))
    
    try:
        # 获取题库信息
        bank = QuestionBank.query.get_or_404(bank_id)
        questions = Question.query.filter_by(bank_id=bank_id).order_by(Question.id).all()
        
        if not questions:
            flash('题库为空，无法导出', 'warning')
            return redirect(url_for('teacher_bank', bank_id=bank_id))
        
        # 根据题型准备数据
        question_type = bank.question_type
        data = []
        
        if question_type in ['single_choice', 'multiple_choice']:
            # 选择题格式
            for q in questions:
                data.append({
                    '题目': q.content,
                    '选项A': q.option_a or '',
                    '选项B': q.option_b or '',
                    '选项C': q.option_c or '',
                    '选项D': q.option_d or '',
                    '正确答案': q.correct_answer,
                    '分值': q.score,
                    '解析': q.explanation or ''
                })
        elif question_type == 'true_false':
            # 判断题格式
            for q in questions:
                data.append({
                    '题目': q.content,
                    '正确答案': q.correct_answer,
                    '分值': q.score,
                    '解析': q.explanation or ''
                })
        elif question_type == 'fill_blank':
            # 填空题格式
            for q in questions:
                data.append({
                    '题目': q.content,
                    '正确答案': q.correct_answer,
                    '分值': q.score,
                    '解析': q.explanation or ''
                })
        elif question_type == 'short_answer':
            # 简答题格式
            for q in questions:
                data.append({
                    '题目': q.content,
                    '参考答案': q.correct_answer or '',
                    '分值': q.score,
                    '解析': q.explanation or ''
                })
        
        # 创建DataFrame
        df = pd.DataFrame(data)
        
        # 创建Excel文件到内存
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='题库')
        output.seek(0)
        
        # 生成文件名
        type_names = {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'true_false': '判断题',
            'fill_blank': '填空题',
            'short_answer': '简答题'
        }
        type_name = type_names.get(question_type, question_type)
        filename = f"{bank.name}_{type_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.error(f"导出题库失败: {str(e)}")
        flash(f'导出失败: {str(e)}', 'danger')
        return redirect(url_for('teacher_bank', bank_id=bank_id))


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


@app.route('/api/question/<question_id>', methods=['GET', 'POST', 'DELETE'])
def manage_question(question_id):
    """获取、更新或删除单个题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    if request.method == 'GET':
        # 获取题目详情
        if question_id == 'new':
            return jsonify({'success': False, 'message': '无效的题目ID'}), 400
        
        question = Question.query.get(question_id)
        if not question:
            return jsonify({'success': False, 'message': '题目不存在'}), 404
        
        return jsonify({
            'success': True,
            'id': question.id,
            'content': question.content,
            'option_a': question.option_a,
            'option_b': question.option_b,
            'option_c': question.option_c,
            'option_d': question.option_d,
            'option_e': question.option_e,
            'correct_answer': question.correct_answer,
            'score': question.score,
            'explanation': question.explanation,
            'image_path': question.image_path,
            'question_type': question.question_type,
            'bank_id': question.bank_id
        })
    
    elif request.method == 'POST':
        # 创建或更新题目
        try:
            # 获取表单数据
            content = request.form.get('content', '').strip()
            if not content:
                return jsonify({'success': False, 'message': '题目内容不能为空'}), 400
            
            if question_id == 'new':
                # 创建新题目
                bank_id = request.form.get('bank_id')
                question_type = request.form.get('question_type')
                
                if not bank_id or not question_type:
                    return jsonify({'success': False, 'message': '缺少必要参数'}), 400
                
                question = Question(
                    question_type=question_type,
                    bank_id=int(bank_id)
                )
            else:
                # 更新现有题目
                question = Question.query.get(question_id)
                if not question:
                    return jsonify({'success': False, 'message': '题目不存在'}), 404
            
            # 更新字段
            question.content = content
            question.correct_answer = request.form.get('correct_answer', '').strip()
            question.score = int(request.form.get('score', 0))
            question.explanation = request.form.get('explanation', '').strip() or None
            
            # 更新选项（如果是选择题）
            if question.question_type in ['single_choice', 'multiple_choice']:
                question.option_a = request.form.get('option_a', '').strip() or None
                question.option_b = request.form.get('option_b', '').strip() or None
                question.option_c = request.form.get('option_c', '').strip() or None
                question.option_d = request.form.get('option_d', '').strip() or None
                if question.question_type == 'multiple_choice':
                    question.option_e = request.form.get('option_e', '').strip() or None
            
            if question_id == 'new':
                db.session.add(question)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': '保存成功', 'id': question.id})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500
    
    elif request.method == 'DELETE':
        # 删除题目
        try:
            if question_id == 'new':
                return jsonify({'success': False, 'message': '无效的题目ID'}), 400
            
            question = Question.query.get(question_id)
            if not question:
                return jsonify({'success': False, 'message': '题目不存在'}), 404
            
            db.session.delete(question)
            db.session.commit()
            
            return jsonify({'success': True, 'message': '删除成功'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@app.route('/api/question_bank/<int:bank_id>/questions', methods=['GET', 'POST'])
def manage_bank_questions(bank_id):
    """获取或更新题库中的题目"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    bank = QuestionBank.query.get(bank_id)
    if not bank:
        return jsonify({'success': False, 'message': '题库不存在'}), 404
    
    if request.method == 'GET':
        # 获取题库内容
        questions = Question.query.filter_by(bank_id=bank_id).order_by(Question.id).all()
        return jsonify({
            'success': True,
            'bank_id': bank.id,
            'bank_name': bank.name,
            'question_type': bank.question_type,
            'questions': [{
                'id': q.id,
                'content': q.content,
                'option_a': q.option_a,
                'option_b': q.option_b,
                'option_c': q.option_c,
                'option_d': q.option_d,
                'option_e': q.option_e,
                'correct_answer': q.correct_answer,
                'score': q.score,
                'explanation': q.explanation,
                'image_path': q.image_path
            } for q in questions]
        })
    
    else:  # POST - 更新题库内容
        try:
            data = request.get_json()
            questions_data = data.get('questions', [])
            
            # 删除现有题目
            Question.query.filter_by(bank_id=bank_id).delete()
            
            # 添加新题目
            for q_data in questions_data:
                # 跳过空题目
                if not q_data.get('content', '').strip():
                    continue
                
                question = Question(
                    question_type=bank.question_type,
                    content=q_data.get('content', '').strip(),
                    option_a=q_data.get('option_a', '').strip() if q_data.get('option_a') else None,
                    option_b=q_data.get('option_b', '').strip() if q_data.get('option_b') else None,
                    option_c=q_data.get('option_c', '').strip() if q_data.get('option_c') else None,
                    option_d=q_data.get('option_d', '').strip() if q_data.get('option_d') else None,
                    option_e=q_data.get('option_e', '').strip() if q_data.get('option_e') else None,
                    correct_answer=q_data.get('correct_answer', '').strip(),
                    score=int(q_data.get('score', 0)) if q_data.get('score') else 0,
                    explanation=q_data.get('explanation', '').strip() if q_data.get('explanation') else None,
                    bank_id=bank_id
                )
                db.session.add(question)
            
            db.session.commit()
            
            return jsonify({'success': True, 'message': '保存成功'})
            
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@app.route('/save_test_settings', methods=['POST'])
def save_test_settings():
    """
    保存测试配置
    
    功能：
    1. 验证所有必填字段
    2. 验证题库中有足够的题目
    3. 自动计算总分
    4. 保存配置或预设
    
    Returns:
        JSON 响应，包含保存结果
    """
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    try:
        # 获取表单数据
        title = request.form.get('test_title', '').strip()
        
        # 获取各题型的配置
        single_choice_count = int(request.form.get('single_choice_count', 0))
        multiple_choice_count = int(request.form.get('multiple_choice_count', 0))
        true_false_count = int(request.form.get('true_false_count', 0))
        fill_blank_count = int(request.form.get('fill_blank_count', 0))
        
        # 处理简答题：新方式 - 获取题号和分值数组
        short_answer_ids = request.form.getlist('short_answer_ids')
        short_answer_scores = request.form.getlist('short_answer_scores')
        
        # 调试日志
        import sys
        print('表单数据 - 简答题ID:', short_answer_ids, file=sys.stderr)
        print('表单数据 - 简答题分值:', short_answer_scores, file=sys.stderr)
        
        # 构建简答题配置（过滤空值）
        short_answer_questions = []
        for i in range(len(short_answer_ids)):
            q_id = short_answer_ids[i].strip()
            q_score = short_answer_scores[i].strip() if i < len(short_answer_scores) else ''
            if q_id and q_score:
                try:
                    short_answer_questions.append({
                        'id': int(q_id),
                        'score': int(q_score)
                    })
                except ValueError:
                    pass
        
        # 简答题数量为配置的题目数量
        short_answer_count = len(short_answer_questions)
        # 将简答题配置转换为 JSON 字符串
        short_answer_questions_json = json.dumps(short_answer_questions) if short_answer_questions else None
        
        # 调试日志
        print('构建的简答题配置:', short_answer_questions, file=sys.stderr)
        print('保存的JSON:', short_answer_questions_json, file=sys.stderr)
        
        # 其他题型的分值
        single_choice_score = int(request.form.get('single_choice_score', 0))
        multiple_choice_score = int(request.form.get('multiple_choice_score', 0))
        true_false_score = int(request.form.get('true_false_score', 0))
        fill_blank_score = int(request.form.get('fill_blank_score', 0))
        # 简答题使用配置中各题的总分（后端不再使用统一分值）
        short_answer_score = sum(q['score'] for q in short_answer_questions) if short_answer_questions else 0
        
        single_choice_bank_id = request.form.get('single_choice_bank')
        multiple_choice_bank_id = request.form.get('multiple_choice_bank')
        true_false_bank_id = request.form.get('true_false_bank')
        fill_blank_bank_id = request.form.get('fill_blank_bank')
        short_answer_bank_id = request.form.get('short_answer_bank')
        
        # 试卷模式字段
        test_mode = request.form.get('test_mode', 'question_bank')
        paper_id = request.form.get('paper_id')
        duration_minutes = request.form.get('duration_minutes')
        
        # 试卷模式下清空题库相关字段
        if test_mode == 'paper':
            single_choice_count = 0
            multiple_choice_count = 0
            true_false_count = 0
            fill_blank_count = 0
            short_answer_count = 0
            single_choice_score = 0
            multiple_choice_score = 0
            true_false_score = 0
            fill_blank_score = 0
            short_answer_score = 0
            short_answer_questions_json = None
            single_choice_bank_id = None
            multiple_choice_bank_id = None
            true_false_bank_id = None
            fill_blank_bank_id = None
            short_answer_bank_id = None
        
        allow_student_choice = request.form.get('allow_student_choice') == 'true'
        
        # 获取AI批改方式设置
        short_answer_grading_method = request.form.get('short_answer_grading_method', 'manual')
        fill_blank_grading_method = request.form.get('fill_blank_grading_method', 'manual')
        
        # 验证AI批改方式的有效性
        if short_answer_grading_method not in ['manual', 'ai']:
            short_answer_grading_method = 'manual'
        if fill_blank_grading_method not in ['manual', 'ai']:
            fill_blank_grading_method = 'manual'
        
        # 如果选择了AI批改但AI服务不可用，强制使用人工批改
        warnings = []
        ai_service = get_ai_grading_service()
        if short_answer_grading_method == 'ai' and not ai_service.is_enabled():
            short_answer_grading_method = 'manual'
            warnings.append('简答题AI批改功能不可用，已自动切换为人工批改')
        if fill_blank_grading_method == 'ai' and not ai_service.is_enabled():
            fill_blank_grading_method = 'manual'
            warnings.append('填空题AI批改功能不可用，已自动切换为人工批改')
        
        # 总是保存为预设，使用测试标题作为预设名
        save_as_preset = True
        preset_name = title
        
        # 验证必填字段
        if not title:
            return jsonify({'success': False, 'message': '测试标题不能为空'}), 400
        
        # 验证至少有一种题型（仅题库模式需要检查）
        if test_mode != 'paper':
            total_questions = (single_choice_count + multiple_choice_count + 
                              true_false_count + fill_blank_count + short_answer_count)
            if total_questions == 0:
                return jsonify({'success': False, 'message': '至少需要设置一种题型的题目数量'}), 400
        
        # 验证题库中有足够的题目
        validation_errors = []
        
        if single_choice_count > 0:
            if not single_choice_bank_id:
                validation_errors.append('单选题：未选择题库')
            else:
                available = Question.query.filter_by(
                    question_type='single_choice',
                    bank_id=int(single_choice_bank_id)
                ).count()
                if available < single_choice_count:
                    validation_errors.append(f'单选题：题库中只有 {available} 道题，需要 {single_choice_count} 道')
        
        if multiple_choice_count > 0:
            if not multiple_choice_bank_id:
                validation_errors.append('多选题：未选择题库')
            else:
                available = Question.query.filter_by(
                    question_type='multiple_choice',
                    bank_id=int(multiple_choice_bank_id)
                ).count()
                if available < multiple_choice_count:
                    validation_errors.append(f'多选题：题库中只有 {available} 道题，需要 {multiple_choice_count} 道')
        
        if true_false_count > 0:
            if not true_false_bank_id:
                validation_errors.append('判断题：未选择题库')
            else:
                available = Question.query.filter_by(
                    question_type='true_false',
                    bank_id=int(true_false_bank_id)
                ).count()
                if available < true_false_count:
                    validation_errors.append(f'判断题：题库中只有 {available} 道题，需要 {true_false_count} 道')
        
        if fill_blank_count > 0:
            if not fill_blank_bank_id:
                validation_errors.append('填空题：未选择题库')
            else:
                available = Question.query.filter_by(
                    question_type='fill_blank',
                    bank_id=int(fill_blank_bank_id)
                ).count()
                if available < fill_blank_count:
                    validation_errors.append(f'填空题：题库中只有 {available} 道题，需要 {fill_blank_count} 道')
        
        # 验证简答题题号是否存在于题库中
        if short_answer_count > 0:
            if not short_answer_bank_id:
                validation_errors.append('简答题：未选择题库')
            else:
                # 验证每个题号是否存在于题库中
                bank_id = int(short_answer_bank_id)
                for q in short_answer_questions:
                    exists = Question.query.filter_by(
                        id=q['id'],
                        question_type='short_answer',
                        bank_id=bank_id
                    ).first()
                    if not exists:
                        validation_errors.append(f'简答题：题号 {q["id"]} 不存在于所选题库中')
        
        if validation_errors:
            return jsonify({
                'success': False,
                'message': '验证失败',
                'errors': validation_errors
            }), 400
        
        # 检查分数设置警告
        if single_choice_count > 0 and single_choice_score == 0:
            warnings.append('单选题：题目数量大于0，但每题分数为0')
        if multiple_choice_count > 0 and multiple_choice_score == 0:
            warnings.append('多选题：题目数量大于0，但每题分数为0')
        if true_false_count > 0 and true_false_score == 0:
            warnings.append('判断题：题目数量大于0，但每题分数为0')
        if fill_blank_count > 0 and fill_blank_score == 0:
            warnings.append('填空题：题目数量大于0，但每题分数为0')
        if short_answer_count > 0 and short_answer_score == 0:
            warnings.append('简答题：题目数量大于0，但总分分数为0')
        
        # 自动计算总分
        total_score = (
            single_choice_count * single_choice_score +
            multiple_choice_count * multiple_choice_score +
            true_false_count * true_false_score +
            fill_blank_count * fill_blank_score +
            short_answer_score
        )
        
        # 总是保存为预设（使用测试标题作为预设名）
        # 查找是否存在相同标题的预设
        preset = TestPreset.query.filter_by(title=preset_name).first()
        
        if preset:
            # 更新现有预设
            preset.single_choice_count = single_choice_count
            preset.multiple_choice_count = multiple_choice_count
            preset.true_false_count = true_false_count
            preset.fill_blank_count = fill_blank_count
            preset.short_answer_count = short_answer_count
            preset.single_choice_score = single_choice_score
            preset.multiple_choice_score = multiple_choice_score
            preset.true_false_score = true_false_score
            preset.fill_blank_score = fill_blank_score
            preset.short_answer_score = short_answer_score
            preset.single_choice_bank_id = int(single_choice_bank_id) if single_choice_bank_id else None
            preset.multiple_choice_bank_id = int(multiple_choice_bank_id) if multiple_choice_bank_id else None
            preset.true_false_bank_id = int(true_false_bank_id) if true_false_bank_id else None
            preset.fill_blank_bank_id = int(fill_blank_bank_id) if fill_blank_bank_id else None
            preset.short_answer_bank_id = int(short_answer_bank_id) if short_answer_bank_id else None
            preset.short_answer_questions = short_answer_questions_json
            preset.allow_student_choice = allow_student_choice
            preset.short_answer_grading_method = short_answer_grading_method
            preset.fill_blank_grading_method = fill_blank_grading_method
            preset.test_mode = test_mode
            preset.paper_id = int(paper_id) if paper_id else None
            preset.duration_minutes = int(duration_minutes) if duration_minutes else None
            message = f'预设 "{preset_name}" 更新成功'
        else:
            # 创建新预设
            preset = TestPreset(
                title=preset_name,
                single_choice_count=single_choice_count,
                multiple_choice_count=multiple_choice_count,
                true_false_count=true_false_count,
                fill_blank_count=fill_blank_count,
                short_answer_count=short_answer_count,
                single_choice_score=single_choice_score,
                multiple_choice_score=multiple_choice_score,
                true_false_score=true_false_score,
                fill_blank_score=fill_blank_score,
                short_answer_score=short_answer_score,
                single_choice_bank_id=int(single_choice_bank_id) if single_choice_bank_id else None,
                multiple_choice_bank_id=int(multiple_choice_bank_id) if multiple_choice_bank_id else None,
                true_false_bank_id=int(true_false_bank_id) if true_false_bank_id else None,
                fill_blank_bank_id=int(fill_blank_bank_id) if fill_blank_bank_id else None,
                short_answer_bank_id=int(short_answer_bank_id) if short_answer_bank_id else None,
                short_answer_questions=short_answer_questions_json,
                allow_student_choice=allow_student_choice,
                short_answer_grading_method=short_answer_grading_method,
                fill_blank_grading_method=fill_blank_grading_method,
                test_mode=test_mode,
                paper_id=int(paper_id) if paper_id else None,
                duration_minutes=int(duration_minutes) if duration_minutes else None
            )
            db.session.add(preset)
            message = f'预设 "{preset_name}" 保存成功'
        
        # 同时创建/更新活跃的测试配置（用于存储 allow_student_choice 标志）
        # 查询所有相同标题的测试记录
        existing_tests = Test.query.filter_by(title=title).all()
        
        # 查找是否有任何一个相同标题的测试记录人次为0
        test_to_update = None
        for test in existing_tests:
            test_count = TestResult.query.filter_by(test_id=test.id).count()
            if test_count == 0:
                test_to_update = test
                break
        
        if test_to_update:
            # 已经确认人次为0，直接更新测试记录
            test_to_update.single_choice_count = single_choice_count
            test_to_update.multiple_choice_count = multiple_choice_count
            test_to_update.true_false_count = true_false_count
            test_to_update.fill_blank_count = fill_blank_count
            test_to_update.short_answer_count = short_answer_count
            test_to_update.single_choice_score = single_choice_score
            test_to_update.multiple_choice_score = multiple_choice_score
            test_to_update.true_false_score = true_false_score
            test_to_update.fill_blank_score = fill_blank_score
            test_to_update.short_answer_score = short_answer_score
            test_to_update.total_score = total_score
            test_to_update.single_choice_bank_id = int(single_choice_bank_id) if single_choice_bank_id else None
            test_to_update.multiple_choice_bank_id = int(multiple_choice_bank_id) if multiple_choice_bank_id else None
            test_to_update.true_false_bank_id = int(true_false_bank_id) if true_false_bank_id else None
            test_to_update.fill_blank_bank_id = int(fill_blank_bank_id) if fill_blank_bank_id else None
            test_to_update.short_answer_bank_id = int(short_answer_bank_id) if short_answer_bank_id else None
            test_to_update.short_answer_questions = short_answer_questions_json
            test_to_update.allow_student_choice = allow_student_choice
            test_to_update.short_answer_grading_method = short_answer_grading_method
            test_to_update.fill_blank_grading_method = fill_blank_grading_method
            test_to_update.is_active = True
                
            # 将其他测试设为非活跃
            Test.query.filter(Test.id != test_to_update.id).update({'is_active': False})
        else:
            # 不存在相同标题的测试，创建新测试
            # 将之前的测试设为非活跃
            Test.query.update({'is_active': False})
            
            # 创建新的测试配置
            test = Test(
                title=title,
                single_choice_count=single_choice_count,
                multiple_choice_count=multiple_choice_count,
                true_false_count=true_false_count,
                fill_blank_count=fill_blank_count,
                short_answer_count=short_answer_count,
                single_choice_score=single_choice_score,
                multiple_choice_score=multiple_choice_score,
                true_false_score=true_false_score,
                fill_blank_score=fill_blank_score,
                short_answer_score=short_answer_score,
                total_score=total_score,
                single_choice_bank_id=int(single_choice_bank_id) if single_choice_bank_id else None,
                multiple_choice_bank_id=int(multiple_choice_bank_id) if multiple_choice_bank_id else None,
                true_false_bank_id=int(true_false_bank_id) if true_false_bank_id else None,
                fill_blank_bank_id=int(fill_blank_bank_id) if fill_blank_bank_id else None,
                short_answer_bank_id=int(short_answer_bank_id) if short_answer_bank_id else None,
                short_answer_questions=short_answer_questions_json,
                allow_student_choice=allow_student_choice,
                short_answer_grading_method=short_answer_grading_method,
                fill_blank_grading_method=fill_blank_grading_method,
                is_active=True
            )
            db.session.add(test)
        db.session.commit()
        
        response_data = {
            'success': True,
            'message': message,
            'preset_id': preset.id,
            'total_score': total_score
        }
        
        # 如果有警告，添加到响应中
        if warnings:
            response_data['warnings'] = warnings
        
        return jsonify(response_data)
    
    except ValueError as e:
        return jsonify({'success': False, 'message': f'数据格式错误: {str(e)}'}), 400
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


@app.route('/api/test_presets')
def get_test_presets():
    """获取所有测试预设"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    presets = TestPreset.query.order_by(TestPreset.created_at.desc()).all()
    return jsonify({
        'success': True,
        'presets': [{
            'id': preset.id,
            'title': preset.title,
            'total_score': (
                (preset.single_choice_count or 0) * (preset.single_choice_score or 0) +
                (preset.multiple_choice_count or 0) * (preset.multiple_choice_score or 0) +
                (preset.true_false_count or 0) * (preset.true_false_score or 0) +
                (preset.fill_blank_count or 0) * (preset.fill_blank_score or 0) +
                (preset.short_answer_count or 0) * (preset.short_answer_score or 0)
            ),
            'created_at': to_bj(preset.created_at).strftime('%Y-%m-%d %H:%M:%S')
        } for preset in presets]
    })


@app.route('/api/test_presets/<int:preset_id>')
def get_test_preset(preset_id):
    """获取指定预设的详细信息"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    preset = TestPreset.query.get_or_404(preset_id)
    
    # 调试日志
    import sys
    print('预设数据:', file=sys.stderr)
    print('ID:', preset.id, file=sys.stderr)
    print('Title:', preset.title, file=sys.stderr)
    print('Short Answer Questions:', preset.short_answer_questions, file=sys.stderr)
    
    return jsonify({
        'success': True,
        'preset': {
            'id': preset.id,
            'title': preset.title,
            'single_choice_count': preset.single_choice_count,
            'multiple_choice_count': preset.multiple_choice_count,
            'true_false_count': preset.true_false_count,
            'fill_blank_count': preset.fill_blank_count,
            'short_answer_count': preset.short_answer_count,
            'single_choice_score': preset.single_choice_score,
            'multiple_choice_score': preset.multiple_choice_score,
            'true_false_score': preset.true_false_score,
            'fill_blank_score': preset.fill_blank_score,
            'short_answer_score': preset.short_answer_score,
            'single_choice_bank_id': preset.single_choice_bank_id,
            'multiple_choice_bank_id': preset.multiple_choice_bank_id,
            'true_false_bank_id': preset.true_false_bank_id,
            'fill_blank_bank_id': preset.fill_blank_bank_id,
            'short_answer_bank_id': preset.short_answer_bank_id,
            'short_answer_questions': preset.short_answer_questions,
            'allow_student_choice': preset.allow_student_choice,
            'short_answer_grading_method': preset.short_answer_grading_method or 'manual',
            'fill_blank_grading_method': preset.fill_blank_grading_method or 'manual',
            'test_mode': getattr(preset, 'test_mode', 'question_bank') or 'question_bank',
            'paper_id': getattr(preset, 'paper_id', None),
            'duration_minutes': getattr(preset, 'duration_minutes', None)
        }
    })


@app.route('/api/test_presets/<int:preset_id>', methods=['DELETE'])
def delete_test_preset(preset_id):
    """删除指定预设"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    preset = TestPreset.query.get_or_404(preset_id)
    db.session.delete(preset)
    db.session.commit()
    
    return jsonify({'success': True, 'message': '预设删除成功'})


@app.route('/api/current_test_settings')
def get_current_test_settings():
    """获取当前测试设置（公开API，学生可访问）"""
    # 获取当前激活的测试
    current_test = Test.query.filter_by(is_active=True).first()
    if not current_test:
        return jsonify({'allow_student_choice': False})
    
    # 返回当前测试的allow_student_choice设置
    return jsonify({'allow_student_choice': current_test.allow_student_choice})


@app.route('/api/test_presets_public')
def get_test_presets_public():
    """获取可供学生选择的测试预设列表（公开API）"""
    # 检查当前测试是否允许学生自选
    current_test = Test.query.filter_by(is_active=True).first()
    
    # 返回所有预设（包括试卷模式），每个预设均表示可用的测试
    presets = TestPreset.query.order_by(TestPreset.created_at.desc()).all()
    return jsonify({
        'presets': [{
            'id': preset.id,
            'title': preset.title,
            'test_mode': getattr(preset, 'test_mode', 'question_bank') or 'question_bank'
        } for preset in presets]
    })


@app.route('/change_password', methods=['POST'])
def change_password():
    """修改密码"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_password = request.form.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        flash('所有字段都必须填写')
        return redirect(url_for('teacher_dashboard'))
    
    if new_password != confirm_password:
        flash('两次输入的新密码不一致')
        return redirect(url_for('teacher_dashboard'))
    
    user = User.query.get(session['user_id'])
    if not user.check_password(current_password):
        flash('当前密码错误')
        return redirect(url_for('teacher_dashboard'))
    
    user.set_password(new_password)
    db.session.commit()
    # flash('密码修改成功')  # 移除成功提示
    return redirect(url_for('teacher_dashboard'))


@app.route('/api/ai_grading_status')
def get_ai_grading_status():
    """获取AI批改功能状态"""
    ai_service = get_ai_grading_service()
    enabled, config_message = ai_service.get_config_status()
    
    if enabled:
        return jsonify({
            'enabled': True,
            'message': 'AI批改功能已正确配置',
            'details': config_message
        })
    else:
        return jsonify({
            'enabled': False,
            'message': 'AI配置不正确',
            'details': config_message,
            'suggestion': '请检查config.py中的AI_GRADING_CONFIG配置'
        })

# ==================== 试卷模式 API ====================

@app.route('/api/paper_banks', methods=['GET', 'POST'])
def manage_paper_banks():
    """获取试卷库列表 / 创建试卷库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    if request.method == 'GET':
        banks = PaperBank.query.order_by(PaperBank.created_at.desc()).all()
        return jsonify({
            'success': True,
            'banks': [{
                'id': b.id,
                'title': b.title,
                'file_type': b.file_type,
                'page_count': b.page_count,
                'total_questions': b.total_questions,
                'created_at': b.created_at.strftime('%Y-%m-%d %H:%M') if b.created_at else ''
            } for b in banks]
        })
    
    # POST - 创建试卷库
    title = request.form.get('title', '').strip()
    if not title:
        return jsonify({'success': False, 'message': '请输入试卷标题'}), 400
    
    file_type = request.form.get('file_type', 'pdf')
    
    paper_bank = PaperBank(
        title=title,
        file_type=file_type,
        teacher_id=session.get('user_id')
    )
    
    # 上传试卷文件
    paper_file = request.files.get('paper_file')
    if paper_file and paper_file.filename:
        paper_dir = os.path.join('uploads', 'papers', str(paper_bank.id if paper_bank.id else 'temp'))
        os.makedirs(paper_dir, exist_ok=True)
        ext = paper_file.filename.rsplit('.', 1)[-1].lower() if '.' in paper_file.filename else 'pdf'
        paper_filename = f"paper.{ext}"
        paper_path = os.path.join(paper_dir, paper_filename)
        
        db.session.flush()
        paper_dir = os.path.join('uploads', 'papers', str(paper_bank.id))
        os.makedirs(paper_dir, exist_ok=True)
        paper_path = os.path.join(paper_dir, paper_filename)
        paper_file.save(paper_path)
        paper_bank.paper_path = paper_path
        
        # 如果是PDF，获取页数
        if ext == 'pdf':
            try:
                from PyPDF2 import PdfReader
                reader = PdfReader(paper_path)
                paper_bank.page_count = len(reader.pages)
            except Exception as e:
                logger.warning(f"读取PDF页数失败: {e}")
    
    # 上传参考答案PDF
    answer_file = request.files.get('answer_file')
    if answer_file and answer_file.filename:
        paper_dir = os.path.join('uploads', 'papers', str(paper_bank.id))
        os.makedirs(paper_dir, exist_ok=True)
        answer_path = os.path.join(paper_dir, 'answer.pdf')
        answer_file.save(answer_path)
        paper_bank.answer_path = answer_path
    
    # 上传答题卡Excel配置
    excel_file = request.files.get('excel_file')
    if excel_file and excel_file.filename:
        try:
            # 保存Excel文件
            excel_path = os.path.join(paper_dir, 'config.xlsx')
            excel_file.save(excel_path)
            paper_bank.excel_path = excel_path
            
            df = pd.read_excel(excel_path)
            config_list = []
            for _, row in df.iterrows():
                q = {
                    'num': int(row.get('题号', 0)),
                    'type': str(row.get('题型', '')),
                    'options': str(row.get('选项', '')) if pd.notna(row.get('选项')) else '',
                    'score': int(row.get('分值', 0)) if pd.notna(row.get('分值')) else 0,
                    'answer': str(row.get('参考答案', '')) if pd.notna(row.get('参考答案')) else ''
                }
                if q['num'] > 0 and q['type']:
                    config_list.append(q)
            paper_bank.answer_config = json.dumps(config_list, ensure_ascii=False)
            paper_bank.total_questions = len(config_list)
        except Exception as e:
            return jsonify({'success': False, 'message': f'Excel解析失败: {str(e)}'}), 400
    
    # 自动检测PDF题号位置
    if paper_bank.paper_path and paper_bank.file_type == 'pdf':
        try:
            positions = detect_question_positions(paper_bank.paper_path, paper_bank.total_questions)
            if positions:
                paper_bank.question_positions = json.dumps(positions, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"题号定位失败: {e}")
    
    db.session.add(paper_bank)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '试卷导入成功',
        'bank': {
            'id': paper_bank.id,
            'title': paper_bank.title,
            'file_type': paper_bank.file_type,
            'page_count': paper_bank.page_count,
            'total_questions': paper_bank.total_questions
        }
    })


def detect_question_positions(pdf_path, total_questions):
    """检测PDF中题号位置"""
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(pdf_path)
        positions = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if not text:
                continue
            lines = text.split('\n')
            y_pos = 0
            for line in lines:
                y_pos += 15  # 估算行高
                import re
                matches = re.findall(r'(?:^|\s)(\d{1,3})[\.、．]\s', line)
                for match in matches:
                    num = int(match)
                    if 1 <= num <= (total_questions or 999):
                        positions.append({
                            'num': num,
                            'page': page_num + 1,
                            'y': y_pos
                        })
        
        positions.sort(key=lambda x: (x['page'], x['y']))
        seen = set()
        unique = []
        for p in positions:
            if p['num'] not in seen:
                seen.add(p['num'])
                unique.append(p)
        return unique
    except Exception as e:
        logger.error(f"题号检测异常: {e}")
        return []


@app.route('/paper_bank/<int:bank_id>/edit', methods=['GET'])
def edit_paper_bank(bank_id):
    """编辑试卷参数页面（重新上传试卷和答题卡）"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect('/teacher/login')
    
    bank = PaperBank.query.get_or_404(bank_id)
    answer_config = json.loads(bank.answer_config) if bank.answer_config else []
    
    return render_template('edit_paper_params.html', bank=bank, answer_config=answer_config)


@app.route('/api/paper_preview', methods=['POST'])
def paper_preview():
    """上传临时文件进行预览"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        title = request.form.get('title', '').strip()
        paper_file = request.files.get('paper_file')
        excel_file = request.files.get('excel_file')
        
        if not title or not paper_file or not excel_file:
            return jsonify({'success': False, 'message': '缺少必要参数'}), 400
        
        preview_id = str(uuid.uuid4())
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'preview', preview_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        paper_path = os.path.join(temp_dir, 'paper.pdf')
        paper_file.save(paper_path)
        
        excel_path = os.path.join(temp_dir, 'config.xlsx')
        excel_file.save(excel_path)
        
        import pandas as pd
        df = pd.read_excel(excel_path)
        config_list = []
        for _, row in df.iterrows():
            q = {
                'num': int(row.get('题号', 0)),
                'type': str(row.get('题型', '')),
                'options': str(row.get('选项', '')) if pd.notna(row.get('选项')) else '',
                'score': int(row.get('分值', 0)) if pd.notna(row.get('分值')) else 0,
                'answer': str(row.get('参考答案', '')) if pd.notna(row.get('参考答案')) else ''
            }
            if q['num'] > 0 and q['type']:
                config_list.append(q)
        
        config_path = os.path.join(temp_dir, 'config.json')
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump({'title': title, 'questions': config_list}, f, ensure_ascii=False)
        
        return jsonify({'success': True, 'preview_id': preview_id})
    
    except Exception as e:
        logger.error(f"预览失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/paper_preview/<preview_id>', methods=['GET'])
def paper_preview_page(preview_id):
    """预览页面"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect('/teacher/login')
    
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'preview', preview_id)
    config_path = os.path.join(temp_dir, 'config.json')
    
    if not os.path.exists(config_path):
        return "预览已过期", 404
    
    with open(config_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    return render_template('paper_preview.html', preview_id=preview_id, title=data['title'], questions=data['questions'])


@app.route('/paper_preview/<preview_id>/save', methods=['POST'])
def save_preview_config(preview_id):
    """保存修改后的答题卡配置"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    try:
        questions = request.json.get('questions', [])
        
        temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'preview', preview_id)
        config_path = os.path.join(temp_dir, 'config.json')
        
        if not os.path.exists(config_path):
            return jsonify({'success': False, 'message': '预览已过期'}), 404
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        data['questions'] = questions
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        
        return jsonify({'success': True, 'message': '保存成功'})
    
    except Exception as e:
        logger.error(f"保存预览配置失败: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/preview_paper/<preview_id>', methods=['GET'])
def preview_paper_file(preview_id):
    """提供预览的PDF文件"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect('/teacher/login')
    
    temp_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'preview', preview_id)
    paper_path = os.path.join(temp_dir, 'paper.pdf')
    
    if not os.path.exists(paper_path):
        return "文件不存在", 404
    
    return send_file(paper_path, mimetype='application/pdf')


@app.route('/api/paper_banks/<int:bank_id>', methods=['GET', 'DELETE', 'PUT'])
def manage_single_paper_bank(bank_id):
    """获取/删除/更新单个试卷库"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    bank = PaperBank.query.get_or_404(bank_id)
    
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'bank': {
                'id': bank.id,
                'title': bank.title,
                'file_type': bank.file_type,
                'page_count': bank.page_count,
                'total_questions': bank.total_questions,
                'answer_config': json.loads(bank.answer_config) if bank.answer_config else [],
                'question_positions': json.loads(bank.question_positions) if bank.question_positions else [],
                'created_at': bank.created_at.strftime('%Y-%m-%d %H:%M') if bank.created_at else ''
            }
        })
    
    if request.method == 'PUT':
        # 更新试卷信息
        data = request.get_json()
        if 'title' in data:
            bank.title = data['title']
        
        if 'answer_config' in data:
            bank.answer_config = json.dumps(data['answer_config'], ensure_ascii=False)
            bank.total_questions = len(data['answer_config'])
        
        db.session.commit()
        return jsonify({'success': True, 'message': '更新成功'})
    
    # DELETE
    try:
        import shutil
        if bank.paper_path:
            bank_dir = os.path.dirname(bank.paper_path)
            if os.path.exists(bank_dir):
                shutil.rmtree(bank_dir)
        db.session.delete(bank)
        db.session.commit()
        return jsonify({'success': True, 'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


@app.route('/api/paper_banks/<int:bank_id>/update', methods=['POST'])
def update_paper_bank(bank_id):
    """更新试卷参数（重新上传试卷和答题卡）"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    bank = PaperBank.query.get_or_404(bank_id)
    
    try:
        title = request.form.get('title')
        if title:
            bank.title = title
        
        paper_file = request.files.get('paper_file')
        if paper_file and paper_file.filename:
            paper_dir = os.path.join('uploads', 'papers', str(bank.id))
            os.makedirs(paper_dir, exist_ok=True)
            ext = paper_file.filename.rsplit('.', 1)[-1].lower() if '.' in paper_file.filename else 'pdf'
            paper_filename = f"paper.{ext}"
            paper_path = os.path.join(paper_dir, paper_filename)
            paper_file.save(paper_path)
            bank.paper_path = paper_path
            bank.file_type = ext
            
            if ext == 'pdf':
                try:
                    from PyPDF2 import PdfReader
                    reader = PdfReader(paper_path)
                    bank.page_count = len(reader.pages)
                except Exception as e:
                    logger.warning(f"读取PDF页数失败: {e}")
        
        excel_file = request.files.get('excel_file')
        if excel_file and excel_file.filename:
            try:
                import pandas as pd
                df = pd.read_excel(excel_file)
                config_list = []
                for _, row in df.iterrows():
                    q = {
                        'num': int(row.get('题号', 0)),
                        'type': str(row.get('题型', '')),
                        'options': str(row.get('选项', '')) if pd.notna(row.get('选项')) else '',
                        'score': int(row.get('分值', 0)) if pd.notna(row.get('分值')) else 0,
                        'answer': str(row.get('参考答案', '')) if pd.notna(row.get('参考答案')) else ''
                    }
                    if q['num'] > 0 and q['type']:
                        config_list.append(q)
                bank.answer_config = json.dumps(config_list, ensure_ascii=False)
                bank.total_questions = len(config_list)
            except Exception as e:
                logger.error(f"解析Excel失败: {e}")
                return jsonify({'success': False, 'message': f'Excel解析失败: {str(e)}'})
        
        db.session.commit()
        return jsonify({'success': True, 'message': '更新成功'})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"更新试卷失败: {e}")
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@app.route('/api/paper_banks/<int:bank_id>/paper', methods=['GET'])
def serve_paper_file(bank_id):
    """提供试卷文件给前端查看"""
    bank = PaperBank.query.get_or_404(bank_id)
    if not bank.paper_path or not os.path.exists(bank.paper_path):
        return jsonify({'success': False, 'message': '文件不存在'}), 404
    return send_file(bank.paper_path)


@app.route('/api/paper_excel_template')
def download_excel_template():
    """下载答题卡Excel模板"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    import pandas as pd
    template_data = {
        '题号': [1, 2, 3, 4, 5],
        '题型': ['单选', '多选', '判断', '填空', '简答'],
        '选项': ['独立|交流|依赖|开放', 'A|B|C|D', '对|错', '', ''],
        '分值': [4, 6, 2, 5, 10],
        '参考答案': ['B', 'ABC', '对|正确|是', '牛顿|Newton、苹果|apple', '见参考答案'],
        '备注': ['', '', '判断题答案：对、正确、是、√、true、1 或 错、错误、否、×、false、0', '填空题规则：不同空用"、"隔开（全角顿号），同一空多个答案用"|"分隔，如"in|IN、i、1|一"表示第1空填in或IN都正确', '']
    }
    df = pd.DataFrame(template_data)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='答题卡配置')
    output.seek(0)
    
    return send_file(output, mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='答题卡配置模板.xlsx')


# ==================== 试卷模式 - 学生端 API ====================

@app.route('/student/paper_test', methods=['GET'])
def student_paper_test():
    """学生试卷测试页面"""
    if 'role' not in session or session['role'] != 'student':
        return redirect(url_for('index'))
    
    preset_id = request.args.get('preset_id')
    if not preset_id:
        flash('请选择测试')
        return redirect(url_for('student_start'))
    
    preset = TestPreset.query.get_or_404(int(preset_id))
    if preset.test_mode != 'paper':
        flash('该预设不是试卷模式')
        return redirect(url_for('student_start'))
    
    if not preset.paper_id:
        flash('该预设未关联试卷')
        return redirect(url_for('student_start'))
    
    paper = PaperBank.query.get(preset.paper_id)
    if not paper:
        flash('试卷不存在')
        return redirect(url_for('student_start'))
    
    student_id = session.get('user_id') or session.get('student_id')
    if not student_id:
        flash('请先登录')
        return redirect(url_for('student_start'))
    
    student = User.query.get(student_id)
    
    # 检查是否已有记录（防止重复开始）
    existing = PaperExamRecord.query.filter_by(
        preset_id=preset.id,
        student_id=student.id,
        is_submitted=False
    ).first()
    
    if existing:
        exam_id = existing.id
        existing.auto_save_at = datetime.utcnow()
        db.session.commit()
    else:
        exam = PaperExamRecord(
            preset_id=preset.id,
            student_id=student.id,
            student_name=student.username,
            class_number=getattr(student, 'class_number', ''),
            ip_address=request.remote_addr,
            created_at=datetime.utcnow()
        )
        db.session.add(exam)
        db.session.commit()
        exam_id = exam.id
    
    answer_config = json.loads(paper.answer_config) if paper.answer_config else []
    
    return render_template('paper_test.html',
                         preset=preset,
                         paper=paper,
                         exam_id=exam_id,
                         answer_config=answer_config,
                         duration_minutes=preset.duration_minutes or 120,
                         student_name=student.username)


@app.route('/api/paper_exam/<int:exam_id>/auto_save', methods=['POST'])
def auto_save_paper_exam(exam_id):
    """自动保存试卷作答"""
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    user_id = session.get('user_id') or session.get('student_id')
    if not user_id:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    exam = PaperExamRecord.query.get_or_404(exam_id)
    if exam.student_id != user_id:
        return jsonify({'success': False, 'message': '无权操作'}), 403
    
    if exam.is_submitted:
        return jsonify({'success': False, 'message': '试卷已提交'}), 400
    
    data = request.get_json()
    exam.answers_json = json.dumps(data.get('answers', {}), ensure_ascii=False)
    exam.auto_save_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({'success': True, 'message': '已自动保存'})


@app.route('/api/paper_exam/<int:exam_id>/submit', methods=['POST'])
def submit_paper_exam(exam_id):
    """提交试卷"""
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    user_id = session.get('user_id') or session.get('student_id')
    if not user_id:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    exam = PaperExamRecord.query.get_or_404(exam_id)
    if exam.student_id != user_id:
        return jsonify({'success': False, 'message': '无权操作'}), 403
    
    if exam.is_submitted:
        return jsonify({'success': False, 'message': '试卷已提交'}), 400
    
    data = request.get_json()
    answers = data.get('answers', {})
    duration_used = data.get('duration_used', 0)
    
    exam.answers_json = json.dumps(answers, ensure_ascii=False)
    exam.is_submitted = True
    exam.submitted_at = datetime.utcnow()
    exam.duration_used = duration_used
    
    # 开始自动批改
    preset = TestPreset.query.get(exam.preset_id)
    paper = PaperBank.query.get(preset.paper_id) if preset else None
    answer_config = json.loads(paper.answer_config) if paper and paper.answer_config else []
    
    total_score = 0.0
    ai_grading_results = {}
    
    for q_config in answer_config:
        q_num = str(q_config['num'])
        student_answer = answers.get(q_num, '')
        q_type = q_config['type']
        q_score = q_config['score']
        q_correct = str(q_config.get('answer', ''))
        
        if q_type == '单选':
            # 选择题对比答案时忽略大小写
            if student_answer.strip().upper() == q_correct.strip().upper():
                total_score += q_score
                ai_grading_results[q_num] = {'score': q_score, 'feedback': '正确', 'success': True}
            else:
                ai_grading_results[q_num] = {'score': 0, 'feedback': f'正确答案: {q_correct}', 'success': True}
        
        elif q_type == '多选':
            # 多选题忽略参考答案与填写答案之间间隔符号，忽略大小写
            def normalize_multi(ans):
                ans = ans.replace(',', '').replace('，', '').replace('、', '').replace(' ', '').replace('/', '').replace('\\', '')
                return set(c.upper() for c in ans if c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            
            correct_set = normalize_multi(q_correct)
            student_set = normalize_multi(student_answer)
            
            if student_set == correct_set:
                total_score += q_score
                ai_grading_results[q_num] = {'score': q_score, 'feedback': '正确', 'success': True}
            elif student_set and student_set.issubset(correct_set):
                partial_score = q_score / 2
                total_score += partial_score
                ai_grading_results[q_num] = {'score': partial_score, 'feedback': f'部分正确，正确答案: {q_correct}', 'success': True}
            else:
                ai_grading_results[q_num] = {'score': 0, 'feedback': f'正确答案: {q_correct}', 'success': True}
        
        elif q_type == '判断':
            # 判断题参考答案为对和错，支持多种表示方式
            def normalize_tf(ans):
                ans = ans.strip().lower()
                true_values = {'对', '正确', '是', '√', 'true', '1', '对的', '是的', '真', 't'}
                false_values = {'错', '错误', '否', '×', 'false', '0', '错的', '不是', '假', 'f'}
                if ans in true_values:
                    return '对'
                elif ans in false_values:
                    return '错'
                return ans
            
            if normalize_tf(student_answer) == normalize_tf(q_correct):
                total_score += q_score
                ai_grading_results[q_num] = {'score': q_score, 'feedback': '正确', 'success': True}
            else:
                ai_grading_results[q_num] = {'score': 0, 'feedback': f'正确答案: {q_correct}', 'success': True}
        
        elif q_type == '填空':
            # 填空题多空时用"/"隔开，同一空多个正确答案用"|"分隔
            # 示例："in|IN、i、1|一" 表示第1空填in或IN都正确，第2空填i正确，第3空填1或一都正确
            def split_blanks(text):
                return text.split('、')
            
            def split_alternatives(text):
                return [a.strip().lower() for a in text.split('|') if a.strip()]
            
            correct_blanks = split_blanks(q_correct)
            student_blanks = split_blanks(student_answer)
            
            if len(correct_blanks) > 0:
                score_per_fill = q_score / len(correct_blanks)
                earned_score = 0
                
                for i in range(len(correct_blanks)):
                    if i < len(student_blanks):
                        student_ans = student_blanks[i].strip().lower()
                        if student_ans:
                            correct_alternatives = split_alternatives(correct_blanks[i])
                            if student_ans in correct_alternatives:
                                earned_score += score_per_fill
                
                earned_score = round(earned_score * 10) / 10  # 保留一位小数
                total_score += earned_score
                
                if earned_score == q_score:
                    ai_grading_results[q_num] = {'score': earned_score, 'feedback': '正确', 'success': True}
                elif earned_score > 0:
                    ai_grading_results[q_num] = {'score': earned_score, 'feedback': f'部分正确，正确答案: {q_correct}', 'success': True}
                elif student_answer.strip():
                    ai_grading_results[q_num] = {'score': 0, 'feedback': f'正确答案: {q_correct}', 'success': True}
                else:
                    ai_grading_results[q_num] = {'score': 0, 'feedback': '未作答', 'success': True}
        
        elif q_type == '简答' and student_answer.strip():
            # AI批改
            try:
                ai_service = get_ai_grading_service()
                if ai_service.is_enabled():
                    success, ai_result = ai_service.grade_answer(
                        question=f"第{q_num}题（简答题）",
                        reference_answer=f"参考答案: {q_correct}",
                        student_answer=student_answer,
                        max_score=q_score,
                        question_type='short_answer'
                    )
                    if success:
                        actual_score = min(ai_result['score'], q_score)
                        total_score += actual_score
                        ai_grading_results[q_num] = {
                            'score': actual_score,
                            'feedback': ai_result.get('feedback', ''),
                            'success': True
                        }
                    else:
                        ai_grading_results[q_num] = {
                            'score': 0,
                            'feedback': f"AI批改失败: {ai_result.get('error_message', '')}",
                            'success': False
                        }
                else:
                    ai_grading_results[q_num] = {
                        'score': 0,
                        'feedback': 'AI未配置，需人工批改',
                        'success': False
                    }
            except Exception as e:
                logger.error(f"简答题AI批改异常: {e}")
                ai_grading_results[q_num] = {
                    'score': 0,
                    'feedback': f'批改异常: {str(e)}',
                    'success': False
                }
        elif q_type == '简答' and not student_answer.strip():
            ai_grading_results[q_num] = {'score': 0, 'feedback': '未作答', 'success': True}
    
    exam.total_score = total_score
    exam.ai_grading_results = json.dumps(ai_grading_results, ensure_ascii=False)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': '试卷已提交',
        'total_score': total_score
    })


@app.route('/api/paper_exam/<int:exam_id>/load', methods=['GET'])
def load_paper_exam_answers(exam_id):
    """加载已保存的作答"""
    if 'role' not in session or session['role'] != 'student':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    user_id = session.get('user_id') or session.get('student_id')
    if not user_id:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    exam = PaperExamRecord.query.get_or_404(exam_id)
    if exam.student_id != user_id:
        return jsonify({'success': False, 'message': '无权操作'}), 403
    
    answers = json.loads(exam.answers_json) if exam.answers_json else {}
    
    return jsonify({
        'success': True,
        'answers': answers,
        'is_submitted': exam.is_submitted,
        'auto_save_at': exam.auto_save_at.strftime('%Y-%m-%d %H:%M:%S') if exam.auto_save_at else None
    })


# ==================== 试卷模式 - 教师批改 API ====================

@app.route('/paper_exam_results')
def paper_exam_results():
    """试卷模式成绩查看页面"""
    if 'role' not in session or session['role'] != 'teacher':
        return redirect(url_for('index'))
    
    preset_id = request.args.get('preset_id', type=int)
    
    presets = TestPreset.query.filter_by(test_mode='paper').order_by(TestPreset.created_at.desc()).all()
    
    results = []
    if preset_id:
        exams = PaperExamRecord.query.filter_by(preset_id=preset_id, is_submitted=True)\
            .order_by(PaperExamRecord.submitted_at.desc()).all()
        
        preset = TestPreset.query.get(preset_id)
        paper = PaperBank.query.get(preset.paper_id) if preset else None
        answer_config = json.loads(paper.answer_config) if paper and paper.answer_config else []
        total_possible = sum(q['score'] for q in answer_config) if answer_config else 0
        
        for exam in exams:
            ai_results = json.loads(exam.ai_grading_results) if exam.ai_grading_results else {}
            needs_review = any(
                r.get('success') == False
                for r in ai_results.values()
            )
            
            results.append({
                'exam_id': exam.id,
                'student_name': exam.student_name,
                'class_number': exam.class_number,
                'total_score': exam.total_score,
                'total_possible': total_possible,
                'submitted_at': exam.submitted_at.strftime('%Y-%m-%d %H:%M') if exam.submitted_at else '',
                'duration_used': exam.duration_used,
                'needs_review': needs_review
            })
    
    return render_template('paper_exam_results.html',
                         presets=presets,
                         selected_preset_id=preset_id,
                         results=results)


@app.route('/api/paper_exam/<int:exam_id>/detail')
def paper_exam_detail(exam_id):
    """获取试卷考试详情（教师和学生均可访问）"""
    exam = PaperExamRecord.query.get_or_404(exam_id)
    
    # 教师可以查看任何记录，学生只能查看自己的记录
    if 'role' in session and session['role'] == 'teacher':
        pass  # 教师有全部权限
    elif 'student_id' in session:
        if exam.student_id != session['student_id']:
            return jsonify({'success': False, 'message': '无权查看'}), 403
    else:
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    preset = TestPreset.query.get(exam.preset_id)
    paper = PaperBank.query.get(preset.paper_id) if preset else None
    
    answers = json.loads(exam.answers_json) if exam.answers_json else {}
    answer_config = json.loads(paper.answer_config) if paper and paper.answer_config else []
    ai_results = json.loads(exam.ai_grading_results) if exam.ai_grading_results else {}
    
    return jsonify({
        'success': True,
        'exam': {
            'id': exam.id,
            'student_name': exam.student_name,
            'class_number': exam.class_number,
            'total_score': exam.total_score,
            'submitted_at': exam.submitted_at.strftime('%Y-%m-%d %H:%M') if exam.submitted_at else '',
            'duration_used': exam.duration_used,
            'paper_title': paper.title if paper else ''
        },
        'answers': answers,
        'answer_config': answer_config,
        'ai_results': ai_results,
    })


@app.route('/api/paper_exam/<int:exam_id>/update_score', methods=['POST'])
def update_paper_exam_score(exam_id):
    """教师手动修改分数"""
    if 'role' not in session or session['role'] != 'teacher':
        return jsonify({'success': False, 'message': '未授权'}), 403
    
    exam = PaperExamRecord.query.get_or_404(exam_id)
    data = request.get_json()
    
    question_num = str(data.get('question_num'))
    new_score = data.get('score', 0)
    feedback = data.get('feedback', '')
    
    ai_results = json.loads(exam.ai_grading_results) if exam.ai_grading_results else {}
    if question_num in ai_results:
        old_score = ai_results[question_num].get('score', 0)
        ai_results[question_num]['score'] = new_score
        ai_results[question_num]['feedback'] = feedback
        ai_results[question_num]['manual_reviewed'] = True
        exam.total_score = exam.total_score - old_score + new_score
        exam.ai_grading_results = json.dumps(ai_results, ensure_ascii=False)
        db.session.commit()
        return jsonify({'success': True, 'total_score': exam.total_score})
    
    return jsonify({'success': False, 'message': '题目不存在'}), 404


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=8000)