# 管理者パスワードリセットスクリプト
from app import app, User, db
from werkzeug.security import generate_password_hash

def reset_admin_password(new_password, email=None):
    with app.app_context():
        if email:
            admin_user = User.query.filter_by(email=email).first()
        else:
            # 管理者権限のユーザーを検索
            admin_user = User.query.filter_by(role='admin').first()
        
        if admin_user:
            admin_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            print(f"管理者パスワードが正常に更新されました:")
            print(f"  Email: {admin_user.email}")
            print(f"  Name: {admin_user.name}")
            print(f"  New Password: {new_password}")
        else:
            print("管理者ユーザーが見つかりません")
            # 全ユーザーを表示
            all_users = User.query.all()
            print("データベース内のユーザー:")
            for user in all_users:
                print(f"  - {user.email} ({user.name}) - Role: {user.role}")

if __name__ == '__main__':
    print("=== 管理者パスワードリセット ===")
    print("現在の管理者ユーザー:")
    with app.app_context():
        admin_users = User.query.filter_by(role='admin').all()
        for user in admin_users:
            print(f"  - {user.email} ({user.name})")
    
    new_password = input("\n新しいパスワードを入力してください: ")
    
    if not new_password.strip():
        print("パスワードが入力されていません。")
        exit(1)
    
    reset_admin_password(new_password)