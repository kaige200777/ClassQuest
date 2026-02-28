from app import app, db, User

def reset_admin_password(new_password):
    with app.app_context():
        admin_user = User.query.filter_by(username='admin').first()
        if admin_user:
            admin_user.set_password(new_password)
            db.session.commit()
            print(f"✓ admin密码已成功重置为: {new_password}")
        else:
            print("✗ 未找到admin用户")

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1:
        new_password = sys.argv[1]
    else:
        new_password = 'admin123'
    reset_admin_password(new_password)
