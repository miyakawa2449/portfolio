#!/usr/bin/env python
"""
チャレンジデータの初期化スクリプト
"""
import sys
import os
from datetime import datetime, date

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Challenge

def init_challenges():
    """チャレンジデータの初期化"""
    with app.app_context():
        challenges = [
            {
                'name': 'Python 100 Days Challenge #1',
                'slug': 'python-100-days-1',
                'description': '最初の100日Pythonチャレンジ。基礎からWebアプリケーション開発まで幅広く学習しました。',
                'start_date': date(2025, 4, 30),
                'end_date': date(2025, 8, 7),
                'target_days': 100,
                'github_repo': 'https://github.com/miyakawa2449/python-100-days-1',
                'is_active': False,
                'display_order': 1
            },
            {
                'name': 'Python 100 Days Challenge #2',
                'slug': 'python-100-days-2',
                'description': '2回目の100日Pythonチャレンジ。さらなるスキル向上を目指して継続学習中。',
                'start_date': date(2025, 8, 13),
                'end_date': None,  # 進行中
                'target_days': 100,
                'github_repo': 'https://github.com/miyakawa2449/python-100-days-2',
                'is_active': True,  # 現在アクティブ
                'display_order': 2
            }
        ]
        
        for challenge_data in challenges:
            # 既存のチャレンジを確認
            existing = Challenge.query.filter_by(slug=challenge_data['slug']).first()
            if existing:
                print(f"チャレンジ '{challenge_data['name']}' は既に存在します。スキップします。")
            else:
                challenge = Challenge(**challenge_data)
                db.session.add(challenge)
                print(f"チャレンジ '{challenge_data['name']}' を追加しました。")
        
        db.session.commit()
        print("\nチャレンジデータの初期化が完了しました。")
        
        # 作成されたチャレンジを表示
        all_challenges = Challenge.query.order_by(Challenge.display_order).all()
        print(f"\n現在のチャレンジ一覧:")
        for challenge in all_challenges:
            status = "✅ 完了" if challenge.end_date else ("🔥 進行中" if challenge.is_active else "⏸️ 停止中")
            print(f"  {challenge.display_order}. {challenge.name} - {status}")
            print(f"     期間: {challenge.start_date} ～ {challenge.end_date or '進行中'}")
            print(f"     進捗: {challenge.days_elapsed}/{challenge.target_days}日 ({challenge.progress_percentage:.1f}%)")

if __name__ == '__main__':
    init_challenges()