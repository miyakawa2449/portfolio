#!/usr/bin/env python3
"""
画像パスを修正するスクリプト
articles/ → uploads/articles/ に変更
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Article
from sqlalchemy import select

def fix_image_paths():
    """画像パスを修正"""
    with app.app_context():
        # featured_imageがあるすべての記事を取得
        articles = db.session.execute(
            select(Article).where(Article.featured_image.is_not(None))
        ).scalars().all()
        
        updated_count = 0
        
        for article in articles:
            # パスがarticles/で始まる場合のみ修正
            if article.featured_image and article.featured_image.startswith('articles/'):
                old_path = article.featured_image
                new_path = f"uploads/{old_path}"
                article.featured_image = new_path
                updated_count += 1
                print(f"Article {article.id}: {old_path} → {new_path}")
        
        if updated_count > 0:
            db.session.commit()
            print(f"\n{updated_count}件の画像パスを修正しました。")
        else:
            print("修正が必要な画像パスはありませんでした。")

if __name__ == "__main__":
    fix_image_paths()