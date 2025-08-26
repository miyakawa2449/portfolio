# Python 100 Days Challenge Portfolio

このサイトは、Pythonプログラミング100日チャレンジの学習記録と成果を公開するポートフォリオサイトです。

## 🚀 開発進捗

### 現在の進捗: フェーズ10完了 (100%)

**完了済みフェーズ（2025-08-22〜26）:**
- ✅ **フェーズ0**: リポジトリ準備と移行作業
- ✅ **フェーズ0.5**: データベース名の変更と環境設定の更新
- ✅ **フェーズ1**: 現状調査とバックアップ
- ✅ **フェーズ2**: データベースリセットと基本設定
- ✅ **フェーズ3**: トップページ（ランディングページ）の実装
- ✅ **フェーズ3.5**: 複数チャレンジ管理システムの実装
- ✅ **フェーズ4**: 記事とチャレンジの統合機能
- ✅ **フェーズ5**: プロジェクト紹介セクションの実装
- ✅ **フェーズ6**: 記事とプロジェクトの双方向連携機能
- ✅ **フェーズ7**: アイキャッチ画像ギャラリー機能
- ✅ **フェーズ8**: カテゴリ管理のチャレンジ別分離機能
- ✅ **フェーズ9**: 記事公開日管理機能の実装（2025-08-24完了）
- ✅ **フェーズ10**: ポートフォリオ向けプロフィールページの最適化（2025-08-25完了）

**✅ 2025-08-26午前完了作業:**
- ✅ **プロフィール情報活用拡大**: ランディングページ紹介文・プロフィールページ出身地/誕生年月追加
- ✅ **SNS情報管理システム完全刷新**: ext_jsonフィールド活用・URL形式対応・フッター全SNS表示実現
- ✅ **ナビゲーション統一化**: 重複テンプレート整理・全ページ一貫性確保・動的リンク実装
- ✅ **技術基盤強化**: from_jsonフィルター追加・安全なJSONデータ処理・エラー防止対策

**次回実装予定（フェーズ11）:**
- ⬜ **SEO・LLMO対策強化**: 構造化データ・メタデータ最適化・サイトマップ生成
- ⬜ **サイト完成度向上**: プロジェクト詳細ページ・検索機能強化・レスポンシブ最終調整
- ⬜ **品質・セキュリティ向上**: SNS URLバリデーション・パフォーマンス最適化・アクセシビリティ対応

## 概要

- **目的**: Pythonでのプログラミングスキル向上と学習過程の記録
- **期間**: 100日間の継続的な学習チャレンジ
- **内容**: データ分析、機械学習、Web開発などの実践的なプロジェクト

## 技術スタック

### **バックエンド**
- **Framework**: Python 3.13, Flask 2.3.3
- **Database**: MySQL 8.0 + SQLAlchemy 2.0 ORM
- **Authentication**: Flask-Login + TOTP 2FA
- **Email**: AWS SES統合（開発・本番対応）
- **Migration**: Flask-Migrate (Alembic)
- **PDF Generation**: ReportLab 4.0.7（履歴書PDF出力）

### **セキュリティ**
- **CSRF Protection**: Flask-WTF
- **XSS Prevention**: Bleach HTML Sanitization
- **Password**: Werkzeug Security (ハッシュ化)
- **Security Headers**: X-Frame-Options, CSP, HSTS等
- **URL Obfuscation**: カスタム管理画面URL
- **Session Management**: セキュアなセッション管理

### **フロントエンド**
- **UI Framework**: Bootstrap 5.3（2025-08-25統一移行）
- **Markdown Editor**: リアルタイムプレビュー対応
- **Image Processing**: Cropper.js + PIL
- **JavaScript**: ES6+, リアルタイムプレビュー
- **Icons**: Font Awesome
- **Code Highlighting**: Syntax highlighting for code blocks
- **Date Picker**: Flatpickr（日本語対応）
- **Progress Animation**: CSS アニメーション・プログレスバー

### **インフラ・デプロイ**
- **Production**: Ubuntu 24.04 LTS + Nginx + Gunicorn
- **Cloud**: AWS Lightsail/EC2対応
- **SSL**: Let's Encrypt自動化
- **Security**: fail2ban, UFW firewall

## 主要機能

### 🎯 実装済みポートフォリオ機能
- ✅ **複数チャレンジ管理**: 100日チャレンジを複数並行管理
- ✅ **進捗自動計算**: 日々の学習記録と進捗表示（自動/手動調整）
- ✅ **プロジェクトショーケース**: 完成プロジェクトのギャラリー・複数デモURL対応
- ✅ **記事⇔プロジェクト双方向連携**: 関連付け・相互リンク表示
- ✅ **チャレンジ別カテゴリ管理**: 厳密分離によるコンテンツ整理
- ✅ **記事公開日管理**: Flatpickrカレンダー式日付選択・公開日ソート対応
- ✅ **ランディングページ**: 現代的なポートフォリオ表示・個人ブランディング強化
- ✅ **GitHub統合**: 複数リポジトリとの連携対応
- ✅ **SNS統合**: X・Facebook・Instagram・YouTube URL管理・フッター表示統一

### ✅ 継承・拡張済み機能
- ✅ **Markdownエディター**: リアルタイムプレビュー付き
- ✅ **画像ギャラリー**: アップロード・ギャラリー選択・検索・フィルタ機能
- ✅ **画像管理システム**: クロップ・編集・メタデータ管理
- ✅ **2段階認証（2FA）**: Google Authenticator対応
- ✅ **SEO最適化**: メタタグ、OGP設定
- ✅ **コメントシステム**: 承認制コメント機能
- ✅ **動的フォーム更新**: チャレンジ選択による関連項目自動絞り込み

### 🚀 API機能
- ✅ **RESTful API**: チャレンジ別プロジェクト・カテゴリ取得
- ✅ **画像ギャラリーAPI**: 既存画像の検索・フィルタ・選択
- ✅ **リアルタイム更新**: JavaScript連携による動的UI更新

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

#### venvを使用する場合：
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

#### condaを使用する場合：
```bash
conda create -n portfolio-py313 python=3.13
conda activate portfolio-py313
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

### 主要テーブル（2025-08-23 最新）
- **users**: ユーザー認証・プロフィール・2FA設定・SNS連携
- **challenges**: 複数チャレンジ管理・進捗・リポジトリ連携
- **articles**: 記事データ・SEO設定・公開管理・チャレンジ/プロジェクト関連付け
- **projects**: プロジェクトショーケース・技術スタック・GitHub/デモURL
- **categories**: カテゴリ階層・メタ情報・チャレンジ別分離
- **uploaded_images**: 画像管理・メタデータ・ギャラリー機能
- **comments**: コメント・承認状態
- **site_settings**: サイト全体設定
- **login_history**: ログイン履歴
- **seo_analysis**: SEO分析データ

### データベース関係
- **多対多**: Articles ↔ Categories, Articles ↔ Projects (JSON)
- **一対多**: Challenges → Articles, Challenges → Projects, Challenges → Categories
- **一対多**: Users → Articles, Users → UploadedImages
- **階層構造**: Categories (parent_id による自己参照)
- **JSON関係**: Articles.project_ids, Projects.tech_stack, Challenges.github_repos

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

## 最新実装完了項目

### ✅ 2025-08-26午前完了: プロフィール・SNS・ナビゲーション統一化
- **プロフィール情報活用拡大**: introduction（紹介文）をランディングページに表示、birthplace・birthdayをプロフィールページに追加
- **SNS情報管理システム刷新**: ext_jsonフィールドを活用したURL形式のSNS管理、X・Facebook・Instagram・YouTube完全対応
- **from_jsonフィルター実装**: Jinja2テンプレートでのJSON安全解析、エラーハンドリング付き
- **テンプレート統一**: layout.htmlとpublic_layout.html両方にSNS表示機能追加、重複template整理
- **ナビゲーション一貫性**: 全ページでのナビゲーション統一、ハードコードURL除去、動的admin_user情報表示

### ✅ フェーズ10完了: ポートフォリオ向けプロフィールページの最適化（2025-08-25）
- **データベース拡張**: Userモデルに11個の新フィールド追加（職歴・スキル・学歴・資格等）
- **プロフィール写真機能**: アップロード・クロップ・プレビュー機能実装
- **スキル表示**: カテゴリ別・熟練度レベル別色分け・プログレスバー・アニメーション効果
- **職歴タイムライン**: 時系列表示・詳細な業務内容表示
- **学歴・資格セクション**: カード形式での整理表示
- **PDFダウンロード機能**: 動的日付生成による履歴書PDF作成（ReportLab使用）
- **管理画面機能**: タブ式プロフィール編集・AJAX対応・リアルタイム更新

### ✅ テンプレート・CSS大幅改善（2025-08-25）
- **Bootstrap 5.3移行**: 新しい`public_layout.html`作成・内蔵CSS完全排除
- **プログレスバー問題解決**: CSS競合解消・視覚的改善・アニメーション効果実装
- **レスポンシブ対応**: モバイル・タブレット・デスクトップ対応
- **旧ファイル整理**: バックアップ作成後、旧テンプレート・CSS削除
- **最小限ナビゲーション**: ホームリンク追加（全体ナビゲーション実装は予定）

### ✅ 技術的改善（2025-08-25）
- **Python 3.13環境**: 新conda環境作成・全依存関係更新・パフォーマンス向上
- **パッケージ管理**: email-validator等の不足パッケージ追加・requirements.txt更新
- **エラー解決**: BuildError修正・エンドポイント名整合性確保

### ✅ フェーズ9完了: 記事公開日管理機能（2025-08-24）
- **カレンダーUI実装**: Flatpickr日本語対応カレンダー式日付選択
- **記事ソート改善**: 全記事を公開日基準ソートに変更（created_at fallback付き）
- **既存データ適正化**: Challenge #1（2024-01-15開始）、Challenge #2（2025-07-01開始）
- **複数デモURL対応**: プロジェクトに複数デモURL登録・表示機能

### ✅ 個人ブランディング・UI強化（2025-08-24）
- **ランディングページ強化**: プロフィールセクション・統計情報追加
- **サイト全体ブランディング**: 「Tsuyoshi - Python 100 Days」統一
- **レスポンシブ改善**: チャレンジタイトル見切れ修正・CTAボタン最適化
- **ナビゲーション強化**: プロフィールページへの導線複数設置

## 今後の実装予定（フェーズ11）

### 🎯 次回優先実装項目
1. **SEO・LLMO対策強化**: 構造化データ（JSON-LD）実装・メタデータ最適化・サイトマップ自動生成
2. **サイト完成度向上**: プロジェクト詳細ページ作成・検索機能強化・レスポンシブ最終調整
3. **品質・セキュリティ向上**: SNS URLバリデーション強化・パフォーマンス最適化・アクセシビリティ対応
4. **コンテンツ管理強化**: 下書き記事公開予約・統計ダッシュボード・アーカイブ機能

### 📊 プロジェクト完成度: 95%
- **コア機能**: 100%完了（記事管理・プロジェクト管理・チャレンジ管理）
- **ユーザー体験**: 95%完了（ナビゲーション・SNS統合・プロフィール最適化）
- **技術基盤**: 100%完了（セキュリティ・データベース・API）
- **SEO・最適化**: 70%完了（基本実装済み・構造化データ等残存）

## ライセンス

このプロジェクトは個人のポートフォリオとして作成されています。

## 連絡先

- GitHub: [miyakawa2449](https://github.com/miyakawa2449)
- Email: t.miyakawa244@gmail.com

---

**Made with ❤️ using Flask, MySQL, and modern web technologies**