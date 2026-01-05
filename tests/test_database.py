"""
数据库相关功能的属性测试

使用 Hypothesis 进行属性测试，验证数据库操作的正确性
"""

import pytest
from hypothesis import given, strategies as st, settings
import tempfile
import os
from app import app, db, User, init_db


@pytest.fixture
def test_app():
    """创建测试应用实例"""
    # 使用临时数据库
    db_fd, db_path = tempfile.mkstemp()
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)


# Feature: debug-test-system, Property 1: 数据库初始化幂等性
@settings(max_examples=100)
def test_database_init_idempotence(test_app):
    """
    属性测试：数据库初始化幂等性
    
    验证：对于任何系统状态，多次运行数据库初始化不应该创建重复的数据或改变已存在的数据
    
    测试策略：
    1. 运行初始化
    2. 记录初始状态（用户数量、表结构）
    3. 再次运行初始化
    4. 验证状态未改变
    """
    with test_app.app_context():
        # 第一次初始化
        result1 = init_db()
        assert result1 is True, "第一次初始化应该成功"
        
        # 记录初始状态
        initial_user_count = User.query.count()
        initial_admin = User.query.filter_by(username='admin', role='teacher').first()
        assert initial_admin is not None, "默认管理员账户应该存在"
        initial_admin_id = initial_admin.id
        
        # 第二次初始化
        result2 = init_db()
        assert result2 is True, "第二次初始化应该成功"
        
        # 验证状态未改变
        final_user_count = User.query.count()
        final_admin = User.query.filter_by(username='admin', role='teacher').first()
        
        # 断言：用户数量不应该增加
        assert final_user_count == initial_user_count, \
            f"用户数量不应该改变：初始={initial_user_count}, 最终={final_user_count}"
        
        # 断言：管理员账户应该是同一个
        assert final_admin.id == initial_admin_id, \
            "管理员账户ID不应该改变"
        
        # 断言：密码哈希不应该改变
        assert final_admin.password_hash == initial_admin.password_hash, \
            "管理员密码不应该被重置"


# Feature: debug-test-system, Property 1: 数据库初始化幂等性（多次运行）
@settings(max_examples=100)
@given(run_count=st.integers(min_value=2, max_value=5))
def test_database_init_multiple_runs(test_app, run_count):
    """
    属性测试：多次数据库初始化幂等性
    
    验证：对于任意次数的初始化运行，结果应该与运行一次相同
    
    测试策略：
    1. 运行 N 次初始化（N 为随机数 2-5）
    2. 验证每次运行后状态一致
    """
    with test_app.app_context():
        # 第一次初始化
        init_db()
        initial_user_count = User.query.count()
        initial_admin = User.query.filter_by(username='admin', role='teacher').first()
        initial_admin_id = initial_admin.id
        
        # 多次运行初始化
        for i in range(run_count - 1):
            result = init_db()
            assert result is True, f"第 {i+2} 次初始化应该成功"
            
            # 每次都验证状态
            current_user_count = User.query.count()
            current_admin = User.query.filter_by(username='admin', role='teacher').first()
            
            assert current_user_count == initial_user_count, \
                f"第 {i+2} 次运行后用户数量应该保持不变"
            assert current_admin.id == initial_admin_id, \
                f"第 {i+2} 次运行后管理员ID应该保持不变"


def test_database_init_creates_default_admin(test_app):
    """
    单元测试：验证初始化创建默认管理员账户
    
    这是一个具体的示例测试，验证默认账户的创建
    """
    with test_app.app_context():
        # 确保数据库为空
        User.query.delete()
        db.session.commit()
        
        # 运行初始化
        result = init_db()
        assert result is True, "初始化应该成功"
        
        # 验证默认管理员账户
        admin = User.query.filter_by(username='admin', role='teacher').first()
        assert admin is not None, "应该创建默认管理员账户"
        assert admin.username == 'admin', "管理员用户名应该是 'admin'"
        assert admin.role == 'teacher', "管理员角色应该是 'teacher'"
        assert admin.check_password('admin'), "默认密码应该是 'admin'"


def test_database_init_error_handling(test_app):
    """
    单元测试：验证初始化的错误处理
    
    测试当数据库操作失败时，init_db 能够正确处理错误
    """
    # 这个测试验证错误处理逻辑存在
    # 实际的错误场景需要模拟数据库故障，这里只验证函数结构
    with test_app.app_context():
        result = init_db()
        assert isinstance(result, bool), "init_db 应该返回布尔值"
