# API仕様書

**プロジェクト**: Python 100 Days Challenge Portfolio  
**作成日**: 2025-09-01  
**APIバージョン**: v1.0  

## 概要

このドキュメントは、ポートフォリオサイトの公開API・管理API・認証APIの全エンドポイント仕様を定義します。

## ベースURL

```
本番環境: https://miyakawa.codes
開発環境: http://127.0.0.1:5001
```

## 認証

### 管理画面アクセス
- **URL**: `/{ADMIN_URL_PREFIX}/`（環境変数で設定）
- **認証**: Flask-Login + TOTP 2FA
- **セッション**: HTTPOnly, SameSite=Strict

## API分類

### 1. 公開API（認証不要）

#### `/api/` - RESTful API

| エンドポイント | メソッド | 説明 | レスポンス |
|-------------|--------|------|-----------|
| `/api/projects/by-challenge/<challenge_id>` | GET | チャレンジ別プロジェクト一覧 | JSON |
| `/api/categories/by-challenge/<challenge_id>` | GET | チャレンジ別カテゴリ一覧 | JSON |
| `/api/images/gallery` | GET | 画像ギャラリー一覧 | JSON |

#### `/` - ランディングページ (landing_bp)

| エンドポイント | メソッド | 説明 | テンプレート |
|-------------|--------|------|-------------|
| `/` | GET | ビジネスランディングページ | `landing.html` |
| `/portfolio` | GET | ポートフォリオ一覧 | `portfolio.html` |
| `/services` | GET | サービス紹介 | `services.html` |
| `/story` | GET | ストーリー | `story.html` |
| `/about/` | GET | プロフィールページ | `about.html` |

#### `/blog/` - 記事機能 (articles_bp)

| エンドポイント | メソッド | 説明 | パラメータ |
|-------------|--------|------|-----------|
| `/blog` | GET | 記事一覧（全チャレンジ） | - |
| `/blog/page/<page>` | GET | 記事一覧（ページング） | page: int |
| `/blog/challenge/<challenge_id>` | GET | チャレンジ別記事一覧 | challenge_id: int |
| `/blog/challenge/<challenge_id>/page/<page>` | GET | チャレンジ別記事（ページング） | challenge_id: int, page: int |
| `/article/<slug>/` | GET | 記事詳細ページ | slug: str |

#### `/projects/` - プロジェクト機能 (projects_bp)

| エンドポイント | メソッド | 説明 | パラメータ |
|-------------|--------|------|-----------|
| `/projects` | GET | プロジェクト一覧 | - |
| `/projects/page/<page>` | GET | プロジェクト一覧（ページング） | page: int |
| `/projects/challenge/<challenge_id>` | GET | チャレンジ別プロジェクト | challenge_id: int |
| `/projects/challenge/<challenge_id>/page/<page>` | GET | チャレンジ別（ページング） | challenge_id: int, page: int |

#### その他機能別エンドポイント

| エンドポイント | メソッド | 説明 | Blueprint | 備考 |
|-------------|--------|------|-----------|------|
| `/category/<slug>/` | GET | カテゴリページ | categories_bp | slug: str |
| `/search` | GET | サイト内検索 | search_bp | q, type, challenge_id |
| `/download/resume/<user_id>` | GET | 履歴書PDF | landing_bp | PDF生成・ダウンロード |
| `/add_comment/<article_id>` | POST | コメント投稿 | comments_bp | 要バリデーション |

### 2. 認証API

#### `/auth/` - 認証システム

| エンドポイント | メソッド | 説明 | フォームデータ |
|-------------|--------|------|-------------|
| `/{LOGIN_URL_PATH}/` | GET, POST | ログイン | email, password |
| `/totp_verify/` | GET, POST | TOTP認証 | totp_token |
| `/logout/` | GET | ログアウト | - |
| `/totp_setup/` | GET, POST | 2FA設定 | setup_token |
| `/totp_disable/` | GET, POST | 2FA無効化 | password |
| `/password_reset_request/` | GET, POST | パスワードリセット要求 | email |
| `/password_reset/<token>/` | GET, POST | パスワードリセット実行 | new_password |

### 3. 管理API（認証必須）

#### `/{ADMIN_URL_PREFIX}/` - 管理画面

**ダッシュボード**
- `GET /`: 管理ダッシュボード
- `GET /debug/simple`: 簡易デバッグ情報
- `GET /debug/stats`: 統計情報

**ユーザー管理**
- `GET /users/`: ユーザー一覧
- `GET, POST /user/create/`: ユーザー作成
- `GET, POST /user/edit/<user_id>/`: ユーザー編集
- `POST /user/delete/<user_id>/`: ユーザー削除
- `GET /user/detail/<user_id>/`: ユーザー詳細
- `POST /user/<user_id>/reset-2fa/`: 2FAリセット
- `POST /user/<user_id>/reset-password/`: パスワードリセット

**記事管理**
- `GET /articles/`: 記事一覧
- `GET, POST /article/create/`: 記事作成
- `GET, POST /article/edit/<article_id>/`: 記事編集
- `POST /article/toggle_status/<article_id>/`: 公開状態切り替え
- `POST /article/delete/<article_id>/`: 記事削除
- `GET /article/preview/<article_id>`: 記事プレビュー

**カテゴリ管理**
- `GET /categories/`: カテゴリ一覧
- `GET, POST /category/create/`: カテゴリ作成
- `GET, POST /category/edit/<category_id>/`: カテゴリ編集
- `POST /category/delete/<category_id>/`: カテゴリ削除
- `POST /categories/bulk-delete`: 一括削除

**コメント管理**
- `GET /comments/`: コメント一覧
- `POST /comment/approve/<comment_id>/`: 承認
- `POST /comment/reject/<comment_id>/`: 拒否  
- `POST /comment/delete/<comment_id>/`: 削除
- `POST /comments/bulk-action/`: 一括操作

**画像管理**
- `POST /upload_image`: 画像アップロード
- `GET /images`: 画像一覧・検索
- `PUT /images/<image_id>`: 画像メタデータ更新
- `DELETE /images/<image_id>`: 画像削除
- `GET /images_manager/`: 画像管理画面

**SEO管理**
- `GET /seo-tools/`: SEOツール一覧
- `GET /static-pages-seo/`: 静的ページSEO管理
- `GET, POST /static-pages-seo/<page_slug>/edit`: 静的ページSEO編集
- `GET, POST /seo-analyze/<article_id>`: 記事SEO分析
- `GET, POST /seo-batch-analyze/`: 一括SEO分析
- `POST /api/seo-suggestions`: SEO提案API
- `GET /seo/dashboard/`: SEOダッシュボード

**チャレンジ管理**
- `GET /challenges`: チャレンジ一覧
- `GET, POST /challenge/new`: チャレンジ作成
- `GET, POST /challenge/<challenge_id>/edit`: チャレンジ編集
- `POST /challenge/<challenge_id>/delete`: チャレンジ削除

**プロジェクト管理**
- `GET /projects`: プロジェクト一覧
- `GET, POST /project/new`: プロジェクト作成
- `GET, POST /project/<project_id>/edit`: プロジェクト編集
- `POST /project/<project_id>/delete`: プロジェクト削除

**プロフィール管理**
- `GET, POST /portfolio/<user_id>`: プロフィール編集
- `GET, POST /portfolio/<user_id>/skills`: スキル管理
- `GET, POST /portfolio/<user_id>/career`: 職歴管理
- `GET, POST /portfolio/<user_id>/education`: 学歴管理
- `GET, POST /portfolio/<user_id>/certifications`: 資格管理

**サイト設定**
- `GET, POST /site_settings/`: サイト設定管理

**アナリティクス**
- `GET, POST /analytics/`: Google Analytics設定
- `GET /access-logs/`: アクセスログ
- `GET /access-logs/download/<log_file>`: ログダウンロード

**ユーティリティ**
- `POST /preview_markdown`: Markdownプレビュー
- `POST /user/<user_id>/request_email_change/`: メール変更要求

### 4. AJAX API

**動的フォーム更新**
```javascript
// チャレンジ変更時のプロジェクト・カテゴリ更新
fetch(`/api/projects/by-challenge/${challengeId}`)
fetch(`/api/categories/by-challenge/${challengeId}`)
```

**画像ギャラリー**
```javascript
// ギャラリー画像一覧取得
fetch('/api/images/gallery')
```

## APIレスポンス仕様

### 成功レスポンス

#### プロジェクト一覧 `/api/projects/by-challenge/<challenge_id>`
```json
{
  "projects": [
    {
      "id": 1,
      "title": "Webスクレイピングツール",
      "challenge_day": 15
    }
  ]
}
```

#### カテゴリ一覧 `/api/categories/by-challenge/<challenge_id>`
```json
{
  "categories": [
    {
      "id": 1,
      "name": "データ分析"
    }
  ]
}
```

#### 画像ギャラリー `/api/images/gallery`
```json
{
  "images": [
    {
      "filename": "screenshot.png",
      "url": "/static/uploads/content/screenshot.png",
      "category": "content",
      "size": 245760,
      "created_at": "2025-09-01T12:00:00",
      "modified_at": "2025-09-01T12:00:00"
    }
  ],
  "total": 42
}
```

### エラーレスポンス

```json
{
  "error": "リソースが見つかりません",
  "code": 404,
  "message": "指定されたチャレンジが存在しません"
}
```

## 認証・認可

### セッション管理
- **エンジン**: Flask-Login
- **タイムアウト**: 24時間（remember_me有効時30日）
- **CSRF**: Flask-WTF による全フォーム保護

### 権限レベル
1. **匿名ユーザー**: 公開ページ・API閲覧のみ
2. **認証ユーザー**: 管理画面アクセス可能
3. **管理者**: 全機能アクセス可能

### 2FA設定
- **TOTP**: Google Authenticator対応
- **必須**: `totp_enabled=True` の場合、ログイン後TOTP認証必須
- **リカバリ**: 管理者による2FAリセット機能

## レート制限・セキュリティ

### セキュリティヘッダー
```http
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

### 入力検証
- **CSRF**: 全POST/PUT/DELETEリクエストでトークン検証
- **XSS対策**: Bleach HTMLサニタイゼーション
- **SQLi対策**: SQLAlchemy ORM使用、生SQL禁止

### データ暗号化
- **対象**: コメント投稿者名・メールアドレス
- **方式**: Fernet対称暗号化（cryptography）
- **キー管理**: 環境変数 `ENCRYPTION_KEY`

## パフォーマンス

### キャッシュ戦略
- **静的ファイル**: Nginx 24時間キャッシュ
- **API応答**: No-Cache（動的データのため）
- **画像**: ブラウザキャッシュ 7日間

### データベース最適化
- **N+1問題**: SQLAlchemy `selectin` ローディング
- **インデックス**: 検索・ソート頻度の高いカラム
- **ページング**: 全一覧ページで実装（10件/ページ）

## エラーハンドリング

### HTTPステータスコード
- `200`: 成功
- `201`: 作成成功  
- `400`: バリデーションエラー
- `401`: 認証エラー
- `403`: 権限エラー
- `404`: リソース未発見
- `500`: サーバーエラー

### カスタムエラーページ
- `404.html`: リソース未発見
- `500.html`: サーバーエラー
- `admin/error.html`: 管理画面エラー

## 統合・連携

### 外部API連携
- **Google Analytics**: GA4 Measurement API
- **AWS SES**: メール送信API
- **Let's Encrypt**: SSL証明書自動更新

### oEmbed対応
- **Twitter/X**: 公式oEmbed API
- **YouTube**: oEmbed API  
- **Instagram**: 標準blockquote形式

## API使用例

### JavaScript フロントエンド統合

```javascript
// チャレンジ変更時の動的更新
async function updateFormData(challengeId) {
    const [projects, categories] = await Promise.all([
        fetch(`/api/projects/by-challenge/${challengeId}`).then(r => r.json()),
        fetch(`/api/categories/by-challenge/${challengeId}`).then(r => r.json())
    ]);
    
    updateSelectOptions('project_ids', projects.projects);
    updateSelectOptions('category_ids', categories.categories);
}

// 画像ギャラリー読み込み
async function loadImageGallery() {
    const response = await fetch('/api/images/gallery');
    const data = await response.json();
    renderImageGrid(data.images);
}
```

### Python クライアント例

```python
import requests

# API呼び出し例
def get_challenge_projects(challenge_id):
    response = requests.get(f'/api/projects/by-challenge/{challenge_id}')
    return response.json()

# 管理API例（認証必要）
def upload_image(file_path, session):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = session.post('/admin/upload_image', files=files)
        return response.json()
```

## 開発・テスト

### API テスト

```bash
# プロジェクト一覧取得
curl -X GET "http://127.0.0.1:5001/api/projects/by-challenge/1"

# カテゴリ一覧取得  
curl -X GET "http://127.0.0.1:5001/api/categories/by-challenge/1"

# 画像ギャラリー
curl -X GET "http://127.0.0.1:5001/api/images/gallery"
```

### 管理API テスト（要認証）

```bash
# セッション取得
curl -c cookies.txt -X POST "http://127.0.0.1:5001/auth-signin-2fa/" \
  -d "email=admin@example.com&password=password"

# 記事作成
curl -b cookies.txt -X POST "http://127.0.0.1:5001/admin/article/create/" \
  -d "title=Test&body=Content&csrf_token=token"
```

## セキュリティ考慮事項

### 機密情報
- **管理URL**: `ADMIN_URL_PREFIX` で難読化
- **ログインURL**: `LOGIN_URL_PATH` で難読化  
- **DB認証情報**: 環境変数で管理
- **暗号化キー**: 32バイト長・自動生成

### アクセス制御
- **管理画面**: `@login_required` デコレータ
- **CSRF**: `@csrf.exempt` は使用禁止
- **ファイルアップロード**: 許可拡張子・サイズ制限

---

**最終更新**: 2025-09-01  
**レビュー**: Flask 3.1.2 + MySQL 8.4 環境で動作確認済み