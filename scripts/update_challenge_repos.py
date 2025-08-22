#!/usr/bin/env python
"""
既存のチャレンジのGitHubリポジトリ情報を更新するスクリプト
"""
import sys
import os

# プロジェクトのルートディレクトリをPythonパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db
from models import Challenge

def update_challenge_repos():
    """チャレンジのGitHubリポジトリ情報を更新"""
    with app.app_context():
        # チャレンジ1のリポジトリ情報
        challenge1_repos = [
            {
                'name': '100day（初期）',
                'url': 'https://github.com/miyakawa2449/100day',
                'description': 'チャレンジ初期の学習記録とプロジェクト'
            },
            {
                'name': 'mini-blog（中期）',
                'url': 'https://github.com/miyakawa2449/mini-blog',
                'description': 'Flask製ブログCMSシステム'
            },
            {
                'name': 'AudioOpt（中期）',
                'url': 'https://github.com/miyakawa2449/AudioOpt',
                'description': '音声処理最適化プロジェクト'
            },
            {
                'name': 'Python_Audio_dataset（中期）',
                'url': 'https://github.com/miyakawa2449/Python_Audio_dataset',
                'description': '音声データセット処理ツール'
            },
            {
                'name': 'Audio-Pipeline-Integrated（中期）',
                'url': 'https://github.com/miyakawa2449/Audio-Pipeline-Integrated',
                'description': '統合音声処理パイプライン'
            },
            {
                'name': 'daily-python-projects（後期）',
                'url': 'https://github.com/miyakawa2449/daily-python-projects',
                'description': '日々のPythonプロジェクト集'
            }
        ]
        
        # チャレンジ2のリポジトリ情報
        challenge2_repos = [
            {
                'name': '100days-of-ml-ai',
                'url': 'https://github.com/miyakawa2449/100days-of-ml-ai',
                'description': 'AI・機械学習・データ分析をテーマとした第2回チャレンジ（進行中）'
            }
        ]
        
        # チャレンジ1を更新
        challenge1 = Challenge.query.filter_by(slug='python-100-days-1').first()
        if challenge1:
            challenge1.set_github_repos(challenge1_repos)
            print(f"チャレンジ1のリポジトリ情報を更新しました ({len(challenge1_repos)}個)")
        
        # チャレンジ2を更新
        challenge2 = Challenge.query.filter_by(slug='python-100-days-2').first()
        if challenge2:
            challenge2.set_github_repos(challenge2_repos)
            print(f"チャレンジ2のリポジトリ情報を更新しました ({len(challenge2_repos)}個)")
        
        db.session.commit()
        print("\nGitHubリポジトリ情報の更新が完了しました。")
        
        # 結果を表示
        all_challenges = Challenge.query.order_by(Challenge.display_order).all()
        for challenge in all_challenges:
            print(f"\n{challenge.name}:")
            repos = challenge.github_repositories
            if repos:
                for i, repo in enumerate(repos, 1):
                    print(f"  {i}. {repo['name']}: {repo['url']}")
                    if repo.get('description'):
                        print(f"     {repo['description']}")
            else:
                print("  リポジトリが設定されていません")

if __name__ == '__main__':
    update_challenge_repos()