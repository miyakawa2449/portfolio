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
- **Framework**: Python 3.10, Flask 2.3.3
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

### **フロントエンド**
- **UI Framework**: Bootstrap 5
- **Image Processing**: Cropper.js + PIL
- **JavaScript**: ES6+, リアルタイムプレビュー
- **Icons**: Font Awesome

### **インフラ・デプロイ**
- **Production**: Ubuntu 24.04 LTS + Nginx + Gunicorn
- **Cloud**: AWS Lightsail/EC2対応
- **SSL**: Let's Encrypt自動化
- **Security**: fail2ban, UFW firewall

## セットアップ

### 1. 仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 3. データベースの初期化

```bash
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

### 4. 管理者アカウントの作成

```bash
python scripts/create_admin.py
```

### 5. 開発サーバーの起動

```bash
python app.py
```

## プロジェクト構造

```
portfolio/
├── app.py              # メインアプリケーション
├── admin.py            # 管理パネル
├── models.py           # データベースモデル
├── templates/          # HTMLテンプレート
├── static/             # 静的ファイル（CSS, JS, 画像）
├── migrations/         # データベースマイグレーション
└── scripts/            # ユーティリティスクリプト
```

## ライセンス

このプロジェクトは個人のポートフォリオとして作成されています。

## 連絡先

- GitHub: [miyakawa2449]
- Email: [t.miyakawa244@gmail.com]