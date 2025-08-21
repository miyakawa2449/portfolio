#!/usr/bin/env python3
"""
既存のアイキャッチ画像をUploadedImageテーブルに移行するスクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Article, UploadedImage
from sqlalchemy import select
from PIL import Image
import re

def migrate_featured_images():
    """既存のアイキャッチ画像をUploadedImageテーブルに移行"""
    with app.app_context():
        # featured_imageがあるすべての記事を取得
        articles = db.session.execute(
            select(Article).where(Article.featured_image.is_not(None))
        ).scalars().all()
        
        migrated_count = 0
        
        for article in articles:
            try:
                # 既にUploadedImageに存在するかチェック
                existing = db.session.execute(
                    select(UploadedImage).where(UploadedImage.file_path == article.featured_image)
                ).scalar_one_or_none()
                
                if existing:
                    print(f"Article {article.id}: 既に移行済み ({article.featured_image})")
                    continue
                
                # ファイルパスを構築
                # featured_image例: "uploads/articles/featured_cropped_26_1754957145276911.jpg"
                file_path_parts = article.featured_image.split('/')
                if len(file_path_parts) >= 3:
                    filename = file_path_parts[-1]  # ファイル名部分
                    full_filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'articles', filename)
                    
                    # ファイルが存在するかチェック
                    if not os.path.exists(full_filepath):
                        print(f"Article {article.id}: ファイルが見つかりません ({full_filepath})")
                        continue
                    
                    # 画像情報を取得
                    with Image.open(full_filepath) as img:
                        width, height = img.size
                    
                    file_size = os.path.getsize(full_filepath)
                    
                    # UploadedImageレコード作成
                    uploaded_image = UploadedImage(
                        filename=filename,
                        original_filename=filename,
                        file_path=article.featured_image,
                        file_size=file_size,
                        mime_type='image/jpeg',
                        width=width,
                        height=height,
                        alt_text=f"{article.title}のアイキャッチ画像",
                        caption="",
                        description="記事のアイキャッチ画像（移行データ）",
                        uploader_id=article.author_id,
                        upload_date=article.created_at,  # 記事作成日を使用
                        is_active=True,
                        usage_count=1
                    )
                    
                    db.session.add(uploaded_image)
                    migrated_count += 1
                    print(f"Article {article.id}: 移行完了 ({filename})")
                
            except Exception as e:
                print(f"Article {article.id}: エラー - {str(e)}")
                continue
        
        if migrated_count > 0:
            db.session.commit()
            print(f"\n{migrated_count}件のアイキャッチ画像を移行しました。")
        else:
            print("移行が必要な画像はありませんでした。")

if __name__ == "__main__":
    migrate_featured_images()