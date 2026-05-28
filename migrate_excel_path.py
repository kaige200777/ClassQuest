import sqlite3

conn = sqlite3.connect('instance/test_system.db')
cursor = conn.cursor()
try:
    cursor.execute('ALTER TABLE paper_bank ADD COLUMN excel_path VARCHAR(500)')
    conn.commit()
    print('excel_path 列添加成功')
except sqlite3.OperationalError as e:
    if 'duplicate column name' in str(e):
        print('excel_path 列已存在')
    else:
        print(f'错误: {e}')
conn.close()