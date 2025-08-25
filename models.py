"""
データベースモデル定義
ミニブログシステムの全データベーステーブル定義
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
from flask_login import UserMixin
import pyotp
import secrets
import json
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy import select, func

db = SQLAlchemy()

# --- 新規：Challengeモデル ---
class Challenge(db.Model):
    __tablename__ = 'challenges'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)  # "Python 100 Days Challenge #1"
    slug = db.Column(db.String(255), unique=True, nullable=False)  # "python-100-days-1"
    description = db.Column(db.Text)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date)  # 完了日（NULL = 進行中）
    target_days = db.Column(db.Integer, default=100)  # 目標日数
    github_repos = db.Column(db.Text)  # JSON形式で複数リポジトリを保存
    is_active = db.Column(db.Boolean, default=False)  # 現在アクティブなチャレンジ
    display_order = db.Column(db.Integer, default=0)  # 表示順
    
    # 手動調整用フィールド
    manual_days = db.Column(db.Integer, nullable=True)  # 手動で設定した日数
    manual_adjustment_date = db.Column(db.Date, nullable=True)  # 手動調整を行った日
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    articles = db.relationship('Article', backref='challenge', lazy='dynamic')
    
    def __repr__(self):
        return f'<Challenge {self.name}>'
    
    @property
    def days_elapsed(self):
        """経過日数を計算（手動調整対応）"""
        if self.end_date:
            # 完了済みの場合
            return (self.end_date - self.start_date).days + 1
        
        # 手動調整が行われている場合
        if self.manual_days is not None and self.manual_adjustment_date is not None:
            today = datetime.now().date()
            # 調整日からの経過日数を加算
            days_since_adjustment = (today - self.manual_adjustment_date).days
            total_days = self.manual_days + days_since_adjustment
            return min(total_days, self.target_days)
        
        # 通常の自動計算
        today = datetime.now().date()
        days = (today - self.start_date).days + 1
        return min(days, self.target_days)
    
    @property
    def progress_percentage(self):
        """進捗率を計算"""
        return min(100, (self.days_elapsed / self.target_days) * 100)
    
    @property
    def status(self):
        """チャレンジのステータス"""
        if self.end_date:
            return 'completed'
        elif self.is_active:
            return 'active'
        else:
            return 'paused'
    
    @property
    def github_repositories(self):
        """GitHubリポジトリ一覧を取得"""
        import json
        if self.github_repos:
            try:
                return json.loads(self.github_repos)
            except json.JSONDecodeError:
                return []
        return []
    
    def add_github_repo(self, name, url, description=None):
        """GitHubリポジトリを追加"""
        import json
        repos = self.github_repositories
        new_repo = {
            'name': name,
            'url': url,
            'description': description
        }
        repos.append(new_repo)
        self.github_repos = json.dumps(repos, ensure_ascii=False)
    
    def remove_github_repo(self, index):
        """GitHubリポジトリを削除（インデックス指定）"""
        import json
        repos = self.github_repositories
        if 0 <= index < len(repos):
            repos.pop(index)
            self.github_repos = json.dumps(repos, ensure_ascii=False)
    
    def set_github_repos(self, repos_list):
        """GitHubリポジトリ一覧を設定"""
        import json
        self.github_repos = json.dumps(repos_list, ensure_ascii=False) if repos_list else None

# --- プロジェクト管理 ---

class Project(db.Model):
    """プロジェクト管理モデル"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    long_description = db.Column(db.Text)  # 詳細説明
    
    # 技術情報
    technologies = db.Column(db.Text)  # JSON形式で技術スタック
    github_url = db.Column(db.String(500))
    demo_url = db.Column(db.String(500))  # 下位互換性のため保持
    demo_urls = db.Column(db.Text)  # JSON形式で複数デモURL
    
    # 画像
    featured_image = db.Column(db.String(255))  # メイン画像
    screenshot_images = db.Column(db.Text)  # JSON形式でスクリーンショット画像
    
    # 関連情報
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)
    challenge_day = db.Column(db.Integer, nullable=True)  # 何日目のプロジェクトか
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id'), nullable=True)  # 関連記事
    
    # ステータス・表示設定
    status = db.Column(db.String(50), default='active')  # active, archived, private
    is_featured = db.Column(db.Boolean, default=False)  # 注目プロジェクト
    display_order = db.Column(db.Integer, default=0)
    
    # メタデータ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーション
    challenge = db.relationship('Challenge', backref='projects')
    article = db.relationship('Article', backref='projects')
    
    def __repr__(self):
        return f'<Project {self.title}>'
    
    @property
    def technology_list(self):
        """技術スタックのリストを取得"""
        if not self.technologies:
            return []
        try:
            return json.loads(self.technologies)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_technologies(self, tech_list):
        """技術スタックを設定"""
        self.technologies = json.dumps(tech_list, ensure_ascii=False)
    
    @property
    def demo_url_list(self):
        """デモURLのリストを取得"""
        if not self.demo_urls:
            # 下位互換性: 古いdemo_urlがあれば変換
            if self.demo_url:
                return [{"name": "デモ", "url": self.demo_url, "type": "demo"}]
            return []
        try:
            return json.loads(self.demo_urls)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_demo_urls(self, demo_list):
        """デモURLを設定"""
        if demo_list:
            self.demo_urls = json.dumps(demo_list, ensure_ascii=False)
        else:
            self.demo_urls = None
    
    def add_demo_url(self, name, url, demo_type="demo"):
        """デモURLを追加"""
        current_demos = self.demo_url_list
        new_demo = {"name": name, "url": url, "type": demo_type}
        current_demos.append(new_demo)
        self.set_demo_urls(current_demos)
    
    @property
    def screenshot_list(self):
        """スクリーンショット画像のリストを取得"""
        if not self.screenshot_images:
            return []
        try:
            return json.loads(self.screenshot_images)
        except (json.JSONDecodeError, TypeError):
            return []
    
    def set_screenshots(self, screenshot_list):
        """スクリーンショット画像を設定"""
        self.screenshot_images = json.dumps(screenshot_list, ensure_ascii=False)
    
    @property
    def related_articles(self):
        """このプロジェクトに関連する記事のリストを取得"""
        from models import Article
        # project_idsにこのプロジェクトのIDが含まれている記事を検索
        articles = Article.query.filter(
            Article.is_published == True,
            Article.project_ids.like(f'%{self.id}%')
        ).all()
        
        # JSON形式で保存されているので、正確にフィルタリング
        related = []
        for article in articles:
            try:
                if article.project_ids:
                    project_ids = json.loads(article.project_ids)
                    if self.id in project_ids:
                        related.append(article)
            except:
                pass
        return related

# --- 中間テーブル: Article と Category の多対多関連 ---
article_categories = db.Table('article_categories',
    db.Column('article_id', db.Integer, db.ForeignKey('articles.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('categories.id'), primary_key=True)
)

class User(db.Model, UserMixin): # UserMixin を継承
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    name_romaji = db.Column(db.String(200), nullable=True)  # ローマ字読み
    handle_name = db.Column(db.String(100))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='author') # 'admin', 'author'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # TOTP関連フィールド
    totp_secret = db.Column(db.String(255), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)
    
    # パスワードリセット関連フィールド
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # 通知設定
    notify_on_publish = db.Column(db.Boolean, default=False)
    notify_on_comment = db.Column(db.Boolean, default=False)
    
    # ログイン管理
    last_login = db.Column(db.DateTime)  # 最終ログイン時刻
    
    # プロフィール情報
    introduction = db.Column(db.Text, nullable=True)  # 紹介文（250文字以内）
    birthplace = db.Column(db.String(10), nullable=True)  # 出身地（10文字以内）
    birthday = db.Column(db.Date, nullable=True)  # 誕生日
    
    # SNSアカウント情報（個別カラム）
    sns_x = db.Column(db.String(100), nullable=True)  # X（旧Twitter）
    sns_facebook = db.Column(db.String(100), nullable=True)  # Facebook
    sns_instagram = db.Column(db.String(100), nullable=True)  # Instagram
    sns_threads = db.Column(db.String(100), nullable=True)  # Threads
    sns_youtube = db.Column(db.String(100), nullable=True)  # YouTube
    
    # ポートフォリオ向けプロフェッショナル情報
    job_title = db.Column(db.String(255), nullable=True)  # 職種・肩書き
    tagline = db.Column(db.String(255), nullable=True)  # キャッチコピー
    profile_photo = db.Column(db.String(255), nullable=True)  # プロフィール写真URL
    resume_pdf = db.Column(db.String(255), nullable=True)  # 履歴書PDFのURL
    
    # スキル・経歴情報（JSON形式）
    skills = db.Column(db.JSON, nullable=True)  # {category: [{name, level, years}]}
    career_history = db.Column(db.JSON, nullable=True)  # [{company, position, period, description}]
    education = db.Column(db.JSON, nullable=True)  # [{school, degree, field, year}]
    certifications = db.Column(db.JSON, nullable=True)  # [{name, issuer, date}]
    
    # プロフェッショナル連絡先
    linkedin_url = db.Column(db.String(255), nullable=True)
    github_username = db.Column(db.String(255), nullable=True)
    portfolio_email = db.Column(db.String(255), nullable=True)  # 公開用メール
    
    ext_json = db.Column(db.Text, nullable=True)  # 拡張用JSON
    
    articles = db.relationship('Article', backref=db.backref('author', lazy='select'), lazy='selectin') # UserとArticleの1対多（パフォーマンス最適化）
    
    def generate_totp_secret(self):
        """TOTP用のシークレットキーを生成"""
        self.totp_secret = pyotp.random_base32()
        return self.totp_secret
    
    def get_totp_uri(self, issuer_name="MiniBlog"):
        """Google Authenticator用のURI生成"""
        if not self.totp_secret:
            self.generate_totp_secret()
        return pyotp.totp.TOTP(self.totp_secret).provisioning_uri(
            name=self.email,
            issuer_name=issuer_name
        )
    
    def verify_totp(self, token):
        """TOTPトークンの検証"""
        if not self.totp_secret or not self.totp_enabled:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(token, valid_window=1)
    
    def generate_reset_token(self):
        """パスワードリセット用トークンを生成"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token
    
    def verify_reset_token(self, token):
        """パスワードリセットトークンの検証"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if datetime.utcnow() > self.reset_token_expires:
            return False
        return self.reset_token == token
    
    def clear_reset_token(self):
        """パスワードリセットトークンをクリア"""
        self.reset_token = None
        self.reset_token_expires = None

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    summary = db.Column(db.Text, nullable=True)  # 記事概要
    body = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 公開設定
    is_published = db.Column(db.Boolean, default=False)
    published_at = db.Column(db.DateTime, nullable=True)
    allow_comments = db.Column(db.Boolean, default=True)
    
    # SEO関連フィールド
    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.String(255), nullable=True)
    canonical_url = db.Column(db.String(255), nullable=True)
    
    # 画像関連
    featured_image = db.Column(db.String(255), nullable=True)  # アイキャッチ画像
    featured_image_alt = db.Column(db.String(255), nullable=True)  # アイキャッチ画像のalt属性
    
    # legacy_body_backup は削除せず保持（データ保護のため）
    legacy_body_backup = db.Column(db.Text, nullable=True)  # 従来のbodyフィールドのバックアップ
    
    # チャレンジ関連
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)
    challenge_day = db.Column(db.Integer, nullable=True)  # Day 1, Day 2, etc.
    
    # プロジェクト関連
    project_ids = db.Column(db.Text, nullable=True)  # JSON形式で複数プロジェクトID保存
    
    # 拡張用
    ext_json = db.Column(db.Text, nullable=True)

    # Article から Category へのリレーションシップ（パフォーマンス最適化）
    categories = db.relationship(
        'Category',
        secondary=article_categories,
        lazy='selectin',  # N+1問題回避のため selectin を使用
        back_populates='articles'
    )
    
    # コメントとのリレーション（CASCADE削除対応）
    comments = db.relationship('Comment', back_populates='article', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_text_content(self):
        """記事のテキストコンテンツを取得（検索用）"""
        return self.body or ''
    
    @property
    def related_projects(self):
        """関連プロジェクトのリストを取得"""
        if not self.project_ids:
            return []
        try:
            project_ids = json.loads(self.project_ids)
            if not project_ids:
                return []
            # IDリストからプロジェクトを取得
            from models import Project
            return Project.query.filter(
                Project.id.in_(project_ids),
                Project.status == 'active'
            ).all()
        except (json.JSONDecodeError, Exception):
            return []
    
    def add_project(self, project_id):
        """プロジェクトを関連付け"""
        try:
            current_ids = json.loads(self.project_ids) if self.project_ids else []
            if project_id not in current_ids:
                current_ids.append(project_id)
                self.project_ids = json.dumps(current_ids)
        except:
            self.project_ids = json.dumps([project_id])
    
    def remove_project(self, project_id):
        """プロジェクトの関連付けを解除"""
        try:
            current_ids = json.loads(self.project_ids) if self.project_ids else []
            if project_id in current_ids:
                current_ids.remove(project_id)
                self.project_ids = json.dumps(current_ids) if current_ids else None
        except:
            pass

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey('challenges.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    meta_title = db.Column(db.String(255), nullable=True)
    meta_description = db.Column(db.Text, nullable=True)
    meta_keywords = db.Column(db.String(255), nullable=True)
    ogp_image = db.Column(db.String(255), nullable=True)
    ogp_image_alt = db.Column(db.String(255), nullable=True)  # OGP画像のalt属性
    canonical_url = db.Column(db.String(255), nullable=True)
    json_ld = db.Column(db.Text, nullable=True)
    ext_json = db.Column(db.Text, nullable=True)

    parent = db.relationship('Category', remote_side=[id], backref=db.backref('children', lazy='select'))
    challenge = db.relationship('Challenge', backref=db.backref('categories', lazy='select'))

    # Category から Article へのリレーションシップ（パフォーマンス最適化）
    articles = db.relationship(
        'Article',
        secondary=article_categories,
        lazy='selectin',  # N+1問題回避のため selectin を使用
        back_populates='categories'
    )

    def __repr__(self):
        return f'<Category {self.name}>'

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    author_name = db.Column(db.String(100), nullable=False)
    author_email = db.Column(db.String(255), nullable=False)
    author_website = db.Column(db.String(255), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_approved = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(45), nullable=True)  # IPv6対応
    user_agent = db.Column(db.String(500), nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('comments.id'), nullable=True)  # 返信機能用
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ（パフォーマンス最適化） - CASCADE削除対応
    article = db.relationship('Article', back_populates='comments')
    parent = db.relationship('Comment', remote_side=[id], backref=db.backref('replies', lazy='selectin'))
    
    def __repr__(self):
        return f'<Comment {self.id}: {self.author_name} on Article {self.article_id}>'

class SiteSetting(db.Model):
    __tablename__ = 'site_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.Text, nullable=True)
    setting_type = db.Column(db.String(20), default='text')  # text, boolean, number, json
    is_public = db.Column(db.Boolean, default=False)  # 公開設定かどうか
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SiteSetting {self.key}: {self.value}>'
    
    @staticmethod
    def get_setting(key, default=None):
        """設定値を取得"""
        setting = db.session.execute(select(SiteSetting).where(SiteSetting.key == key)).scalar_one_or_none()
        return setting.value if setting else default
    
    @staticmethod
    def set_setting(key, value, description=None, setting_type='text', is_public=False):
        """設定値を保存または更新"""
        setting = db.session.execute(select(SiteSetting).where(SiteSetting.key == key)).scalar_one_or_none()
        if setting:
            setting.value = value
            setting.description = description or setting.description
            setting.setting_type = setting_type
            setting.is_public = is_public
            setting.updated_at = datetime.utcnow()
        else:
            setting = SiteSetting(
                key=key,
                value=value,
                description=description,
                setting_type=setting_type,
                is_public=is_public
            )
            db.session.add(setting)
        db.session.commit()
        return setting

# --- 画像管理用モデル ---

class UploadedImage(db.Model):
    """アップロード済み画像管理"""
    __tablename__ = 'uploaded_images'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)  # 保存時のファイル名
    original_filename = db.Column(db.String(255), nullable=False)  # 元のファイル名
    file_path = db.Column(db.String(500), nullable=False)  # 相対パス
    file_size = db.Column(db.Integer, nullable=False)  # ファイルサイズ（バイト）
    mime_type = db.Column(db.String(100), nullable=False)  # MIMEタイプ
    width = db.Column(db.Integer)  # 画像幅
    height = db.Column(db.Integer)  # 画像高さ
    
    # メタデータ
    alt_text = db.Column(db.String(255))  # alt属性
    caption = db.Column(db.Text)  # キャプション
    description = db.Column(db.Text)  # 説明
    
    # アップロード情報
    uploader_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 管理情報
    is_active = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)  # 使用回数
    last_used_at = db.Column(db.DateTime)  # 最終使用日時
    
    # タイムスタンプ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ
    uploader = db.relationship('User', backref=db.backref('uploaded_images', lazy='select'))
    
    def __repr__(self):
        return f'<UploadedImage {self.filename}: {self.alt_text or "No alt"}>'
    
    @property
    def file_url(self):
        """画像のURLを取得"""
        return f"/static/{self.file_path}"
    
    @property
    def file_size_mb(self):
        """ファイルサイズをMBで取得"""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def markdown_syntax(self):
        """マークダウン記法を生成"""
        alt = self.alt_text or self.original_filename
        if self.caption:
            return f'![{alt}]({self.file_url} "{self.caption}")'
        else:
            return f'![{alt}]({self.file_url})'
    
    def increment_usage(self):
        """使用回数を増加"""
        self.usage_count += 1
        self.last_used_at = datetime.utcnow()
        db.session.commit()

# --- ユーザーアクティビティ管理用モデル ---

class LoginHistory(db.Model):
    """ログイン履歴管理"""
    __tablename__ = 'login_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    login_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ip_address = db.Column(db.String(45))  # IPv6対応のため長め
    user_agent = db.Column(db.Text)
    success = db.Column(db.Boolean, default=True, nullable=False)
    failure_reason = db.Column(db.String(255))  # 失敗理由
    session_id = db.Column(db.String(255))  # セッションID
    
    # リレーションシップ
    user = db.relationship('User', backref=db.backref('login_history', lazy='select', order_by='LoginHistory.login_at.desc()'))
    
    def __repr__(self):
        return f'<LoginHistory {self.user.email}: {self.login_at} ({"Success" if self.success else "Failed"})>'
    
    @property
    def browser_info(self):
        """ユーザーエージェントからブラウザ情報を抽出"""
        if not self.user_agent:
            return "不明"
        
        ua = self.user_agent.lower()
        if 'chrome' in ua:
            return 'Chrome'
        elif 'firefox' in ua:
            return 'Firefox'
        elif 'safari' in ua and 'chrome' not in ua:
            return 'Safari'
        elif 'edge' in ua:
            return 'Edge'
        else:
            return 'その他'
    
    @property
    def os_info(self):
        """ユーザーエージェントからOS情報を抽出"""
        if not self.user_agent:
            return "不明"
        
        ua = self.user_agent.lower()
        if 'windows' in ua:
            return 'Windows'
        elif 'mac' in ua:
            return 'macOS'
        elif 'linux' in ua:
            return 'Linux'
        elif 'android' in ua:
            return 'Android'
        elif 'iphone' in ua or 'ipad' in ua:
            return 'iOS'
        else:
            return 'その他'

# --- SEO分析用モデル ---

class SEOAnalysis(db.Model):
    """SEO分析結果保存"""
    __tablename__ = 'seo_analysis'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.Integer, db.ForeignKey('articles.id', ondelete='CASCADE'), nullable=False)
    analysis_type = db.Column(db.String(50), nullable=False)  # 'llmo', 'aio', 'traditional'
    analysis_data = db.Column(db.Text, nullable=False)  # JSON形式の分析結果
    score = db.Column(db.Float, nullable=False)  # 総合スコア
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # リレーションシップ - CASCADE削除対応
    article = db.relationship('Article')
    
    def __repr__(self):
        return f'<SEOAnalysis {self.analysis_type}: {self.score}>'

# --- メールアドレス変更要求管理 ---

class EmailChangeRequest(db.Model):
    """メールアドレス変更要求管理"""
    __tablename__ = 'email_change_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    current_email = db.Column(db.String(255), nullable=False)  # 現在のメールアドレス
    new_email = db.Column(db.String(255), nullable=False)  # 新しいメールアドレス
    token = db.Column(db.String(255), nullable=False, unique=True)  # 確認用トークン
    expires_at = db.Column(db.DateTime, nullable=False)  # 有効期限
    is_verified = db.Column(db.Boolean, default=False)  # 確認済みフラグ
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)  # 確認完了日時
    
    # リレーション
    user = db.relationship('User', backref=db.backref('email_change_requests', lazy='dynamic'))
    
    def is_expired(self):
        """トークンが期限切れかどうか"""
        return datetime.utcnow() > self.expires_at
    
    def generate_token(self):
        """確認用トークンを生成"""
        self.token = secrets.token_urlsafe(32)
        self.expires_at = datetime.utcnow() + timedelta(hours=24)  # 24時間有効
        return self.token
    
    @staticmethod
    def verify_token(token):
        """トークンを検証して要求オブジェクトを返す"""
        request = db.session.execute(
            select(EmailChangeRequest).where(
                EmailChangeRequest.token == token,
                EmailChangeRequest.is_verified == False
            )
        ).scalar_one_or_none()
        
        if request and not request.is_expired():
            return request
        return None
