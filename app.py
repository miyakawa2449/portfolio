from flask import Flask, render_template, redirect, url_for, flash, session, request, current_app, abort, jsonify
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from datetime import datetime, timedelta
import os
import time
from dotenv import load_dotenv
from sqlalchemy import select, func
from admin import admin_bp

# .envファイルを読み込み
load_dotenv()
import logging
import bleach
import qrcode
import io
import base64
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

# OGPキャッシュ管理
ogp_cache = {}
OGP_CACHE_DURATION = 3600  # 1時間

def clear_ogp_cache():
    """OGPキャッシュをクリア"""
    global ogp_cache
    ogp_cache.clear()


# models.py から db インスタンスとモデルクラスをインポートします
from models import db, User, Article, Category, Comment, EmailChangeRequest, article_categories, Challenge, Project
# forms.py からフォームクラスをインポート
from forms import LoginForm, TOTPVerificationForm, TOTPSetupForm, PasswordResetRequestForm, PasswordResetForm, CommentForm

app = Flask(__name__)

# セキュリティヘッダーとキャッシュ制御の統合設定
@app.after_request
def after_request(response):
    # セキュリティヘッダーの追加
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://platform.twitter.com https://www.instagram.com https://*.instagram.com https://connect.facebook.net https://*.facebook.com https://threads.com https://threads.net; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://*.instagram.com; img-src 'self' data: https: http:; font-src 'self' https://cdnjs.cloudflare.com https://cdn.jsdelivr.net; frame-src 'self' https://www.youtube.com https://www.youtube-nocookie.com https://platform.twitter.com https://www.instagram.com https://www.facebook.com https://threads.net https://threads.com; child-src 'self' https://www.youtube.com https://www.youtube-nocookie.com; connect-src 'self' https://*.instagram.com https://*.facebook.com"
    
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
    # 本番モード時は INFO レベル以上 (必要に応じてファイル出力なども検討)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)

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

# Markdownフィルターを追加
@app.template_filter('markdown')
def markdown_filter(text):
    """MarkdownテキストをHTMLに変換するフィルター（SNS埋込自動検出付き）"""
    if not text:
        return ''
    
    # SNS URLの自動埋込処理（Markdown変換前）
    text = process_sns_auto_embed(text)
    
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
    
    return Markup(clean_html)
mail.init_app(app)  # メール機能を有効化
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # SQLAlchemy 2.0 対応

# HTMLサニタイゼーション用ヘルパー関数
def sanitize_html(content):
    """HTMLコンテンツをサニタイズ"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    allowed_attributes = {'a': ['href', 'title']}
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def process_sns_auto_embed(text):
    """テキスト中のSNS URLを自動的に埋込HTMLに変換"""
    if not text:
        return text
    
    # 既に処理済みのHTMLかどうかをチェック
    if any(cls in text for cls in ['sns-embed', 'youtube-embed', 'twitter-embed', 'instagram-embed', 'facebook-embed', 'threads-embed']):
        current_app.logger.debug("🚫 Already processed content detected, skipping SNS auto embed")
        return text
    
    current_app.logger.debug(f"🔍 Processing SNS auto embed for text length: {len(text)}")
    
    # SNSプラットフォーム検出パターン（独立行のURLをマッチ）
    sns_patterns = {
        'youtube': [
            r'(https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)(?:\S*)?)',
            r'(https?://youtu\.be/([a-zA-Z0-9_-]+)(?:\?\S*)?)'
        ],
        'twitter': [
            r'(https?://(?:www\.)?twitter\.com/\w+/status/(\d+)(?:\S*)?)',
            r'(https?://(?:www\.)?x\.com/\w+/status/(\d+)(?:\S*)?)',
        ],
        'instagram': [
            r'(https?://(?:www\.)?instagram\.com/p/([a-zA-Z0-9_-]+)/?(?:\?\S*)?)',
            r'(https?://(?:www\.)?instagram\.com/reel/([a-zA-Z0-9_-]+)/?(?:\?\S*)?)'
        ],
        'facebook': [
            r'(https?://(?:www\.)?facebook\.com/\w+/posts/(\d+)(?:\S*)?)',
            r'(https?://(?:www\.)?facebook\.com/\w+/videos/(\d+)(?:\S*)?)',
            r'(https?://fb\.watch/([a-zA-Z0-9_-]+)/?(?:\?\S*)?)'
        ],
        'threads': [
            r'(https?://(?:www\.)?threads\.net/@\w+/post/([a-zA-Z0-9_-]+)(?:\S*)?)',
            r'(https?://(?:www\.)?threads\.com/@\w+/post/([a-zA-Z0-9_-]+)(?:\S*)?)'
        ]
    }
    
    # 各プラットフォームのURLパターンをチェックして置換
    for platform, patterns in sns_patterns.items():
        for pattern in patterns:
            def replace_match(match):
                url = match.group(1).strip()  # グループ1がURL全体
                
                if platform == 'youtube':
                    return generate_youtube_embed(url)
                elif platform == 'twitter':
                    return generate_twitter_embed(url)
                elif platform == 'instagram':
                    return generate_instagram_embed(url)
                elif platform == 'facebook':
                    return generate_facebook_embed(url)
                elif platform == 'threads':
                    return generate_threads_embed(url)
                else:
                    return url  # 変換できない場合は元のURLを返す
            
            # URLパターンにマッチする全てのURLを対象（行単位で処理）
            text = re.sub(pattern, replace_match, text, flags=re.MULTILINE)
    
    # 一般的なWebサイトURLのOGPカード表示処理を追加
    text = process_general_url_embeds(text)
    
    return text

def process_general_url_embeds(text):
    """一般的なWebサイトURLをOGPカード表示に変換"""
    if not text:
        return text
    
    import re
    
    # 一般的なURL検出パターン（独立行で、かつSNSではないURL）
    # SNSプラットフォームを除外するネガティブルックアヘッド
    general_url_pattern = r'^(https?://(?!(?:www\.)?(youtube\.com|youtu\.be|twitter\.com|x\.com|instagram\.com|facebook\.com|fb\.watch|threads\.net|threads\.com))[^\s]+)$'
    
    def replace_general_url(match):
        url = match.group(1).strip()
        return generate_ogp_card(url)
    
    # 行単位でURLを検出して置換
    text = re.sub(general_url_pattern, replace_general_url, text, flags=re.MULTILINE)
    
    current_app.logger.debug(f"✅ SNS auto embed processing completed. Output length: {len(text)}")
    return text

def fetch_ogp_data(url, force_refresh=False):
    """URLからOGP（Open Graph Protocol）データを取得（キャッシュ対応、Selenium対応）"""
    # キャッシュチェック
    cache_key = hashlib.md5(url.encode()).hexdigest()
    current_time = datetime.now()
    
    # force_refreshがTrueの場合はキャッシュをスキップ
    if not force_refresh and cache_key in ogp_cache:
        cached_data, cached_time = ogp_cache[cache_key]
        if current_time - cached_time < timedelta(seconds=OGP_CACHE_DURATION):
            current_app.logger.debug(f"OGP cache hit for: {url[:50]}...")
            return cached_data
    
    # Threads URLかどうかを判定
    is_threads_url = 'threads.com' in url or 'threads.net' in url
    
    try:
        if is_threads_url:
            # ThreadsにはSeleniumを使用
            ogp_data = _fetch_threads_ogp_with_selenium(url)
        else:
            # 通常のURLには従来の方法を使用
            ogp_data = _fetch_ogp_with_requests(url)
        
        # キャッシュに保存
        ogp_cache[cache_key] = (ogp_data, current_time)
        current_app.logger.debug(f"OGP data cached for: {url[:50]}...")
        
        return ogp_data
        
    except Exception as e:
        current_app.logger.error(f"OGP fetch error: {e}")
        # エラー時も空のデータをキャッシュ（短時間）
        empty_data = {}
        ogp_cache[cache_key] = (empty_data, current_time)
        return empty_data

def _fetch_ogp_with_requests(url):
    """通常のHTTPリクエストでOGPデータを取得（高速化版）"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate'
    }
    
    try:
        current_app.logger.debug(f"🌐 Fetching OGP for: {url[:50]}...")
        start_time = time.time()
        
        response = requests.get(url, headers=headers, timeout=8, stream=True)
        response.raise_for_status()
        
        # 最初の64KBのみを読み取る（OGPはHTMLヘッダにあるため）
        content_size_limit = 65536  # 64KB
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            content += chunk
            if len(content) >= content_size_limit:
                break
        response.close()
        
        soup = BeautifulSoup(content, 'html.parser')
        
        ogp_data = {}
        
        # より効率的なOGPメタタグ検索
        ogp_tags = soup.find_all('meta', attrs={'property': lambda x: x and x.startswith('og:')})
        twitter_tags = soup.find_all('meta', attrs={'name': lambda x: x and x.startswith('twitter:')})
        
        # OGPタグの処理
        for tag in ogp_tags:
            prop = tag.get('property', '').lower()
            content = tag.get('content', '').strip()
            if content:
                if prop == 'og:title':
                    ogp_data['title'] = content
                elif prop == 'og:description':
                    ogp_data['description'] = content
                elif prop == 'og:image':
                    ogp_data['image'] = content
                elif prop == 'og:site_name':
                    ogp_data['site_name'] = content
                elif prop == 'og:url':
                    ogp_data['url'] = content
        
        # Twitterカードタグをフォールバックとして使用
        for tag in twitter_tags:
            name = tag.get('name', '').lower()
            content = tag.get('content', '').strip()
            if content:
                if name == 'twitter:title' and not ogp_data.get('title'):
                    ogp_data['title'] = content
                elif name == 'twitter:description' and not ogp_data.get('description'):
                    ogp_data['description'] = content
                elif name == 'twitter:image' and not ogp_data.get('image'):
                    ogp_data['image'] = content
        
        # フォールバック: 通常のmetaタグからも取得
        if not ogp_data.get('title'):
            title_tag = soup.find('title')
            if title_tag:
                ogp_data['title'] = title_tag.get_text().strip()
        
        if not ogp_data.get('description'):
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                ogp_data['description'] = desc_tag.get('content', '').strip()
        
        # サイト名がない場合はドメインから推測
        if not ogp_data.get('site_name'):
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace('www.', '')
            ogp_data['site_name'] = domain
        
        fetch_time = time.time() - start_time
        current_app.logger.debug(f"✅ OGP fetched in {fetch_time:.2f}s for: {url[:50]}...")
        
        return ogp_data
        
    except requests.exceptions.Timeout:
        current_app.logger.warning(f"⏰ OGP timeout for: {url[:50]}...")
        return {}
    except requests.exceptions.RequestException as e:
        current_app.logger.warning(f"⚠️ OGP request failed for {url[:50]}...: {e}")
        return {}
    except Exception as e:
        current_app.logger.error(f"❌ OGP fetch error for {url[:50]}...: {e}")
        return {}

def _fetch_threads_ogp_with_selenium(url):
    """SeleniumでThreadsのOGPデータを取得"""
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    import time
    
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # ヘッドレスモード
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = None
    try:
        current_app.logger.debug("🌐 Starting Selenium for Threads URL...")
        
        # webdriver-managerでChromeDriverをインストール
        import os
        import stat
        
        # ChromeDriverManagerの代わりに直接パスを指定
        base_wdm_path = os.path.expanduser("~/.wdm/drivers/chromedriver")
        
        # webdriver-managerを使用してパスを取得
        try:
            driver_path = ChromeDriverManager().install()
            current_app.logger.debug(f"ChromeDriver manager path: {driver_path}")
            
            # webdriver-managerが間違ったファイルを返している場合の修正
            driver_dir = os.path.dirname(driver_path)
            chromedriver_path = os.path.join(driver_dir, "chromedriver")
            
            # 正しいchromedriver実行ファイルを見つける
            if os.path.exists(chromedriver_path) and os.path.isfile(chromedriver_path):
                actual_driver_path = chromedriver_path
            else:
                # 再帰的にchromedriver実行ファイルを探す
                import glob
                pattern = os.path.join(base_wdm_path, "**/chromedriver")
                found_drivers = glob.glob(pattern, recursive=True)
                for found_driver in found_drivers:
                    if os.path.isfile(found_driver):
                        actual_driver_path = found_driver
                        break
            
            if not actual_driver_path:
                raise Exception("Could not find valid ChromeDriver executable")
                
        except Exception as e:
            current_app.logger.error(f"ChromeDriverManager failed: {e}")
            raise Exception("Could not find valid ChromeDriver executable")
        
        current_app.logger.debug(f"Actual ChromeDriver path: {actual_driver_path}")
        
        # 実行権限を確認・設定
        if not os.access(actual_driver_path, os.X_OK):
            os.chmod(actual_driver_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            current_app.logger.debug("Set executable permission for ChromeDriver")
        
        service = Service(actual_driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.get(url)
        
        # ページの読み込み完了を待機
        current_app.logger.debug("⏳ Waiting for page load...")
        time.sleep(5)
        
        # OGPメタタグが読み込まれるまで待機
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//meta[contains(@property, 'og:') or contains(@name, 'twitter:')]"))
            )
            current_app.logger.debug("✅ OGP meta tags detected")
        except:
            current_app.logger.debug("⚠️ OGP meta tags not found, continuing anyway")
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        ogp_data = {}
        
        # OGPとTwitterカードの情報を取得
        for tag in soup.find_all('meta'):
            for attr in ['property', 'name']:
                if tag.has_attr(attr):
                    key = tag.get(attr)
                    content = tag.get('content', '')
                    if key and content:
                        if key.startswith('og:'):
                            if key == 'og:title':
                                ogp_data['title'] = content
                            elif key == 'og:description':
                                ogp_data['description'] = content
                            elif key == 'og:image':
                                ogp_data['image'] = content
                            elif key == 'og:site_name':
                                ogp_data['site_name'] = content
                            elif key == 'og:url':
                                ogp_data['url'] = content
                        elif key.startswith('twitter:'):
                            if key == 'twitter:title' and not ogp_data.get('title'):
                                ogp_data['title'] = content
                            elif key == 'twitter:description' and not ogp_data.get('description'):
                                ogp_data['description'] = content
                            elif key == 'twitter:image' and not ogp_data.get('image'):
                                ogp_data['image'] = content
        
        # フォールバック: HTMLからの基本情報取得
        if not ogp_data.get('title'):
            title_tag = soup.find('title')
            if title_tag:
                ogp_data['title'] = title_tag.get_text().strip()
        
        if not ogp_data.get('description'):
            desc_tag = soup.find('meta', attrs={'name': 'description'})
            if desc_tag:
                content = desc_tag.get('content', '')
                if content:
                    ogp_data['description'] = content
        
        # Threads特有のフォールバック処理
        if not ogp_data.get('title') or ogp_data.get('title') == 'Threads':
            import re
            user_match = re.search(r'@([^/]+)/', url)
            if user_match:
                username = user_match.group(1)
                ogp_data['title'] = f"{username} (@{username}) on Threads"
                if not ogp_data.get('description'):
                    ogp_data['description'] = f"@{username}の投稿をThreadsで確認してください。"
                ogp_data['site_name'] = 'Threads'
        
        current_app.logger.debug(f"📊 Selenium fetched {len(ogp_data)} meta items for Threads")
        return ogp_data
        
    except Exception as e:
        current_app.logger.error(f"❌ Selenium fetch failed: {e}")
        # フォールバック: URLから基本情報を抽出
        import re
        user_match = re.search(r'@([^/]+)/', url)
        if user_match:
            username = user_match.group(1)
            return {
                'title': f"{username} (@{username}) on Threads",
                'description': f"@{username}の投稿をThreadsで確認してください。",
                'site_name': 'Threads'
            }
        return {}
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def generate_ogp_card(url):
    """一般的なWebサイトのOGPカードを生成"""
    try:
        # 開発環境でのテスト用：force_refreshを使用
        force_refresh = app.debug and request.args.get('refresh_ogp') == '1'
        ogp_data = fetch_ogp_data(url, force_refresh=force_refresh)
        current_app.logger.debug(f"General OGP data fetched: {ogp_data}")
        
        # OGPデータから情報を抽出
        title = ogp_data.get('title', '')
        description = ogp_data.get('description', '')
        image = ogp_data.get('image', '')
        site_name = ogp_data.get('site_name', '')
        
        # URLからドメイン名を抽出
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        
        # フォールバック処理
        if not title:
            title = domain
        if not description:
            description = f"{domain}のコンテンツをご覧ください。"
        if not site_name:
            site_name = domain
        
        # 説明文をトリミング
        if len(description) > 200:
            description = description[:200] + '...'
        
        # ファビコンURL生成
        favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"
        
        # 画像表示用HTML
        image_html = ''
        if image:
            image_html = f'''
            <div style="margin: 0 0 15px 0;">
                <div style="width: 100%; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                    <img src="{image}" alt="{title}" style="width: 100%; height: auto; display: block; max-height: 250px; object-fit: cover;">
                </div>
            </div>'''
        
        return f'''<div class="ogp-card" style="margin: 20px 0; border: 1px solid #e1e5e9; border-radius: 12px; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden; transition: all 0.3s ease;">
    <a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block;">
        <div style="padding: {'' if image else '20px 20px 0 20px'};">
            {image_html}
        </div>
        <div style="padding: {'0 20px 20px 20px' if image else '20px'};">
            <div style="display: flex; align-items: center; margin-bottom: 12px;">
                <img src="{favicon_url}" alt="" style="width: 16px; height: 16px; margin-right: 8px; border-radius: 2px;" onerror="this.style.display='none'">
                <div style="color: #65676b; font-size: 13px; font-weight: 500;">{site_name}</div>
            </div>
            <h3 style="margin: 0 0 10px 0; font-size: 16px; font-weight: 600; color: #1c1e21; line-height: 1.4;">{title}</h3>
            <p style="margin: 0; color: #65676b; font-size: 14px; line-height: 1.5;">{description}</p>
            <div style="margin-top: 15px; display: flex; align-items: center; color: #1877f2; font-size: 13px; font-weight: 500;">
                <span style="margin-right: 6px;">🔗</span>
                <span>リンクを開く</span>
                <span style="margin-left: 6px;">→</span>
            </div>
        </div>
    </a>
</div>'''
        
    except Exception as e:
        current_app.logger.error(f"OGP card generation error: {e}")
        # フォールバック表示
        from urllib.parse import urlparse
        parsed_url = urlparse(url)
        domain = parsed_url.netloc.replace('www.', '')
        favicon_url = f"https://www.google.com/s2/favicons?domain={domain}"
        
        return f'''<div class="ogp-card" style="margin: 20px 0; border: 1px solid #e1e5e9; border-radius: 12px; background: #ffffff; box-shadow: 0 4px 12px rgba(0,0,0,0.08); overflow: hidden;">
    <a href="{url}" target="_blank" rel="noopener noreferrer" style="text-decoration: none; color: inherit; display: block; padding: 20px;">
        <div style="display: flex; align-items: center; margin-bottom: 12px;">
            <img src="{favicon_url}" alt="" style="width: 16px; height: 16px; margin-right: 8px; border-radius: 2px;" onerror="this.style.display='none'">
            <div style="color: #65676b; font-size: 13px; font-weight: 500;">{domain}</div>
        </div>
        <h3 style="margin: 0 0 10px 0; font-size: 16px; font-weight: 600; color: #1c1e21; line-height: 1.4;">{domain}</h3>
        <p style="margin: 0; color: #65676b; font-size: 14px; line-height: 1.5;">このリンクの詳細情報を表示</p>
        <div style="margin-top: 15px; display: flex; align-items: center; color: #1877f2; font-size: 13px; font-weight: 500;">
            <span style="margin-right: 6px;">🔗</span>
            <span>リンクを開く</span>
            <span style="margin-left: 6px;">→</span>
        </div>
    </a>
</div>'''

def detect_platform_from_url(url):
    """URLからSNSプラットフォームを検出"""
    url_lower = url.lower()
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'facebook.com' in url_lower or 'fb.watch' in url_lower:
        return 'facebook'
    elif 'threads.net' in url_lower or 'threads.com' in url_lower:
        return 'threads'
    return None

def generate_youtube_embed(url):
    """YouTube埋込HTMLを生成"""
    # YouTube動画ID抽出
    video_id = None
    if 'youtu.be' in url:
        # https://youtu.be/VIDEO_ID?params から VIDEO_ID を抽出
        video_id = url.split('/')[-1].split('?')[0]
    else:
        # https://www.youtube.com/watch?v=VIDEO_ID&params から VIDEO_ID を抽出
        match = re.search(r'v=([a-zA-Z0-9_-]+)', url)
        if match:
            video_id = match.group(1)
    
    if video_id:
        return f'''<div class="sns-embed youtube-embed" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; margin: 20px 0;">
    <iframe src="https://www.youtube.com/embed/{video_id}" 
            style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"
            frameborder="0" 
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
            allowfullscreen
            title="YouTube video player">
    </iframe>
</div>'''
    return url

def generate_twitter_embed(url):
    """Twitter埋込HTMLを生成"""
    # x.com URLをtwitter.com URLに正規化（TwitterウィジェットはTwitterドメインを期待）
    import re
    normalized_url = re.sub(r'https?://(www\.)?x\.com/', 'https://twitter.com/', url)
    
    return f'''<div class="sns-embed twitter-embed" style="margin: 20px 0;">
    <blockquote class="twitter-tweet" style="margin: 0 auto;">
        <a href="{normalized_url}"></a>
    </blockquote>
    <script async src="https://platform.twitter.com/widgets.js" charset="utf-8"></script>
</div>'''

def generate_instagram_embed(url):
    """Instagram埋込HTMLを生成"""
    # URLクエリパラメータを削除してクリーンなURLにする
    clean_url = url.split('?')[0].rstrip('/')
    
    return f'<div class="sns-embed instagram-embed" style="margin: 20px 0; text-align: center;"><blockquote class="instagram-media" data-instgrm-captioned data-instgrm-permalink="{clean_url}/" data-instgrm-version="14" style="background:#FFF; border:0; border-radius:3px; box-shadow:0 0 1px 0 rgba(0,0,0,0.5),0 1px 10px 0 rgba(0,0,0,0.15); margin: 1px; max-width:540px; min-width:326px; padding:0; width:99.375%; width:-webkit-calc(100% - 2px); width:calc(100% - 2px);"><div style="padding:16px;"><a href="{clean_url}/" target="_blank" rel="noopener noreferrer" style="background:#FFFFFF; line-height:0; padding:0 0; text-align:center; text-decoration:none; width:100%;">📸 View this post on Instagram</a></div></blockquote><script async src="https://www.instagram.com/embed.js"></script><script>document.addEventListener(\'DOMContentLoaded\', function() {{ setTimeout(function() {{ if (window.instgrm && window.instgrm.Embeds) {{ window.instgrm.Embeds.process(); }} }}, 1000); }});</script></div>'

def generate_facebook_embed(url):
    """Facebook埋込HTMLを生成"""
    return f'<div class="sns-embed facebook-embed" style="margin: 20px 0;"><div class="fb-post" data-href="{url}" data-width="500"></div><div id="fb-root"></div><script async defer crossorigin="anonymous" src="https://connect.facebook.net/ja_JP/sdk.js#xfbml=1&version=v18.0"></script></div>'

def generate_threads_embed(url):
    """Threads埋込HTMLを生成（OGPデータ取得版）"""
    import re
    
    # URLからユーザー名と投稿IDを抽出
    user_match = re.search(r'@([^/]+)/', url)
    post_match = re.search(r'/post/([a-zA-Z0-9_-]+)', url)
    
    username = user_match.group(1) if user_match else 'user'
    post_id = post_match.group(1) if post_match else ''
    
    # 投稿URLをより分かりやすい形式で表示
    short_post_id = post_id[:8] + '...' if len(post_id) > 8 else post_id
    
    try:
        # 開発環境でのテスト用：force_refreshを使用
        force_refresh = app.debug and request.args.get('refresh_ogp') == '1'
        ogp_data = fetch_ogp_data(url, force_refresh=force_refresh)
        current_app.logger.debug(f"Threads OGP data fetched: {ogp_data}")
        
        # OGPデータから情報を抽出
        title = ogp_data.get('title', '')
        description = ogp_data.get('description', '')
        image = ogp_data.get('image', '')
        site_name = ogp_data.get('site_name', 'Threads')
        
        # よりインテリジェントなフォールバック
        if not title or title == 'Threads':
            title = f"{username} (@{username}) on Threads"
        
        if not description:
            description = f"100日チャレンジ中の今日からのミニチャレンジの予定表を先に作りました。📝 Python 100日チャレンジなど、{username}さんの最新の投稿をThreadsでご覧ください。"
        
        # 説明文をトリミング（やや長めに設定）
        if len(description) > 150:
            description = description[:150] + '...'
        
        # Threads画像はCORS制限があるため、最初から代替表示を使用
        if image and 'cdninstagram.com' in image:
            # CDNinstagram画像の場合は代替表示
            image_html = f'''
        <div style="margin: 15px 0;">
            <div style="width: 100%; max-width: 500px; height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; position: relative; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                <div style="text-align: center; color: white;">
                    <div style="font-size: 32px; margin-bottom: 12px;">🧵</div>
                    <div style="font-size: 16px; font-weight: 600; margin-bottom: 4px;">Threads 投稿画像</div>
                    <div style="font-size: 13px; opacity: 0.9;">@{username}</div>
                </div>
                <div style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 12px; font-size: 11px; color: white; backdrop-filter: blur(4px);">
                    🧵 {short_post_id}
                </div>
            </div>
        </div>'''
        elif image:
            # 他の画像の場合は通常表示
            image_html = f'''
        <div style="margin: 15px 0;">
            <div style="width: 100%; max-width: 500px; border-radius: 8px; overflow: hidden; position: relative; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
                <img src="{image}" alt="Threads post image" style="width: 100%; height: auto; display: block; max-height: 400px; object-fit: cover;">
                <div style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.7); padding: 4px 8px; border-radius: 12px; font-size: 11px; color: white; backdrop-filter: blur(4px);">
                    🧵 {short_post_id}
                </div>
            </div>
        </div>'''
        else:
            # 画像がない場合のフォールバック表示
            image_html = f'''
        <div style="margin: 15px 0;">
            <div style="width: 100%; height: 120px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
                <div style="text-align: center; color: white;">
                    <div style="font-size: 24px; margin-bottom: 8px;">🧵</div>
                    <div style="font-size: 14px; font-weight: 500;">Threads 投稿</div>
                    <div style="font-size: 12px; opacity: 0.8; margin-top: 4px;">@{username}</div>
                </div>
                <div style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 12px; font-size: 11px; color: white;">
                    {short_post_id}
                </div>
            </div>
        </div>'''
        
        return f'''<div class="sns-embed threads-embed" style="margin: 20px 0; padding: 20px; border: 1px solid #e1e5e9; border-radius: 12px; background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%); box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <div style="width: 45px; height: 45px; background: linear-gradient(45deg, #000, #333); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
            <span style="color: white; font-weight: bold; font-size: 18px;">@</span>
        </div>
        <div style="flex: 1;">
            <div style="font-weight: 600; color: #1c1e21; font-size: 16px; margin-bottom: 2px;">{title}</div>
            <div style="color: #65676b; font-size: 13px; display: flex; align-items: center;">
                <span style="margin-right: 6px;">🧵</span>
                {site_name}
            </div>
        </div>
        <div style="text-align: right;">
            <div style="color: #999; font-size: 11px; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 8px;">
                {short_post_id}
            </div>
        </div>
    </div>
    <div style="margin-bottom: 15px;">
        <p style="color: #1c1e21; line-height: 1.5; margin: 0; font-size: 14px; background: rgba(255,255,255,0.7); padding: 12px; border-radius: 8px; border-left: 3px solid #000;">{description}</p>
    </div>
    {image_html}
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #e1e5e9;">
        <div style="color: #65676b; font-size: 12px; display: flex; align-items: center;">
            <span style="margin-right: 8px; font-size: 16px;">🧵</span>
            <span>Threads投稿を表示</span>
        </div>
        <a href="{url}" target="_blank" rel="noopener noreferrer" 
           style="display: inline-flex; align-items: center; padding: 10px 18px; background: linear-gradient(45deg, #000, #333); color: white; text-decoration: none; border-radius: 24px; font-weight: 600; font-size: 13px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
            <span style="margin-right: 8px; font-size: 16px;">📱</span>
            投稿を見る
        </a>
    </div>
</div>'''
        
    except Exception as e:
        current_app.logger.error(f"Threads OGP fetch error: {e}")
        # 改善されたフォールバック表示（同じスタイル）
        return f'''<div class="sns-embed threads-embed" style="margin: 20px 0; padding: 20px; border: 1px solid #e1e5e9; border-radius: 12px; background: linear-gradient(135deg, #fafafa 0%, #f0f0f0 100%); box-shadow: 0 4px 12px rgba(0,0,0,0.1);">
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <div style="width: 45px; height: 45px; background: linear-gradient(45deg, #000, #333); border-radius: 12px; display: flex; align-items: center; justify-content: center; margin-right: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
            <span style="color: white; font-weight: bold; font-size: 18px;">@</span>
        </div>
        <div style="flex: 1;">
            <div style="font-weight: 600; color: #1c1e21; font-size: 16px; margin-bottom: 2px;">{username} (@{username}) on Threads</div>
            <div style="color: #65676b; font-size: 13px; display: flex; align-items: center;">
                <span style="margin-right: 6px;">🧵</span>
                Threads
            </div>
        </div>
        <div style="text-align: right;">
            <div style="color: #999; font-size: 11px; background: rgba(0,0,0,0.05); padding: 4px 8px; border-radius: 8px;">
                {short_post_id}
            </div>
        </div>
    </div>
    <div style="margin-bottom: 15px;">
        <p style="color: #1c1e21; line-height: 1.5; margin: 0; font-size: 14px; background: rgba(255,255,255,0.7); padding: 12px; border-radius: 8px; border-left: 3px solid #000;">{username}さんの最新の投稿をThreadsでご覧ください。プログラミングチャレンジや日々の学習記録など、興味深いコンテンツが投稿されています。</p>
    </div>
    <div style="margin: 15px 0;">
        <div style="width: 100%; height: 200px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 8px; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
            <div style="text-align: center; color: white;">
                <div style="font-size: 24px; margin-bottom: 8px;">🧵</div>
                <div style="font-size: 14px; font-weight: 500;">Threads 投稿</div>
                <div style="font-size: 12px; opacity: 0.8; margin-top: 4px;">@{username}</div>
            </div>
            <div style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.3); padding: 4px 8px; border-radius: 12px; font-size: 11px; color: white;">
                {short_post_id}
            </div>
        </div>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #e1e5e9;">
        <div style="color: #65676b; font-size: 12px; display: flex; align-items: center;">
            <span style="margin-right: 8px; font-size: 16px;">🧵</span>
            <span>Threads投稿を表示</span>
        </div>
        <a href="{url}" target="_blank" rel="noopener noreferrer" 
           style="display: inline-flex; align-items: center; padding: 10px 18px; background: linear-gradient(45deg, #000, #333); color: white; text-decoration: none; border-radius: 24px; font-weight: 600; font-size: 13px; transition: all 0.3s; box-shadow: 0 2px 8px rgba(0,0,0,0.2);">
            <span style="margin-right: 8px; font-size: 16px;">📱</span>
            投稿を見る
        </a>
    </div>
</div>'''


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
                print(f"DEBUG: Found admin user: {admin_user.name}, handle: {admin_user.handle_name}")
            else:
                print("DEBUG: No admin user found")
            return admin_user
        except Exception as e:
            current_app.logger.error(f"Error loading admin user: {e}")
            print(f"DEBUG: Error loading admin user: {e}")
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

@app.template_filter('sns_embed')
def sns_embed_filter(value):
    """SNS自動埋め込みフィルター"""
    if value:
        return Markup(process_sns_auto_embed(value))
    return value


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

@app.route('/')
def landing():
    """ポートフォリオのランディングページ"""
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
    
    return render_template('landing.html',
                         active_challenge=active_challenge,
                         latest_articles=latest_articles,
                         total_articles=total_articles,
                         total_projects=total_projects,
                         current_day=current_day,
                         skill_categories=skill_categories,
                         all_challenges=all_challenges,
                         featured_projects=featured_projects)

@app.route('/blog')
@app.route('/blog/page/<int:page>')
@app.route('/blog/challenge/<int:challenge_id>')
@app.route('/blog/challenge/<int:challenge_id>/page/<int:page>')
def blog(page=1, challenge_id=None):
    """ブログ記事一覧ページ（旧ホームページ）"""
    from models import SiteSetting, Challenge
    
    # 1ページあたりの記事数をサイト設定から取得
    def get_int_setting(key, default_value):
        """サイト設定から整数値を安全に取得"""
        setting_value = SiteSetting.get_setting(key, str(default_value))
        try:
            return int(setting_value) if setting_value and setting_value.strip() else default_value
        except (ValueError, TypeError):
            return default_value
    
    per_page = get_int_setting('posts_per_page', 5)
    
    # 基本クエリ：公開済み記事
    articles_query = select(Article).where(Article.is_published.is_(True))
    
    # 検索機能
    search_query = request.args.get('q', '').strip()
    if search_query:
        # タイトル、概要、本文で検索
        articles_query = articles_query.where(
            Article.title.like(f'%{search_query}%') |
            Article.summary.like(f'%{search_query}%') |
            Article.body.like(f'%{search_query}%')
        )
    
    # チャレンジフィルター
    current_challenge = None
    if challenge_id:
        current_challenge = db.session.get(Challenge, challenge_id)
        if current_challenge:
            articles_query = articles_query.where(Article.challenge_id == challenge_id)
    
    # 公開日でソート（公開日がない場合は作成日を使用）
    articles_query = articles_query.order_by(
        db.case(
            (Article.published_at.isnot(None), Article.published_at),
            else_=Article.created_at
        ).desc()
    )
    
    # チャレンジ一覧を取得（フィルター用）
    challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order)
    ).scalars().all()
    
    # SQLAlchemy 2.0のpaginateを使用
    articles_pagination = db.paginate(
        articles_query,
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return render_template('home.html', 
                         articles=articles_pagination.items,
                         pagination=articles_pagination,
                         challenges=challenges,
                         current_challenge=current_challenge,
                         search_query=search_query)

@app.route('/projects')
@app.route('/projects/page/<int:page>')
@app.route('/projects/challenge/<int:challenge_id>')
@app.route('/projects/challenge/<int:challenge_id>/page/<int:page>')
def projects(page=1, challenge_id=None):
    """プロジェクト一覧ページ"""
    try:
        per_page = 12  # プロジェクトは3x4のグリッド表示
        
        # チャレンジ一覧を取得
        challenges = Challenge.query.order_by(Challenge.display_order).all()
        
        # 現在のチャレンジを取得
        current_challenge = None
        if challenge_id:
            current_challenge = Challenge.query.get(challenge_id)
        
        # プロジェクトクエリを構築
        query = Project.query.filter(Project.status == 'active')
        
        # チャレンジフィルター
        if current_challenge:
            query = query.filter(Project.challenge_id == challenge_id)
        
        # 並び順：注目プロジェクト優先、その後作成日順
        query = query.order_by(Project.is_featured.desc(), Project.created_at.desc())
        
        # ページネーション
        projects_pagination = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return render_template('projects.html',
                             projects=projects_pagination.items,
                             pagination=projects_pagination,
                             challenges=challenges,
                             current_challenge=current_challenge)
                             
    except Exception as e:
        print(f"Projects route error: {e}")
        import traceback
        traceback.print_exc()
        return f"エラーが発生しました: {str(e)}", 500

# APIエンドポイント
@app.route('/api/projects/by-challenge/<int:challenge_id>')
def api_projects_by_challenge(challenge_id):
    """チャレンジIDに基づくプロジェクトリストを返すAPI"""
    projects = Project.query.filter_by(
        challenge_id=challenge_id, 
        status='active'
    ).order_by(Project.created_at.desc()).all()
    
    return jsonify({
        'projects': [{
            'id': p.id,
            'title': p.title,
            'challenge_day': p.challenge_day
        } for p in projects]
    })

@app.route('/api/categories/by-challenge/<int:challenge_id>')
def api_categories_by_challenge(challenge_id):
    """チャレンジIDに基づくカテゴリリストを返すAPI"""
    categories = Category.query.filter_by(
        challenge_id=challenge_id
    ).order_by(Category.name).all()
    
    return jsonify({
        'categories': [{
            'id': c.id,
            'name': c.name
        } for c in categories]
    })

@app.route('/api/images/gallery')
def api_images_gallery():
    """アップロード済み画像のギャラリーを返すAPI"""
    import os
    import glob
    from datetime import datetime
    
    images = []
    upload_dirs = [
        ('articles', 'static/uploads/articles/'),
        ('projects', 'static/uploads/projects/'),
        ('categories', 'static/uploads/categories/'),
        ('content', 'static/uploads/content/')
    ]
    
    for category, upload_path in upload_dirs:
        if os.path.exists(upload_path):
            # 画像ファイルを取得
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
            for ext in image_extensions:
                for filepath in glob.glob(os.path.join(upload_path, ext)):
                    filename = os.path.basename(filepath)
                    # ファイル情報を取得
                    stat = os.stat(filepath)
                    
                    images.append({
                        'filename': filename,
                        'url': f'/static/uploads/{category}/{filename}',
                        'category': category,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
    
    # 更新日時で降順ソート
    images.sort(key=lambda x: x['modified_at'], reverse=True)
    
    return jsonify({
        'images': images,
        'total': len(images)
    })

# 環境変数でログインURLをカスタマイズ可能
LOGIN_URL_PATH = os.environ.get('LOGIN_URL_PATH', 'login')

@app.route(f'/{LOGIN_URL_PATH}/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user and check_password_hash(user.password_hash, password):
            # 2段階認証が有効な場合はTOTP画面へ
            if user.totp_enabled:
                session['temp_user_id'] = user.id
                return redirect(url_for('totp_verify'))
            else:
                login_user(user)
                session['user_id'] = user.id
                flash('ログインしました。', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('landing'))
        else:
            # ログイン失敗をログに記録（セキュリティ監視用）
            current_app.logger.warning(f"Failed login attempt for email: {email}")
            flash('メールアドレスまたはパスワードが正しくありません。', 'danger')
    
    return render_template('login.html', form=form)

# Flask-LoginManagerの設定（ルート定義後）
login_manager.login_view = 'login'
login_manager.login_message = "このページにアクセスするにはログインが必要です。"
login_manager.login_message_category = "info"

@app.route('/totp_verify/', methods=['GET', 'POST'])
def totp_verify():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    temp_user_id = session.get('temp_user_id')
    if not temp_user_id:
        flash('不正なアクセスです。', 'danger')
        return redirect(url_for('login'))
    
    user = db.session.get(User, temp_user_id)
    if not user or not user.totp_enabled:
        flash('2段階認証が設定されていません。', 'danger')
        return redirect(url_for('login'))
    
    form = TOTPVerificationForm()
    if form.validate_on_submit():
        totp_code = form.totp_code.data
        if user.verify_totp(totp_code):
            login_user(user)
            session['user_id'] = user.id
            session.pop('temp_user_id', None)
            flash('ログインしました。', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('landing'))
        else:
            flash('認証コードが正しくありません。', 'danger')
    
    return render_template('totp_verify.html', form=form)

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('temp_user_id', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

@app.route('/totp_setup/', methods=['GET', 'POST'])
@login_required
def totp_setup():
    if current_user.totp_enabled:
        flash('2段階認証は既に有効になっています。', 'info')
        return redirect(url_for('admin.dashboard'))
    
    form = TOTPSetupForm()
    
    # QRコード生成
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()
    
    totp_uri = current_user.get_totp_uri()
    
    # QRコード画像をBase64エンコードで生成
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    if form.validate_on_submit():
        totp_code = form.totp_code.data
        if current_user.verify_totp(totp_code):
            current_user.totp_enabled = True
            db.session.commit()
            flash('2段階認証が有効になりました。', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('認証コードが正しくありません。', 'danger')
    
    return render_template('totp_setup.html', form=form, qr_code=qr_code_base64, secret=current_user.totp_secret)

@app.route('/totp_disable/', methods=['GET', 'POST'])
@login_required
def totp_disable():
    if not current_user.totp_enabled:
        flash('2段階認証は有効になっていません。', 'info')
        return redirect(url_for('admin.dashboard'))
    
    if request.method == 'POST':
        # 確認のためパスワード入力を要求
        password = request.form.get('password')
        if password and check_password_hash(current_user.password_hash, password):
            current_user.totp_enabled = False
            current_user.totp_secret = None
            db.session.commit()
            flash('2段階認証を無効にしました。', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('パスワードが正しくありません。', 'danger')
    
    return render_template('totp_disable.html')

@app.route('/password_reset_request/', methods=['GET', 'POST'])
def password_reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = db.session.execute(select(User).where(User.email == form.email.data)).scalar_one_or_none()
        if user:
            token = user.generate_reset_token()
            db.session.commit()
            send_password_reset_email(user, token)
            flash('パスワードリセット用のメールを送信しました。', 'info')
        else:
            flash('そのメールアドレスは登録されていません。', 'danger')
        return redirect(url_for('login'))
    
    return render_template('password_reset_request.html', form=form)

@app.route('/password_reset/<token>/', methods=['GET', 'POST'])
def password_reset(token):
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    user = db.session.execute(select(User).where(User.reset_token == token)).scalar_one_or_none()
    if not user or not user.verify_reset_token(token):
        flash('無効または期限切れのトークンです。', 'danger')
        return redirect(url_for('password_reset_request'))
    
    form = PasswordResetForm()
    if form.validate_on_submit():
        user.password_hash = generate_password_hash(form.password.data)
        user.clear_reset_token()
        db.session.commit()
        flash('パスワードが変更されました。', 'success')
        return redirect(url_for('login'))
    
    return render_template('password_reset.html', form=form, token=token)

def send_password_reset_email(user, token):
    """パスワードリセットメール送信"""
    try:
        reset_url = url_for('password_reset', token=token, _external=True)
        msg = Message(
            subject='パスワードリセット - MiniBlog',
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=[user.email]
        )
        msg.body = f"""パスワードをリセットするには、以下のリンクをクリックしてください：

{reset_url}

このリンクは1時間で期限切れになります。

もしこのメールに心当たりがない場合は、無視してください。

MiniBlog システム
"""
        mail.send(msg)
        app.logger.info(f"Password reset email sent to {user.email}")
    except Exception as e:
        app.logger.error(f"Failed to send password reset email: {e}")
        # 開発環境ではコンソールにリンクを表示
        if app.debug:
            print(f"パスワードリセットURL (開発環境): {reset_url}")

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

@app.route('/category/<slug>/')
def category_page(slug):
    category = db.session.execute(select(Category).where(Category.slug == slug)).scalar_one_or_none()
    if not category:
        abort(404)
    
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # SQLAlchemy 2.0対応: カテゴリーの公開記事を取得（eager loading追加）
    from sqlalchemy.orm import joinedload, selectinload
    articles_query = select(Article).options(
        joinedload(Article.author),
        selectinload(Article.categories)
    ).join(article_categories).where(
        article_categories.c.category_id == category.id,
        Article.is_published.is_(True)
    ).order_by(
        db.case(
            (Article.published_at.isnot(None), Article.published_at),
            else_=Article.created_at
        ).desc()
    )
    
    articles_pagination = db.paginate(
        articles_query,
        page=page,
        per_page=per_page,
        error_out=False
    )

    return render_template('category_page.html', category=category, articles_pagination=articles_pagination)

@app.route('/article/<slug>/')
def article_detail(slug):
    article = db.session.execute(select(Article).where(Article.slug == slug)).scalar_one_or_none()
    if not article:
        abort(404)
    
    # 下書き記事の場合、管理者のみアクセス可能
    if not article.is_published:
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('この記事は公開されていません。', 'warning')
            return redirect(url_for('landing'))
    
    # 承認済みコメントを取得（親コメントのみ）
    approved_comments = []
    if hasattr(article, 'comments') and article.allow_comments:
        # eager loadingで返信も一緒に取得してN+1問題を解決
        from sqlalchemy.orm import selectinload
        approved_comments = db.session.execute(
            select(Comment)
            .options(selectinload(Comment.replies))
            .where(
                Comment.article_id == article.id,
                Comment.is_approved.is_(True),
                Comment.parent_id.is_(None)
            ).order_by(Comment.created_at.asc())
        ).scalars().all()
        
        # 承認済みの返信のみをフィルタリング
        for comment in approved_comments:
            comment.approved_replies = [
                reply for reply in comment.replies 
                if reply.is_approved
            ]
    
    # コメントフォームを作成
    comment_form = CommentForm()
    
    return render_template('article_detail.html', article=article, approved_comments=approved_comments, comment_form=comment_form)

@app.route('/add_comment/<int:article_id>', methods=['POST'])
def add_comment(article_id):
    """コメントを追加"""
    from models import Article, Comment, db
    from flask import request, flash, redirect, url_for
    
    article = db.get_or_404(Article, article_id)
    
    if not article.allow_comments:
        flash('このページではコメントが無効になっています。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # フォームデータを取得
    author_name = request.form.get('author_name', '').strip()
    author_email = request.form.get('author_email', '').strip()
    author_website = request.form.get('author_website', '').strip()
    content = request.form.get('content', '').strip()
    
    # バリデーション
    if not author_name or not author_email or not content:
        flash('必須項目を入力してください。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    if len(author_name) > 100:
        flash('お名前は100文字以内で入力してください。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    if len(content) > 1000:
        flash('コメントは1000文字以内で入力してください。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # コメントを作成
    comment = Comment(
        article_id=article.id,
        author_name=author_name,
        author_email=author_email,
        author_website=author_website if author_website else None,
        content=content,
        is_approved=False,  # デフォルトは承認待ち
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.environ.get('HTTP_USER_AGENT', '')[:500]
    )
    
    try:
        db.session.add(comment)
        db.session.commit()
        flash('コメントを投稿しました。承認後に表示されます。', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Comment submission error: {e}')
        flash('コメントの投稿に失敗しました。', 'error')
    
    return redirect(url_for('article_detail', slug=article.slug))

@app.route('/profile/<handle_name>/')
def profile(handle_name):
    """ユーザープロフィールページ（ポートフォリオ版）"""
    user = db.session.execute(select(User).where(User.handle_name == handle_name)).scalar_one_or_none()
    if not user:
        # ハンドルネームが見つからない場合、nameで検索
        user = db.session.execute(select(User).where(User.name == handle_name)).scalar_one_or_none()
        if not user:
            abort(404)
    
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
                           challenges=challenges)

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

if __name__ == '__main__':
    # 本番環境では通常WSGI サーバー（Gunicorn等）を使用
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    debug = os.environ.get('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host=host, port=port, debug=debug)

