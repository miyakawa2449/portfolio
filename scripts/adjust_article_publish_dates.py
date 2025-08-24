#!/usr/bin/env python
"""
既存記事の公開日（published_at）を適正化するスクリプト

チャレンジ日数に基づいて、適切な公開日を設定します。
Challenge #1: 2024年1月開始
Challenge #2: 2025年7月開始
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Article, Challenge
from app import app
from datetime import datetime, timedelta

# チャレンジの開始日設定
CHALLENGE_START_DATES = {
    1: datetime(2024, 1, 15),  # Challenge #1: 2024年1月15日開始
    2: datetime(2025, 7, 1),   # Challenge #2: 2025年7月1日開始
}

def adjust_article_publish_dates():
    """記事の公開日を調整"""
    with app.app_context():
        # チャレンジごとに処理
        challenges = Challenge.query.all()
        
        for challenge in challenges:
            print(f"\n=== {challenge.name} の記事を処理中 ===")
            
            # チャレンジの開始日を取得
            start_date = CHALLENGE_START_DATES.get(challenge.id)
            if not start_date:
                print(f"警告: Challenge ID {challenge.id} の開始日が設定されていません")
                continue
            
            # チャレンジに関連する記事を取得
            articles = Article.query.filter_by(
                challenge_id=challenge.id
            ).order_by(Article.challenge_day.asc()).all()
            
            print(f"記事数: {len(articles)}")
            print(f"開始日: {start_date.strftime('%Y-%m-%d')}")
            
            # 各記事の公開日を調整
            updated_count = 0
            for article in articles:
                if article.challenge_day:
                    # チャレンジ日数から公開日を計算
                    # Day 1 = 開始日、Day 2 = 開始日 + 1日...
                    new_published_at = start_date + timedelta(days=article.challenge_day - 1)
                    
                    # 時刻は午前10時に統一
                    new_published_at = new_published_at.replace(hour=10, minute=0, second=0, microsecond=0)
                    
                    if article.published_at != new_published_at:
                        old_date = article.published_at.strftime('%Y-%m-%d %H:%M') if article.published_at else 'なし'
                        article.published_at = new_published_at
                        updated_count += 1
                        
                        print(f"  記事: {article.title}")
                        print(f"    Day {article.challenge_day}: {old_date} → {new_published_at.strftime('%Y-%m-%d %H:%M')}")
                else:
                    print(f"  警告: 記事「{article.title}」にchallenge_dayが設定されていません")
            
            print(f"更新された記事数: {updated_count}")
        
        # 変更を適用
        print("\n=== 変更を適用中 ===")
        db.session.commit()
        print("✅ 公開日の調整が完了しました！")
        
        # 調整後の状態を表示
        print("\n=== 調整後の記事一覧（最新10件） ===")
        recent_articles = Article.query.filter_by(is_published=True).order_by(
            Article.published_at.desc()
        ).limit(10).all()
        
        for i, article in enumerate(recent_articles, 1):
            print(f"{i}. {article.title}")
            print(f"   Challenge: {article.challenge.name if article.challenge else 'なし'}")
            print(f"   Day: {article.challenge_day}")
            print(f"   公開日: {article.published_at.strftime('%Y-%m-%d %H:%M') if article.published_at else 'なし'}")
            print()

if __name__ == '__main__':
    adjust_article_publish_dates()