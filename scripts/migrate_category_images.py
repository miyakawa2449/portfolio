#!/usr/bin/env python3
"""
既存のカテゴリ画像をUploadedImageテーブルに移行するスクリプト
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import Category, UploadedImage
from sqlalchemy import select
from PIL import Image
import re

def migrate_category_images():
    """既存のカテゴリ画像をUploadedImageテーブルに移行"""
    with app.app_context():
        # ogp_imageがあるすべてのカテゴリを取得
        categories = db.session.execute(
            select(Category).where(Category.ogp_image.is_not(None))
        ).scalars().all()
        
        migrated_count = 0
        
        for category in categories:
            try:
                # 既にUploadedImageに存在するかチェック
                existing = db.session.execute(
                    select(UploadedImage).where(UploadedImage.file_path == category.ogp_image)
                ).scalar_one_or_none()
                
                if existing:
                    print(f"Category {category.id} ({category.name}): 既に移行済み ({category.ogp_image})")
                    continue
                
                # ファイルパスを構築
                # ogp_image例: "uploads/categories/category_ogp_1_1723456789.jpg"
                full_filepath = os.path.join(app.static_folder, category.ogp_image)
                
                # ファイルが存在するかチェック
                if not os.path.exists(full_filepath):
                    print(f"Category {category.id} ({category.name}): ファイルが見つかりません ({full_filepath})")
                    continue
                
                # ファイル名を抽出
                filename = os.path.basename(category.ogp_image)
                
                # 画像情報を取得
                try:
                    with Image.open(full_filepath) as img:
                        width, height = img.size
                except Exception as img_error:
                    print(f"Category {category.id} ({category.name}): 画像読み込みエラー - {img_error}")
                    continue
                
                file_size = os.path.getsize(full_filepath)
                
                # UploadedImageレコード作成
                uploaded_image = UploadedImage(
                    filename=filename,
                    original_filename=filename,  # カテゴリ画像は生成されたファイル名を使用
                    file_path=category.ogp_image,
                    file_size=file_size,
                    mime_type='image/jpeg',
                    width=width,
                    height=height,
                    alt_text=f"{category.name}のOGP画像",
                    caption="",
                    description="カテゴリOGP画像（移行データ）",
                    uploader_id=1,  # 管理者ユーザーのIDを使用（要調整）
                    upload_date=category.created_at,  # カテゴリ作成日を使用
                    is_active=True,
                    usage_count=1
                )
                
                db.session.add(uploaded_image)
                migrated_count += 1
                print(f"Category {category.id} ({category.name}): 移行完了 ({filename})")
                
            except Exception as e:
                print(f"Category {category.id} ({category.name}): エラー - {str(e)}")
                continue
        
        if migrated_count > 0:
            db.session.commit()
            print(f"\n{migrated_count}件のカテゴリ画像を移行しました。")
        else:
            print("移行が必要な画像はありませんでした。")

if __name__ == "__main__":
    migrate_category_images()