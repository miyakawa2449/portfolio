#!/usr/bin/env python
"""
ポートフォリオサイト用の初期設定を追加するスクリプト
"""
import sys
import os
from datetime import datetime

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import SiteSetting

def init_portfolio_settings():
    """ポートフォリオ用の初期設定を追加"""
    with app.app_context():
        settings = [
            {
                'key': 'challenge_start_date',
                'value': '2025-01-01',
                'description': 'Python 100日チャレンジの開始日',
                'setting_type': 'text',
                'is_public': True
            },
            {
                'key': 'github_repo_url',
                'value': 'https://github.com/miyakawa2449/portfolio',
                'description': 'GitHubリポジトリのURL',
                'setting_type': 'text',
                'is_public': True
            },
            {
                'key': 'github_username',
                'value': 'miyakawa2449',
                'description': 'GitHubユーザー名',
                'setting_type': 'text',
                'is_public': True
            },
            {
                'key': 'site_name',
                'value': 'Python 100 Days Challenge',
                'description': 'サイト名',
                'setting_type': 'text',
                'is_public': True
            },
            {
                'key': 'site_description',
                'value': '100日間のPython学習の旅を記録するポートフォリオサイト',
                'description': 'サイトの説明',
                'setting_type': 'text',
                'is_public': True
            }
        ]
        
        for setting_data in settings:
            # 既存の設定を確認
            existing = SiteSetting.query.filter_by(key=setting_data['key']).first()
            if existing:
                print(f"設定 '{setting_data['key']}' は既に存在します。スキップします。")
            else:
                setting = SiteSetting(**setting_data)
                db.session.add(setting)
                print(f"設定 '{setting_data['key']}' を追加しました。")
        
        db.session.commit()
        print("\n初期設定の追加が完了しました。")

if __name__ == '__main__':
    init_portfolio_settings()