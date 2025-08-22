"""
記事・カテゴリ・ユーザー管理のためのサービスクラス
重複実装を解消し、統一的なCRUD操作を提供
"""
import os
import re
import io
import base64
from PIL import Image
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from sqlalchemy import select, func
from models import db, Article, Category, User, article_categories
from werkzeug.security import generate_password_hash
import time


class ArticleService:
    """記事管理サービスクラス"""
    
    @staticmethod
    def create_article(form_data, author_id):
        """記事作成"""
        try:
            # 記事インスタンス作成
            article = Article(
                title=form_data['title'],
                slug=ArticleService.generate_unique_slug(form_data['slug'] or form_data['title']),
                summary=form_data.get('summary', ''),
                body=form_data.get('body', ''),
                is_published=form_data.get('is_published', False),
                allow_comments=form_data.get('allow_comments', True),
                meta_title=form_data.get('meta_title', ''),
                meta_description=form_data.get('meta_description', ''),
                meta_keywords=form_data.get('meta_keywords', ''),
                canonical_url=form_data.get('canonical_url', ''),
                author_id=author_id,
                challenge_id=form_data.get('challenge_id') if form_data.get('challenge_id') else None,
                challenge_day=form_data.get('challenge_day'),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            # データベースに追加
            db.session.add(article)
            db.session.flush()  # IDを取得するため
            
            # カテゴリ割り当て
            if form_data.get('category_id'):
                ArticleService.assign_category(article, form_data['category_id'])
            
            # アイキャッチ画像処理
            if form_data.get('cropped_image_data'):
                ArticleService.process_article_image(article, form_data['cropped_image_data'])
            elif form_data.get('featured_image') and hasattr(form_data['featured_image'], 'filename'):
                # 通常の画像アップロード処理
                file = form_data['featured_image']
                if file.filename:
                    timestamp = str(int(time.time() * 1000000))
                    filename = f"featured_cropped_{article.id}_{timestamp}.{file.filename.rsplit('.', 1)[1].lower()}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'articles', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    article.featured_image = f"uploads/articles/{filename}"
            
            # コミット
            db.session.commit()
            return article, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"記事作成エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def update_article(article, form_data):
        """記事更新"""
        try:
            # 基本情報更新
            article.title = form_data['title']
            article.slug = ArticleService.generate_unique_slug(form_data['slug'] or form_data['title'], article.id)
            article.summary = form_data.get('summary', '')
            article.body = form_data.get('body', '')
            article.is_published = form_data.get('is_published', False)
            article.allow_comments = form_data.get('allow_comments', True)
            article.meta_title = form_data.get('meta_title', '')
            article.meta_description = form_data.get('meta_description', '')
            article.meta_keywords = form_data.get('meta_keywords', '')
            article.canonical_url = form_data.get('canonical_url', '')
            article.updated_at = datetime.utcnow()
            
            # カテゴリ更新
            if form_data.get('category_id'):
                ArticleService.assign_category(article, form_data['category_id'])
            
            # アイキャッチ画像処理
            # 新しい画像データがある場合のみ更新
            if form_data.get('cropped_image_data'):
                ArticleService.process_article_image(article, form_data['cropped_image_data'])
            elif form_data.get('featured_image') and hasattr(form_data['featured_image'], 'filename'):
                # 通常の画像アップロード処理
                file = form_data['featured_image']
                if file.filename:
                    timestamp = str(int(time.time() * 1000000))
                    filename = f"featured_cropped_{article.id}_{timestamp}.{file.filename.rsplit('.', 1)[1].lower()}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'articles', filename)
                    os.makedirs(os.path.dirname(filepath), exist_ok=True)
                    file.save(filepath)
                    article.featured_image = f"uploads/articles/{filename}"
            # 画像削除フラグがある場合
            elif form_data.get('remove_featured_image'):
                article.featured_image = None
            
            # コミット
            db.session.commit()
            return article, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"記事更新エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def setup_category_choices(form):
        """フォームにカテゴリ選択肢を設定"""
        categories = db.session.execute(select(Category).order_by(Category.name)).scalars().all()
        form.category_id.choices = [(0, 'カテゴリを選択')] + [(c.id, c.name) for c in categories]
    
    @staticmethod
    def setup_challenge_choices(form):
        """フォームにチャレンジ選択肢を設定"""
        from models import Challenge
        challenges = db.session.execute(select(Challenge).order_by(Challenge.display_order)).scalars().all()
        form.challenge_id.choices = [(0, 'チャレンジを選択')] + [(c.id, c.name) for c in challenges]
    
    @staticmethod
    def generate_unique_slug(title, article_id=None):
        """ユニークなスラッグを生成"""
        # 基本的なスラッグ生成
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # 重複チェック
        base_slug = slug
        counter = 1
        while True:
            query = select(Article).where(Article.slug == slug)
            if article_id:
                query = query.where(Article.id != article_id)
            
            existing = db.session.execute(query).scalar_one_or_none()
            if not existing:
                break
            
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    @staticmethod
    def validate_article_data(form, article_id=None):
        """記事データのバリデーション"""
        errors = []
        
        # タイトル必須チェック
        if not form.title.data:
            errors.append("タイトルは必須です")
        
        # スラッグ重複チェック
        if form.slug.data:
            query = select(Article).where(Article.slug == form.slug.data)
            if article_id:
                query = query.where(Article.id != article_id)
            
            existing = db.session.execute(query).scalar_one_or_none()
            if existing:
                errors.append("このスラッグは既に使用されています")
        
        return errors
    
    @staticmethod
    def process_article_image(article, cropped_image_data):
        """記事のアイキャッチ画像処理"""
        try:
            # Base64データから画像を生成
            image_data = re.sub('^data:image/.+;base64,', '', cropped_image_data)
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            # ファイル名生成
            timestamp = str(int(time.time() * 1000000))
            filename = f"featured_cropped_{article.id}_{timestamp}.jpg"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'articles', filename)
            
            # ディレクトリ作成
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # 画像保存
            image.save(filepath, 'JPEG', quality=85)
            article.featured_image = f"uploads/articles/{filename}"
            
            # UploadedImageテーブルにも保存
            ArticleService._save_to_uploaded_images(
                filename=filename,
                file_path=f"uploads/articles/{filename}",
                image=image,
                uploader_id=article.author_id,
                alt_text=f"{article.title}のアイキャッチ画像",
                description="記事のアイキャッチ画像"
            )
            
            # 重要: データベースセッションに変更を追加
            db.session.add(article)
            
        except Exception as e:
            current_app.logger.error(f"画像処理エラー: {str(e)}")
    
    @staticmethod
    def _save_to_uploaded_images(filename, file_path, image, uploader_id, alt_text="", caption="", description=""):
        """UploadedImageテーブルに画像情報を保存"""
        from models import UploadedImage
        import os
        
        try:
            # ファイルサイズを取得
            full_filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'articles', filename)
            file_size = os.path.getsize(full_filepath) if os.path.exists(full_filepath) else 0
            
            # UploadedImageレコード作成
            uploaded_image = UploadedImage(
                filename=filename,
                original_filename=filename,  # アイキャッチ画像の場合、生成されたファイル名を使用
                file_path=file_path,
                file_size=file_size,
                mime_type='image/jpeg',
                width=image.width,
                height=image.height,
                alt_text=alt_text,
                caption=caption,
                description=description,
                uploader_id=uploader_id,
                is_active=True,
                usage_count=1  # アイキャッチ画像として使用されているため1
            )
            
            db.session.add(uploaded_image)
            
        except Exception as e:
            current_app.logger.error(f"UploadedImage保存エラー: {str(e)}")
    
    @staticmethod
    def assign_category(article, category_id):
        """記事にカテゴリを割り当て"""
        # 既存のカテゴリをクリア
        article.categories.clear()
        
        # 新しいカテゴリを追加
        if category_id and category_id != 0:
            category = db.session.get(Category, category_id)
            if category:
                article.categories.append(category)
    
    @staticmethod
    def get_article_context(article=None):
        """記事フォーム用のコンテキストを取得"""
        from flask import url_for
        return {
            'is_edit': article is not None,
            'article': article,
            'form_title': '記事編集' if article else '記事作成',
            'submit_text': '更新' if article else '作成',
            'form_action': url_for('admin.edit_article', article_id=article.id) if article else url_for('admin.create_article')
        }


class CategoryService:
    """カテゴリ管理サービスクラス"""
    
    @staticmethod
    def create_category(form_data):
        """カテゴリ作成"""
        try:
            category = Category(
                name=form_data['name'],
                slug=CategoryService.generate_unique_slug(form_data['slug'] or form_data['name']),
                description=form_data.get('description', ''),
                meta_title=form_data.get('meta_title', ''),
                meta_description=form_data.get('meta_description', ''),
                ogp_title=form_data.get('ogp_title', ''),
                ogp_description=form_data.get('ogp_description', ''),
                created_at=datetime.utcnow()
            )
            
            db.session.add(category)
            db.session.flush()
            
            # OGP画像処理
            crop_data = CategoryService.extract_crop_data(form_data)
            if form_data.get('ogp_image_data'):
                CategoryService.process_category_image(category, form_data['ogp_image_data'], crop_data)
            
            db.session.commit()
            return category, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"カテゴリ作成エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def update_category(category, form_data):
        """カテゴリ更新"""
        try:
            category.name = form_data['name']
            category.slug = CategoryService.generate_unique_slug(form_data['slug'] or form_data['name'], category.id)
            category.description = form_data.get('description', '')
            category.meta_title = form_data.get('meta_title', '')
            category.meta_description = form_data.get('meta_description', '')
            category.ogp_title = form_data.get('ogp_title', '')
            category.ogp_description = form_data.get('ogp_description', '')
            
            # OGP画像処理
            crop_data = CategoryService.extract_crop_data(form_data)
            if form_data.get('ogp_image_data'):
                CategoryService.process_category_image(category, form_data['ogp_image_data'], crop_data)
            
            db.session.commit()
            return category, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"カテゴリ更新エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def generate_unique_slug(name, category_id=None):
        """ユニークなスラッグを生成"""
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        
        base_slug = slug
        counter = 1
        while True:
            query = select(Category).where(Category.slug == slug)
            if category_id:
                query = query.where(Category.id != category_id)
            
            existing = db.session.execute(query).scalar_one_or_none()
            if not existing:
                break
            
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    @staticmethod
    def validate_category_data(form_data, category_id=None):
        """カテゴリデータのバリデーション"""
        errors = []
        
        if not form_data.get('name'):
            errors.append("カテゴリ名は必須です")
        
        if form_data.get('slug'):
            query = select(Category).where(Category.slug == form_data['slug'])
            if category_id:
                query = query.where(Category.id != category_id)
            
            existing = db.session.execute(query).scalar_one_or_none()
            if existing:
                errors.append("このスラッグは既に使用されています")
        
        return errors
    
    @staticmethod
    def process_category_image(category, ogp_image_data, crop_data=None):
        """カテゴリのOGP画像処理"""
        try:
            image_data = re.sub('^data:image/.+;base64,', '', ogp_image_data)
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            # クロップ処理
            if crop_data and all(crop_data.values()):
                image = image.crop((
                    int(crop_data['x']),
                    int(crop_data['y']),
                    int(crop_data['x']) + int(crop_data['width']),
                    int(crop_data['y']) + int(crop_data['height'])
                ))
            
            # リサイズ (1200x630)
            image = image.resize((1200, 630), Image.Resampling.LANCZOS)
            
            # 保存
            timestamp = str(int(time.time() * 1000000))
            filename = f"category_ogp_{category.id}_{timestamp}.jpg"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], 'category_ogp', filename)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            image.save(filepath, 'JPEG', quality=85)
            
            category.ogp_image = f"category_ogp/{filename}"
            
        except Exception as e:
            current_app.logger.error(f"OGP画像処理エラー: {str(e)}")
    
    @staticmethod
    def extract_crop_data(form_data):
        """フォームデータからクロップ情報を抽出"""
        return {
            'x': form_data.get('ogp_crop_x'),
            'y': form_data.get('ogp_crop_y'),
            'width': form_data.get('ogp_crop_width'),
            'height': form_data.get('ogp_crop_height')
        }
    
    @staticmethod
    def get_category_context(category=None):
        """カテゴリフォーム用のコンテキストを取得"""
        from flask import url_for
        return {
            'is_edit': category is not None,
            'category': category,
            'form_title': 'カテゴリ編集' if category else 'カテゴリ作成',
            'submit_text': '更新' if category else '作成',
            'form_action': url_for('admin.edit_category', category_id=category.id) if category else url_for('admin.create_category')
        }


class UserService:
    """ユーザー管理サービスクラス"""
    
    @staticmethod
    def create_user(form_data):
        """ユーザー作成"""
        try:
            user = User(
                email=form_data['email'],
                name=form_data['name'],
                handle_name=form_data.get('handle_name', ''),
                password_hash=generate_password_hash(form_data['password']),
                role=form_data.get('role', 'author'),
                notify_on_publish=form_data.get('notify_on_publish', False),
                notify_on_comment=form_data.get('notify_on_comment', False),
                introduction=form_data.get('introduction', ''),
                birthplace=form_data.get('birthplace', ''),
                birthday=form_data.get('birthday'),
                sns_x=form_data.get('sns_x', ''),
                sns_facebook=form_data.get('sns_facebook', ''),
                sns_instagram=form_data.get('sns_instagram', ''),
                sns_threads=form_data.get('sns_threads', ''),
                sns_youtube=form_data.get('sns_youtube', ''),
                created_at=datetime.utcnow()
            )
            
            db.session.add(user)
            db.session.commit()
            return user, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"ユーザー作成エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def update_user(user, form_data):
        """ユーザー更新"""
        try:
            user.email = form_data['email']
            user.name = form_data['name']
            user.handle_name = form_data.get('handle_name', '')
            user.role = form_data.get('role', 'author')
            user.notify_on_publish = form_data.get('notify_on_publish', False)
            user.notify_on_comment = form_data.get('notify_on_comment', False)
            user.introduction = form_data.get('introduction', '')
            user.birthplace = form_data.get('birthplace', '')
            user.birthday = form_data.get('birthday')
            user.sns_x = form_data.get('sns_x', '')
            user.sns_facebook = form_data.get('sns_facebook', '')
            user.sns_instagram = form_data.get('sns_instagram', '')
            user.sns_threads = form_data.get('sns_threads', '')
            user.sns_youtube = form_data.get('sns_youtube', '')
            
            # パスワード更新（空でない場合のみ）
            if form_data.get('password'):
                user.password_hash = generate_password_hash(form_data['password'])
            
            db.session.commit()
            return user, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"ユーザー更新エラー: {str(e)}")
            return None, str(e)
    
    @staticmethod
    def validate_password(password):
        """パスワードバリデーション"""
        if len(password) < 8:
            return "パスワードは8文字以上で入力してください"
        return None
    
    @staticmethod
    def validate_user_data(form_data, user_id=None):
        """ユーザーデータのバリデーション"""
        errors = []
        
        # メールアドレス必須チェック
        if not form_data.get('email'):
            errors.append("メールアドレスは必須です")
        
        # メールアドレス重複チェック
        if form_data.get('email'):
            query = select(User).where(User.email == form_data['email'])
            if user_id:
                query = query.where(User.id != user_id)
            
            existing = db.session.execute(query).scalar_one_or_none()
            if existing:
                errors.append("このメールアドレスは既に使用されています")
        
        # パスワードチェック（新規作成時は必須）
        if not user_id and not form_data.get('password'):
            errors.append("パスワードは必須です")
        elif form_data.get('password'):
            password_error = UserService.validate_password(form_data['password'])
            if password_error:
                errors.append(password_error)
        
        return errors
    
    @staticmethod
    def process_user_form_data(form_data):
        """フォームデータの処理・変換"""
        processed = {}
        for key, value in form_data.items():
            if value == '':
                processed[key] = None
            else:
                processed[key] = value
        return processed
    
    @staticmethod
    def get_user_context(user=None):
        """ユーザーフォーム用のコンテキストを取得"""
        from flask import url_for
        return {
            'is_edit': user is not None,
            'user': user,
            'form_title': 'ユーザー編集' if user else 'ユーザー作成',
            'submit_text': '更新' if user else '作成',
            'form_action': url_for('admin.edit_user', user_id=user.id) if user else url_for('admin.create_user')
        }


class ImageProcessingService:
    """画像処理サービスクラス"""
    
    @staticmethod
    def delete_old_image(old_path):
        """古い画像ファイルを削除"""
        if old_path:
            try:
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], old_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    current_app.logger.info(f"古い画像を削除: {file_path}")
            except Exception as e:
                current_app.logger.error(f"画像削除エラー: {str(e)}")
    
    @staticmethod
    def process_uploaded_image(file, prefix, entity_id):
        """アップロードされた画像を処理"""
        if file and file.filename:
            timestamp = str(int(time.time() * 1000000))
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{prefix}_{entity_id}_{timestamp}.{ext}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], prefix, filename)
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
            
            return f"{prefix}/{filename}"
        return None