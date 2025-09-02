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
                published_at=form_data.get('published_at') if form_data.get('is_published', False) else None,
                allow_comments=form_data.get('allow_comments', True),
                show_toc=form_data.get('show_toc', True),
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
            # デバッグ用ログ
            print(f"DEBUG update_article: challenge_id={form_data.get('challenge_id')}, challenge_day={form_data.get('challenge_day')}")
            print(f"DEBUG update_article: category_id={form_data.get('category_id')}")
            
            # 基本情報更新
            article.title = form_data['title']
            article.slug = ArticleService.generate_unique_slug(form_data['slug'] or form_data['title'], article.id)
            article.summary = form_data.get('summary', '')
            article.body = form_data.get('body', '')
            article.is_published = form_data.get('is_published', False)
            article.published_at = form_data.get('published_at') if form_data.get('is_published', False) else None
            article.allow_comments = form_data.get('allow_comments', True)
            article.show_toc = form_data.get('show_toc', True)
            article.meta_title = form_data.get('meta_title', '')
            article.meta_description = form_data.get('meta_description', '')
            article.meta_keywords = form_data.get('meta_keywords', '')
            article.canonical_url = form_data.get('canonical_url', '')
            
            # チャレンジ情報更新
            challenge_id = form_data.get('challenge_id')
            if challenge_id and challenge_id != 0:
                article.challenge_id = challenge_id
                article.challenge_day = form_data.get('challenge_day')
                print(f"DEBUG: Setting challenge_id={challenge_id}, challenge_day={form_data.get('challenge_day')}")
            else:
                article.challenge_id = None
                article.challenge_day = None
                print(f"DEBUG: Clearing challenge data (challenge_id was {challenge_id})")
            
            article.updated_at = datetime.utcnow()
            
            # カテゴリ更新
            print(f"DEBUG: About to assign category - category_id={form_data.get('category_id')}")
            ArticleService.assign_category(article, form_data.get('category_id'))
            
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
    def setup_category_choices(form, challenge_id=None):
        """フォームにカテゴリ選択肢を設定"""
        query = select(Category).order_by(Category.name)
        if challenge_id:
            query = query.where(Category.challenge_id == challenge_id)
        categories = db.session.execute(query).scalars().all()
        form.category_id.choices = [(0, 'カテゴリを選択')] + [(c.id, c.name) for c in categories]
    
    @staticmethod
    def setup_challenge_choices(form):
        """フォームにチャレンジ選択肢を設定"""
        from models import Challenge
        challenges = db.session.execute(select(Challenge).order_by(Challenge.display_order)).scalars().all()
        form.challenge_id.choices = [(0, 'チャレンジを選択')] + [(c.id, c.name) for c in challenges]
    
    @staticmethod
    def setup_project_choices(form, challenge_id=None):
        """フォームにプロジェクト選択肢を設定"""
        from models import Project
        query = select(Project).where(Project.status == 'active')
        if challenge_id:
            query = query.where(Project.challenge_id == challenge_id)
        query = query.order_by(Project.created_at.desc())
        projects = db.session.execute(query).scalars().all()
        form.related_projects.choices = [(p.id, f"{p.title} (Day {p.challenge_day})" if p.challenge_day else p.title) for p in projects]
    
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
        
        # デバッグ用ログ
        print(f"DEBUG validate_article_data: challenge_id={form.challenge_id.data}, category_id={form.category_id.data}")
        print(f"DEBUG form.category_id.data type: {type(form.category_id.data)}")
        
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
        
        # チャレンジとカテゴリの整合性チェック
        # カテゴリが「カテゴリを選択」(0)の場合はスキップ
        if (form.challenge_id.data and 
            form.category_id.data is not None and 
            int(form.category_id.data) != 0):
            
            print(f"DEBUG: Performing category validation - category_id={form.category_id.data}")
            
            from models import Category
            category = db.session.execute(
                select(Category).where(Category.id == form.category_id.data)
            ).scalar_one_or_none()
            
            if category and category.challenge_id and category.challenge_id != form.challenge_id.data:
                print(f"DEBUG: Category challenge mismatch - category.challenge_id={category.challenge_id}, form.challenge_id={form.challenge_id.data}")
                errors.append(f"選択されたカテゴリ「{category.name}」は、選択されたチャレンジに対応していません")
        else:
            print(f"DEBUG: Skipping category validation - challenge_id={form.challenge_id.data}, category_id={form.category_id.data}")
        
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
        print(f"DEBUG assign_category: received category_id={category_id}, type={type(category_id)}")
        
        # 既存のカテゴリをクリア
        article.categories.clear()
        print(f"DEBUG assign_category: cleared existing categories")
        
        # 新しいカテゴリを追加
        if category_id and category_id != 0:
            print(f"DEBUG assign_category: attempting to add category {category_id}")
            category = db.session.get(Category, category_id)
            if category:
                article.categories.append(category)
                print(f"DEBUG assign_category: added category {category.name}")
            else:
                print(f"DEBUG assign_category: category {category_id} not found")
        else:
            print(f"DEBUG assign_category: skipping category assignment (category_id={category_id})")
    
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
    
    @staticmethod
    def get_published_articles(page=1, per_page=10, challenge_id=None):
        """公開記事を取得（ページング対応）"""
        query = Article.query.filter_by(is_published=True)
        
        if challenge_id:
            query = query.filter_by(challenge_id=challenge_id)
        
        query = query.order_by(Article.published_at.desc())
        return query.paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def get_article_by_slug(slug):
        """スラッグから記事を取得"""
        return Article.query.filter_by(slug=slug, is_published=True).first()
    
    @staticmethod
    def search_articles(query_string, challenge_id=None):
        """記事検索"""
        search_filter = db.or_(
            Article.title.contains(query_string),
            Article.body.contains(query_string),
            Article.summary.contains(query_string)
        )
        
        query = Article.query.filter(search_filter, Article.is_published == True)
        
        if challenge_id:
            query = query.filter_by(challenge_id=challenge_id)
        
        return query.order_by(Article.published_at.desc()).all()
    
    @staticmethod
    def get_related_articles(article, limit=5):
        """関連記事を取得"""
        # 同じカテゴリの記事を取得
        if article.categories:
            category_ids = [c.id for c in article.categories]
            related = Article.query.join(
                article_categories
            ).filter(
                article_categories.c.category_id.in_(category_ids),
                Article.id != article.id,
                Article.is_published == True
            ).order_by(
                Article.published_at.desc()
            ).limit(limit).all()
            
            if related:
                return related
        
        # カテゴリがない場合は同じチャレンジの記事
        if article.challenge_id:
            return Article.query.filter(
                Article.challenge_id == article.challenge_id,
                Article.id != article.id,
                Article.is_published == True
            ).order_by(
                Article.published_at.desc()
            ).limit(limit).all()
        
        # それもない場合は最新記事
        return Article.query.filter(
            Article.id != article.id,
            Article.is_published == True
        ).order_by(
            Article.published_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def get_article_stats():
        """記事統計情報を取得"""
        try:
            total = Article.query.count()
            published = Article.query.filter_by(is_published=True).count()
            draft = Article.query.filter_by(is_published=False).count()
            
            # 今日の記事数
            today = datetime.utcnow().date()
            today_count = Article.query.filter(
                func.date(Article.created_at) == today
            ).count()
            
            # チャレンジ別統計
            from models import Challenge
            challenge_stats = db.session.query(
                Challenge.name,
                func.count(Article.id).label('count')
            ).join(
                Article, Article.challenge_id == Challenge.id
            ).group_by(
                Challenge.name
            ).all()
            
            return {
                'total': total,
                'published': published,
                'draft': draft,
                'today': today_count,
                'by_challenge': {name: count for name, count in challenge_stats}
            }
        except Exception as e:
            current_app.logger.error(f"統計取得エラー: {str(e)}")
            return {
                'total': 0,
                'published': 0,
                'draft': 0,
                'today': 0,
                'by_challenge': {}
            }
    
    @staticmethod
    def delete_article(article_id):
        """記事削除"""
        try:
            article = db.session.get(Article, article_id)
            if not article:
                return False, "記事が見つかりません"
            
            # 関連画像の削除
            if article.featured_image:
                ImageProcessingService.delete_old_image(article.featured_image)
            
            db.session.delete(article)
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"記事削除エラー: {str(e)}")
            return False, "記事の削除中にエラーが発生しました"
    
    @staticmethod
    def bulk_delete_articles(article_ids):
        """記事一括削除"""
        try:
            deleted = 0
            for article_id in article_ids:
                article = db.session.get(Article, article_id)
                if article:
                    if article.featured_image:
                        ImageProcessingService.delete_old_image(article.featured_image)
                    db.session.delete(article)
                    deleted += 1
            
            db.session.commit()
            return deleted, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"一括削除エラー: {str(e)}")
            return 0, "一括削除中にエラーが発生しました"
    
    @staticmethod
    def update_article_status(article_id, is_published):
        """記事の公開状態を更新"""
        try:
            article = db.session.get(Article, article_id)
            if not article:
                return False, "記事が見つかりません"
            
            article.is_published = is_published
            if is_published and not article.published_at:
                article.published_at = datetime.utcnow()
            
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"ステータス更新エラー: {str(e)}")
            return False, "ステータス更新中にエラーが発生しました"
    
    @staticmethod
    def get_latest_articles(limit=5, exclude_id=None):
        """最新記事を取得"""
        query = Article.query.filter_by(is_published=True)
        
        if exclude_id:
            query = query.filter(Article.id != exclude_id)
        
        return query.order_by(Article.published_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_articles_by_category(category_id, page=1, per_page=10):
        """カテゴリ別記事を取得"""
        return Article.query.join(
            article_categories
        ).filter(
            article_categories.c.category_id == category_id,
            Article.is_published == True
        ).order_by(
            Article.published_at.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)
    
    @staticmethod
    def generate_article_seo_data(article):
        """記事のSEOデータを生成"""
        from seo import generate_article_structured_data
        
        # メタタイトル（空の場合はデフォルト）
        meta_title = article.meta_title or f"{article.title} - Python 100 Days Challenge"
        
        # メタ説明（空の場合は要約または本文から生成）
        if article.meta_description:
            meta_description = article.meta_description
        elif article.summary:
            meta_description = article.summary[:160]
        else:
            # Markdownを除去して説明を生成
            from utils import strip_markdown
            meta_description = strip_markdown(article.body)[:160] if article.body else ""
        
        # 構造化データ
        structured_data = generate_article_structured_data(article)
        
        return {
            'title': meta_title,
            'description': meta_description,
            'keywords': article.meta_keywords or "",
            'canonical_url': article.canonical_url or "",
            'structured_data': structured_data
        }


class CategoryService:
    """カテゴリ管理サービスクラス"""
    
    @staticmethod
    def setup_challenge_choices(form):
        """カテゴリフォームにチャレンジ選択肢を設定"""
        from models import Challenge
        challenges = db.session.execute(select(Challenge).order_by(Challenge.display_order)).scalars().all()
        form.challenge_id.choices = [(0, 'チャレンジを選択')] + [(c.id, c.name) for c in challenges]
    
    @staticmethod
    def create_category(form_data):
        """カテゴリ作成"""
        try:
            category = Category(
                name=form_data['name'],
                slug=CategoryService.generate_unique_slug(form_data['slug'] or form_data['name']),
                description=form_data.get('description', ''),
                challenge_id=form_data.get('challenge_id') if form_data.get('challenge_id') else None,
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
            category.challenge_id = form_data.get('challenge_id') if form_data.get('challenge_id') else None
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