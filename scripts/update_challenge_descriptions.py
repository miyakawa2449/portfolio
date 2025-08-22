#!/usr/bin/env python
"""
チャレンジの説明を実際の内容に合わせて更新するスクリプト
"""
import sys
import os

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Challenge

def update_challenge_descriptions():
    """チャレンジの説明を更新"""
    with app.app_context():
        # チャレンジ1の説明を更新
        challenge1 = Challenge.query.filter_by(slug='python-100-days-1').first()
        if challenge1:
            challenge1.description = 'Python基礎から音声処理、Web開発まで幅広く学習。初期のプログラミング学習から、中期の音声処理プロジェクト、後期の日々のプロジェクト作成まで段階的にスキルアップしました。'
            print("チャレンジ1の説明を更新しました")
        
        # チャレンジ2の説明を更新
        challenge2 = Challenge.query.filter_by(slug='python-100-days-2').first()
        if challenge2:
            challenge2.description = 'AI・機械学習・データ分析に特化した第2回チャレンジ。第1回で培った基礎を活かし、より専門的な分野に挑戦中。'
            print("チャレンジ2の説明を更新しました")
        
        db.session.commit()
        print("\nチャレンジ説明の更新が完了しました。")

if __name__ == '__main__':
    update_challenge_descriptions()