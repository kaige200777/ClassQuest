from app import app, db, Test

def add_preset_id_column():
    with app.app_context():
        try:
            # 检查列是否已存在
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('test')]
            
            if 'preset_id' not in columns:
                # 添加preset_id列
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE test ADD COLUMN preset_id INTEGER'))
                    conn.commit()
                print("✓ 成功添加 preset_id 列到 test 表")
            else:
                print("✓ preset_id 列已存在，无需添加")
                
        except Exception as e:
            print(f"✗ 添加列失败: {e}")

if __name__ == '__main__':
    add_preset_id_column()
