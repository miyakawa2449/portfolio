#!/usr/bin/env python3
"""管理者ユーザー作成スクリプト"""

from app import app
from models import db, User
from werkzeug.security import generate_password_hash

def create_admin():
    with app.app_context():
        # 既存の管理者をチェック
        existing_admin = User.query.filter_by(role='admin').first()
        if existing_admin:
            print(f"管理者ユーザーが既に存在します: {existing_admin.email}")
            return

        # 管理者ユーザーを作成
        admin_email = "admin@example.com"
        admin_password = "AdminPass123!"
        admin_name = "管理者"
        
        admin_user = User(
            email=admin_email,
            name=admin_name,
            handle_name="admin",
            password_hash=generate_password_hash(admin_password),
            role='admin'
        )
        
        db.session.add(admin_user)
        db.session.commit()
        
        print("管理者ユーザーが作成されました:")
        print(f"メールアドレス: {admin_email}")
        print(f"パスワード: {admin_password}")
        print("※セキュリティのため、本番環境では必ずパスワードを変更してください。")

if __name__ == '__main__':
    create_admin()