from flask import Blueprint, render_template, redirect, url_for, request, flash, session, current_app, jsonify
from flask_login import login_required, current_user
from models import db, User, Article, Category, Comment, SiteSetting, UploadedImage, LoginHistory, SEOAnalysis, EmailChangeRequest, article_categories
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
import os
from PIL import Image
import time
import re
import json
from forms import CategoryForm, ArticleForm, WordPressImportForm, GoogleAnalyticsForm

# 新しいサービスクラスをインポート
from article_service import ArticleService, CategoryService, ImageProcessingService, UserService

# 環境変数で管理画面URLをカスタマイズ可能
ADMIN_URL_PREFIX = os.environ.get('ADMIN_URL_PREFIX', 'admin')
admin_bp = Blueprint('admin', __name__, url_prefix=f'/{ADMIN_URL_PREFIX}')

# ユーティリティ関数
def admin_required(f):
    """管理者認証デコレータ"""
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('ログインが必要です', 'info')
            return redirect(url_for('login'))
        if current_user.role != 'admin':
            flash('管理者権限が必要です', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return login_required(decorated_function)

def allowed_file(filename):
    """ファイル拡張子チェック"""
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config.get('ALLOWED_EXTENSIONS', {'png', 'jpg', 'jpeg', 'gif'})

def get_safe_count(query_or_model):
    """安全にカウントを取得（SQLAlchemy 2.0対応）"""
    try:
        if hasattr(query_or_model, '__name__'):
            # モデルクラスの場合
            count = db.session.execute(select(func.count(query_or_model.id))).scalar()
            current_app.logger.info(f"Model {query_or_model.__name__} count: {count}")
            return count
        elif hasattr(query_or_model, '__len__'):
            # リストやInstrumentedListの場合
            count = len(query_or_model)
            current_app.logger.info(f"Collection count: {count}")
            return count
        else:
            # SQLAlchemy 2.0 select statement の場合
            count = db.session.execute(query_or_model).scalar()
            current_app.logger.info(f"Query count: {count}")
            return count
    except SQLAlchemyError as e:
        current_app.logger.error(f"Database error in count query: {e}")
        return 0
    except Exception as e:
        current_app.logger.error(f"Unexpected error in count query: {e}")
        return 0

def generate_slug_from_name(name):
    """名前からスラッグを自動生成"""
    if not name:
        return None
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[\s_-]+', '-', slug)
    return slug.strip('-')

def process_ogp_image(image_file, category_id=None, crop_data=None):
    """OGP画像の処理（アップロード、クロップ、リサイズ）"""
    if not image_file:
        return None
    
    try:
        timestamp = int(time.time())
        file_ext = os.path.splitext(secure_filename(image_file.filename))[1]
        filename = f"category_ogp_{category_id or 'new'}_{timestamp}{file_ext}"
        
        upload_folder = os.path.join(current_app.config['UPLOAD_FOLDER'], 'categories')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        image_path = os.path.join(upload_folder, filename)
        temp_path = os.path.join(upload_folder, f"temp_{filename}")
        
        # 一時保存
        image_file.save(temp_path)
        
        # 画像処理
        with Image.open(temp_path) as img:
            # クロップ処理
            if crop_data:
                # クロップ座標の範囲チェック
                img_width, img_height = img.size
                x = max(0, min(int(crop_data['x']), img_width))
                y = max(0, min(int(crop_data['y']), img_height))
                width = min(int(crop_data['width']), img_width - x)
                height = min(int(crop_data['height']), img_height - y)
                
                crop_box = (x, y, x + width, y + height)
                
                # クロップボックスが有効かチェック
                if width > 0 and height > 0:
                    img = img.crop(crop_box)
                    current_app.logger.info(f"OGP画像クロップ完了: {crop_box}")
            
            # リサイズ（OGP画像の標準サイズ）
            resized_img = img.resize((1200, 630), Image.Resampling.LANCZOS)
            resized_img.save(image_path, format='JPEG', quality=85)
        
        # 一時ファイル削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # 相対パスを返す（static/から見た相対パス）
        relative_path = f"uploads/categories/{filename}"
        current_app.logger.info(f"OGP画像保存完了: {relative_path}")
        
        # UploadedImageテーブルにも保存
        try:
            file_size = os.path.getsize(image_path)
            uploaded_image = UploadedImage(
                filename=filename,
                original_filename=image_file.filename,
                file_path=relative_path,  # パスを統一
                file_size=file_size,
                mime_type='image/jpeg',
                width=1200,  # OGP標準サイズ
                height=630,
                alt_text=f"カテゴリ{category_id or 'new'}のOGP画像",
                caption="",
                description="カテゴリOGP画像",
                uploader_id=current_user.id if current_user.is_authenticated else None,
                is_active=True,
                usage_count=1
            )
            db.session.add(uploaded_image)
            current_app.logger.info(f"UploadedImageテーブルに保存完了: {filename}")
        except Exception as upload_error:
            current_app.logger.error(f"UploadedImage保存エラー: {upload_error}")
            # エラーでもファイル保存は成功しているので処理を続行
        
        return relative_path
    
    except Exception as e:
        current_app.logger.error(f"OGP画像処理エラー: {e}")
        return None

def delete_old_image(image_path):
    """古い画像ファイルを削除"""
    if image_path:
        try:
            full_path = os.path.join(current_app.static_folder, image_path)
            if os.path.exists(full_path):
                os.remove(full_path)
                return True
        except Exception as e:
            current_app.logger.error(f"画像削除エラー: {e}")
    return False

def process_featured_image(image_file, article_id=None):
    """アイキャッチ画像の処理（アップロード、リサイズ）"""
    if not image_file or not image_file.filename:
        current_app.logger.info("No image file provided")
        return None
    
    try:
        current_app.logger.info(f"Processing image: {image_file.filename}")
        
        timestamp = int(time.time())
        file_ext = os.path.splitext(secure_filename(image_file.filename))[1]
        if not file_ext:
            file_ext = '.jpg'
        
        filename = f"featured_{article_id or 'new'}_{timestamp}{file_ext}"
        
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'articles')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
            current_app.logger.info(f"Created upload directory: {upload_folder}")
        
        image_path = os.path.join(upload_folder, filename)
        temp_path = os.path.join(upload_folder, f"temp_{filename}")
        
        current_app.logger.info(f"Saving image to: {image_path}")
        
        # 一時保存
        image_file.save(temp_path)
        current_app.logger.info(f"Saved temp file: {temp_path}")
        
        # 画像処理
        with Image.open(temp_path) as img:
            # RGB変換（JPEG保存のため）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # アイキャッチ画像のリサイズ（16:9比率、最大1200x675）
            resized_img = img.resize((1200, 675), Image.Resampling.LANCZOS)
            resized_img.save(image_path, format='JPEG', quality=85)
            current_app.logger.info(f"Processed and saved image: {image_path}")
        
        # 一時ファイル削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            current_app.logger.info(f"Removed temp file: {temp_path}")
        
        # 相対パスを返す
        relative_path = os.path.relpath(image_path, current_app.static_folder)
        current_app.logger.info(f"Returning relative path: {relative_path}")
        return relative_path
    
    except Exception as e:
        current_app.logger.error(f"アイキャッチ画像処理エラー: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        # 一時ファイルをクリーンアップ
        if 'temp_path' in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
                current_app.logger.info(f"Cleaned up temp file: {temp_path}")
            except OSError as e:
                current_app.logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
            except Exception as e:
                current_app.logger.error(f"Unexpected error cleaning temp file {temp_path}: {e}")
        return None

def process_featured_image_with_crop(image_file, article_id, crop_data=None):
    """アイキャッチ画像の処理（クロップ対応版）"""
    if not image_file or not image_file.filename:
        current_app.logger.info("No image file provided")
        return None
    
    try:
        current_app.logger.info(f"Processing featured image with crop: {image_file.filename}")
        
        timestamp = int(time.time())
        file_ext = os.path.splitext(secure_filename(image_file.filename))[1]
        if not file_ext:
            file_ext = '.jpg'
        
        filename = f"featured_cropped_{article_id or 'new'}_{timestamp}{file_ext}"
        
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'articles')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
            current_app.logger.info(f"Created upload directory: {upload_folder}")
        
        image_path = os.path.join(upload_folder, filename)
        temp_path = os.path.join(upload_folder, f"temp_{filename}")
        
        current_app.logger.info(f"Saving image to: {image_path}")
        
        # 一時保存
        image_file.save(temp_path)
        current_app.logger.info(f"Saved temp file: {temp_path}")
        
        # 画像処理
        with Image.open(temp_path) as img:
            # RGB変換（JPEG保存のため）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # クロップ処理（データがある場合）
            if crop_data:
                current_app.logger.info(f"Applying crop: {crop_data}")
                cropped_img = img.crop((
                    crop_data['x'],
                    crop_data['y'],
                    crop_data['x'] + crop_data['width'],
                    crop_data['y'] + crop_data['height']
                ))
                # 16:9比率で800x450にリサイズ
                resized_img = cropped_img.resize((800, 450), Image.Resampling.LANCZOS)
            else:
                # クロップなしの場合は16:9比率で800x450にリサイズ
                resized_img = img.resize((800, 450), Image.Resampling.LANCZOS)
            
            resized_img.save(image_path, format='JPEG', quality=85)
            current_app.logger.info(f"Processed and saved image: {image_path}")
        
        # 一時ファイル削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
            current_app.logger.info(f"Removed temp file: {temp_path}")
        
        # 相対パスを返す
        relative_path = os.path.relpath(image_path, current_app.static_folder)
        current_app.logger.info(f"Returning relative path: {relative_path}")
        return relative_path.replace('\\', '/')
        
    except Exception as e:
        current_app.logger.error(f"Featured image with crop processing error: {e}")
        return None

def process_cropped_image(cropped_data, article_id=None):
    """トリミング後の画像データの処理"""
    import base64
    import io
    
    try:
        current_app.logger.info(f"Processing cropped image data for article ID: {article_id}")
        
        # Data URLからbase64データを抽出
        if cropped_data.startswith('data:image'):
            header, base64_data = cropped_data.split(',', 1)
        else:
            base64_data = cropped_data
        
        # base64デコード
        image_data = base64.b64decode(base64_data)
        
        # PILで画像を開く
        img = Image.open(io.BytesIO(image_data))
        
        # RGB変換（JPEG保存のため）
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        
        # ファイル名生成
        timestamp = int(time.time())
        filename = f"featured_cropped_{article_id or 'new'}_{timestamp}.jpg"
        
        # 保存先ディレクトリ
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'articles')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
            current_app.logger.info(f"Created upload directory: {upload_folder}")
        
        image_path = os.path.join(upload_folder, filename)
        
        # 画像保存
        img.save(image_path, format='JPEG', quality=85)
        current_app.logger.info(f"Cropped image saved: {image_path}")
        
        # 相対パスを返す
        relative_path = os.path.relpath(image_path, current_app.static_folder)
        current_app.logger.info(f"Returning relative path: {relative_path}")
        return relative_path
        
    except Exception as e:
        current_app.logger.error(f"Cropped image processing error: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def process_uploaded_image(image_file, alt_text="", caption="", description=""):
    """記事本文用の画像アップロード処理"""
    import mimetypes
    
    if not image_file or not image_file.filename:
        return None, "画像ファイルが選択されていません。"
    
    try:
        # ファイル名の安全化
        original_filename = secure_filename(image_file.filename)
        if not original_filename:
            return None, "無効なファイル名です。"
        
        # 拡張子チェック
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        file_ext = os.path.splitext(original_filename)[1].lower()
        if file_ext not in allowed_extensions:
            return None, f"サポートされていないファイル形式です。対応形式: {', '.join(allowed_extensions)}"
        
        # MIMEタイプ検証
        mime_type, _ = mimetypes.guess_type(original_filename)
        if not mime_type or not mime_type.startswith('image/'):
            return None, "画像ファイルではありません。"
        
        # ファイルサイズチェック（10MB制限 - トリミング画像対応）
        image_file.seek(0, 2)  # ファイル末尾に移動
        file_size = image_file.tell()
        image_file.seek(0)  # ファイル先頭に戻る
        
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            return None, f"ファイルサイズが大きすぎます（最大{max_size // (1024*1024)}MB）。"
        
        # ユニークなファイル名生成
        timestamp = int(time.time())
        filename = f"content_{current_user.id}_{timestamp}{file_ext}"
        
        # 保存先ディレクトリ
        upload_folder = os.path.join(current_app.config.get('UPLOAD_FOLDER', 'static/uploads'), 'content')
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder, exist_ok=True)
        
        # 一時保存
        temp_path = os.path.join(upload_folder, f"temp_{filename}")
        image_file.save(temp_path)
        
        # 画像処理とメタデータ取得
        final_path = os.path.join(upload_folder, filename)
        width, height = None, None
        
        with Image.open(temp_path) as img:
            width, height = img.size
            
            # RGB変換（JPEG保存のため）
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # 大きすぎる画像はリサイズ（最大2000px）
            max_dimension = 2000
            if max(width, height) > max_dimension:
                ratio = max_dimension / max(width, height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                width, height = new_width, new_height
            
            # 最終保存
            img.save(final_path, format='JPEG' if file_ext in ['.jpg', '.jpeg'] else 'PNG', 
                    quality=85 if file_ext in ['.jpg', '.jpeg'] else None)
        
        # 一時ファイル削除
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        # データベースに保存
        relative_path = os.path.relpath(final_path, current_app.static_folder)
        
        uploaded_image = UploadedImage(
            filename=filename,
            original_filename=original_filename,
            file_path=relative_path,
            file_size=os.path.getsize(final_path),
            mime_type=mime_type,
            width=width,
            height=height,
            alt_text=alt_text,
            caption=caption,
            description=description,
            uploader_id=current_user.id
        )
        
        db.session.add(uploaded_image)
        db.session.commit()
        
        current_app.logger.info(f"Image uploaded successfully: {filename}")
        return uploaded_image, None
        
    except Exception as e:
        current_app.logger.error(f"Image upload error: {e}")
        import traceback
        current_app.logger.error(f"Traceback: {traceback.format_exc()}")
        
        # クリーンアップ
        for cleanup_path in [locals().get('temp_path'), locals().get('final_path')]:
            if cleanup_path and os.path.exists(cleanup_path):
                try:
                    os.remove(cleanup_path)
                except:
                    pass
        
        return None, "画像のアップロードに失敗しました。"

# デバッグ用ルート（開発環境でのみ登録）
def register_debug_routes():
    """開発環境でのみデバッグルートを登録"""
    import os
    
    if os.environ.get('FLASK_DEBUG', 'false').lower() == 'true':
        @admin_bp.route('/debug/simple')
        def debug_simple():
            """簡易データベーステスト"""
            try:
                user_count = db.session.execute(select(func.count(User.id))).scalar()
                article_count = db.session.execute(select(func.count(Article.id))).scalar()
                category_count = db.session.execute(select(func.count(Category.id))).scalar()
                
                return f"""<h2>DB Test</h2>
                <p>Users: {user_count}</p>
                <p>Articles: {article_count}</p>
                <p>Categories: {category_count}</p>"""
            except Exception as e:
                return f"<h2>Error</h2><pre>{str(e)}</pre>"
        
        @admin_bp.route('/debug/stats')
        @admin_required
        def debug_stats():
            """統計データデバッグ"""
            try:
                debug_info = {
                    'user_count': db.session.execute(select(func.count(User.id))).scalar(),
                    'article_count': db.session.execute(select(func.count(Article.id))).scalar(),
                    'category_count': db.session.execute(select(func.count(Category.id))).scalar()
                }
                import json
                return f"<pre>{json.dumps(debug_info, indent=2, ensure_ascii=False)}</pre>"
            except Exception as e:
                return f"<pre>Debug error: {str(e)}</pre>"

# ダッシュボード
@admin_bp.route('/')
@admin_required
def dashboard():
    """管理者ダッシュボード（シンプル版）"""
    # 基本的な統計のみ
    stats = {
        'user_count': db.session.execute(select(func.count(User.id))).scalar(),
        'article_count': db.session.execute(select(func.count(Article.id))).scalar(),
        'category_count': db.session.execute(select(func.count(Category.id))).scalar(),
        'comment_count': db.session.execute(select(func.count(Comment.id))).scalar() if hasattr(Comment, 'id') else 0
    }
    
    # 今月の統計を計算
    import calendar
    
    current_date = datetime.now()
    current_year = current_date.year
    current_month = current_date.month
    
    # 今月の開始日と終了日を計算
    first_day = datetime(current_year, current_month, 1)
    last_day = datetime(current_year, current_month, calendar.monthrange(current_year, current_month)[1], 23, 59, 59)
    
    # 今月作成された記事数
    articles_this_month = db.session.execute(
        select(func.count(Article.id)).where(
            Article.created_at >= first_day,
            Article.created_at <= last_day
        )
    ).scalar()
    
    # 今月作成されたユーザー数（created_atフィールドがある場合）
    users_this_month = 0
    if hasattr(User, 'created_at'):
        users_this_month = db.session.execute(
            select(func.count(User.id)).where(
                User.created_at >= first_day,
                User.created_at <= last_day
            )
        ).scalar()
    
    current_app.logger.info(f"Monthly stats calculation: articles_this_month={articles_this_month}, period={first_day} to {last_day}")
    
    # 今月のコメント数
    comments_this_month = 0
    if hasattr(Comment, 'created_at'):
        comments_this_month = db.session.execute(
            select(func.count(Comment.id)).where(
                Comment.created_at >= first_day,
                Comment.created_at <= last_day
            )
        ).scalar()
    
    monthly_stats = {
        'articles_this_month': articles_this_month,
        'users_this_month': users_this_month,
        'comments_this_month': comments_this_month
    }
    
    # 最近の記事
    recent_articles = db.session.execute(select(Article).order_by(Article.created_at.desc()).limit(5)).scalars().all()
    
    # 承認待ちコメント数
    pending_comments = 0
    if hasattr(Comment, 'is_approved'):
        pending_comments = db.session.execute(
            select(func.count(Comment.id)).where(
                Comment.is_approved.is_(False)
            )
        ).scalar()
    
    recent_data = {
        'recent_articles': recent_articles,
        'pending_comments': pending_comments
    }
    
    return render_template('admin/dashboard.html', 
                         stats=stats,
                         monthly_stats=monthly_stats,
                         recent_data=recent_data,
                         chart_data=[])

# ユーザー管理
@admin_bp.route('/users/')
@admin_required
def users():
    """ユーザー一覧（検索・フィルタリング・ページネーション対応）"""
    try:
        # パラメータ取得
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        role_filter = request.args.get('role', '', type=str)
        per_page = 10  # 1ページあたりのユーザー数
        
        # ベースクエリ
        query = select(User).order_by(User.created_at.desc())
        
        # 検索フィルタ
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                db.or_(
                    User.name.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.handle_name.ilike(search_pattern)
                )
            )
        
        # 役割フィルタ
        if role_filter:
            query = query.where(User.role == role_filter)
        
        # ページネーション実行
        pagination = db.paginate(
            query,
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        users = pagination.items
        
        # 統計情報の取得
        total_users = db.session.execute(select(func.count(User.id))).scalar()
        admin_count = db.session.execute(select(func.count(User.id)).where(User.role == 'admin')).scalar()
        totp_enabled_count = db.session.execute(select(func.count(User.id)).where(User.totp_enabled == True)).scalar()
        
        # 今月の新規ユーザー数
        current_month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_users_this_month = db.session.execute(
            select(func.count(User.id)).where(User.created_at >= current_month_start)
        ).scalar()
        
        return render_template('admin/users.html', 
                               users=users,
                               pagination=pagination,
                               search=search,
                               role_filter=role_filter,
                               total_users=total_users,
                               admin_count=admin_count,
                               totp_enabled_count=totp_enabled_count,
                               new_users_this_month=new_users_this_month)
    
    except Exception as e:
        current_app.logger.error(f"Users page error: {e}")
        flash('ユーザーデータの取得中にエラーが発生しました。', 'danger')
        return render_template('admin/users.html', 
                               users=[], 
                               pagination=None,
                               search='',
                               role_filter='',
                               total_users=0,
                               admin_count=0,
                               totp_enabled_count=0,
                               new_users_this_month=0)

@admin_bp.route('/user/create/', methods=['GET', 'POST'])
@admin_required
def create_user():
    """ユーザー作成"""
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        role = request.form.get('role', 'author')
        
        # バリデーション
        if not all([email, name, password]):
            flash('必須項目を入力してください。', 'danger')
            return render_template('admin/create_user.html')
        
        if len(password) < 8:
            flash('パスワードは8文字以上である必要があります。', 'danger')
            return render_template('admin/create_user.html')
        
        if db.session.execute(select(User).where(User.email == email)).scalar_one_or_none():
            flash('このメールアドレスは既に使用されています。', 'danger')
            return render_template('admin/create_user.html')
        
        try:
            new_user = User(
                email=email,
                name=name,
                password_hash=generate_password_hash(password),
                role=role,
                handle_name=request.form.get('handle_name', ''),
                introduction=request.form.get('introduction', ''),
                created_at=datetime.utcnow()
            )
            db.session.add(new_user)
            db.session.commit()
            flash(f'ユーザー「{name}」を作成しました。', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User creation error: {e}")
            flash('ユーザーの作成に失敗しました。', 'danger')
    
    return render_template('admin/create_user.html')

@admin_bp.route('/user/edit/<int:user_id>/', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """ユーザー編集"""
    user = db.get_or_404(User, user_id)
    
    if request.method == 'POST':
        # 自分自身の管理者権限削除チェック（自分以外でroleフィールドが送信された場合のみ）
        submitted_role = request.form.get('role')
        if user.id != current_user.id and submitted_role and user.role == 'admin' and submitted_role != 'admin':
            # 他の管理者の権限を削除しようとしている場合のチェック
            admin_count = db.session.execute(select(func.count(User.id)).where(User.role == 'admin')).scalar()
            if admin_count <= 1:
                flash('最後の管理者の権限は削除できません。', 'danger')
                return render_template('admin/edit_user.html', user=user)
        
        try:
            # パスワード確認チェック
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            if new_password and new_password != confirm_password:
                flash('パスワードが一致しません。', 'danger')
                return render_template('admin/edit_user.html', user=user)
            
            # 基本データ更新
            user.name = request.form.get('name', user.name)
            user.handle_name = request.form.get('handle_name', user.handle_name or '')
            # 権限更新（自分自身の場合はhiddenフィールドで'admin'が送信される）
            user.role = request.form.get('role', user.role)
            
            # プロフィール情報更新
            user.introduction = request.form.get('introduction', user.introduction or '')
            user.birthplace = request.form.get('birthplace', user.birthplace or '')
            
            # 誕生日の処理
            birthday_str = request.form.get('birthday')
            if birthday_str:
                from datetime import datetime
                user.birthday = datetime.strptime(birthday_str, '%Y-%m-%d').date()
            else:
                user.birthday = None
            
            # SNSアカウント更新
            user.sns_x = request.form.get('sns_x', user.sns_x or '')
            user.sns_facebook = request.form.get('sns_facebook', user.sns_facebook or '')
            user.sns_instagram = request.form.get('sns_instagram', user.sns_instagram or '')
            user.sns_threads = request.form.get('sns_threads', user.sns_threads or '')
            user.sns_youtube = request.form.get('sns_youtube', user.sns_youtube or '')
            
            # パスワード変更
            if new_password:
                if len(new_password) < 8:
                    flash('パスワードは8文字以上である必要があります。', 'danger')
                    return render_template('admin/edit_user.html', user=user)
                user.password_hash = generate_password_hash(new_password)
            
            # 通知設定
            user.notify_on_publish = 'notify_on_publish' in request.form
            user.notify_on_comment = 'notify_on_comment' in request.form
            
            db.session.commit()
            flash('ユーザー情報を更新しました。', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"User update error: {e}")
            flash('ユーザー情報の更新に失敗しました。', 'danger')
    
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/user/delete/<int:user_id>/', methods=['POST'])
@admin_required
def delete_user(user_id):
    """ユーザー削除"""
    user = db.get_or_404(User, user_id)
    
    # 削除制限チェック
    if user.id == current_user.id:
        flash('自分自身を削除することはできません。', 'danger')
        return redirect(url_for('admin.users'))
    
    admin_count = db.session.execute(select(func.count(User.id)).where(User.role == 'admin')).scalar()
    if user.role == 'admin' and admin_count <= 1:
        flash('最後の管理者を削除することはできません。', 'danger')
        return redirect(url_for('admin.users'))
    
    try:
        # 関連記事の処理
        user_articles = db.session.execute(select(Article).where(Article.author_id == user.id)).scalars().all()
        if user_articles:
            action = request.form.get('article_action', 'keep')
            if action == 'delete':
                for article in user_articles:
                    db.session.delete(article)
            elif action == 'transfer':
                transfer_to_id = request.form.get('transfer_to_user')
                if transfer_to_id:
                    for article in user_articles:
                        article.author_id = int(transfer_to_id)
        
        db.session.delete(user)
        db.session.commit()
        flash(f'ユーザー「{user.name}」を削除しました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"User deletion error: {e}")
        flash('ユーザーの削除に失敗しました。', 'danger')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/user/detail/<int:user_id>/')
@admin_required
def user_detail(user_id):
    """ユーザー詳細情報"""
    user = db.get_or_404(User, user_id)
    
    try:
        # ユーザー統計情報
        total_articles = db.session.execute(select(func.count(Article.id)).where(Article.author_id == user.id)).scalar()
        published_articles = db.session.execute(select(func.count(Article.id)).where(Article.author_id == user.id, Article.is_published == True)).scalar()
        draft_articles = total_articles - published_articles
        
        # 最近の記事（5件）
        recent_articles = db.session.execute(
            select(Article)
            .where(Article.author_id == user.id)
            .order_by(Article.created_at.desc())
            .limit(5)
        ).scalars().all()
        
        # ログイン履歴（10件）
        login_history = db.session.execute(
            select(LoginHistory)
            .where(LoginHistory.user_id == user.id)
            .order_by(LoginHistory.login_at.desc())
            .limit(10)
        ).scalars().all()
        
        # 最近のログイン統計
        successful_logins = db.session.execute(
            select(func.count(LoginHistory.id))
            .where(LoginHistory.user_id == user.id, LoginHistory.success == True)
        ).scalar()
        
        failed_logins = db.session.execute(
            select(func.count(LoginHistory.id))
            .where(LoginHistory.user_id == user.id, LoginHistory.success == False)
        ).scalar()
        
        return render_template('admin/user_detail.html',
                               user=user,
                               total_articles=total_articles,
                               published_articles=published_articles,
                               draft_articles=draft_articles,
                               recent_articles=recent_articles,
                               login_history=login_history,
                               successful_logins=successful_logins,
                               failed_logins=failed_logins)
    
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        current_app.logger.error(f"User detail error: {e}\nTraceback: {error_traceback}")
        flash(f'ユーザー詳細情報の取得中にエラーが発生しました: {str(e)}', 'danger')
        return redirect(url_for('admin.users'))

@admin_bp.route('/user/<int:user_id>/reset-2fa/', methods=['POST'])
@admin_required
def reset_user_2fa(user_id):
    """ユーザーの2FA設定をリセット"""
    user = db.get_or_404(User, user_id)
    
    try:
        user.totp_enabled = False
        user.totp_secret = None
        db.session.commit()
        flash(f'ユーザー「{user.name}」の2FA設定をリセットしました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"2FA reset error: {e}")
        flash('2FA設定のリセットに失敗しました。', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

@admin_bp.route('/user/<int:user_id>/reset-password/', methods=['POST'])
@admin_required
def admin_reset_user_password(user_id):
    """管理者によるユーザーパスワードリセット"""
    user = db.get_or_404(User, user_id)
    new_password = request.form.get('new_password')
    
    if not new_password or len(new_password) < 8:
        flash('パスワードは8文字以上で入力してください。', 'danger')
        return redirect(url_for('admin.user_detail', user_id=user_id))
    
    try:
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        db.session.commit()
        flash(f'ユーザー「{user.name}」のパスワードをリセットしました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Password reset error: {e}")
        flash('パスワードのリセットに失敗しました。', 'danger')
    
    return redirect(url_for('admin.user_detail', user_id=user_id))

# 記事管理
@admin_bp.route('/articles/')
@admin_required
def articles():
    """記事一覧（シンプル版）"""
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # ページネーション（eager loading で関連データも取得）
    from sqlalchemy.orm import selectinload
    articles_pagination = db.paginate(
        select(Article)
        .options(
            selectinload(Article.categories)
        )
        .order_by(Article.created_at.desc()),
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # 基本統計
    total_articles = db.session.execute(select(func.count(Article.id))).scalar()
    published_articles = db.session.execute(select(func.count(Article.id)).where(Article.is_published.is_(True))).scalar()
    draft_articles = db.session.execute(select(func.count(Article.id)).where(Article.is_published.is_(False))).scalar()
    
    # 今月の記事数
    from datetime import datetime
    current_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    this_month_articles = db.session.execute(select(func.count(Article.id)).where(Article.created_at >= current_month)).scalar()
    
    return render_template('admin/articles.html', 
                         articles_list=articles_pagination,
                         total_articles=total_articles,
                         published_articles=published_articles,
                         draft_articles=draft_articles,
                         this_month_articles=this_month_articles)

@admin_bp.route('/article/create/', methods=['GET', 'POST'])
@admin_required
def create_article():
    """記事作成（統一版）"""
    form = ArticleForm()
    
    # カテゴリ選択肢を設定
    ArticleService.setup_category_choices(form)
    
    if form.validate_on_submit():
        # バリデーション
        validation_errors = ArticleService.validate_article_data(form)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
            return render_template('admin/article_form.html', 
                                 form=form, 
                                 **ArticleService.get_article_context())
        
        # フォームデータ準備
        form_data = {
            'title': form.title.data,
            'slug': form.slug.data,
            'summary': form.summary.data,
            'body': form.body.data,
            'is_published': form.is_published.data,
            'allow_comments': form.allow_comments.data,
            'meta_title': form.meta_title.data,
            'meta_description': form.meta_description.data,
            'meta_keywords': form.meta_keywords.data,
            'canonical_url': form.canonical_url.data,
            'category_id': form.category_id.data,
            'cropped_image_data': request.form.get('cropped_image_data'),
            'featured_image': request.files.get('featured_image'),
            'featured_crop_x': request.form.get('featured_crop_x'),
            'featured_crop_y': request.form.get('featured_crop_y'),
            'featured_crop_width': request.form.get('featured_crop_width'),
            'featured_crop_height': request.form.get('featured_crop_height')
        }
        
        # 記事作成
        article, error = ArticleService.create_article(form_data, current_user.id)
        
        if article:
            flash('記事が作成されました。', 'success')
            return redirect(url_for('admin.articles'))
        else:
            flash(f'記事の作成に失敗しました: {error}', 'danger')
    
    # フォーム表示
    return render_template('admin/article_form.html', 
                         form=form, 
                         **ArticleService.get_article_context())

@admin_bp.route('/article/edit/<int:article_id>/', methods=['GET', 'POST'])
@admin_required
def edit_article(article_id):
    """記事編集（統一版）"""
    article = db.get_or_404(Article, article_id)
    
    
    form = ArticleForm(obj=article)
    
    # カテゴリ選択肢を設定
    ArticleService.setup_category_choices(form)
    
    # 現在のカテゴリを設定
    current_category = article.categories[0] if article.categories else None
    if current_category:
        form.category_id.data = current_category.id
    
    if form.validate_on_submit():
        # バリデーション
        validation_errors = ArticleService.validate_article_data(form, article_id)
        if validation_errors:
            for error in validation_errors:
                flash(error, 'danger')
        else:
            # フォームデータ準備
            form_data = {
                'title': form.title.data,
                'slug': form.slug.data,
                'summary': form.summary.data,
                'body': form.body.data,
                'is_published': form.is_published.data,
                'allow_comments': form.allow_comments.data,
                'meta_title': form.meta_title.data,
                'meta_description': form.meta_description.data,
                'meta_keywords': form.meta_keywords.data,
                'canonical_url': form.canonical_url.data,
                'category_id': form.category_id.data,
                'cropped_image_data': request.form.get('cropped_image_data'),
                'featured_image': request.files.get('featured_image'),
                'featured_crop_x': request.form.get('featured_crop_x'),
                'featured_crop_y': request.form.get('featured_crop_y'),
                'featured_crop_width': request.form.get('featured_crop_width'),
                'featured_crop_height': request.form.get('featured_crop_height'),
                'remove_featured_image': request.form.get('remove_featured_image') == 'true'
            }
            
            # 記事更新
            updated_article, error = ArticleService.update_article(article, form_data)
            
            if updated_article:
                flash('記事が更新されました。', 'success')
                return redirect(url_for('admin.articles'))
            else:
                flash(f'記事の更新に失敗しました: {error}', 'danger')
    
    # フォーム表示
    return render_template('admin/article_form.html', 
                         form=form, 
                         **ArticleService.get_article_context(article))


@admin_bp.route('/article/toggle_status/<int:article_id>/', methods=['POST'])
@admin_required
def toggle_article_status(article_id):
    """記事ステータスの切り替え"""
    from flask import jsonify
    from flask_wtf.csrf import validate_csrf
    from werkzeug.exceptions import BadRequest
    
    article = db.get_or_404(Article, article_id)
    
    try:
        # フォームデータから状態を取得
        new_status = request.form.get('is_published', 'false').lower() == 'true'
        was_published = article.is_published
        
        # ステータス更新
        article.is_published = new_status
        if new_status and not was_published:
            article.published_at = datetime.utcnow()
        
        db.session.commit()
        
        status_text = '公開' if new_status else '下書き'
        current_app.logger.info(f'Article {article.id} status changed to {status_text}')
        flash(f'記事ステータスを{status_text}に変更しました', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Status toggle error: {e}")
        flash(f'ステータス変更に失敗しました: {str(e)}', 'danger')
    
    return redirect(url_for('admin.articles'))

@admin_bp.route('/article/delete/<int:article_id>/', methods=['POST'])
@admin_required
def delete_article(article_id):
    """記事削除"""
    article = db.get_or_404(Article, article_id)
    article_title = article.title  # 削除前にタイトルを保存
    
    try:
        # SQLAlchemyのCASCADE設定により関連データも自動削除される
        db.session.delete(article)
        db.session.commit()
        flash(f'記事「{article_title}」を削除しました。', 'success')
        current_app.logger.info(f"Article deleted successfully: {article_id}")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Article deletion error: {e}")
        print(f"Article deletion error: {e}")  # デバッグ用
        flash('記事の削除に失敗しました。', 'danger')
    
    return redirect(url_for('admin.articles'))

# カテゴリ管理
@admin_bp.route('/categories/')
@admin_required
def categories():
    """カテゴリ一覧"""
    page = request.args.get('page', 1, type=int)
    from sqlalchemy.orm import selectinload
    categories_list = db.paginate(
        select(Category).options(selectinload(Category.articles)).order_by(Category.name),
        page=page, per_page=10, error_out=False
    )
    
    # 統計情報を計算
    total_categories = db.session.execute(select(func.count(Category.id))).scalar()
    
    # 現在ページのカテゴリに関連する記事数
    current_page_articles = 0
    for category in categories_list.items:
        current_page_articles += len(category.articles) if category.articles else 0
    
    # 全カテゴリの記事数（最適化）
    total_articles_in_categories = db.session.execute(
        select(func.count(article_categories.c.article_id))
    ).scalar()
    
    # 記事が割り当てられていないカテゴリ数（最適化）
    empty_categories = db.session.execute(
        select(func.count(Category.id)).where(
            ~Category.id.in_(select(article_categories.c.category_id))
        )
    ).scalar()
    
    stats = {
        'total_categories': total_categories,
        'current_page_articles': current_page_articles,
        'total_articles_in_categories': total_articles_in_categories,
        'empty_categories': empty_categories
    }
    
    return render_template('admin/categories.html', 
                         categories_list=categories_list,
                         stats=stats)

@admin_bp.route('/category/create/', methods=['GET', 'POST'])
@admin_required
def create_category():
    """カテゴリ作成"""
    form = CategoryForm()
    
    if form.validate_on_submit():
        # スラッグ自動生成
        slug = form.slug.data or generate_slug_from_name(form.name.data)
        if not slug:
            flash('有効なスラッグを生成できませんでした。', 'danger')
            return render_template('admin/create_category.html', form=form)
        
        # 重複チェック
        if db.session.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none():
            flash('そのスラッグは既に使用されています。', 'danger')
            return render_template('admin/create_category.html', form=form)
        
        if db.session.execute(select(Category).where(Category.name == form.name.data)).scalar_one_or_none():
            flash('そのカテゴリ名は既に使用されています。', 'danger')
            return render_template('admin/create_category.html', form=form)
        
        try:
            # カテゴリ作成
            new_category = Category(
                name=form.name.data,
                slug=slug,
                description=form.description.data,
                created_at=datetime.utcnow()
            )
            
            db.session.add(new_category)
            db.session.flush()  # IDを取得するためにflushを実行
            
            # OGP画像の処理
            if form.ogp_image.data:
                try:
                    # クロップデータの取得
                    crop_data = None
                    if all([form.ogp_crop_x.data, form.ogp_crop_y.data, form.ogp_crop_width.data, form.ogp_crop_height.data]):
                        crop_data = {
                            'x': float(form.ogp_crop_x.data),
                            'y': float(form.ogp_crop_y.data),
                            'width': float(form.ogp_crop_width.data),
                            'height': float(form.ogp_crop_height.data)
                        }
                        current_app.logger.info(f"OGP crop data for new category: {crop_data}")
                    
                    ogp_image_path = process_ogp_image(form.ogp_image.data, new_category.id, crop_data)
                    if ogp_image_path:
                        new_category.ogp_image = ogp_image_path
                        current_app.logger.info(f"OGP image saved successfully: {ogp_image_path}")
                    else:
                        flash('OGP画像の処理中にエラーが発生しました。', 'warning')
                        
                except Exception as img_error:
                    current_app.logger.error(f"OGP image processing error for new category: {img_error}")
                    flash('OGP画像の処理中にエラーが発生しました。', 'warning')
                    # 画像処理エラーでもカテゴリ作成は続行
            
            db.session.commit()
            flash('カテゴリが作成されました。', 'success')
            return redirect(url_for('admin.categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Category creation error: {e}")
            flash(f'カテゴリの作成中にエラーが発生しました: {str(e)}', 'danger')
    
    return render_template('admin/create_category.html', form=form)

@admin_bp.route('/category/edit/<int:category_id>/', methods=['GET', 'POST'])
@admin_required
def edit_category(category_id):
    """カテゴリ編集"""
    category = db.get_or_404(Category, category_id)
    form = CategoryForm(obj=category)
    
    if form.validate_on_submit():
        
        try:
            # データ更新
            category.name = form.name.data
            category.slug = form.slug.data
            category.description = form.description.data
            
            # カテゴリ画像削除処理
            if request.form.get('remove_category_image') == 'true':
                category.ogp_image = None
                current_app.logger.info(f"Category {category.id} OGP image removed")
            
            # OGP画像の処理
            elif form.ogp_image.data:
                try:
                    # 古い画像を削除
                    if category.ogp_image:
                        old_image_path = os.path.join(current_app.static_folder, category.ogp_image)
                        delete_old_image(old_image_path)
                        current_app.logger.info(f"Old OGP image deleted: {old_image_path}")
                    
                    # クロップデータの取得
                    crop_data = None
                    if all([form.ogp_crop_x.data, form.ogp_crop_y.data, form.ogp_crop_width.data, form.ogp_crop_height.data]):
                        crop_data = {
                            'x': float(form.ogp_crop_x.data),
                            'y': float(form.ogp_crop_y.data),
                            'width': float(form.ogp_crop_width.data),
                            'height': float(form.ogp_crop_height.data)
                        }
                        current_app.logger.info(f"OGP crop data: {crop_data}")
                    
                    # 新しい画像を処理
                    ogp_image_path = process_ogp_image(form.ogp_image.data, category.id, crop_data)
                    if ogp_image_path:
                        category.ogp_image = ogp_image_path
                        current_app.logger.info(f"OGP image updated successfully: {ogp_image_path}")
                    else:
                        flash('OGP画像の処理中にエラーが発生しました。', 'warning')
                        
                except Exception as img_error:
                    current_app.logger.error(f"OGP image processing error: {img_error}")
                    flash('OGP画像の処理中にエラーが発生しました。', 'warning')
                    # 画像処理エラーでもカテゴリ情報は保存を続行
            
            db.session.commit()
            flash('カテゴリが正常に更新されました。', 'success')
            return redirect(url_for('admin.categories'))
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Category update error: {e}")
            flash('カテゴリの更新中にエラーが発生しました。', 'danger')
    else:
        if request.method == 'POST':
            current_app.logger.warning(f"フォームバリデーション失敗: {form.errors}")
            current_app.logger.info(f"受信データ: {dict(request.form)}")
            current_app.logger.info(f"ファイルデータ: {dict(request.files)}")
    
    return render_template('admin/edit_category.html', form=form, category=category)

@admin_bp.route('/category/delete/<int:category_id>/', methods=['POST'])
@admin_required
def delete_category(category_id):
    """カテゴリ削除"""
    from sqlalchemy.orm import selectinload
    category = db.session.execute(
        select(Category).options(selectinload(Category.articles)).where(Category.id == category_id)
    ).scalar_one_or_none()
    
    if not category:
        flash('カテゴリが見つかりません。', 'danger')
        return redirect(url_for('admin.categories'))
    
    try:
        # 関連記事のカテゴリ関連付けを削除（eager loading済み）
        for article in category.articles:
            article.categories.remove(category)
        
        db.session.delete(category)
        db.session.commit()
        flash(f'カテゴリ「{category.name}」を削除しました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Category deletion error: {e}")
        flash('カテゴリの削除中にエラーが発生しました。', 'danger')
    
    return redirect(url_for('admin.categories'))

@admin_bp.route('/categories/bulk-delete', methods=['POST'])
@admin_required
def bulk_delete_categories():
    """カテゴリ一括削除"""
    category_ids = request.form.getlist('category_ids')
    
    if not category_ids:
        flash('削除するカテゴリが選択されていません。', 'warning')
        return redirect(url_for('admin.categories'))
    
    try:
        deleted_count = 0
        from sqlalchemy.orm import selectinload
        for category_id in category_ids:
            category = db.session.execute(
                select(Category).options(selectinload(Category.articles)).where(Category.id == category_id)
            ).scalar_one_or_none()
            if category:
                # 関連記事のカテゴリ関連付けを削除（eager loading済み）
                for article in category.articles:
                    article.categories.remove(category)
                
                db.session.delete(category)
                deleted_count += 1
        
        db.session.commit()
        flash(f'{deleted_count}個のカテゴリを削除しました。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk category deletion error: {e}")
        flash('カテゴリの削除中にエラーが発生しました。', 'danger')
    
    return redirect(url_for('admin.categories'))

# サイト設定
# Removed duplicate site_settings function

# コメント管理（admin.py の最後に追加）
@admin_bp.route('/comments/')
@admin_required
def comments():
    """コメント管理"""
    try:
        page = request.args.get('page', 1, type=int)
        status_filter = request.args.get('status', 'all')
        
        # Commentモデルが存在するかチェック
        if not hasattr(Comment, 'query'):
            flash('コメント機能は実装されていません。', 'info')
            return render_template('admin/comments.html',
                                 comments_list=None,
                                 status_filter=status_filter,
                                 total=0,
                                 approved=0,
                                 pending=0)
        
        query_stmt = select(Comment)
        if status_filter == 'approved':
            if hasattr(Comment, 'is_approved'):
                query_stmt = query_stmt.where(Comment.is_approved.is_(True))
        elif status_filter == 'pending':
            if hasattr(Comment, 'is_approved'):
                query_stmt = query_stmt.where(Comment.is_approved.is_(False))
        
        comments_pagination = db.paginate(
            query_stmt.order_by(Comment.created_at.desc()),
            page=page, per_page=20, error_out=False
        )
        
        # 統計
        stats = {
            'total': get_safe_count(Comment),
            'approved': db.session.execute(select(func.count(Comment.id)).where(Comment.is_approved.is_(True))).scalar() if hasattr(Comment, 'is_approved') else 0,
            'pending': db.session.execute(select(func.count(Comment.id)).where(Comment.is_approved.is_(False))).scalar() if hasattr(Comment, 'is_approved') else 0
        }
        
        return render_template('admin/comments.html',
                             comments_list=comments_pagination,
                             status_filter=status_filter,
                             **stats)
                             
    except Exception as e:
        current_app.logger.error(f"Comments page error: {e}")
        
        # エラー時の空のページネーション
        class EmptyPagination:
            def __init__(self):
                self.items = []
                self.total = 0
                self.page = 1
                self.pages = 0
                self.per_page = 20
                self.has_prev = False
                self.has_next = False
                self.prev_num = None
                self.next_num = None
            
            def iter_pages(self, **kwargs):
                return []
        
        empty_pagination = EmptyPagination()
        stats = {
            'total': 0,
            'approved': 0,
            'pending': 0
        }
        
        flash('コメントデータの取得中にエラーが発生しました。', 'warning')
        return render_template('admin/comments.html',
                             comments_list=empty_pagination,
                             status_filter='all',
                             **stats)

@admin_bp.route('/comment/approve/<int:comment_id>/', methods=['POST'])
@admin_required
def approve_comment(comment_id):
    """コメント承認"""
    try:
        comment = db.get_or_404(Comment, comment_id)
        if hasattr(comment, 'is_approved'):
            comment.is_approved = True
            db.session.commit()
            flash('コメントを承認しました。', 'success')
        else:
            flash('承認機能は実装されていません。', 'warning')
    except Exception as e:
        current_app.logger.error(f"Comment approval error: {e}")
        flash('コメントの承認に失敗しました。', 'danger')
    
    return redirect(url_for('admin.comments'))

@admin_bp.route('/comment/reject/<int:comment_id>/', methods=['POST'])
@admin_required
def reject_comment(comment_id):
    """コメント拒否"""
    try:
        comment = db.get_or_404(Comment, comment_id)
        if hasattr(comment, 'is_approved'):
            comment.is_approved = False
            db.session.commit()
            flash('コメントを拒否しました。', 'info')
        else:
            flash('拒否機能は実装されていません。', 'warning')
    except Exception as e:
        current_app.logger.error(f"Comment rejection error: {e}")
        flash('コメントの拒否に失敗しました。', 'danger')
    
    return redirect(url_for('admin.comments'))

@admin_bp.route('/comment/delete/<int:comment_id>/', methods=['POST'])
@admin_required
def delete_comment(comment_id):
    """コメント削除"""
    try:
        comment = db.get_or_404(Comment, comment_id)
        db.session.delete(comment)
        db.session.commit()
        flash('コメントを削除しました。', 'success')
    except Exception as e:
        current_app.logger.error(f"Comment deletion error: {e}")
        flash('コメントの削除に失敗しました。', 'danger')
    
    return redirect(url_for('admin.comments'))

@admin_bp.route('/comments/bulk-action/', methods=['POST'])
@admin_required
def bulk_comment_action():
    """コメント一括操作"""
    action = request.form.get('action')
    comment_ids = request.form.getlist('comment_ids')
    
    if not comment_ids:
        flash('コメントが選択されていません。', 'warning')
        return redirect(url_for('admin.comments'))
    
    try:
        comments = db.session.execute(select(Comment).where(Comment.id.in_(comment_ids))).scalars().all()
        
        if action == 'approve' and hasattr(Comment, 'is_approved'):
            for comment in comments:
                comment.is_approved = True
            flash(f'{len(comments)}件のコメントを承認しました。', 'success')
        elif action == 'reject' and hasattr(Comment, 'is_approved'):
            for comment in comments:
                comment.is_approved = False
            flash(f'{len(comments)}件のコメントを拒否しました。', 'info')
        elif action == 'delete':
            for comment in comments:
                db.session.delete(comment)
            flash(f'{len(comments)}件のコメントを削除しました。', 'success')
        else:
            flash('無効な操作です。', 'warning')
            return redirect(url_for('admin.comments'))
        
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Bulk comment action error: {e}")
        flash('一括操作に失敗しました。', 'danger')
    
    return redirect(url_for('admin.comments'))


@admin_bp.route('/article/preview/<int:article_id>')
@admin_required
def article_preview(article_id):
    """記事プレビュー（Markdownエディタ）"""
    article = db.get_or_404(Article, article_id)
    return render_template('article_detail.html', article=article, is_preview=True)

# ===============================
# WordPress インポート機能
# ===============================

@admin_bp.route('/wordpress-import/', methods=['GET', 'POST'])
@admin_required
def wordpress_import():
    """WordPress インポート画面"""
    form = WordPressImportForm()
    import_results = None
    
    if form.validate_on_submit():
        try:
            # XMLファイルの保存
            xml_file = form.xml_file.data
            filename = secure_filename(xml_file.filename)
            timestamp = int(time.time())
            filename = f"wp_import_{timestamp}_{filename}"
            
            # 一時保存ディレクトリ
            temp_dir = os.path.join(current_app.instance_path, 'temp')
            os.makedirs(temp_dir, exist_ok=True)
            xml_path = os.path.join(temp_dir, filename)
            xml_file.save(xml_path)
            
            # 必要なモジュールをインポート
            import xml.etree.ElementTree as ET
            import html
            import requests
            from urllib.parse import urlparse
            
            # WordPress インポーターの統合版を作成
            class WebWordPressImporter:
                """Web版 WordPress インポーター"""
                
                def __init__(self, xml_file, author_id, options):
                    self.xml_file = xml_file
                    self.author_id = author_id
                    self.dry_run = options.get('dry_run', False)
                    self.import_categories = options.get('import_categories', True)
                    self.import_images = options.get('import_images', True)
                    self.skip_duplicates = options.get('skip_duplicates', True)
                    self.stats = {
                        'categories_imported': 0,
                        'posts_imported': 0,
                        'images_downloaded': 0,
                        'errors': [],
                        'skipped': []
                    }
                
                def run(self):
                    """インポート実行"""
                    
                    # WordPress XML の名前空間定義
                    namespaces = {
                        'wp': 'http://wordpress.org/export/1.2/',
                        'dc': 'http://purl.org/dc/elements/1.1/',
                        'content': 'http://purl.org/rss/1.0/modules/content/',
                        'excerpt': 'http://wordpress.org/export/1.2/excerpt/'
                    }
                    
                    try:
                        # XML解析
                        tree = ET.parse(self.xml_file)
                        root = tree.getroot()
                        
                        # カテゴリ抽出・インポート
                        if self.import_categories:
                            categories = self._extract_categories(root, namespaces)
                            self._import_categories(categories)
                        
                        # 記事抽出・インポート
                        posts = self._extract_posts(root, namespaces)
                        self._import_posts(posts)
                        
                        return True
                        
                    except Exception as e:
                        current_app.logger.error(f"WordPress import error: {e}")
                        self.stats['errors'].append(f"インポートエラー: {e}")
                        return False
                
                def _generate_slug(self, text):
                    """スラッグ生成"""
                    if not text:
                        return 'untitled'
                    slug = re.sub(r'[^\w\s-]', '', text.lower())
                    slug = re.sub(r'[-\s]+', '-', slug)
                    return slug.strip('-')[:50]
                
                def _extract_categories(self, root, namespaces):
                    """カテゴリ抽出"""
                    categories = []
                    for cat_elem in root.findall('.//wp:category', namespaces):
                        cat_name = cat_elem.find('wp:cat_name', namespaces)
                        category_nicename = cat_elem.find('wp:category_nicename', namespaces)
                        category_description = cat_elem.find('wp:category_description', namespaces)
                        
                        if cat_name is not None and cat_name.text:
                            categories.append({
                                'name': html.unescape(cat_name.text),
                                'slug': category_nicename.text if category_nicename is not None else self._generate_slug(cat_name.text),
                                'description': html.unescape(category_description.text) if category_description is not None and category_description.text else ''
                            })
                    return categories
                
                def _extract_posts(self, root, namespaces):
                    """記事抽出"""
                    posts = []
                    for item in root.findall('.//item'):
                        post_type = item.find('wp:post_type', namespaces)
                        post_status = item.find('wp:status', namespaces)
                        
                        if (post_type is not None and post_type.text == 'post' and 
                            post_status is not None and post_status.text == 'publish'):
                            
                            title = item.find('title')
                            content = item.find('content:encoded', namespaces)
                            excerpt = item.find('excerpt:encoded', namespaces)
                            post_name = item.find('wp:post_name', namespaces)
                            post_date = item.find('wp:post_date', namespaces)
                            
                            # カテゴリ抽出
                            categories = []
                            for cat in item.findall('category[@domain="category"]'):
                                if cat.text:
                                    categories.append(cat.text)
                            
                            posts.append({
                                'title': html.unescape(title.text) if title is not None else 'Untitled',
                                'slug': post_name.text if post_name is not None else self._generate_slug(title.text if title is not None else 'untitled'),
                                'content': html.unescape(content.text) if content is not None else '',
                                'summary': html.unescape(excerpt.text) if excerpt is not None and excerpt.text else '',
                                'published_at': self._parse_wp_date(post_date.text if post_date is not None else ''),
                                'categories': categories
                            })
                    return posts
                
                def _parse_wp_date(self, date_str):
                    """日付解析"""
                    if not date_str:
                        return datetime.now()
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return datetime.now()
                
                def _import_categories(self, categories):
                    """カテゴリインポート"""
                    for category_data in categories:
                        try:
                            if self.skip_duplicates:
                                # 既存チェック（SQLAlchemy 2.0対応）- slug と name の両方でチェック（大文字小文字区別なし）
                                from sqlalchemy import or_, func
                                existing = db.session.execute(
                                    select(Category).where(
                                        or_(Category.slug == category_data['slug'], 
                                            Category.name == category_data['name'],
                                            func.lower(Category.name) == category_data['name'].lower())
                                    )
                                ).scalar_one_or_none()
                                if existing:
                                    self.stats['skipped'].append(f"カテゴリ: {category_data['name']} (既存: {existing.name})")
                                    continue
                            
                            if not self.dry_run:
                                category = Category(
                                    name=category_data['name'],
                                    slug=category_data['slug'],
                                    description=category_data['description']
                                )
                                db.session.add(category)
                                db.session.commit()
                            
                            self.stats['categories_imported'] += 1
                            
                        except Exception as e:
                            self.stats['errors'].append(f"カテゴリ作成失敗: {category_data['name']} - {e}")
                            db.session.rollback()
                
                def _import_posts(self, posts):
                    """記事インポート"""
                    for post_data in posts:
                        try:
                            if self.skip_duplicates:
                                existing = db.session.execute(select(Article).where(Article.slug == post_data['slug'])).scalar_one_or_none()
                                if existing:
                                    self.stats['skipped'].append(f"記事: {post_data['title']}")
                                    continue
                            
                            if not self.dry_run:
                                # 記事作成（元記事の日付を使用）
                                publish_date = post_data['published_at']
                                article = Article(
                                    title=post_data['title'],
                                    slug=post_data['slug'],
                                    body=post_data['content'],  # contentではなくbodyを使用
                                    summary=post_data['summary'],
                                    is_published=True,  # statusではなくis_publishedを使用
                                    published_at=publish_date,
                                    created_at=publish_date,  # 元記事の日付を作成日にも設定
                                    updated_at=publish_date,  # 元記事の日付を更新日にも設定
                                    author_id=self.author_id,
                                )
                                db.session.add(article)
                                db.session.flush()
                                
                                # カテゴリ関連付け（多対多関係を使用）
                                for category_name in post_data['categories']:
                                    category = db.session.execute(select(Category).where(Category.name == category_name)).scalar_one_or_none()
                                    if not category:
                                        category_slug = self._generate_slug(category_name)
                                        category = db.session.execute(select(Category).where(Category.slug == category_slug)).scalar_one_or_none()
                                    
                                    if category:
                                        # 多対多関係でカテゴリを記事に関連付け
                                        article.categories.append(category)
                                
                                db.session.commit()
                            
                            self.stats['posts_imported'] += 1
                            
                        except Exception as e:
                            self.stats['errors'].append(f"記事作成失敗: {post_data['title']} - {e}")
                            db.session.rollback()
            
            # インポート実行
            options = {
                'dry_run': form.dry_run.data,
                'import_categories': form.import_categories.data,
                'import_images': form.import_images.data,
                'skip_duplicates': form.skip_duplicates.data
            }
            
            importer = WebWordPressImporter(xml_path, form.author_id.data, options)
            success = importer.run()
            import_results = importer.stats
            import_results['is_dry_run'] = form.dry_run.data  # テスト実行フラグを追加
            
            # 一時ファイル削除
            try:
                os.remove(xml_path)
            except:
                pass
            
            if success:
                if form.dry_run.data:
                    flash(f'テストインポート完了: カテゴリ{import_results["categories_imported"]}個、記事{import_results["posts_imported"]}個（実際のインポートは実行されていません）', 'info')
                else:
                    flash(f'インポート完了: カテゴリ{import_results["categories_imported"]}個、記事{import_results["posts_imported"]}個', 'success')
            else:
                if form.dry_run.data:
                    flash('テストインポート中にエラーが発生しました', 'warning')
                else:
                    flash('インポート中にエラーが発生しました', 'danger')
                
        except Exception as e:
            current_app.logger.error(f"WordPress import form error: {e}")
            flash(f'インポートエラー: {e}', 'danger')
    
    return render_template('admin/wordpress_import.html', 
                         form=form, 
                         import_results=import_results)

# ===============================
# Google Analytics 設定機能
# ===============================

@admin_bp.route('/analytics/', methods=['GET', 'POST'])
@admin_required
def analytics_settings():
    """Google Analytics設定画面"""
    form = GoogleAnalyticsForm()
    
    # 現在の設定値を取得してフォームに設定
    if request.method == 'GET':
        form.google_analytics_enabled.data = SiteSetting.get_setting('google_analytics_enabled', 'false').lower() == 'true'
        form.google_analytics_id.data = SiteSetting.get_setting('google_analytics_id', '')
        form.google_tag_manager_id.data = SiteSetting.get_setting('google_tag_manager_id', '')
        form.custom_analytics_code.data = SiteSetting.get_setting('custom_analytics_code', '')
        form.analytics_track_admin.data = SiteSetting.get_setting('analytics_track_admin', 'false').lower() == 'true'
        
        # Enhanced E-commerce and Custom Events
        form.enhanced_ecommerce_enabled.data = SiteSetting.get_setting('enhanced_ecommerce_enabled', 'false').lower() == 'true'
        form.track_scroll_events.data = SiteSetting.get_setting('track_scroll_events', 'true').lower() == 'true'
        form.track_file_downloads.data = SiteSetting.get_setting('track_file_downloads', 'true').lower() == 'true'
        form.track_external_links.data = SiteSetting.get_setting('track_external_links', 'true').lower() == 'true'
        form.track_page_engagement.data = SiteSetting.get_setting('track_page_engagement', 'true').lower() == 'true'
        form.track_site_search.data = SiteSetting.get_setting('track_site_search', 'true').lower() == 'true'
        form.track_user_properties.data = SiteSetting.get_setting('track_user_properties', 'false').lower() == 'true'
        
        # Privacy and Cookie Consent
        form.cookie_consent_enabled.data = SiteSetting.get_setting('cookie_consent_enabled', 'true').lower() == 'true'
        form.gdpr_mode.data = SiteSetting.get_setting('gdpr_mode', 'true').lower() == 'true'
        form.ccpa_mode.data = SiteSetting.get_setting('ccpa_mode', 'false').lower() == 'true'
        form.consent_banner_text.data = SiteSetting.get_setting('consent_banner_text', form.consent_banner_text.default)
        form.privacy_policy_url.data = SiteSetting.get_setting('privacy_policy_url', '/privacy-policy')
        form.analytics_storage.data = SiteSetting.get_setting('analytics_storage', 'denied')
        form.ad_storage.data = SiteSetting.get_setting('ad_storage', 'denied')
    
    if form.validate_on_submit():
        try:
            # 設定を保存
            SiteSetting.set_setting('google_analytics_enabled', 
                                   'true' if form.google_analytics_enabled.data else 'false',
                                   'Google Analyticsを有効にする', 'boolean', True)
            
            SiteSetting.set_setting('google_analytics_id', 
                                   form.google_analytics_id.data or '',
                                   'Google Analytics 4 Measurement ID', 'text', True)
            
            SiteSetting.set_setting('google_tag_manager_id', 
                                   form.google_tag_manager_id.data or '',
                                   'Google Tag Manager Container ID', 'text', True)
            
            SiteSetting.set_setting('custom_analytics_code', 
                                   form.custom_analytics_code.data or '',
                                   'カスタムアナリティクスコード', 'text', True)
            
            SiteSetting.set_setting('analytics_track_admin', 
                                   'true' if form.analytics_track_admin.data else 'false',
                                   '管理者のアクセスも追跡する', 'boolean', False)
            
            # Enhanced E-commerce and Custom Events
            SiteSetting.set_setting('enhanced_ecommerce_enabled',
                                   'true' if form.enhanced_ecommerce_enabled.data else 'false',
                                   'Enhanced E-commerce追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_scroll_events',
                                   'true' if form.track_scroll_events.data else 'false',
                                   'スクロール追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_file_downloads',
                                   'true' if form.track_file_downloads.data else 'false',
                                   'ファイルダウンロード追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_external_links',
                                   'true' if form.track_external_links.data else 'false',
                                   '外部リンククリック追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_page_engagement',
                                   'true' if form.track_page_engagement.data else 'false',
                                   'ページエンゲージメント追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_site_search',
                                   'true' if form.track_site_search.data else 'false',
                                   'サイト内検索追跡を有効にする', 'boolean', True)
            
            SiteSetting.set_setting('track_user_properties',
                                   'true' if form.track_user_properties.data else 'false',
                                   'ユーザープロパティ追跡を有効にする', 'boolean', True)
            
            # Privacy and Cookie Consent
            SiteSetting.set_setting('cookie_consent_enabled',
                                   'true' if form.cookie_consent_enabled.data else 'false',
                                   'Cookie同意バナーを有効にする', 'boolean', True)
            
            SiteSetting.set_setting('gdpr_mode',
                                   'true' if form.gdpr_mode.data else 'false',
                                   'GDPR対応モードを有効にする', 'boolean', True)
            
            SiteSetting.set_setting('ccpa_mode',
                                   'true' if form.ccpa_mode.data else 'false',
                                   'CCPA対応モードを有効にする', 'boolean', True)
            
            SiteSetting.set_setting('consent_banner_text',
                                   form.consent_banner_text.data or '',
                                   'Cookie同意バナーテキスト', 'text', True)
            
            SiteSetting.set_setting('privacy_policy_url',
                                   form.privacy_policy_url.data or '/privacy-policy',
                                   'プライバシーポリシーURL', 'text', True)
            
            SiteSetting.set_setting('analytics_storage',
                                   form.analytics_storage.data or 'denied',
                                   'Analytics Storage設定', 'text', True)
            
            SiteSetting.set_setting('ad_storage',
                                   form.ad_storage.data or 'denied',
                                   'Ad Storage設定', 'text', True)
            
            flash('Google Analytics設定を保存しました', 'success')
            current_app.logger.info('Google Analytics settings updated')
            
        except Exception as e:
            current_app.logger.error(f"Analytics settings save error: {e}")
            flash(f'設定の保存に失敗しました: {str(e)}', 'danger')
    else:
        # バリデーションエラーがある場合
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{field}: {error}', 'danger')
    
    # 現在の設定状況を取得（表示用）
    current_settings = {
        'google_analytics_enabled': SiteSetting.get_setting('google_analytics_enabled', 'false'),
        'google_analytics_id': SiteSetting.get_setting('google_analytics_id', ''),
        'google_tag_manager_id': SiteSetting.get_setting('google_tag_manager_id', ''),
        'analytics_track_admin': SiteSetting.get_setting('analytics_track_admin', 'false'),
        'enhanced_ecommerce_enabled': SiteSetting.get_setting('enhanced_ecommerce_enabled', 'false'),
        'track_scroll_events': SiteSetting.get_setting('track_scroll_events', 'true'),
        'track_file_downloads': SiteSetting.get_setting('track_file_downloads', 'true'),
        'track_external_links': SiteSetting.get_setting('track_external_links', 'true'),
        'track_page_engagement': SiteSetting.get_setting('track_page_engagement', 'true'),
        'track_site_search': SiteSetting.get_setting('track_site_search', 'true'),
        'track_user_properties': SiteSetting.get_setting('track_user_properties', 'false'),
        'cookie_consent_enabled': SiteSetting.get_setting('cookie_consent_enabled', 'true'),
        'gdpr_mode': SiteSetting.get_setting('gdpr_mode', 'true'),
        'ccpa_mode': SiteSetting.get_setting('ccpa_mode', 'false'),
        'consent_banner_text': SiteSetting.get_setting('consent_banner_text', ''),
        'privacy_policy_url': SiteSetting.get_setting('privacy_policy_url', '/privacy-policy'),
        'analytics_storage': SiteSetting.get_setting('analytics_storage', 'denied'),
        'ad_storage': SiteSetting.get_setting('ad_storage', 'denied')
    }
    
    return render_template('admin/enhanced_analytics_settings.html', 
                         form=form, 
                         current_settings=current_settings)

# ===============================
# アクセスログアナライザー機能
# ===============================

@admin_bp.route('/access-logs/', methods=['GET'])
@admin_required
def access_logs():
    """アクセスログ分析画面"""
    from access_log_analyzer import AccessLogAnalyzer
    
    log_files = []
    reports = {}
    error_message = None
    
    try:
        # 利用可能なログファイルを検索
        log_patterns = ['flask.log', 'server.log', 'access.log', 'app.log', 'test_access.log']
        for pattern in log_patterns:
            if os.path.exists(pattern):
                log_files.append(pattern)
        
        # デフォルトのログファイルを分析
        if log_files:
            primary_log = log_files[0]
            analyzer = AccessLogAnalyzer(primary_log)
            
            # 最新1000行のみ分析（パフォーマンス考慮）
            stats = analyzer.analyze_logs(max_lines=1000)
            reports[primary_log] = analyzer.generate_report()
            
            current_app.logger.info(f"Access log analysis completed for {primary_log}")
        else:
            error_message = "アクセスログファイルが見つかりません"
    
    except Exception as e:
        current_app.logger.error(f"Access log analysis error: {e}")
        error_message = f"ログ分析エラー: {str(e)}"
    
    return render_template('admin/access_logs.html', 
                         log_files=log_files,
                         reports=reports,
                         error_message=error_message)

@admin_bp.route('/access-logs/download/<log_file>')
@admin_required  
def download_log_report(log_file):
    """ログレポートのJSONダウンロード"""
    from access_log_analyzer import AccessLogAnalyzer
    from flask import jsonify
    
    try:
        if not os.path.exists(log_file):
            return jsonify({'error': 'ログファイルが見つかりません'}), 404
        
        analyzer = AccessLogAnalyzer(log_file)
        stats = analyzer.analyze_logs(max_lines=5000)  # より多くのデータを分析
        report = analyzer.generate_report()
        
        # タイムスタンプを追加
        report['generated_at'] = datetime.now().isoformat()
        report['log_file'] = log_file
        
        return jsonify(report)
    
    except Exception as e:
        current_app.logger.error(f"Log report download error: {e}")
        return jsonify({'error': str(e)}), 500

# ===============================
# AI/LLM SEO対策機能
# ===============================

@admin_bp.route('/seo-tools/', methods=['GET'])
@admin_required
def seo_tools():
    """SEO対策ツール画面"""
    # 最近の記事を取得（SEO分析対象）
    recent_articles = db.session.execute(select(Article).order_by(Article.created_at.desc()).limit(10)).scalars().all()
    
    return render_template('admin/seo_tools.html', 
                         recent_articles=recent_articles)

@admin_bp.route('/seo-analyze/<int:article_id>', methods=['GET', 'POST'])
@admin_required
def seo_analyze_article(article_id):
    """記事の総合SEO分析（既存+新LLMO/AIO）"""
    from llmo_analyzer import LLMOAnalyzer, AIOOptimizer
    import json
    
    article = db.get_or_404(Article, article_id)
    analysis_result = None
    llmo_analysis = None
    aio_analysis = None
    
    # 既存のSEO分析結果を取得
    existing_llmo = SEOAnalysis.query.filter_by(
        article_id=article_id,
        analysis_type='llmo'
    ).first()
    
    existing_aio = SEOAnalysis.query.filter_by(
        article_id=article_id,
        analysis_type='aio'
    ).first()
    
    if request.method == 'POST':
        try:
            content = article.body or ''
            target_keywords = article.meta_keywords.split(',') if article.meta_keywords else []
            target_keywords = [kw.strip() for kw in target_keywords if kw.strip()]
            
            # LLMO分析
            llmo_analyzer = LLMOAnalyzer()
            llmo_result = llmo_analyzer.analyze_content_for_llm(
                content=content,
                title=article.title,
                keywords=target_keywords
            )
            
            # AIO分析
            aio_optimizer = AIOOptimizer()
            aio_result = aio_optimizer.optimize_for_ai_overview(
                article_content=content,
                title=article.title
            )
            
            # 結果保存
            # LLMO結果
            if not existing_llmo:
                existing_llmo = SEOAnalysis(
                    article_id=article_id,
                    analysis_type='llmo'
                )
            
            existing_llmo.analysis_dict = llmo_result
            existing_llmo.score = llmo_result['llm_friendliness_score']
            db.session.add(existing_llmo)
            
            # AIO結果
            if not existing_aio:
                existing_aio = SEOAnalysis(
                    article_id=article_id,
                    analysis_type='aio'
                )
            
            existing_aio.analysis_dict = aio_result
            existing_aio.score = aio_result['optimization_score']
            db.session.add(existing_aio)
            
            db.session.commit()
            
            flash('SEO分析が完了しました', 'success')
            current_app.logger.info(f'SEO analysis completed for article {article_id}')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'SEO analysis error: {e}')
            flash(f'SEO分析エラー: {str(e)}', 'danger')
    
    return render_template('admin/seo_analyze.html',
                         article=article,
                         llmo_analysis=existing_llmo,
                         aio_analysis=existing_aio,
                         analysis=analysis_result,
                         llm_suggestions=llm_suggestions)

@admin_bp.route('/seo-batch-analyze/', methods=['GET', 'POST'])
@admin_required
def seo_batch_analyze():
    """複数記事の一括SEO分析"""
    from seo_optimizer import SEOOptimizer
    
    results = []
    
    if request.method == 'POST':
        try:
            # 分析対象記事の選択
            article_ids = request.form.getlist('article_ids')
            if not article_ids:
                flash('分析対象の記事を選択してください', 'warning')
                return redirect(url_for('admin.seo_batch_analyze'))
            
            optimizer = SEOOptimizer()
            
            for article_id in article_ids:
                article = db.session.get(Article, int(article_id))
                if not article:
                    continue
                
                content = article.content or article.body or ''
                target_keywords = article.meta_keywords.split(',') if article.meta_keywords else []
                target_keywords = [kw.strip() for kw in target_keywords if kw.strip()]
                
                analysis = optimizer.analyze_content(
                    title=article.title,
                    content=content,
                    target_keywords=target_keywords
                )
                
                results.append({
                    'article': article,
                    'analysis': analysis
                })
            
            flash(f'{len(results)}件の記事を分析しました', 'success')
            
        except Exception as e:
            current_app.logger.error(f"Batch SEO analysis error: {e}")
            flash(f'一括分析エラー: {str(e)}', 'danger')
    
    # 分析対象記事一覧
    articles = db.session.execute(select(Article).order_by(Article.created_at.desc()).limit(50)).scalars().all()
    
    return render_template('admin/seo_batch_analyze.html',
                         articles=articles,
                         results=results)

@admin_bp.route('/api/seo-suggestions', methods=['POST'])
@admin_required
def api_seo_suggestions():
    """SEO改善提案API"""
    from seo_optimizer import SEOOptimizer
    
    try:
        data = request.get_json()
        title = data.get('title', '')
        content = data.get('content', '')
        keywords = data.get('keywords', [])
        
        if not title and not content:
            return jsonify({'error': 'タイトルまたはコンテンツが必要です'}), 400
        
        optimizer = SEOOptimizer()
        analysis = optimizer.analyze_content(title, content, keywords)
        
        return jsonify({
            'success': True,
            'analysis': analysis
        })
        
    except Exception as e:
        current_app.logger.error(f"SEO suggestions API error: {e}")
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/site_settings/', methods=['GET', 'POST'])
@admin_required
def site_settings():
    """サイト設定画面"""
    if request.method == 'POST':
        try:
            # サイト基本設定
            # 更新対象の設定項目（新しい設定項目に対応）
            settings_to_update = [
                # 基本情報
                'site_name', 'site_description', 'contact_email',
                # 外観
                'site_logo_url', 'site_favicon_url', 'theme_color', 'footer_text',
                # 機能
                'maintenance_mode', 'registration_enabled', 'comment_moderation', 'max_upload_size',
                # SEO
                'seo_keywords', 'google_search_console_verification',
                # アナリティクス
                'google_analytics_id',
                # SNS（JSON形式）
                'social_media_links',
                # レガシー設定項目（後方互換性のため保持）
                'site_title', 'site_subtitle', 'site_keywords',
                'site_author', 'site_email', 'site_url', 'site_logo',
                'contact_phone', 'contact_address',
                'social_twitter', 'social_facebook', 'social_instagram', 'social_github', 'social_youtube',
                'seo_google_analytics', 'seo_google_tag_manager',
                'comments_enabled', 'allowed_file_types', 'posts_per_page'
            ]
            
            for setting_key in settings_to_update:
                setting_value = request.form.get(setting_key, '')
                
                # 既存設定を取得または新規作成
                setting = db.session.execute(select(SiteSetting).where(SiteSetting.key == setting_key)).scalar_one_or_none()
                
                # 設定タイプに応じた値の処理
                if setting and setting.setting_type == 'boolean':
                    # チェックボックスの場合
                    setting_value = 'true' if request.form.get(setting_key) == 'on' else 'false'
                elif setting and setting.setting_type == 'number':
                    # 数値の場合
                    try:
                        float(setting_value) if setting_value else 0
                    except ValueError:
                        current_app.logger.warning(f"Invalid number value for {setting_key}: {setting_value}")
                        setting_value = '0'
                
                if setting:
                    setting.value = setting_value
                    setting.updated_at = datetime.utcnow()
                else:
                    # 新規設定の場合、setting_typeを推測
                    setting_type = 'text'
                    if setting_key in ['maintenance_mode', 'registration_enabled', 'comment_moderation', 'comments_enabled']:
                        setting_type = 'boolean'
                    elif setting_key in ['max_upload_size', 'posts_per_page']:
                        setting_type = 'number'
                    elif setting_key in ['social_media_links']:
                        setting_type = 'json'
                    
                    setting = SiteSetting(
                        key=setting_key, 
                        value=setting_value,
                        setting_type=setting_type,
                        description=setting_key.replace('_', ' ').title()
                    )
                    db.session.add(setting)
            
            # SNS設定の同期（個別設定からJSON設定を更新）
            sns_links = {
                'twitter': request.form.get('social_twitter', ''),
                'facebook': request.form.get('social_facebook', ''),
                'instagram': request.form.get('social_instagram', ''),
                'github': request.form.get('social_github', ''),
                'youtube': request.form.get('social_youtube', '')
            }
            
            import json
            # social_media_links（JSON形式）を更新
            sns_setting = db.session.execute(select(SiteSetting).where(SiteSetting.key == 'social_media_links')).scalar_one_or_none()
            if sns_setting:
                sns_setting.value = json.dumps(sns_links)
                sns_setting.updated_at = datetime.utcnow()
            else:
                sns_setting = SiteSetting(
                    key='social_media_links',
                    value=json.dumps(sns_links),
                    description='SNSリンク（JSON形式）',
                    setting_type='json',
                    is_public=True
                )
                db.session.add(sns_setting)
            
            db.session.commit()
            flash('サイト設定を更新しました', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Site settings update error: {e}")
            flash(f'設定更新エラー: {str(e)}', 'danger')
    
    # 現在の設定値を取得
    settings = {}
    all_settings = db.session.execute(select(SiteSetting)).scalars().all()
    for setting in all_settings:
        settings[setting.key] = setting.value
    
    return render_template('admin/site_settings.html', settings=settings)

@admin_bp.route('/preview_markdown', methods=['POST'])
@admin_required
def preview_markdown():
    """Markdownプレビュー用エンドポイント"""
    try:
        # CSRF検証
        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.form.get('csrf_token'))
        except Exception as csrf_error:
            current_app.logger.error(f"CSRF validation failed: {csrf_error}")
            return '<p class="text-danger">セキュリティトークンが無効です</p>', 400
            
        markdown_text = request.form.get('markdown_text', '')
        
        if not markdown_text:
            return '<p class="text-muted">プレビューを表示するには本文を入力してください。</p>'
        
        # Markdownライブラリを直接使用してHTMLに変換
        import markdown
        from markdown.extensions import codehilite, fenced_code, tables, toc
        
        md = markdown.Markdown(extensions=[
            'codehilite',
            'fenced_code',
            'tables',
            'toc',
            'nl2br'
        ])
        html_content = md.convert(markdown_text)
        return str(html_content)
    except Exception as e:
        current_app.logger.error(f"Markdown preview error: {e}")
        return f'<p class="text-danger">プレビューエラー: {str(e)}</p>'

@admin_bp.route('/upload_image', methods=['POST'])
@admin_required
def upload_image():
    """画像アップロード用APIエンドポイント"""
    try:
        # ファイル取得
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': '画像ファイルが送信されていません。'
            }), 400
        
        image_file = request.files['image']
        alt_text = request.form.get('alt_text', '').strip()
        caption = request.form.get('caption', '').strip()
        description = request.form.get('description', '').strip()
        
        # 画像処理
        uploaded_image, error = process_uploaded_image(
            image_file, alt_text, caption, description
        )
        
        if error:
            return jsonify({
                'success': False,
                'error': error
            }), 400
        
        # 成功レスポンス
        return jsonify({
            'success': True,
            'image': {
                'id': uploaded_image.id,
                'filename': uploaded_image.filename,
                'original_filename': uploaded_image.original_filename,
                'url': uploaded_image.file_url,
                'alt_text': uploaded_image.alt_text,
                'caption': uploaded_image.caption,
                'width': uploaded_image.width,
                'height': uploaded_image.height,
                'file_size': uploaded_image.file_size_mb,
                'markdown': uploaded_image.markdown_syntax
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Upload image API error: {e}")
        return jsonify({
            'success': False,
            'error': '画像のアップロードに失敗しました。'
        }), 500

@admin_bp.route('/images', methods=['GET'])
@admin_required
def list_images():
    """アップロード済み画像一覧API"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        
        # 基本クエリ
        query = select(UploadedImage).where(UploadedImage.is_active == True)
        
        # 検索フィルター
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                db.or_(
                    UploadedImage.original_filename.ilike(search_filter),
                    UploadedImage.alt_text.ilike(search_filter),
                    UploadedImage.caption.ilike(search_filter),
                    UploadedImage.description.ilike(search_filter)
                )
            )
        
        # ページネーション
        pagination = query.order_by(UploadedImage.upload_date.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        images = []
        for img in pagination.items:
            images.append({
                'id': img.id,
                'filename': img.filename,
                'original_filename': img.original_filename,
                'url': img.file_url,
                'alt_text': img.alt_text,
                'caption': img.caption,
                'width': img.width,
                'height': img.height,
                'file_size': img.file_size_mb,
                'upload_date': img.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
                'usage_count': img.usage_count,
                'markdown': img.markdown_syntax
            })
        
        return jsonify({
            'success': True,
            'images': images,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"List images API error: {e}")
        return jsonify({
            'success': False,
            'error': '画像一覧の取得に失敗しました。'
        }), 500

@admin_bp.route('/images/<int:image_id>', methods=['PUT'])
@admin_required
def update_image(image_id):
    """画像情報更新API"""
    try:
        image = db.get_or_404(UploadedImage, image_id)
        
        # フォームデータから取得
        alt_text = request.form.get('alt_text', '').strip()
        caption = request.form.get('caption', '').strip()
        description = request.form.get('description', '').strip()
        
        # バリデーション
        if not alt_text:
            return jsonify({
                'success': False,
                'error': 'Alt属性は必須です。'
            }), 400
        
        # 更新
        image.alt_text = alt_text
        image.caption = caption if caption else None
        image.description = description if description else None
        image.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '画像情報を更新しました。',
            'image': {
                'id': image.id,
                'alt_text': image.alt_text,
                'caption': image.caption,
                'description': image.description,
                'markdown': image.markdown_syntax
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Update image API error: {e}")
        return jsonify({
            'success': False,
            'error': '画像情報の更新に失敗しました。'
        }), 500

@admin_bp.route('/images/<int:image_id>', methods=['DELETE'])
@admin_required
def delete_image(image_id):
    """画像削除API"""
    try:
        image = db.get_or_404(UploadedImage, image_id)
        
        # ファイル削除
        file_path = os.path.join(current_app.static_folder, image.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        # データベースから削除（論理削除）
        image.is_active = False
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '画像を削除しました。'
        })
        
    except Exception as e:
        current_app.logger.error(f"Delete image API error: {e}")
        return jsonify({
            'success': False,
            'error': '画像の削除に失敗しました。'
        }), 500

@admin_bp.route('/images_manager/')
@admin_required
def images_manager():
    """画像管理ページ"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        per_page = 12  # グリッド表示のため12個ずつ
        
        # 基本クエリ
        query = select(UploadedImage).where(UploadedImage.is_active == True)
        
        # 検索フィルター
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                db.or_(
                    UploadedImage.original_filename.ilike(search_filter),
                    UploadedImage.alt_text.ilike(search_filter),
                    UploadedImage.caption.ilike(search_filter),
                    UploadedImage.description.ilike(search_filter)
                )
            )
        
        # ページネーション
        images_pagination = db.paginate(
            query.order_by(UploadedImage.upload_date.desc()),
            page=page, per_page=per_page, error_out=False
        )
        
        # 統計情報
        total_images = db.session.execute(select(func.count(UploadedImage.id)).where(UploadedImage.is_active == True)).scalar()
        total_size = db.session.execute(select(func.sum(UploadedImage.file_size)).where(UploadedImage.is_active == True)).scalar() or 0
        
        stats = {
            'total_images': total_images,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'search_results': len(images_pagination.items) if search else None
        }
        
        return render_template('admin/images.html',
                             images=images_pagination,
                             search=search,
                             stats=stats)
                             
    except Exception as e:
        current_app.logger.error(f"Images manager error: {e}")
        flash('画像管理ページの読み込みに失敗しました。', 'danger')
        return redirect(url_for('admin.dashboard'))

# ====================================
# サイト設定管理の強化
# ====================================
# 既存のsite_settings機能を活用し、新しい設定項目に対応

# ===============================
# SEO分析機能
# ===============================

@admin_bp.route('/seo/analyze/<int:article_id>/', methods=['GET', 'POST'])
@admin_required
def analyze_article_seo(article_id):
    """記事SEO分析"""
    from llmo_analyzer import LLMOAnalyzer, AIOOptimizer
    import json
    
    article = db.get_or_404(Article, article_id)
    
    if request.method == 'POST':
        try:
            # LLMO分析
            llmo_analyzer = LLMOAnalyzer()
            llmo_result = llmo_analyzer.analyze_content_for_llm(
                content=article.body or '',
                title=article.title,
                keywords=article.meta_keywords.split(',') if article.meta_keywords else []
            )
            
            # AIO分析
            aio_optimizer = AIOOptimizer()
            aio_result = aio_optimizer.optimize_for_ai_overview(
                article_content=article.body or '',
                title=article.title
            )
            
            # 分析結果をデータベースに保存
            # LLMO分析結果
            llmo_analysis = SEOAnalysis.query.filter_by(
                article_id=article_id,
                analysis_type='llmo'
            ).first()
            
            if not llmo_analysis:
                llmo_analysis = SEOAnalysis(
                    article_id=article_id,
                    analysis_type='llmo'
                )
            
            llmo_analysis.analysis_dict = llmo_result
            llmo_analysis.score = llmo_result['llm_friendliness_score']
            db.session.add(llmo_analysis)
            
            # AIO分析結果
            aio_analysis = SEOAnalysis.query.filter_by(
                article_id=article_id,
                analysis_type='aio'
            ).first()
            
            if not aio_analysis:
                aio_analysis = SEOAnalysis(
                    article_id=article_id,
                    analysis_type='aio'
                )
            
            aio_analysis.analysis_dict = aio_result
            aio_analysis.score = aio_result['optimization_score']
            db.session.add(aio_analysis)
            
            db.session.commit()
            
            flash('SEO分析が完了しました', 'success')
            current_app.logger.info(f'SEO analysis completed for article {article_id}')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'SEO analysis error: {e}')
            flash(f'SEO分析エラー: {str(e)}', 'danger')
    
    # 既存の分析結果を取得
    llmo_analysis = SEOAnalysis.query.filter_by(
        article_id=article_id,
        analysis_type='llmo'
    ).first()
    
    aio_analysis = SEOAnalysis.query.filter_by(
        article_id=article_id,
        analysis_type='aio'
    ).first()
    
    return render_template('admin/seo_analyze.html',
                           article=article,
                           llmo_analysis=llmo_analysis,
                           aio_analysis=aio_analysis)

@admin_bp.route('/seo/batch-analyze/', methods=['GET', 'POST'])
@admin_required
def batch_analyze_seo():
    """バッチSEO分析"""
    if request.method == 'POST':
        try:
            from llmo_analyzer import LLMOAnalyzer, AIOOptimizer
            
            # 分析対象の記事を取得（公開済みのみ）
            articles = db.session.execute(
                select(Article)
                .where(Article.is_published == True)
                .order_by(Article.created_at.desc())
                .limit(10)  # パフォーマンス考慮で初回は10件まで
            ).scalars().all()
            
            llmo_analyzer = LLMOAnalyzer()
            aio_optimizer = AIOOptimizer()
            
            analyzed_count = 0
            
            for article in articles:
                try:
                    # LLMO分析
                    llmo_result = llmo_analyzer.analyze_content_for_llm(
                        content=article.body or '',
                        title=article.title,
                        keywords=article.meta_keywords.split(',') if article.meta_keywords else []
                    )
                    
                    # AIO分析
                    aio_result = aio_optimizer.optimize_for_ai_overview(
                        article_content=article.body or '',
                        title=article.title
                    )
                    
                    # 結果保存
                    for analysis_type, result in [('llmo', llmo_result), ('aio', aio_result)]:
                        analysis = SEOAnalysis.query.filter_by(
                            article_id=article.id,
                            analysis_type=analysis_type
                        ).first()
                        
                        if not analysis:
                            analysis = SEOAnalysis(
                                article_id=article.id,
                                analysis_type=analysis_type
                            )
                        
                        analysis.analysis_dict = result
                        if analysis_type == 'llmo':
                            analysis.score = result['llm_friendliness_score']
                        else:
                            analysis.score = result['optimization_score']
                        
                        db.session.add(analysis)
                    
                    analyzed_count += 1
                    
                except Exception as e:
                    current_app.logger.error(f'Batch analysis error for article {article.id}: {e}')
                    continue
            
            db.session.commit()
            flash(f'{analyzed_count}件の記事のSEO分析が完了しました', 'success')
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Batch SEO analysis error: {e}')
            flash(f'バッチ分析エラー: {str(e)}', 'danger')
    
    # 分析結果の統計
    total_analyses = db.session.execute(select(func.count(SEOAnalysis.id))).scalar()
    llmo_analyses = db.session.execute(
        select(func.count(SEOAnalysis.id)).where(SEOAnalysis.analysis_type == 'llmo')
    ).scalar()
    aio_analyses = db.session.execute(
        select(func.count(SEOAnalysis.id)).where(SEOAnalysis.analysis_type == 'aio')
    ).scalar()
    
    # 最新の分析結果
    recent_analyses = db.session.execute(
        select(SEOAnalysis)
        .join(Article)
        .order_by(SEOAnalysis.created_at.desc())
        .limit(20)
    ).scalars().all()
    
    return render_template('admin/seo_batch_analyze.html',
                           total_analyses=total_analyses,
                           llmo_analyses=llmo_analyses,
                           aio_analyses=aio_analyses,
                           recent_analyses=recent_analyses)

@admin_bp.route('/seo/dashboard/')
@admin_required
def seo_dashboard():
    """新しいSEOダッシュボード"""
    try:
        # SEO分析結果の統計
        total_articles = db.session.execute(select(func.count(Article.id))).scalar()
        analyzed_articles = db.session.execute(
            select(func.count(func.distinct(SEOAnalysis.article_id)))
        ).scalar()
        
        # 平均スコア
        avg_llmo_score = db.session.execute(
            select(func.avg(SEOAnalysis.score))
            .where(SEOAnalysis.analysis_type == 'llmo')
        ).scalar() or 0
        
        avg_aio_score = db.session.execute(
            select(func.avg(SEOAnalysis.score))
            .where(SEOAnalysis.analysis_type == 'aio')
        ).scalar() or 0
        
        # スコア別分布
        score_ranges = {
            'excellent': (80, 100),
            'good': (60, 79),
            'fair': (40, 59),
            'poor': (0, 39)
        }
        
        score_distribution = {}
        for range_name, (min_score, max_score) in score_ranges.items():
            count = db.session.execute(
                select(func.count(SEOAnalysis.id))
                .where(SEOAnalysis.score >= min_score)
                .where(SEOAnalysis.score <= max_score)
            ).scalar()
            score_distribution[range_name] = count
        
        # 最新の分析結果（トップスコア）
        top_articles = db.session.execute(
            select(SEOAnalysis, Article.title)
            .join(Article)
            .where(SEOAnalysis.analysis_type == 'llmo')
            .order_by(SEOAnalysis.score.desc())
            .limit(10)
        ).all()
        
        return render_template('admin/seo_dashboard.html',
                               total_articles=total_articles,
                               analyzed_articles=analyzed_articles,
                               avg_llmo_score=round(avg_llmo_score, 1),
                               avg_aio_score=round(avg_aio_score, 1),
                               score_distribution=score_distribution,
                               top_articles=top_articles)
                               
    except Exception as e:
        current_app.logger.error(f'SEO dashboard error: {e}')
        flash('SEOダッシュボードの読み込みに失敗しました。', 'danger')
        return redirect(url_for('admin.dashboard'))

# === メールアドレス変更機能 ===

@admin_bp.route('/user/<int:user_id>/request_email_change/', methods=['POST'])
@admin_required
def request_email_change(user_id):
    """メールアドレス変更要求"""
    try:
        user = db.get_or_404(User, user_id)
        
        # 権限チェック（自分自身のアカウントのみ変更可能）
        if user.id != current_user.id:
            return jsonify({
                'success': False, 
                'message': '自分自身のメールアドレスのみ変更できます。'
            }), 403
        
        # フォームデータ取得
        current_password = request.form.get('current_password')
        new_email = request.form.get('new_email')
        
        if not current_password or not new_email:
            return jsonify({
                'success': False,
                'message': 'パスワードと新しいメールアドレスを入力してください。'
            }), 400
        
        # パスワード確認
        if not check_password_hash(user.password_hash, current_password):
            return jsonify({
                'success': False,
                'message': '現在のパスワードが正しくありません。'
            }), 400
        
        # 新しいメールアドレスの重複チェック
        existing_user = db.session.execute(
            select(User).where(User.email == new_email)
        ).scalar_one_or_none()
        
        if existing_user:
            return jsonify({
                'success': False,
                'message': 'そのメールアドレスは既に使用されています。'
            }), 400
        
        # 既存の未確認要求を削除
        db.session.execute(
            db.delete(EmailChangeRequest).where(
                EmailChangeRequest.user_id == user.id,
                EmailChangeRequest.is_verified == False
            )
        )
        
        # 新しい変更要求を作成
        change_request = EmailChangeRequest(
            user_id=user.id,
            current_email=user.email,
            new_email=new_email
        )
        change_request.generate_token()
        
        db.session.add(change_request)
        db.session.commit()
        
        # 確認メール送信
        send_email_change_confirmation(change_request)
        
        return jsonify({
            'success': True,
            'message': f'確認メールを {new_email} に送信しました。メール内のリンクをクリックして変更を完了してください（24時間有効）。'
        })
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Email change request error: {e}')
        return jsonify({
            'success': False,
            'message': 'システムエラーが発生しました。しばらく後でお試しください。'
        }), 500

def send_email_change_confirmation(change_request):
    """メールアドレス変更確認メール送信"""
    try:
        # 確認URL生成
        confirm_url = url_for('confirm_email_change', 
                            token=change_request.token, 
                            _external=True)
        
        # メール本文作成
        subject = '【Mini Blog】メールアドレス変更の確認'
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>🔐 メールアドレス変更の確認</h2>
            <p>こんにちは、</p>
            <p>あなたのアカウントのメールアドレス変更要求を受け付けました。</p>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin: 20px 0;">
                <p><strong>現在のメールアドレス:</strong> {change_request.current_email}</p>
                <p><strong>新しいメールアドレス:</strong> {change_request.new_email}</p>
            </div>
            
            <p>この変更を完了するには、以下のボタンをクリックしてください：</p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{confirm_url}" 
                   style="background-color: #007bff; color: white; padding: 12px 30px; 
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    ✅ メールアドレス変更を確認
                </a>
            </div>
            
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <p><strong>⚠️ 重要な注意事項:</strong></p>
                <ul>
                    <li>このリンクは24時間後に無効になります</li>
                    <li>心当たりがない場合は、このメールを無視してください</li>
                    <li>このメールアドレス変更を要求していない場合は、アカウントのセキュリティを確認してください</li>
                </ul>
            </div>
            
            <p>リンクがクリックできない場合は、以下のURLをコピーしてブラウザに貼り付けてください：</p>
            <p style="word-break: break-all; color: #666; font-size: 14px;">{confirm_url}</p>
            
            <hr style="margin: 30px 0;">
            <p style="color: #666; font-size: 12px;">
                このメールは自動送信されています。返信はできません。<br>
                ご質問がある場合は、サイト管理者にお問い合わせください。
            </p>
        </div>
        """
        
        # 環境に応じたメール送信
        mail_debug = os.environ.get('MAIL_DEBUG', 'true').lower() == 'true'
        
        if mail_debug:
            # 開発環境：デバッグモード
            send_debug_email(subject, change_request.new_email, html_body, confirm_url)
        else:
            # 本番環境：AWS SES 使用
            send_ses_email(subject, change_request.new_email, html_body)
        
        current_app.logger.info(f'Email change confirmation sent to {change_request.new_email}')
        
    except Exception as e:
        current_app.logger.error(f'Failed to send email change confirmation: {e}')
        raise

def send_debug_email(subject, recipient, html_body, confirm_url):
    """開発環境用：デバッグメール送信"""
    print("\n" + "="*80)
    print("📧 DEBUG: メール送信")
    print("="*80)
    print(f"宛先: {recipient}")
    print(f"件名: {subject}")
    print(f"確認URL: {confirm_url}")
    print("="*80)
    print("HTML本文:")
    print(html_body)
    print("="*80 + "\n")
    
    # ファイルにも保存
    import os
    from datetime import datetime
    
    debug_dir = "debug_emails"
    if not os.path.exists(debug_dir):
        os.makedirs(debug_dir)
    
    filename = f"{debug_dir}/email_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{subject}</title>
</head>
<body>
    <h1>デバッグメール</h1>
    <p><strong>宛先:</strong> {recipient}</p>
    <p><strong>件名:</strong> {subject}</p>
    <p><strong>確認URL:</strong> <a href="{confirm_url}">{confirm_url}</a></p>
    <hr>
    {html_body}
</body>
</html>
        """)
    
    print(f"📁 デバッグメールを保存: {filename}")

def send_ses_email(subject, recipient, html_body):
    """AWS SES を使用したメール送信"""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        # AWS 設定
        aws_region = os.environ.get('AWS_REGION', 'ap-northeast-1')
        sender = os.environ.get('MAIL_DEFAULT_SENDER')
        
        # SES クライアント作成
        ses_client = boto3.client(
            'ses',
            region_name=aws_region,
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
        )
        
        # メール送信
        response = ses_client.send_email(
            Destination={
                'ToAddresses': [recipient],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': html_body,
                    },
                },
                'Subject': {
                    'Charset': 'UTF-8',
                    'Data': subject,
                },
            },
            Source=sender,
        )
        
        current_app.logger.info(f'SES email sent successfully. MessageId: {response["MessageId"]}')
        return True
        
    except ClientError as e:
        current_app.logger.error(f'SES send email error: {e.response["Error"]["Message"]}')
        raise
    except Exception as e:
        current_app.logger.error(f'SES send email unexpected error: {e}')
        raise

