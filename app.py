from flask import Flask, render_template, redirect, url_for, flash, session, request, current_app, abort, jsonify
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_login import LoginManager, current_user, login_required
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from sqlalchemy import select, func
from admin import admin_bp
from comments import comments_bp
from articles import articles_bp
from projects import projects_bp
from search import search_bp
from categories import categories_bp

# .envファイルを読み込み
load_dotenv()
import logging
import bleach
import markdown
from markupsafe import Markup
import re
import requests
from bs4 import BeautifulSoup

# MySQL対応: PyMySQLをmysqldbとして登録
import pymysql
pymysql.install_as_MySQLdb()

# OGPキャッシュ用
from functools import lru_cache
import hashlib
from datetime import datetime, timedelta


# models.py から db インスタンスとモデルクラスをインポートします
from models import db, User, Article, Category, Comment, EmailChangeRequest, article_categories, Challenge, Project
# forms.py からフォームクラスをインポート
from forms import CommentForm

app = Flask(__name__)

# セキュリティヘッダーとキャッシュ制御の統合設定
@app.after_request
def after_request(response):
    # セキュリティヘッダーの追加
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://platform.twitter.com https://www.instagram.com https://*.instagram.com https://connect.facebook.net https://*.facebook.com https://threads.com https://threads.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://*.instagram.com; img-src 'self' data: https: http:; font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://platform.twitter.com https://www.instagram.com https://www.facebook.com https://threads.net https://threads.com https://twitframe.com; child-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; connect-src 'self' https://*.instagram.com https://*.facebook.com"
    # Permissions Policy: SNS埋込でunloadイベントを許可
    response.headers['Permissions-Policy'] = "unload=*"
    
    # 開発時のみ：静的ファイルのキャッシュを無効化
    if app.debug:
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    
    # アクセスログを記録
    try:
        remote_addr = request.environ.get('REMOTE_ADDR', '-')
        method = request.method
        path = request.path
        protocol = request.environ.get('SERVER_PROTOCOL', 'HTTP/1.1')
        status = response.status_code
        content_length = response.content_length or '-'
        referrer = request.referrer or '-'
        user_agent = request.headers.get('User-Agent', '-')
        
        # アクセスログの記録（Apache Combined Log Format風）
        log_entry = f'{remote_addr} - - [{datetime.now().strftime("%d/%b/%Y:%H:%M:%S %z")}] "{method} {path} {protocol}" {status} {content_length} "{referrer}" "{user_agent}"'
        
        # access.log ファイルに記録
        with open('access.log', 'a', encoding='utf-8') as f:
            f.write(log_entry + '\n')
            
    except Exception as e:
        # ログ記録エラーは無視（アプリケーションの動作に影響しないように）
        app.logger.debug(f"Access log error: {e}")
    
    return response

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///portfolio.db')
app.config['ENCRYPTION_KEY'] = os.environ.get('ENCRYPTION_KEY')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/uploads' # staticフォルダ内のuploadsを基本とする
app.config['CATEGORY_OGP_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'category_ogp')
app.config['BLOCK_IMAGE_UPLOAD_FOLDER'] = os.path.join(app.config['UPLOAD_FOLDER'], 'blocks')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # デフォルト: 16MB
app.config['WTF_CSRF_TIME_LIMIT'] = int(os.environ.get('WTF_CSRF_TIME_LIMIT', 3600))  # デフォルト: 1時間
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true'
app.config['SESSION_COOKIE_HTTPONLY'] = True  # XSS対策でJavaScriptからのアクセスを禁止
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF対策

# セキュリティ強化設定
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=int(os.environ.get('SESSION_LIFETIME_HOURS', 24)))
app.config['WTF_CSRF_ENABLED'] = os.environ.get('WTF_CSRF_ENABLED', 'true').lower() == 'true'

# メール設定
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'localhost')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@miniblog.local')

# デバッグモードの設定（環境変数ベース）
app.debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'

# --- ロガー設定を追加 ---
if app.debug:
    # 開発モード時は DEBUG レベル以上のログをコンソールに出力
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.DEBUG)
else:
    # 本番モード時も一時的にDEBUGレベルに設定（SNSデバッグ用）
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.DEBUG)

# アクセスログファイルハンドラーを追加
import logging.handlers
access_log_handler = logging.handlers.RotatingFileHandler(
    'access.log', maxBytes=10*1024*1024, backupCount=5  # 10MB, 5ファイルまで
)
access_log_handler.setLevel(logging.INFO)
access_log_formatter = logging.Formatter(
    '%(remote_addr)s - - [%(asctime)s] "%(method)s %(path)s %(protocol)s" %(status)s %(content_length)s "%(referrer)s" "%(user_agent)s"',
    datefmt='%d/%b/%Y:%H:%M:%S %z'
)
access_log_handler.setFormatter(access_log_formatter)

# Flaskのアクセスログ用ロガーを作成
access_logger = logging.getLogger('access_log')
access_logger.addHandler(access_log_handler)
access_logger.setLevel(logging.INFO)
# --- ここまで追加 ---

migrate = Migrate()  # Migrate インスタンスの作成はここでもOK
csrf = CSRFProtect()  # CSRF保護の初期化
mail = Mail()  # メール機能の初期化

login_manager = LoginManager()
# login_viewは後でルート定義後に設定

# models.py からインポートした db をアプリケーションに登録します
db.init_app(app)
# migrate も同様に、インポートした db を使用します
migrate.init_app(app, db)
csrf.init_app(app)  # CSRF保護を有効化

# JSONフィルターを追加
import json

@app.template_filter('from_json')
def from_json_filter(text):
    """JSON文字列をPythonオブジェクトに変換するフィルター"""
    if not text:
        return {}
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}

# Markdownフィルターを追加
@app.template_filter('markdown')
def markdown_filter(text):
    """MarkdownテキストをHTMLに変換するフィルター（SNS埋込自動検出付き）"""
    if not text:
        return ''
    
    # SNS URLの自動埋込処理（Markdown変換前）
    # oEmbedハンドラーを使用するため、ここでは実行しない
    # text = process_sns_auto_embed(text)
    
    # Markdownの拡張機能を設定
    md = markdown.Markdown(
        extensions=['extra', 'codehilite', 'toc', 'nl2br'],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': False
            }
        },
        tab_length=2  # タブ長を短く設定
    )
    
    # MarkdownをHTMLに変換
    html = md.convert(text)
    
    # セキュリティのためHTMLをサニタイズ（SNS埋込用タグを追加）
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'strong', 'em', 'u', 'del',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        # SNS埋込用タグ
        'div', 'iframe', 'script', 'blockquote', 'noscript'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
        'h1': ['id'], 'h2': ['id'], 'h3': ['id'], 'h4': ['id'], 'h5': ['id'], 'h6': ['id'],
        # SNS埋込用属性
        'div': ['class', 'id', 'style', 'data-href', 'data-width', 'data-instgrm-permalink'],
        'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'title', 'style'],
        'script': ['src', 'async', 'defer', 'charset', 'crossorigin'],
        'blockquote': ['class', 'style', 'data-instgrm-permalink'],
        'noscript': []
    }
    
    # SNS埋込HTMLがある場合はbleachを適用しない（安全なHTMLのため）
    if any(cls in html for cls in ['sns-embed', 'youtube-embed', 'twitter-embed', 'instagram-embed', 'facebook-embed', 'threads-embed']):
        clean_html = html
    else:
        # 通常のMarkdownコンテンツのみサニタイズ
        clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes)
    
    # 見出しにアンカーIDを追加
    clean_html = add_heading_anchors(clean_html)
    
    return Markup(clean_html)
mail.init_app(app)  # メール機能を有効化
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # SQLAlchemy 2.0 対応

# ユーティリティ関数のインポート
from utils import sanitize_html, generate_table_of_contents, add_heading_anchors, perform_search
# SEO/OGP関数のインポート  
from seo import process_sns_auto_embed, process_general_url_embeds, fetch_ogp_data, generate_ogp_card, generate_article_structured_data




# CSRF トークンをテンプレートで利用可能にする
@app.context_processor
def inject_csrf_token():
    from flask_wtf.csrf import generate_csrf
    from markupsafe import Markup
    
    def csrf_token():
        token = generate_csrf()
        return Markup(f'<input type="hidden" name="csrf_token" value="{token}"/>')
    
    def csrf_token_value():
        return generate_csrf()
    
    return dict(csrf_token=csrf_token, csrf_token_value=csrf_token_value)

# Google Analytics統合
@app.context_processor
def inject_analytics():
    """Google Analyticsの設定をテンプレートに注入"""
    from models import SiteSetting
    from markupsafe import Markup
    
    def google_analytics_code():
        """Enhanced Google Analytics トラッキングコードを生成"""
        from ga4_analytics import GA4AnalyticsManager
        
        analytics_manager = GA4AnalyticsManager()
        
        # ユーザーを追跡すべきかチェック
        user = current_user if current_user.is_authenticated else None
        
        # トラッキングコードを生成
        tracking_code = analytics_manager.generate_tracking_code(user)
        
        # カスタムアナリティクスコード
        custom_code = SiteSetting.get_setting('custom_analytics_code', '')
        if custom_code:
            tracking_code = Markup(str(tracking_code) + f'\n<!-- Custom Analytics Code -->\n{custom_code}')
        
        return tracking_code
    
    def google_tag_manager_noscript():
        """Enhanced Google Tag Manager noscript 部分"""
        from ga4_analytics import GA4AnalyticsManager
        
        analytics_manager = GA4AnalyticsManager()
        
        # ユーザーを追跡すべきかチェック
        user = current_user if current_user.is_authenticated else None
        
        # GTM noscript部分を生成
        return analytics_manager.generate_gtm_noscript(user)
    
    return dict(
        google_analytics_code=google_analytics_code,
        google_tag_manager_noscript=google_tag_manager_noscript
    )

# サイト設定をテンプレートに注入
@app.context_processor
def inject_site_settings():
    """サイト設定をすべてのテンプレートで利用可能にする"""
    from models import SiteSetting
    import json
    
    def get_site_settings():
        """公開設定のみを取得（キャッシュ機能付き）"""
        try:
            # 公開設定のみを取得
            public_settings = db.session.execute(
                select(SiteSetting).where(SiteSetting.is_public == True)
            ).scalars().all()
            
            settings = {}
            for setting in public_settings:
                value = setting.value
                
                # 設定タイプに応じて値を変換
                if setting.setting_type == 'boolean':
                    value = value.lower() == 'true'
                elif setting.setting_type == 'number':
                    try:
                        value = float(value) if '.' in value else int(value)
                    except ValueError:
                        value = 0
                elif setting.setting_type == 'json':
                    try:
                        value = json.loads(value) if value else {}
                    except json.JSONDecodeError:
                        value = {}
                
                settings[setting.key] = value
            
            return settings
        except Exception as e:
            current_app.logger.error(f"Error loading site settings: {e}")
            return {}
    
    def get_setting(key, default=None):
        """個別設定値を取得"""
        try:
            return SiteSetting.get_setting(key, default)
        except Exception as e:
            current_app.logger.error(f"Error getting setting {key}: {e}")
            return default
    
    def get_admin_user():
        """管理者ユーザー情報を取得"""
        try:
            from sqlalchemy import select
            from models import User
            admin_user = db.session.execute(
                select(User).where(User.role == 'admin').limit(1)
            ).scalar_one_or_none()
            if admin_user:
                pass
            else:
                current_app.logger.warning("No admin user found")
            return admin_user
        except Exception as e:
            current_app.logger.error(f"Error loading admin user: {e}")
            return None
    
    return dict(
        site_settings=get_site_settings(),
        get_setting=get_setting,
        admin_user=get_admin_user()
    )

# カスタムフィルター
@app.template_filter('nl2br')
def nl2br(value):
    """改行をHTMLの<br>タグに変換"""
    from markupsafe import Markup
    if value:
        return Markup(value.replace('\n', '<br>'))
    return value

@app.template_filter('striptags')
def striptags(value):
    """HTMLタグを除去"""
    import re
    if value:
        return re.sub(r'<[^>]*>', '', value)
    return value

@app.template_filter('oembed_process')
def oembed_process_filter(html_content):
    """oEmbedを使用してHTML内のURLを埋込に変換"""
    if not html_content:
        return html_content
    
    try:
        from oembed_handler import process_markdown_content
        result = process_markdown_content(html_content)
        return Markup(result)
    except Exception as e:
        current_app.logger.error(f"oEmbed processing error: {e}")
        # エラー時は元のHTMLを返す
        return Markup(html_content)


# 開発環境でのみデバッグルートを登録（Blueprint登録前）
if app.debug:
    try:
        from admin import register_debug_routes
        register_debug_routes()
    except ImportError:
        pass

# 管理画面Blueprintの登録（環境変数対応）
ADMIN_URL_PREFIX = os.environ.get('ADMIN_URL_PREFIX', 'admin')
app.register_blueprint(admin_bp, url_prefix=f'/{ADMIN_URL_PREFIX}')

def get_static_page_seo(page_slug):
    """静的ページのSEO設定を取得"""
    from models import StaticPageSEO
    page_seo = db.session.execute(
        select(StaticPageSEO).where(StaticPageSEO.page_slug == page_slug)
    ).scalar_one_or_none()
    return page_seo

def generate_article_structured_data(article):
    """記事の構造化データ（JSON-LD）を生成"""
    import json
    from datetime import datetime
    
    # 既にJSON-LDが設定されている場合はそれを使用
    if hasattr(article, 'json_ld') and article.json_ld:
        try:
            # 既存のJSON-LDが有効かチェック
            json.loads(article.json_ld)
            return article.json_ld
        except (json.JSONDecodeError, TypeError):
            pass
    
    # サイト設定を取得
    from models import SiteSetting
    try:
        site_name = SiteSetting.get_setting('site_name', 'Python 100日チャレンジ')
    except:
        site_name = 'Python 100日チャレンジ'
    
    # 基本的な記事の構造化データを生成
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article.title,
        "description": article.meta_description or (
            article.summary[:160] + '...' if article.summary and len(article.summary) > 160 
            else article.summary
        ) or "",
        "author": {
            "@type": "Person",
            "name": (
                article.author.display_name if hasattr(article, 'author') and article.author and hasattr(article.author, 'display_name') and article.author.display_name
                else article.author.email if hasattr(article, 'author') and article.author and hasattr(article.author, 'email') and article.author.email
                else "管理者"
            )
        },
        "datePublished": article.published_at.isoformat() if article.published_at else article.created_at.isoformat(),
        "dateModified": article.updated_at.isoformat() if article.updated_at else article.created_at.isoformat(),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url_for('article_detail', slug=article.slug, _external=True)
        },
        "publisher": {
            "@type": "Organization",
            "name": site_name,
            "logo": {
                "@type": "ImageObject",
                "url": url_for('static', filename='images/logo.png', _external=True)
            }
        }
    }
    
    # アイキャッチ画像があれば追加
    if hasattr(article, 'featured_image') and article.featured_image:
        structured_data["image"] = url_for('static', filename=article.featured_image, _external=True)
    
    # カテゴリがあれば追加
    if hasattr(article, 'categories') and article.categories:
        structured_data["about"] = [
            {
                "@type": "Thing",
                "name": category.name
            } for category in article.categories
        ]
    
    # キーワードがあれば追加
    if article.meta_keywords:
        keywords = [kw.strip() for kw in article.meta_keywords.split(',') if kw.strip()]
        if keywords:
            structured_data["keywords"] = keywords
    
    # 文字数を推定（SEO指標として）
    if article.body:
        word_count = len(article.body.split())
        structured_data["wordCount"] = word_count
    
    return json.dumps(structured_data, ensure_ascii=False, indent=2)

# 関数はutils.pyに移動済み

@app.route('/')
def landing():
    """ビジネス・サービス中心のトップページ"""
    # 基本的なデータを取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 注目プロジェクト（最新実績として表示）
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('home')
    
    return render_template('landing.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         featured_projects=featured_projects,
                         page_seo=page_seo)

@app.route('/portfolio')
def portfolio():
    """ポートフォリオページ（100日チャレンジ）"""
    from models import SiteSetting, Challenge
    
    # アクティブなチャレンジを取得
    active_challenge = db.session.execute(
        select(Challenge).where(Challenge.is_active.is_(True))
    ).scalar_one_or_none()
    
    if not active_challenge:
        # アクティブなチャレンジがない場合、最新のチャレンジを取得
        active_challenge = db.session.execute(
            select(Challenge).order_by(Challenge.display_order.desc())
        ).scalar_one_or_none()
    
    # 最新記事を取得（アクティブチャレンジの記事を優先）
    if active_challenge:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(
            # アクティブチャレンジの記事を優先、その後公開日順
            (Article.challenge_id == active_challenge.id).desc(),
            Article.published_at.desc()
        ).limit(5)
    else:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(Article.published_at.desc()).limit(5)
    
    latest_articles = db.session.execute(latest_articles_query).scalars().all()
    
    # 記事の総数を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    # スキルカテゴリを取得
    skill_categories = db.session.execute(
        select(Category).where(Category.parent_id.is_(None)).order_by(Category.name)
    ).scalars().all()
    
    # すべてのチャレンジを取得（一覧表示用）
    all_challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order)
    ).scalars().all()
    
    # 注目プロジェクトを取得（最大3件）
    from models import Project
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # プロジェクト総数を取得
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 現在の学習日数を計算（アクティブチャレンジベース）
    current_day = 0
    if active_challenge:
        current_day = active_challenge.days_elapsed
    
    return render_template('portfolio.html',
                         active_challenge=active_challenge,
                         latest_articles=latest_articles,
                         total_articles=total_articles,
                         total_projects=total_projects,
                         current_day=current_day,
                         skill_categories=skill_categories,
                         all_challenges=all_challenges,
                         featured_projects=featured_projects)

@app.route('/services')
def services():
    """サービス詳細ページ"""
    # 実績プロジェクト（詳細表示用）
    all_projects = db.session.execute(
        select(Project).where(Project.status == 'active')
        .order_by(Project.display_order)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('services')
    
    return render_template('services.html',
                         all_projects=all_projects,
                         page_seo=page_seo)

@app.route('/story')
def story():
    """キャリアストーリーページ"""
    # 実際の数値を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('story')
    
    return render_template('story.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         page_seo=page_seo)



# Blueprint登録
from api import api_bp
from auth import auth_bp
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(comments_bp)
app.register_blueprint(articles_bp)
app.register_blueprint(projects_bp)
app.register_blueprint(search_bp)
app.register_blueprint(categories_bp)


# Flask-LoginManagerの設定（ルート定義後）
login_manager.login_view = 'auth.login'
login_manager.login_message = "このページにアクセスするにはログインが必要です。"
login_manager.login_message_category = "info"





@app.route('/admin/article/upload_image/', methods=['POST'])
def upload_image():
    if 'image' not in request.files:
        flash('ファイルがありません')
        return redirect(request.referrer)
    file = request.files['image']
    if file.filename == '':
        flash('ファイルが選択されていません')
        return redirect(request.referrer)
    if file and allowed_file(file.filename):
        filename = file.filename
        save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(save_path)
        flash('アップロード成功')
        return redirect(request.referrer)
    else:
        flash('許可されていないファイル形式です')
        return redirect(request.referrer)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']



@app.route('/about/')
def profile():
    """ユーザープロフィールページ（ポートフォリオ版）"""
    # 管理者ユーザーを取得（一人管理前提）
    user = db.session.execute(select(User).where(User.role == 'admin')).scalar_one_or_none()
    if not user:
        abort(404)
    
    # SEO設定を取得
    page_seo = get_static_page_seo('about')
    
    # 公開記事のみ取得
    articles = db.session.execute(
        select(Article).where(Article.author_id == user.id, Article.is_published.is_(True)).order_by(
            db.case(
                (Article.published_at.isnot(None), Article.published_at),
                else_=Article.created_at
            ).desc()
        )
    ).scalars().all()
    
    # プロジェクトを取得（作成者でフィルタ可能な場合）
    projects = db.session.execute(
        select(Project).order_by(Project.created_at.desc())
    ).scalars().all()
    
    # 注目プロジェクトを取得
    featured_projects = [p for p in projects if p.is_featured]
    
    # チャレンジ情報を取得
    challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order, Challenge.id)
    ).scalars().all()
    
    return render_template('profile_portfolio.html', 
                           user=user, 
                           articles=articles,
                           projects=projects,
                           featured_projects=featured_projects,
                           challenges=challenges,
                           page_seo=page_seo)

@app.route('/download/resume/<int:user_id>')
@login_required
def download_resume(user_id):
    """履歴書PDFダウンロード（動的日付生成）"""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from flask import make_response
    
    # 日本語フォント設定
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    
    # ユーザー情報取得
    user = User.query.get_or_404(user_id)
    
    # アクセス権限チェック（本人または管理者のみ）
    if current_user.id != user.id and current_user.role != 'admin':
        abort(403)
    
    # PDFバッファー作成
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    # スタイル設定
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#333333'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='HeiseiKakuGo-W5'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        fontName='HeiseiKakuGo-W5'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        fontName='HeiseiKakuGo-W5'
    )
    
    # ドキュメント要素
    elements = []
    
    # タイトル
    elements.append(Paragraph("履歴書", title_style))
    elements.append(Spacer(1, 12))
    
    # 日付（動的生成）
    today = datetime.now().strftime('%Y年%m月%d日')
    elements.append(Paragraph(f"{today} 現在", normal_style))
    elements.append(Spacer(1, 20))
    
    # 基本情報テーブル
    basic_info = [
        ['氏名', user.handle_name or user.name],
        ['メールアドレス', user.portfolio_email or user.email],
        ['職種', user.job_title or '未設定']
    ]
    
    if user.birthplace:
        basic_info.append(['出身地', user.birthplace])
    
    basic_table = Table(basic_info, colWidths=[4*cm, 10*cm])
    basic_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'HeiseiKakuGo-W5'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(basic_table)
    elements.append(Spacer(1, 30))
    
    # スキル情報
    if user.skills:
        elements.append(Paragraph("スキル・技術", heading_style))
        for category, skills_list in user.skills.items():
            skill_names = [f"{skill['name']} ({skill.get('years', 'N/A')}年)" for skill in skills_list]
            elements.append(Paragraph(f"<b>{category}:</b> {', '.join(skill_names)}", normal_style))
            elements.append(Spacer(1, 6))
        elements.append(Spacer(1, 20))
    
    # 職歴
    if user.career_history:
        elements.append(Paragraph("職歴", heading_style))
        for i, job in enumerate(user.career_history):
            elements.append(Paragraph(f"<b>{job['company']}</b> - {job['position']}", normal_style))
            elements.append(Paragraph(f"期間: {job['period']}", normal_style))
            if job.get('description'):
                elements.append(Paragraph(job['description'], normal_style))
            if i < len(user.career_history) - 1:
                elements.append(Spacer(1, 12))
    
    # PDF生成
    doc.build(elements)
    
    # レスポンス作成
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=resume_{user.id}_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response

# 開発用テスト関数
@app.route('/test_ogp')
def test_ogp():
    """開発用：OGPカード表示のテスト"""
    if not app.debug:
        return "Not available in production", 404
    
    test_content = """テスト記事

一般的なWebサイトのOGPカード表示をテスト：

https://docs.python.org/

Threadsの投稿も表示：

https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp

終了。"""
    
    processed_content = process_sns_auto_embed(test_content)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>OGP Test</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>OGP Card Test</h1>
    <div class="content">
        {processed_content.replace(chr(10), '<br>')}
    </div>
</body>
</html>"""

@app.route('/debug_ogp')
def debug_ogp():
    """開発用：OGP取得のデバッグテスト"""
    if not app.debug:
        return "Not available in production", 404
    
    url = request.args.get('url', 'https://docs.python.org/')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    try:
        current_app.logger.info(f"🔍 Debug OGP test for URL: {url}")
        ogp_data = fetch_ogp_data(url, force_refresh=force_refresh)
        
        # OGPカード生成も試す
        if url.startswith('http'):
            card_html = generate_ogp_card(url)
        else:
            card_html = "Invalid URL"
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>OGP Debug Test</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .debug-info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .content {{ line-height: 1.6; }}
        pre {{ background: #f0f0f0; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <h1>OGP Debug Test</h1>
    
    <div class="debug-info">
        <h3>Test Parameters:</h3>
        <p><strong>URL:</strong> {url}</p>
        <p><strong>Force Refresh:</strong> {force_refresh}</p>
    </div>
    
    <div class="debug-info">
        <h3>Raw OGP Data:</h3>
        <pre>{ogp_data}</pre>
    </div>
    
    <div class="debug-info">
        <h3>Generated Card:</h3>
        {card_html}
    </div>
    
    <div class="debug-info">
        <h3>Test Different URLs:</h3>
        <ul>
            <li><a href="/debug_ogp?url=https://docs.python.org/&force_refresh=true">Python Docs (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://github.com/&force_refresh=true">GitHub (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp&force_refresh=true">Threads Post (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://invalid-url-test.com&force_refresh=true">Invalid URL Test</a></li>
        </ul>
    </div>
</body>
</html>"""
    except Exception as e:
        current_app.logger.error(f"🚨 OGP Debug Error: {str(e)}")
        return f"""<!DOCTYPE html>
<html>
<head><title>OGP Debug Error</title></head>
<body>
    <h1>OGP Debug Error</h1>
    <p><strong>URL:</strong> {url}</p>
    <p><strong>Error:</strong> {str(e)}</p>
    <p><a href="/debug_ogp">Try Again</a></p>
</body>
</html>"""

@app.route('/debug_filter')
def debug_filter():
    """テンプレートフィルターのデバッグ用エンドポイント"""
    if not app.debug:
        return "Not available in production", 404
    
    test_text = """これはテストです。
https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp
普通のテキスト
https://miyakawa.me/2018/09/13/3865/
最後のテキスト"""
    
    app.logger.info("🔍 Debug Filter: フィルターテスト開始")
    try:
        processed_text = sns_embed_filter(test_text)
        app.logger.info(f"✅ Debug Filter: 処理完了、結果の長さ {len(processed_text)} 文字")
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>Template Filter Debug Test</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .debug-info {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; }}
        .content {{ line-height: 1.6; }}
        pre {{ background: #f0f0f0; padding: 10px; border-radius: 4px; overflow-x: auto; white-space: pre-wrap; }}
    </style>
</head>
<body>
    <h1>Template Filter Debug Test</h1>
    
    <div class="debug-info">
        <h3>元のテキスト:</h3>
        <pre>{test_text}</pre>
    </div>
    
    <div class="debug-info">
        <h3>処理後のテキスト:</h3>
        <div class="content">{processed_text}</div>
    </div>
    
    <div class="debug-info">
        <h3>処理後のHTMLソース:</h3>
        <pre>{processed_text.replace('<', '&lt;').replace('>', '&gt;')}</pre>
    </div>
</body>
</html>"""
    except Exception as e:
        app.logger.error(f"🚨 Debug Filter Error: {str(e)}")
        return f"""<!DOCTYPE html>
<html>
<head><title>Filter Debug Error</title></head>
<body>
    <h1>Filter Debug Error</h1>
    <p><strong>Error:</strong> {str(e)}</p>
    <p><a href="/debug_filter">Try Again</a></p>
</body>
</html>"""

# === メールアドレス変更確認処理 ===

@app.route('/confirm_email_change/<token>')
def confirm_email_change(token):
    """メールアドレス変更確認処理"""
    try:
        # トークン検証
        change_request = EmailChangeRequest.verify_token(token)
        
        if not change_request:
            flash('無効または期限切れの確認リンクです。', 'danger')
            return redirect(url_for('landing'))
        
        # ユーザー取得
        user = db.session.get(User, change_request.user_id)
        if not user:
            flash('ユーザーが見つかりません。', 'danger')
            return redirect(url_for('landing'))
        
        # メールアドレス重複チェック（再確認）
        existing_user = db.session.execute(
            select(User).where(User.email == change_request.new_email)
        ).scalar_one_or_none()
        
        if existing_user:
            flash('そのメールアドレスは既に使用されています。', 'danger')
            return redirect(url_for('landing'))
        
        # メールアドレス変更実行
        old_email = user.email
        user.email = change_request.new_email
        
        # 変更要求を確認済みにマーク
        change_request.is_verified = True
        change_request.verified_at = datetime.utcnow()
        
        db.session.commit()
        
        # ログ記録
        current_app.logger.info(f'Email changed from {old_email} to {user.email} for user {user.id}')
        
        # 成功メッセージ
        flash(f'メールアドレスを {user.email} に変更しました。', 'success')
        
        # ログインページにリダイレクト（セキュリティのため再ログインを促す）
        return redirect(url_for('login'))
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Email change confirmation error: {e}')
        flash('メールアドレス変更中にエラーが発生しました。', 'danger')
        return redirect(url_for('landing'))


@app.route('/debug/sns-test')
def debug_sns_test():
    """SNS埋込のデバッグテスト"""
    # OGPキャッシュをクリア
    from seo import ogp_cache
    ogp_cache.clear()
    current_app.logger.debug("🗑️ OGP cache cleared")
    
    test_content = """TwitterのURL:
https://x.com/miyakawa2449/status/1953377889820561624

ブログのURL:
https://miyakawa.me/2023/03/27/9324/

YouTubeのURL:
https://www.youtube.com/watch?v=xvFZjo5PgG0"""
    
    current_app.logger.debug(f"🔍 SNS test input: {test_content}")
    result = process_sns_auto_embed(test_content)
    current_app.logger.debug(f"✅ SNS test output length: {len(result)}")
    
    return f"""<html><head><title>SNS Test</title></head><body>
    <h1>SNS Embed Test (Cache Cleared)</h1>
    <h2>Original:</h2><pre>{test_content}</pre>
    <h2>Processed:</h2><div>{result}</div>
    </body></html>"""

if __name__ == '__main__':
    # 本番環境では通常WSGI サーバー（Gunicorn等）を使用
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug)

