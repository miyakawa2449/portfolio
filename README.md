# Python 100 Days Challenge Portfolio

このサイトは、Pythonプログラミング100日チャレンジの学習記録と成果を公開するポートフォリオサイトです。

## 🚀 移行作業進捗

### 現在の進捗: フェーズ2/8完了 (25%)

- ✅ **フェーズ0**: リポジトリ準備と移行作業
- ✅ **フェーズ0.5**: データベース名の変更と環境設定の更新
- ✅ **フェーズ1**: 現状調査とバックアップ
- ✅ **フェーズ2**: データベースリセットと基本設定
- ⬜ **フェーズ3**: トップページ（ランディングページ）の実装
- ⬜ **フェーズ4**: 100日チャレンジ進捗機能の実装
- ⬜ **フェーズ5**: プロジェクト展示ページの実装
- ⬜ **フェーズ6**: AI SEO（AIO/LLMO）機能とsitemap.xmlの実装
- ⬜ **フェーズ7**: 検索機能の修正
- ⬜ **フェーズ8**: UIの調整とテスト

## 概要

- **目的**: Pythonでのプログラミングスキル向上と学習過程の記録
- **期間**: 100日間の継続的な学習チャレンジ
- **内容**: データ分析、機械学習、Web開発などの実践的なプロジェクト

## 技術スタック

### **バックエンド**
- **Framework**: Python 3.10+, Flask 2.3.3
- **Database**: MySQL 8.0 + SQLAlchemy 2.0 ORM
- **Authentication**: Flask-Login + TOTP 2FA
- **Email**: AWS SES統合（開発・本番対応）
- **Migration**: Flask-Migrate (Alembic)

### **セキュリティ**
- **CSRF Protection**: Flask-WTF
- **XSS Prevention**: Bleach HTML Sanitization
- **Password**: Werkzeug Security (ハッシュ化)
- **Security Headers**: X-Frame-Options, CSP, HSTS等
- **URL Obfuscation**: カスタム管理画面URL
- **Session Management**: セキュアなセッション管理

### **フロントエンド**
- **UI Framework**: Bootstrap 5
- **Markdown Editor**: リアルタイムプレビュー対応
- **Image Processing**: Cropper.js + PIL
- **JavaScript**: ES6+, リアルタイムプレビュー
- **Icons**: Font Awesome
- **Code Highlighting**: Syntax highlighting for code blocks

### **インフラ・デプロイ**
- **Production**: Ubuntu 24.04 LTS + Nginx + Gunicorn
- **Cloud**: AWS Lightsail/EC2対応
- **SSL**: Let's Encrypt自動化
- **Security**: fail2ban, UFW firewall

## 主要機能

### 🎯 ポートフォリオ機能（実装予定）
- **100日チャレンジ進捗管理**: 日々の学習記録と進捗表示
- **プロジェクトショーケース**: 完成プロジェクトのギャラリー
- **スキルセット表示**: 習得技術の可視化
- **GitHub統合**: リポジトリとの連携

### ✅ 既存機能（mini-blogから継承）
- **Markdownエディター**: リアルタイムプレビュー付き
- **画像管理システム**: アップロード、編集、管理機能
- **2段階認証（2FA）**: Google Authenticator対応
- **SEO最適化**: メタタグ、OGP設定
- **コメントシステム**: 承認制コメント機能
- **カテゴリ管理**: 階層的カテゴリ構造

## セットアップ

### 要件
- Python 3.10+
- MySQL 8.0+
- 仮想環境（venv/conda推奨）

### 1. リポジトリのクローン

```bash
git clone https://github.com/miyakawa2449/portfolio.git
cd portfolio
```

### 2. 仮想環境の作成と有効化

#### venvを使用する場合：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### condaを使用する場合：
```bash
conda create -n portfolio python=3.10
conda activate portfolio
```

### 3. 環境設定ファイルの作成

```bash
cp .env.example .env
# .envファイルを編集して必要な情報を設定
```

### 4. 依存関係のインストール

```bash
pip install -r requirements.txt
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
├── 🐍 Core Application
│   ├── app.py                 # メインアプリケーション
│   ├── admin.py               # 管理画面Blueprint
│   ├── models.py              # データベースモデル
│   ├── forms.py               # WTForms定義
│   ├── article_service.py     # 記事管理サービス
│   └── ga4_analytics.py       # Google Analytics統合
├── 📁 Static Assets
│   ├── static/
│   │   ├── css/              # スタイルシート
│   │   ├── js/               # JavaScriptファイル
│   │   └── uploads/          # アップロード画像
│   └── templates/            # Jinja2テンプレート
│       ├── admin/            # 管理画面テンプレート
│       └── *.html            # 公開ページテンプレート
├── 🗄️ Database
│   ├── migrations/           # データベースマイグレーション
│   └── instance/             # SQLiteデータベース（開発用）
├── 📝 Documentation
│   ├── reports/              # 作業レポート・計画書
│   ├── CLAUDE.md            # AIアシスタント用ガイド
│   ├── WORK_STATUS.md       # 作業進捗管理
│   └── README.md            # このファイル
└── ⚙️ Configuration
    ├── requirements.txt      # Python依存関係
    ├── .env                  # 環境変数（要作成）
    ├── .env.example         # 環境変数テンプレート
    └── .gitignore           # Git除外設定
```

## データベース設計

### 主要テーブル
- **users**: ユーザー認証・プロフィール・2FA設定
- **articles**: 記事データ・SEO設定・公開管理
- **categories**: カテゴリ階層・メタ情報
- **uploaded_images**: 画像管理・メタデータ
- **comments**: コメント・承認状態
- **site_settings**: サイト全体設定
- **login_history**: ログイン履歴
- **seo_analysis**: SEO分析データ

### データベース関係
- **多対多**: Articles ↔ Categories
- **一対多**: Users → Articles, Users → UploadedImages
- **階層構造**: Categories (parent_id による自己参照)

## 環境変数設定（.env）

```env
# Flask設定
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# データベース設定
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/portfolio_db?charset=utf8mb4

# セキュリティ設定
ADMIN_URL_PREFIX=management-panel-2024
LOGIN_URL_PATH=auth-signin-2fa

# Google Analytics（オプション）
GA4_MEASUREMENT_ID=G-XXXXXXXXXX

# AWS設定（将来使用予定）
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
```

## セキュリティ機能

- **2段階認証（2FA）**: Google Authenticator対応
- **CSRF保護**: すべてのフォームで実装
- **XSS対策**: Bleachによる入力サニタイゼーション
- **SQLインジェクション対策**: SQLAlchemy ORM使用
- **セキュアセッション**: HTTPOnly、SameSite設定
- **カスタムURL**: 管理画面URLの難読化

## トラブルシューティング

### よくある問題

1. **データベース接続エラー**
   ```bash
   # MySQLサービスの確認
   sudo systemctl status mysql
   # または
   brew services list  # macOS
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

## 今後の実装予定

1. **フェーズ3**: ランディングページ実装
2. **フェーズ4**: 100日チャレンジ進捗機能
3. **フェーズ5**: プロジェクトショーケース
4. **フェーズ6**: AI SEO最適化
5. **フェーズ7**: 検索機能の修正
6. **フェーズ8**: UI/UXの最終調整

## ライセンス

このプロジェクトは個人のポートフォリオとして作成されています。

## 連絡先

- GitHub: [miyakawa2449](https://github.com/miyakawa2449)
- Email: t.miyakawa244@gmail.com

---

**Made with ❤️ using Flask, MySQL, and modern web technologies**