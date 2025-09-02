"""
SEO/OGP Functions - SEO最適化とOpen Graph Protocol関連機能
"""
import re
import time
import hashlib
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup
from flask import current_app, url_for

# OGPデータキャッシュ（メモリ）
ogp_cache = {}
OGP_CACHE_DURATION = 3600  # 1時間

def process_sns_auto_embed(text):
    """テキスト中のSNS URLを自動的に埋込HTMLに変換"""
    if not text:
        return text
    
    # 既に処理済みのHTMLかどうかをチェック
    if any(cls in text for cls in ['sns-embed', 'youtube-embed', 'twitter-embed', 'instagram-embed', 'facebook-embed', 'threads-embed', 'ogp-card']):
        current_app.logger.debug("🚫 Already processed content detected, skipping SNS auto embed")
        return text
    
    current_app.logger.debug(f"🔍 Processing SNS auto embed for text length: {len(text)}")
    
    # SNSプラットフォーム検出パターン（URLをマッチ）
    sns_patterns = {
        'youtube': [
            r'(https?://(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]+)(?:\S*)?)',
            r'(https?://youtu\.be/([a-zA-Z0-9_-]+)(?:\?\S*)?)'
        ],
        'twitter': [
            r'(https?://(?:www\.)?twitter\.com/[a-zA-Z0-9_]+/status/(\d+)(?:\S*)?)',
            r'(https?://(?:www\.)?x\.com/[a-zA-Z0-9_]+/status/(\d+)(?:\S*)?)',
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
            # デバッグ: パターンマッチのテスト
            matches = re.findall(pattern, text)
            if matches:
                current_app.logger.debug(f"📱 Found {len(matches)} {platform} URLs: {matches}")
            
            def replace_match(match):
                url = match.group(1).strip()  # グループ1がURL全体
                current_app.logger.debug(f"🔄 Converting {platform} URL: {url[:50]}...")
                
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
            
            # URLパターンにマッチする全てのURLを対象
            text = re.sub(pattern, replace_match, text)
    
    # 一般的なWebサイトURLのOGPカード表示処理を追加
    text = process_general_url_embeds(text)
    
    return text

def process_general_url_embeds(text):
    """一般的なWebサイトURLをOGPカード表示に変換"""
    if not text:
        return text
    
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

def detect_platform_from_url(url):
    """URLからプラットフォームを検出"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'twitter.com' in url or 'x.com' in url:
        return 'twitter'
    elif 'instagram.com' in url:
        return 'instagram'
    elif 'facebook.com' in url or 'fb.watch' in url:
        return 'facebook'
    elif 'threads.com' in url or 'threads.net' in url:
        return 'threads'
    else:
        return 'general'

def generate_youtube_embed(url):
    """YouTube URLを埋込HTMLに変換"""
    video_id_patterns = [
        r'(?:youtube\.com/watch\?v=)([a-zA-Z0-9_-]+)',
        r'(?:youtu\.be/)([a-zA-Z0-9_-]+)'
    ]
    
    video_id = None
    for pattern in video_id_patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            break
    
    if video_id:
        return f'''<div class="sns-embed youtube-embed">
    <iframe width="100%" height="315" src="https://www.youtube-nocookie.com/embed/{video_id}" 
            title="YouTube video player" frameborder="0" allowfullscreen>
    </iframe>
</div>'''
    else:
        return f'<a href="{url}" target="_blank">{url}</a>'

def generate_twitter_embed(url):
    """Twitter/X URLを埋込HTMLに変換"""
    # JavaScript埋込の代わりにOGPカード形式を使用
    return generate_ogp_card(url)

def generate_instagram_embed(url):
    """Instagram URLを埋込HTMLに変換"""
    return f'''<div class="sns-embed instagram-embed">
    <blockquote class="instagram-media" data-instgrm-permalink="{url}">
        <a href="{url}" target="_blank">{url}</a>
    </blockquote>
    <script async src="https://www.instagram.com/embed.js"></script>
</div>'''

def generate_facebook_embed(url):
    """Facebook URLを埋込HTMLに変換"""
    return f'''<div class="sns-embed facebook-embed">
    <div class="fb-post" data-href="{url}"></div>
</div>'''

def generate_threads_embed(url):
    """Threads URLを埋込HTMLに変換"""
    return f'''<div class="sns-embed threads-embed">
    <blockquote class="threads-post">
        <a href="{url}" target="_blank">{url}</a>
    </blockquote>
</div>'''

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
    """URLのOGPカードHTMLを生成"""
    try:
        ogp_data = fetch_ogp_data(url)
        
        if not ogp_data:
            # OGPデータが取得できない場合はシンプルなリンクを返す
            return f'<a href="{url}" target="_blank" class="simple-link">{url}</a>'
        
        # サイト名の短縮表示
        site_name = ogp_data.get('site_name', '')
        if len(site_name) > 20:
            site_name = site_name[:17] + '...'
        
        # タイトルの短縮表示
        title = ogp_data.get('title', url)
        if len(title) > 80:
            title = title[:77] + '...'
        
        # 説明文の短縮表示
        description = ogp_data.get('description', '')
        if len(description) > 120:
            description = description[:117] + '...'
        
        # 画像URLの処理
        image_url = ogp_data.get('image', '')
        image_html = ''
        if image_url:
            # 相対URLの場合は絶対URLに変換
            if image_url.startswith('/'):
                from urllib.parse import urljoin
                image_url = urljoin(url, image_url)
            image_html = f'<img src="{image_url}" alt="{title}" onerror="this.style.display=\'none\'">'
        
        # OGPカードHTMLの生成
        card_html = f'''<div class="ogp-card" style="border: 1px solid #e1e8ed; border-radius: 12px; overflow: hidden; margin: 16px 0; max-width: 500px; text-decoration: none; color: inherit;">
    <a href="{url}" target="_blank" style="text-decoration: none; color: inherit; display: block;">
        {f'<div class="ogp-image" style="width: 100%; height: 200px; overflow: hidden; background: #f7f9fa;">{image_html}</div>' if image_url else ''}
        <div class="ogp-content" style="padding: 16px;">
            <div class="ogp-title" style="font-weight: bold; font-size: 16px; line-height: 1.3; margin-bottom: 8px; color: #14171a;">{title}</div>
            {f'<div class="ogp-description" style="font-size: 14px; line-height: 1.4; color: #657786; margin-bottom: 8px;">{description}</div>' if description else ''}
            <div class="ogp-site" style="font-size: 12px; color: #657786; text-transform: uppercase;">{site_name}</div>
        </div>
    </a>
</div>'''
        
        return card_html
        
    except Exception as e:
        current_app.logger.error(f"Error generating OGP card: {e}")
        return f'<a href="{url}" target="_blank" class="simple-link">{url}</a>'

def generate_article_structured_data(article):
    """記事用のJSON-LD構造化データを生成"""
    try:
        # 作成者情報を安全に取得
        author_name = "Unknown Author"  # デフォルト値
        if hasattr(article, 'user') and article.user:
            if hasattr(article.user, 'display_name') and article.user.display_name:
                author_name = article.user.display_name
            elif hasattr(article.user, 'email') and article.user.email:
                author_name = article.user.email
        
        # カテゴリ情報を取得
        categories = []
        if hasattr(article, 'categories') and article.categories:
            categories = [cat.name for cat in article.categories if hasattr(cat, 'name')]
        
        # 記事の文字数を計算
        word_count = len(article.body) if article.body else 0
        
        # 公開日の処理
        published_date = article.published_at if article.published_at else article.created_at
        if published_date:
            published_iso = published_date.isoformat()
        else:
            from datetime import datetime
            published_iso = datetime.now().isoformat()
        
        # JSON-LD構造化データ
        structured_data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": article.title or "Untitled",
            "description": article.summary or article.title or "No description available",
            "author": {
                "@type": "Person",
                "name": author_name
            },
            "datePublished": published_iso,
            "dateModified": article.updated_at.isoformat() if article.updated_at else published_iso,
            "wordCount": word_count,
            "articleSection": categories,
            "keywords": categories,
            "publisher": {
                "@type": "Organization",
                "name": "Miyakawa.codes",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://miyakawa.codes/static/images/logo.png"
                }
            }
        }
        
        # アイキャッチ画像が設定されている場合
        if hasattr(article, 'featured_image_url') and article.featured_image_url:
            structured_data["image"] = {
                "@type": "ImageObject",
                "url": f"https://miyakawa.codes{article.featured_image_url}"
            }
        
        return json.dumps(structured_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        current_app.logger.error(f"Error generating structured data: {e}")
        return None

def get_static_page_seo(page_name):
    """静的ページ用のSEO設定を取得"""
    seo_configs = {
        'home': {
            'title': 'Miyakawa.codes - Python 100 Days Challenge Portfolio',
            'description': 'Python 100日チャレンジの学習記録とプロジェクト成果をまとめたポートフォリオサイトです。',
            'keywords': 'Python, プログラミング, 100日チャレンジ, ポートフォリオ, 学習記録',
            'og_type': 'website'
        },
        'blog': {
            'title': 'ブログ - Python学習記録',
            'description': 'Python 100日チャレンジの日々の学習記録とプログラミングの成長過程を記録しています。',
            'keywords': 'Python, プログラミング学習, ブログ, 100日チャレンジ',
            'og_type': 'blog'
        },
        'projects': {
            'title': 'プロジェクト - 作品ギャラリー',
            'description': 'Python 100日チャレンジで作成したプロジェクトと作品のギャラリーです。',
            'keywords': 'Python, プロジェクト, 作品, ギャラリー, ポートフォリオ',
            'og_type': 'website'
        }
    }
    
    return seo_configs.get(page_name, {
        'title': 'Miyakawa.codes',
        'description': 'Python学習とプログラミングの記録',
        'keywords': 'Python, プログラミング',
        'og_type': 'website'
    })