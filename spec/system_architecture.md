# システムアーキテクチャ仕様書

**プロジェクト**: Python 100 Days Challenge Portfolio  
**作成日**: 2025-09-01  
**バージョン**: v1.0  

## 概要

Python 100日チャレンジポートフォリオサイトのシステム全体設計とアーキテクチャ仕様を定義します。

## システム構成概要

```
┌─────────────────────────────────────────────────────────┐
│                   Nginx (Reverse Proxy)                │
│                    SSL Termination                     │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                Flask Application                        │
│  ┌─────────────────┬─────────────────┬─────────────────┐│
│  │   Public Pages  │   Admin Panel   │   Auth System   ││
│  │   (/, /blog)    │ (/admin-xxx/)   │ (/auth-xxx/)    ││
│  └─────────────────┴─────────────────┴─────────────────┘│
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────────────┐
│                MySQL 8.4 LTS                           │
│              (portfolio_db)                             │
└─────────────────────────────────────────────────────────┘
```

## アプリケーション構造

### 1. Flask Blueprint アーキテクチャ

```python
app.py (Main Application - 336行)
├── admin_bp      # 管理画面 (/{ADMIN_URL_PREFIX}/)
├── api_bp        # RESTful API (/api/)
├── auth_bp       # 認証システム (/{LOGIN_URL_PATH}/)
├── articles_bp   # 記事機能 (/blog/, /article/)
├── projects_bp   # プロジェクト機能 (/projects/)
├── comments_bp   # コメント機能
├── search_bp     # 検索機能 (/search)
├── categories_bp # カテゴリ機能 (/category/)
└── landing_bp    # ランディングページ (/, /portfolio, /services, /story, /about)
```

### 2. ディレクトリ構造

```
portfolio/
├── 🐍 Core Application
│   ├── app.py                 # メインアプリケーション（1130行）
│   ├── admin.py               # 管理画面Blueprint（3800行）
│   ├── api.py                 # RESTful API（79行）
│   ├── auth.py                # 認証Blueprint（150行）
│   ├── articles.py            # 記事機能Blueprint（291行）
│   ├── projects.py            # プロジェクト機能Blueprint（276行）
│   ├── comments.py            # コメント機能Blueprint（168行）
│   ├── search.py              # 検索機能Blueprint（100行）
│   ├── categories.py          # カテゴリ機能Blueprint（56行）
│   ├── models.py              # データベースモデル（771行）
│   ├── forms.py               # WTForms定義
│   ├── utils.py               # ユーティリティ関数（170行）
│   ├── seo.py                 # SEO機能（400行）
│   └── encryption_utils.py    # 暗号化サービス
├── 📁 Templates & Static
│   ├── templates/             # Jinja2テンプレート
│   │   ├── admin/            # 管理画面テンプレート
│   │   ├── layout.html       # 管理画面レイアウト
│   │   ├── public_layout.html # 公開ページレイアウト
│   │   └── *.html            # 各種ページテンプレート
│   └── static/               # 静的ファイル
│       ├── css/              # スタイルシート
│       ├── js/               # JavaScriptファイル
│       └── uploads/          # アップロード画像
├── 🗄️ Database & Migration
│   ├── migrations/           # Flask-Migrate
│   └── instance/             # SQLiteファイル（開発用）
├── 📝 Documentation
│   ├── spec/                 # 仕様書（GitHubに含めない）
│   ├── reports/              # 作業レポート（GitHubに含めない）
│   ├── CLAUDE.md            # AI開発ガイド
│   ├── WORK_STATUS.md       # 作業状況
│   └── README.md            # プロジェクト概要
└── ⚙️ Configuration & Deploy
    ├── requirements.txt      # Python依存関係
    ├── .env                  # 環境変数
    ├── docker-compose.yml    # Docker設定
    ├── Dockerfile            # コンテナ定義
    └── scripts/              # デプロイスクリプト
```

## レイヤードアーキテクチャ

### 1. プレゼンテーション層（Templates + Routes）

```python
# Flask Routes (app.py)
@app.route('/')                    # → home.html
@app.route('/blog')                # → blog.html  
@app.route('/article/<slug>')      # → article_detail.html

# Admin Routes (admin.py)  
@admin_bp.route('/articles/')      # → admin/articles.html
@admin_bp.route('/users/')         # → admin/users.html

# API Routes (api.py)
@api_bp.route('/projects/by-challenge/<id>')  # → JSON Response
```

### 2. ビジネスロジック層（Services）

```python
# 記事サービス (article_service.py)
class ArticleService:
    ├── create_article()              # 記事作成
    ├── update_article()              # 記事更新
    ├── generate_unique_slug()        # スラッグ生成
    ├── validate_article_data()       # バリデーション
    ├── process_article_image()       # 画像処理
    └── assign_category()             # カテゴリ割当

# コメントサービス (comment_service.py)
class CommentService:
    ├── create_comment()              # コメント作成（暗号化含む）
    ├── approve_comment()             # コメント承認
    ├── reject_comment()              # コメント拒否
    ├── delete_comment()              # コメント削除
    ├── bulk_approve_comments()       # 一括承認
    ├── bulk_reject_comments()        # 一括拒否
    ├── bulk_delete_comments()        # 一括削除
    ├── get_approved_comments()       # 承認済み取得
    ├── get_pending_comments()        # 未承認取得
    ├── get_comment_stats()           # 統計情報
    ├── validate_comment_data()       # バリデーション
    ├── sanitize_content()            # サニタイゼーション
    ├── get_decrypted_comment_data()  # 復号化
    └── search_comments()             # コメント検索

# その他の処理（app.py内の関数）
def get_article_data(slug)         # 記事データ取得
def process_article_content(body)  # Markdown処理・SNS埋込

# コメントサービス
def encrypt_comment_data(name, email)  # 個人情報暗号化
def get_approved_comments(article_id)  # 承認済みコメント取得

# 認証サービス（auth.py）
def verify_totp_token(user, token)     # 2FA認証
def generate_password_reset_token()    # パスワードリセット
```

### 3. データアクセス層（Models + SQLAlchemy）

```python
# ORM Models (models.py)
class User(db.Model, UserMixin)        # ユーザー・認証
class Article(db.Model)                # 記事・コンテンツ
class Challenge(db.Model)              # チャレンジ管理
class Project(db.Model)                # プロジェクト
class Comment(db.Model)                # コメント（暗号化対応）
```

## コンポーネント設計

### 1. 認証・認可システム

```python
# 認証フロー
Flask-Login + TOTP 2FA
├── ログイン認証 (email/password)
├── TOTP認証 (Google Authenticator)  
├── セッション管理 (HTTPOnly Cookie)
└── 権限チェック (@login_required)

# セキュリティ機能
├── CSRF保護 (Flask-WTF)
├── XSS対策 (Bleach sanitization)
├── セキュアセッション (SameSite, Secure)
└── 暗号化 (Fernet encryption)
```

### 2. コンテンツ管理システム

```python
# コンテンツ構造
Challenge (100日チャレンジ)
├── Articles (学習記録)
│   ├── Categories (多対多)
│   ├── Projects (JSON関連付け)  
│   └── Comments (承認制)
└── Projects (成果物)
    ├── Technologies (JSON配列)
    ├── Demo URLs (JSON配列)
    └── Screenshots (JSON配列)
```

### 3. ファイル・画像管理

```python
# アップロードシステム
static/uploads/
├── articles/     # 記事内画像
├── projects/     # プロジェクト画像
├── categories/   # カテゴリOGP画像
└── content/      # コンテンツ画像

# 画像処理機能
├── アップロード検証 (拡張子・サイズ)
├── メタデータ管理 (UploadedImage model)
├── ギャラリー機能 (検索・フィルタ)
└── 自動リサイズ・最適化
```

## データフロー

### 1. 記事表示フロー

```
Request: /article/python-day-1
    ↓
app.py: article_detail(slug)
    ↓
models.py: Article.query.filter_by(slug=slug)
    ↓
utils.py: process_markdown(article.body)
    ↓  
seo.py: generate_json_ld(article)
    ↓
templates/article_detail.html
    ↓
Response: HTML + JSON-LD
```

### 2. コメント投稿フロー

```
POST: /add_comment/<article_id>
    ↓
app.py: add_comment(article_id)
    ↓
encryption_utils.py: encrypt(name, email)
    ↓
models.py: Comment.create(encrypted_data)
    ↓
admin.py: comments管理（復号化表示）
    ↓
承認後 → 公開ページ表示
```

### 3. API呼び出しフロー

```
AJAX: /api/projects/by-challenge/1
    ↓
api.py: projects_by_challenge(challenge_id)
    ↓
models.py: Project.query.filter_by()
    ↓
JSON Response: {"projects": [...]}
    ↓
JavaScript: 動的フォーム更新
```

## セキュリティアーキテクチャ

### 1. 多層防御

```
┌─────────────────────────────────────────┐
│ 1. Nginx (Rate Limiting, SSL)          │
├─────────────────────────────────────────┤
│ 2. Flask Security Headers              │  
├─────────────────────────────────────────┤
│ 3. CSRF Protection (Flask-WTF)         │
├─────────────────────────────────────────┤
│ 4. Input Validation (WTForms)          │
├─────────────────────────────────────────┤
│ 5. Authentication (2FA)                │
├─────────────────────────────────────────┤
│ 6. Authorization (@login_required)      │
├─────────────────────────────────────────┤
│ 7. Data Encryption (Fernet)            │
├─────────────────────────────────────────┤
│ 8. Database (MySQL with constraints)   │
└─────────────────────────────────────────┘
```

### 2. 暗号化システム

```python
# encryption_utils.py
class EncryptionService:
    ├── encrypt(plaintext) → base64_encrypted_text
    ├── decrypt(encrypted_text) → plaintext  
    ├── _is_encrypted_data() → boolean
    └── get_cipher_suite() → Fernet instance

# 適用箇所
Comment.author_name     # 投稿者名暗号化
Comment.author_email    # メールアドレス暗号化
```

## パフォーマンス設計

### 1. データベース最適化

```python
# SQLAlchemy最適化設定
lazy='selectin'    # N+1問題回避（categories, uploaded_images）
lazy='dynamic'     # 大量データ対応（comments）
lazy='select'      # 標準読み込み

# インデックス戦略
CREATE INDEX idx_articles_published ON articles(is_published, published_at DESC);
CREATE INDEX idx_projects_status ON projects(status, display_order);
CREATE INDEX idx_comments_approval ON comments(is_approved, created_at DESC);
```

### 2. フロントエンド最適化

```javascript
// 非同期データ読み込み
async function loadData(challengeId) {
    const [projects, categories] = await Promise.all([
        fetchProjects(challengeId),
        fetchCategories(challengeId)
    ]);
}

// 画像遅延読み込み
<img src="placeholder.jpg" data-src="actual.jpg" loading="lazy">
```

## 拡張性設計

### 1. モジュール分離

```python
# 現在の分離状況
app.py      (1858行) # メインルーティング
admin.py    (3800行) # 管理機能
api.py      (79行)   # API機能
auth.py     (150行)  # 認証機能
utils.py    (170行)  # ユーティリティ
seo.py      (400行)  # SEO機能

# 今後の分離予定
app.py → comments.py    # コメント機能分離
app.py → articles.py    # 記事機能分離  
app.py → projects.py    # プロジェクト機能分離
```

### 2. サービス層強化

```python
# 実装済みのサービス層
class ArticleService (article_service.py):
    ├── 記事CRUD操作
    ├── バリデーション
    ├── 画像処理
    └── カテゴリ管理

class CommentService (comment_service.py):
    ├── コメントCRUD操作
    ├── 暗号化・復号化
    ├── 一括操作
    └── 統計・検索

class CategoryService (article_service.py):
    ├── カテゴリCRUD操作
    └── OGP画像処理

class UserService (article_service.py):
    ├── ユーザーCRUD操作
    └── パスワード管理
```

## デプロイアーキテクチャ

### 1. Docker構成

```yaml
# docker-compose.yml
services:
  web:
    build: .
    ports: ["5000:5000"]
    depends_on: ["db"]
    environment:
      - DATABASE_URL=mysql+pymysql://root:password@db:3306/portfolio_db
  
  db:
    image: mysql:8.4
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=portfolio_db
    volumes:
      - mysql_data:/var/lib/mysql

  nginx:
    image: nginx:alpine
    ports: ["80:80", "443:443"]
    depends_on: ["web"]
```

### 2. AWS Lightsail構成

```
┌─────────────────────────────────────────┐
│           AWS Lightsail Instance        │
│  ┌─────────────────────────────────────┐ │
│  │         Ubuntu 24.04 LTS           │ │
│  │  ┌─────────────────────────────────┐ │ │
│  │  │          Docker Engine         │ │ │
│  │  │  ┌─────────────────────────────┐ │ │ │
│  │  │  │      Application Stack     │ │ │ │
│  │  │  │  ┌─────────────────────────┐ │ │ │ │
│  │  │  │  │ Nginx + Flask + MySQL  │ │ │ │ │
│  │  │  │  └─────────────────────────┘ │ │ │ │
│  │  │  └─────────────────────────────┘ │ │ │
│  │  └─────────────────────────────────┘ │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## 技術スタック詳細

### 1. バックエンド技術

| コンポーネント | バージョン | 用途 | 設定ファイル |
|-------------|----------|------|-------------|
| Python | 3.13 | アプリケーション基盤 | Dockerfile |
| Flask | 3.1.2 | Webフレームワーク | app.py |
| SQLAlchemy | 2.0+ | ORM・データベース操作 | models.py |
| MySQL | 8.4 LTS | データベース | docker-compose.yml |
| Gunicorn | latest | WSGIサーバー | 本番デプロイ |
| Flask-Login | latest | 認証管理 | auth.py |
| Flask-WTF | latest | フォーム・CSRF | forms.py |
| Flask-Migrate | latest | データベース移行 | migrations/ |

### 2. セキュリティ技術

| コンポーネント | バージョン | 用途 | 実装場所 |
|-------------|----------|------|----------|
| pyotp | latest | TOTP 2FA | auth.py |
| cryptography | 42.0.5 | データ暗号化 | encryption_utils.py |
| bleach | latest | HTMLサニタイゼーション | utils.py |
| werkzeug.security | latest | パスワードハッシュ化 | models.py |

### 3. フロントエンド技術

| コンポーネント | バージョン | 用途 | ファイル |
|-------------|----------|------|---------|
| Bootstrap | 5.3 | UI フレームワーク | public_layout.html |
| Font Awesome | 6.0 | アイコン | layout.html |
| Flatpickr | latest | 日付選択 | admin/articles.html |
| Cropper.js | latest | 画像編集 | admin/images.html |
| Markdown-it | latest | Markdownプレビュー | admin/*.html |

## API設計パターン

### 1. RESTful API（/api/）

```python
# リソース指向設計
GET    /api/projects/by-challenge/<id>  # チャレンジ別プロジェクト一覧
GET    /api/categories/by-challenge/<id> # チャレンジ別カテゴリ一覧
GET    /api/images/gallery              # 画像ギャラリー

# レスポンス統一形式
{
  "data": [...],      # メインデータ
  "total": 42,        # 総数
  "meta": {...}       # メタデータ
}
```

### 2. 管理API（/admin/）

```python
# CRUD操作パターン
GET    /admin/articles/           # 一覧
GET    /admin/article/create/     # 作成フォーム
POST   /admin/article/create/     # 作成実行
GET    /admin/article/edit/<id>   # 編集フォーム
POST   /admin/article/edit/<id>   # 更新実行
POST   /admin/article/delete/<id> # 削除実行
```

## 状態管理

### 1. ユーザーセッション

```python
# Flask-Login セッション
session['user_id']              # ユーザーID
session['_user_id']             # Flask-Login内部ID
session['totp_verified']        # 2FA認証状態
session['csrf_token']           # CSRFトークン
```

### 2. アプリケーション設定

```python
# データベース駆動設定（SiteSetting model）
site_name                       # サイト名
admin_email                     # 管理者メール
comments_enabled               # コメント機能ON/OFF
ga4_measurement_id             # Google Analytics設定
footer_links                   # フッターリンク（JSON）
```

## 統合・連携設計

### 1. 外部サービス連携

```python
# Google Analytics 4
ga4_analytics.py               # 統計データ取得
templates/*.html               # gtag.js統合

# AWS SES（将来）
email_service.py              # メール送信サービス
admin/users.html              # パスワードリセット通知

# Let's Encrypt
nginx.conf                    # SSL証明書自動更新
deploy.sh                     # 証明書更新スクリプト
```

### 2. SNS埋込システム

```python
# oEmbed API統合（utils.py）
def process_twitter_embed()    # X/Twitter埋込
def process_youtube_embed()    # YouTube埋込  
def process_instagram_embed()  # Instagram埋込

# Markdown拡張
def process_sns_urls(markdown_text) # URL自動検出・埋込
```

## 監視・ログ設計

### 1. アプリケーションログ

```python
# ログレベル設定
logging.basicConfig(level=logging.INFO)

# ログ出力先
logs/
├── app.log              # アプリケーションログ
├── access.log           # アクセスログ
├── error.log            # エラーログ
└── security.log         # セキュリティイベント
```

### 2. 監視指標

```python
# パフォーマンス指標
- Response Time         # レスポンス時間
- Database Query Time   # DB クエリ時間
- Memory Usage         # メモリ使用量
- CPU Usage           # CPU使用率

# ビジネス指標  
- Page Views          # ページビュー
- User Sessions       # ユーザーセッション
- Comment Submissions # コメント投稿数
- Admin Logins        # 管理画面ログイン
```

## 品質保証

### 1. テスト戦略（今後実装）

```python
# テスト階層
tests/
├── unit/               # 単体テスト
│   ├── test_models.py     # モデルテスト
│   ├── test_utils.py      # ユーティリティテスト
│   └── test_auth.py       # 認証テスト
├── integration/        # 統合テスト
│   ├── test_api.py        # API テスト
│   └── test_admin.py      # 管理画面テスト
└── e2e/               # E2Eテスト
    ├── test_user_flow.py  # ユーザーフロー
    └── test_admin_flow.py # 管理者フロー
```

### 2. コード品質（今後実装）

```python
# Linting設定
.flake8                # PEP8準拠
pyproject.toml         # Black設定
.pre-commit-config.yaml # Git hooks

# 型ヒント
from typing import List, Dict, Optional
def get_articles() -> List[Article]:
def process_data(data: Dict[str, Any]) -> Optional[str]:
```

## 災害復旧・バックアップ

### 1. バックアップ戦略

```bash
# データベースバックアップ（日次）
mysqldump --single-transaction portfolio_db > backup_$(date +%Y%m%d).sql

# ファイルバックアップ（週次）
tar -czf uploads_backup_$(date +%Y%m%d).tar.gz static/uploads/

# 設定バックアップ
cp .env backup_env_$(date +%Y%m%d)
```

### 2. 復旧手順

```bash
# 1. データベース復元
mysql -u root -p portfolio_db < backup_20250901.sql

# 2. ファイル復元  
tar -xzf uploads_backup_20250901.tar.gz

# 3. 設定復元
cp backup_env_20250901 .env

# 4. アプリケーション再起動
docker-compose down && docker-compose up -d
```

## 今後の拡張計画

### Phase A: 効率化（実装中）
- ドキュメント整備 ✅
- コードリファクタリング
- 開発ツール導入

### Phase B: 機能完成
- 残タスク解決
- 品質向上
- パフォーマンス最適化

### Phase C: 本番運用
- AWS デプロイ
- 監視システム
- 運用自動化

---

**最終更新**: 2025-09-01  
**アーキテクチャレビュー**: Flask 3.1.2 + MySQL 8.4 LTS で設計検証済み