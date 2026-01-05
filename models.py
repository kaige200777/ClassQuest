from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)  # teacher or student
    student_name = db.Column(db.String(80))
    class_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class QuestionBank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    question_type = db.Column(db.String(20), nullable=False)  # single_choice, multiple_choice, true_false, fill_blank, short_answer
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    questions = db.relationship('Question', backref='bank', lazy=True)

    @property
    def question_type_display(self):
        type_map = {
            'single_choice': '单选题',
            'multiple_choice': '多选题',
            'true_false': '判断题',
            'fill_blank': '填空题',
            'short_answer': '简答题'
        }
        return type_map.get(self.question_type, self.question_type)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    option_a = db.Column(db.String(200))
    option_b = db.Column(db.String(200))
    option_c = db.Column(db.String(200))
    option_d = db.Column(db.String(200))
    correct_answer = db.Column(db.String(200), nullable=False)
    score = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Test(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 题目数量设置
    single_choice_count = db.Column(db.Integer, default=0)
    multiple_choice_count = db.Column(db.Integer, default=0)
    true_false_count = db.Column(db.Integer, default=0)
    fill_blank_count = db.Column(db.Integer, default=0)
    short_answer_count = db.Column(db.Integer, default=0)
    
    # 题目分值设置
    single_choice_score = db.Column(db.Integer, default=0)
    multiple_choice_score = db.Column(db.Integer, default=0)
    true_false_score = db.Column(db.Integer, default=0)
    fill_blank_score = db.Column(db.Integer, default=0)
    short_answer_score = db.Column(db.Integer, default=0)
    
    # 总分
    total_score = db.Column(db.Integer, default=100)
    
    # 题库选择
    single_choice_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'))
    multiple_choice_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'))
    true_false_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'))
    fill_blank_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'))
    short_answer_bank_id = db.Column(db.Integer, db.ForeignKey('question_bank.id'))

class TestResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    test_id = db.Column(db.Integer, db.ForeignKey('test.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(80))
    class_number = db.Column(db.String(20))
    ip_address = db.Column(db.String(64))  # 提交时学生电脑IP
    score = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class StudentTestHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    student_name = db.Column(db.String(80))
    class_number = db.Column(db.String(20))
    test_count = db.Column(db.Integer, default=0)
    total_score = db.Column(db.Integer, default=0)
    average_score = db.Column(db.Float, default=0)
    highest_score = db.Column(db.Integer, default=0)
    lowest_score = db.Column(db.Integer, default=0)
    last_test_at = db.Column(db.DateTime) 

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow) 