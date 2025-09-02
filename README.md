# Python 100 Days Challenge Portfolio

このサイトは、Pythonプログラミング100日チャレンジの学習記録と成果を公開するポートフォリオサイトです。

## 概要

- **目的**: Pythonでのプログラミングスキル向上と学習過程の記録
- **期間**: 100日間の継続的な学習チャレンジ
- **内容**: データ分析、機械学習、Web開発などの実践的なプロジェクト

## 技術スタック

### バックエンド
- **Framework**: Python 3.13, Flask 3.1.2
- **Database**: MySQL 8.4 LTS + SQLAlchemy 2.0 ORM
- **Authentication**: Flask-Login + TOTP 2FA
- **Migration**: Flask-Migrate (Alembic)
- **PDF Generation**: ReportLab（履歴書PDF出力）
- **Encryption**: cryptography（個人情報保護）

### セキュリティ
- **CSRF Protection**: Flask-WTF
- **XSS Prevention**: Bleach HTML Sanitization
- **Password**: Werkzeug Security (ハッシュ化)
- **Personal Data**: Fernet暗号化（コメント投稿者情報）
- **Security Headers**: X-Frame-Options, CSP, HSTS等
- **2FA**: Google Authenticator対応

### フロントエンド
- **UI Framework**: Bootstrap 5.3
- **Markdown Editor**: リアルタイムプレビュー対応
- **JavaScript**: ES6+, リアルタイム機能
- **Icons**: Font Awesome
- **Date Picker**: Flatpickr（日本語対応）

### インフラ・デプロイ
- **Production**: Ubuntu 24.04 LTS + Nginx + Gunicorn
- **Cloud**: AWS Lightsail
- **SSL**: Let's Encrypt自動化
- **Security**: fail2ban, UFW firewall
- **Containerization**: Docker + docker-compose

## 主要機能

### ポートフォリオ機能
- **複数チャレンジ管理**: 100日チャレンジを複数並行管理
- **進捗自動計算**: 日々の学習記録と進捗表示
- **プロジェクトショーケース**: 完成プロジェクトのギャラリー・複数デモURL対応
- **記事⇔プロジェクト双方向連携**: 関連付け・相互リンク表示
- **チャレンジ別カテゴリ管理**: 厳密分離によるコンテンツ整理
- **GitHub統合**: 複数リポジトリとの連携対応

### CMS機能
- **Markdownエディター**: リアルタイムプレビュー付き
- **画像ギャラリー**: アップロード・ギャラリー選択・検索・フィルタ
- **スキル管理UI**: ドラッグ&ドロップによる並び替え
- **コメントシステム**: 承認制・個人情報暗号化
- **SEO最適化**: メタタグ、OGP設定、JSON-LD構造化データ
- **サイト内検索**: 記事・プロジェクト横断検索

### API機能
- **RESTful API**: チャレンジ別プロジェクト・カテゴリ取得
- **画像ギャラリーAPI**: 既存画像の検索・フィルタ・選択
- **リアルタイム更新**: JavaScript連携による動的UI更新

## セットアップ

### 要件
- Python 3.13+
- MySQL 8.0+
- 仮想環境（venv/conda推奨）

### 1. リポジトリのクローン

```bash
git clone https://github.com/miyakawa2449/portfolio.git
cd portfolio
```

### 2. 仮想環境の作成と有効化

#### condaを使用する場合（推奨）：
```bash
conda create -n portfolio-py313 python=3.13
conda activate portfolio-py313
```

#### venvを使用する場合：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 4. 環境設定ファイルの作成

```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

### 5. データベースの初期化

```bash
flask db upgrade
```

### 6. 管理者アカウントの作成

```bash
python scripts/create_admin.py
```

### 7. 開発サーバーの起動

```bash
python app.py
```

サーバーは http://127.0.0.1:5001 で起動します。

## プロジェクト構造

```
portfolio/
├── app.py                 # メインアプリケーション（336行）
├── Blueprint分離アーキテクチャ
│   ├── admin.py           # 管理画面
│   ├── articles.py        # 記事機能
│   ├── projects.py        # プロジェクト機能
│   ├── search.py          # 検索機能
│   ├── categories.py      # カテゴリ機能
│   ├── landing.py         # ランディングページ
│   ├── auth.py           # 認証機能
│   ├── comments.py       # コメント機能
│   ├── api.py            # REST API
│   ├── filters.py        # テンプレートフィルター
│   ├── errors.py         # エラーハンドラー
│   └── context.py        # コンテキストプロセッサー
├── models.py              # データベースモデル
├── forms.py               # WTForms定義
├── utils.py               # ユーティリティ関数
├── seo.py                 # SEO・OGP機能
├── article_service.py     # ビジネスロジック
├── templates/             # Jinja2テンプレート
├── static/                # CSS・JS・画像
├── migrations/            # データベースマイグレーション
├── scripts/               # ユーティリティスクリプト
├── reports/               # 開発レポート
└── spec/                  # 技術仕様書
```

## 環境変数設定（.env）

```env
# Flask設定
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# データベース設定
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/portfolio_db?charset=utf8mb4

# セキュリティ設定
ADMIN_URL_PREFIX=your-custom-admin-path
LOGIN_URL_PATH=your-custom-login-path

# Google Analytics（オプション）
GA4_MEASUREMENT_ID=G-XXXXXXXXXX
```

## 開発コマンド

```bash
# 開発サーバー起動
python app.py

# データベースマイグレーション
flask db migrate -m "description"
flask db upgrade

# 管理者アカウント作成
python scripts/create_admin.py

# Docker開発環境
docker-compose -f docker-compose.dev.yml up

# Docker本番環境
docker-compose -f docker-compose.prod.yml up -d
```

## 主要データベーステーブル

- **users**: ユーザー認証・プロフィール・2FA設定
- **challenges**: 複数チャレンジ管理・進捗
- **articles**: 記事データ・SEO設定・公開管理
- **projects**: プロジェクトショーケース・技術スタック
- **categories**: カテゴリ階層・チャレンジ別分離
- **comments**: コメント・承認状態・暗号化
- **uploaded_images**: 画像管理・メタデータ

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   ```bash
   # MySQLサービスの確認
   sudo systemctl status mysql  # Linux
   brew services list           # macOS
   ```

2. **依存関係エラー**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **マイグレーションエラー**
   ```bash
   flask db stamp head
   flask db migrate -m "Fix migration"
   flask db upgrade
   ```

4. **ポート競合**
   - app.pyのポート番号を変更（デフォルト: 5001）

## 開発状況

**最新更新**: 2025年9月2日  
**現在のフェーズ**: コードリファクタリング完了・開発ツール導入準備  
**次回実装予定**: サービス層拡張・型ヒント追加・Linting導入

詳細な進捗・計画は `DEVELOPMENT_PLAN_2025-09.md` を参照してください。

## ライセンス

このプロジェクトは個人のポートフォリオとして作成されています。

## 連絡先

- GitHub: [miyakawa2449](https://github.com/miyakawa2449)
- Email: t.miyakawa244@gmail.com

---

**Made with ❤️ using Flask, MySQL, and modern web technologies**