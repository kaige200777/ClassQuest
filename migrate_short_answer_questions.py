from app import app, db
import sqlite3

with app.app_context():
    with db.engine.connect() as conn:
        # 添加 short_answer_questions 字段到 Test 表
        try:
            conn.execute(db.text('ALTER TABLE test ADD COLUMN short_answer_questions TEXT'))
            print("已添加 short_answer_questions 字段到 test 表")
        except Exception as e:
            print(f"test 表可能已存在该字段: {e}")
        
        # 添加 short_answer_questions 字段到 TestPreset 表
        try:
            conn.execute(db.text('ALTER TABLE test_preset ADD COLUMN short_answer_questions TEXT'))
            print("已添加 short_answer_questions 字段到 test_preset 表")
        except Exception as e:
            print(f"test_preset 表可能已存在该字段: {e}")
        
        conn.commit()
    
    print("数据库迁移完成")
