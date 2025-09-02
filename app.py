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
from landing import landing_bp
from debug import debug_bp
from filters import register_filters
from errors import errors_bp
from context import register_context_processors

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

mail.init_app(app)  # メール機能を有効化
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # SQLAlchemy 2.0 対応

# ユーティリティ関数のインポート
from utils import sanitize_html, generate_table_of_contents, add_heading_anchors, perform_search
# SEO/OGP関数のインポート  
from seo import process_sns_auto_embed, process_general_url_embeds, fetch_ogp_data, generate_ogp_card, generate_article_structured_data







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
app.register_blueprint(landing_bp)
if app.debug:
    app.register_blueprint(debug_bp)
app.register_blueprint(errors_bp)

# テンプレートフィルターとコンテキストプロセッサーを登録
register_filters(app)
register_context_processors(app)


# Flask-LoginManagerの設定（ルート定義後）
login_manager.login_view = 'auth.login'
login_manager.login_message = "このページにアクセスするにはログインが必要です。"
login_manager.login_message_category = "info"















if __name__ == '__main__':
    # 本番環境では通常WSGI サーバー（Gunicorn等）を使用
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug)

