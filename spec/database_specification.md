# データベース仕様書

**プロジェクト**: Python 100 Days Challenge Portfolio  
**データベース**: MySQL 8.4 LTS  
**作成日**: 2025-09-01  
**バージョン**: v1.0  

## 概要

本ドキュメントは、Pythonポートフォリオサイトのデータベース設計と仕様を定義します。ポートフォリオサイトには複数のチャレンジ管理、記事・プロジェクト管理、認証システム、コメント機能が含まれます。

## データベース設定

```sql
-- データベース: portfolio_db
-- 文字セット: utf8mb4
-- 照合順序: utf8mb4_unicode_ci
-- エンジン: InnoDB
```

## テーブル一覧

| テーブル名 | 用途 | 主要機能 |
|-----------|------|----------|
| `users` | ユーザー認証・プロフィール | 2FA認証、プロフィール情報、SNS連携 |
| `challenges` | チャレンジ管理 | 100日チャレンジ複数管理、進捗追跡 |
| `articles` | 記事管理 | 学習記録、SEO設定、公開管理 |
| `projects` | プロジェクト管理 | 成果物、技術スタック、デモURL |
| `categories` | カテゴリ管理 | 階層構造、チャレンジ別分離 |
| `comments` | コメント機能 | 承認制、個人情報暗号化 |
| `uploaded_images` | 画像管理 | ギャラリー機能、メタデータ |
| `site_settings` | サイト設定 | 全体設定、機能ON/OFF |
| `static_page_seo` | 静的ページSEO | ランディングページ等のSEO |
| `login_history` | ログイン履歴 | セキュリティ監査 |
| `seo_analysis` | SEO分析 | 分析結果保存 |
| `email_change_requests` | メール変更 | 安全なメール変更 |

## テーブル詳細仕様

### 1. users - ユーザー管理

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_romaji VARCHAR(200),
    handle_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'author',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- 2FA認証
    totp_secret VARCHAR(255),
    totp_enabled BOOLEAN DEFAULT FALSE,
    
    -- パスワードリセット
    reset_token VARCHAR(255),
    reset_token_expires DATETIME,
    
    -- 通知設定
    notify_on_publish BOOLEAN DEFAULT FALSE,
    notify_on_comment BOOLEAN DEFAULT FALSE,
    last_login DATETIME,
    
    -- 基本プロフィール
    introduction TEXT,
    birthplace VARCHAR(10),
    birthday DATE,
    
    -- SNS連携
    sns_x VARCHAR(100),
    sns_facebook VARCHAR(100),
    sns_instagram VARCHAR(100),
    sns_threads VARCHAR(100),
    sns_youtube VARCHAR(100),
    
    -- プロフェッショナル情報
    job_title VARCHAR(255),
    tagline VARCHAR(255),
    profile_photo VARCHAR(255),
    resume_pdf VARCHAR(255),
    
    -- JSON構造化データ
    skills JSON,
    career_history JSON,
    education JSON,
    certifications JSON,
    
    -- 公開連絡先
    linkedin_url VARCHAR(255),
    github_username VARCHAR(255),
    portfolio_email VARCHAR(255),
    
    ext_json TEXT
);
```

**フィールド詳細**:
- `password_hash`: werkzeug.security でハッシュ化（pbkdf2:sha256）
- `role`: 'admin', 'author' の2種類
- `skills`: JSON配列形式 `[{category, skills: [{name, level, years}]}]`
- `career_history`: `[{company, position, period, description}]`

### 2. challenges - チャレンジ管理

```sql
CREATE TABLE challenges (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    start_date DATE NOT NULL,
    end_date DATE,
    target_days INT DEFAULT 100,
    github_repos TEXT,
    is_active BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    
    -- 手動調整機能
    manual_days INT,
    manual_adjustment_date DATE,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**ビジネスロジック**:
- 進捗計算: `days_elapsed` プロパティで自動計算
- 手動調整: `manual_days` + 調整日からの経過日数
- GitHub連携: JSON形式で複数リポジトリ管理

### 3. articles - 記事管理

```sql
CREATE TABLE articles (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    summary TEXT,
    body TEXT,
    author_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 公開設定
    is_published BOOLEAN DEFAULT FALSE,
    published_at DATETIME,
    allow_comments BOOLEAN DEFAULT TRUE,
    
    -- SEO設定
    meta_title VARCHAR(255),
    meta_description TEXT,
    meta_keywords VARCHAR(255),
    canonical_url VARCHAR(255),
    json_ld TEXT,
    
    -- 画像
    featured_image VARCHAR(255),
    featured_image_alt VARCHAR(255),
    
    -- チャレンジ関連
    challenge_id INT,
    challenge_day INT,
    
    -- プロジェクト関連（JSON配列）
    project_ids TEXT,
    
    -- UI設定
    show_toc BOOLEAN DEFAULT TRUE,
    
    -- レガシー・拡張
    legacy_body_backup TEXT,
    ext_json TEXT,
    
    FOREIGN KEY (author_id) REFERENCES users(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id)
);
```

**重要な設計決定**:
- `project_ids`: JSON配列形式 `[1, 3, 5]` で複数プロジェクト関連付け
- `published_at`: 独立した公開日管理（created_atと分離）
- `show_toc`: 記事別目次表示制御

### 4. projects - プロジェクト管理

```sql
CREATE TABLE projects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    long_description TEXT,
    
    -- 技術情報（JSON配列）
    technologies TEXT,
    github_url VARCHAR(500),
    demo_url VARCHAR(500),  -- 下位互換性用
    demo_urls TEXT,  -- JSON配列形式
    
    -- 画像
    featured_image VARCHAR(255),
    screenshot_images TEXT,  -- JSON配列
    
    -- 関連情報
    challenge_id INT,
    challenge_day INT,
    article_id INT,
    
    -- 表示設定
    status VARCHAR(50) DEFAULT 'active',
    is_featured BOOLEAN DEFAULT FALSE,
    display_order INT DEFAULT 0,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (challenge_id) REFERENCES challenges(id),
    FOREIGN KEY (article_id) REFERENCES articles(id)
);
```

### 5. categories - カテゴリ管理

```sql
CREATE TABLE categories (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL UNIQUE,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    parent_id INT,
    challenge_id INT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- SEO設定
    meta_title VARCHAR(255),
    meta_description TEXT,
    meta_keywords VARCHAR(255),
    ogp_image VARCHAR(255),
    ogp_image_alt VARCHAR(255),
    canonical_url VARCHAR(255),
    json_ld TEXT,
    ext_json TEXT,
    
    FOREIGN KEY (parent_id) REFERENCES categories(id),
    FOREIGN KEY (challenge_id) REFERENCES challenges(id)
);
```

**階層構造**: 自己参照外部キー（parent_id）による無制限階層

### 6. comments - コメント管理

```sql
CREATE TABLE comments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    article_id INT NOT NULL,
    author_name VARCHAR(500) NOT NULL,  -- 暗号化データ格納用
    author_email VARCHAR(500) NOT NULL,  -- 暗号化データ格納用
    author_website VARCHAR(255),
    content TEXT NOT NULL,
    is_approved BOOLEAN DEFAULT FALSE,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    parent_id INT,  -- 返信機能用
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES comments(id)
);
```

**セキュリティ設計**:
- **暗号化**: `author_name`, `author_email` はFernet対称暗号化
- **varchar(500)**: 暗号化によるデータ膨張対応
- **復号化**: モデルプロパティ `decrypted_author_name/email` で透過的処理

### 7. uploaded_images - 画像管理

```sql
CREATE TABLE uploaded_images (
    id INT PRIMARY KEY AUTO_INCREMENT,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INT NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    width INT,
    height INT,
    
    -- メタデータ
    alt_text VARCHAR(255),
    caption TEXT,
    description TEXT,
    
    -- 管理情報
    uploader_id INT NOT NULL,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    usage_count INT DEFAULT 0,
    last_used_at DATETIME,
    
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (uploader_id) REFERENCES users(id)
);
```

## 中間テーブル

### article_categories - 記事カテゴリ関連

```sql
CREATE TABLE article_categories (
    article_id INT NOT NULL,
    category_id INT NOT NULL,
    PRIMARY KEY (article_id, category_id),
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);
```

## インデックス設計

### パフォーマンス重要インデックス

```sql
-- 記事検索・表示用
CREATE INDEX idx_articles_published ON articles(is_published, published_at DESC);
CREATE INDEX idx_articles_challenge ON articles(challenge_id, challenge_day);
CREATE INDEX idx_articles_slug ON articles(slug);

-- プロジェクト検索用
CREATE INDEX idx_projects_status ON projects(status, display_order);
CREATE INDEX idx_projects_challenge ON projects(challenge_id, challenge_day);

-- カテゴリ検索用
CREATE INDEX idx_categories_challenge ON categories(challenge_id);
CREATE INDEX idx_categories_parent ON categories(parent_id);

-- コメント管理用
CREATE INDEX idx_comments_article ON comments(article_id, is_approved);
CREATE INDEX idx_comments_approval ON comments(is_approved, created_at DESC);

-- ログイン履歴
CREATE INDEX idx_login_history_user ON login_history(user_id, login_at DESC);

-- 画像検索用
CREATE INDEX idx_images_uploader ON uploaded_images(uploader_id, upload_date DESC);
CREATE INDEX idx_images_active ON uploaded_images(is_active, usage_count DESC);
```

## JSON データ構造

### challenges.github_repos
```json
[
  {
    "name": "100-days-python",
    "url": "https://github.com/username/100-days-python",
    "description": "メインチャレンジリポジトリ"
  }
]
```

### projects.technologies
```json
["Python", "Flask", "MySQL", "Bootstrap", "JavaScript"]
```

### projects.demo_urls
```json
[
  {
    "name": "ライブデモ",
    "url": "https://example.com/demo",
    "type": "demo"
  },
  {
    "name": "GitHub Pages",
    "url": "https://username.github.io/project",
    "type": "github"
  }
]
```

### users.skills
```json
[
  {
    "category": "プログラミング言語",
    "skills": [
      {"name": "Python", "level": 4, "years": 3},
      {"name": "JavaScript", "level": 3, "years": 2}
    ]
  }
]
```

## セキュリティ仕様

### 暗号化対象データ

| テーブル | フィールド | 暗号化方式 | 用途 |
|---------|-----------|-----------|------|
| `comments` | `author_name` | Fernet | 投稿者名保護 |
| `comments` | `author_email` | Fernet | メールアドレス保護 |

### 暗号化仕様
- **暗号化ライブラリ**: `cryptography==42.0.5`
- **方式**: Fernet対称暗号化
- **キー管理**: 環境変数 `ENCRYPTION_KEY`
- **エンコーディング**: Base64
- **後方互換性**: 暗号化判定ロジックで平文データ対応

## リレーション関係図

```
[challenges] 1 ──── N [articles]
     │                   │
     │                   │ N
     │                   │
     │                   M ──── N [categories]
     │                   │
     │                   │ 1
     │                   │
     1 ──── N [projects] ─┘
                │
                │ 1
                │
                N [article_categories] N ──── 1 [categories]

[users] 1 ──── N [articles]
   │
   │ 1
   │
   N [uploaded_images]
   │
   │ 1
   │
   N [login_history]

[articles] 1 ──── N [comments]
     │
     │ 1
     │
     N [seo_analysis]
```

## 制約・ルール

### ビジネスルール
1. **アクティブチャレンジ**: 同時に1つのみ（`is_active=TRUE`）
2. **記事公開**: `is_published=TRUE` かつ `published_at` 設定必須
3. **コメント表示**: `is_approved=TRUE` かつ記事の `allow_comments=TRUE` かつ サイト設定 `comments_enabled=TRUE`
4. **カテゴリ階層**: 無制限階層だが実用上3階層まで推奨

### データ整合性
1. **CASCADE削除**: articles削除時、関連comments・seo_analysisも削除
2. **外部キー制約**: 全テーブル間で参照整合性保証
3. **UNIQUE制約**: slug, email等の重複防止

## パフォーマンス考慮事項

### SQLAlchemy最適化設定
- `lazy='selectin'`: N+1問題回避（categories, uploaded_images）
- `lazy='dynamic'`: 大量データ対応（articles.comments）
- `back_populates`: 双方向リレーション最適化

### 推奨クエリパターン

#### 公開記事一覧（ページング対応）
```python
articles = Article.query.filter(
    Article.is_published == True
).order_by(
    Article.published_at.desc()
).paginate(page=page, per_page=10)
```

#### チャレンジ別記事取得
```python
articles = Article.query.filter(
    Article.challenge_id == challenge_id,
    Article.is_published == True
).order_by(Article.challenge_day.asc()).all()
```

#### 承認済みコメント取得
```python
comments = Comment.query.filter(
    Comment.article_id == article_id,
    Comment.is_approved == True
).order_by(Comment.created_at.asc()).all()
```

## 移行・メンテナンス

### Flask-Migrate設定
```bash
# 初期化
flask db init

# マイグレーション作成
flask db migrate -m "migration description"

# 適用
flask db upgrade
```

### バックアップ戦略
```bash
# 定期バックアップ（日次）
mysqldump --single-transaction --quick --lock-tables=false \
  -u root -p portfolio_db > backup_$(date +%Y%m%d).sql

# データのみバックアップ
mysqldump --no-create-info --complete-insert \
  -u root -p portfolio_db > data_backup_$(date +%Y%m%d).sql
```

## 拡張予定

### 今後の機能追加
1. **タグシステム**: 記事・プロジェクト横断タグ機能
2. **API Rate Limiting**: APIアクセス制限テーブル
3. **統計情報**: 閲覧数・滞在時間等の分析テーブル
4. **コメント拡張**: いいね機能・返信機能強化

---

**最終更新**: 2025-09-01  
**レビュー**: MySQL 8.4 LTS環境で動作確認済み