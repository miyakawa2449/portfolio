# Python 100 Days Challenge Portfolio

このサイトは、Pythonプログラミング100日チャレンジの学習記録と成果を公開するポートフォリオサイトです。

## 概要

- **目的**: Pythonでのプログラミングスキル向上と学習過程の記録
- **期間**: 100日間の継続的な学習チャレンジ
- **内容**: データ分析、機械学習、Web開発などの実践的なプロジェクト

## 技術スタック

- **Backend**: Python 3.10+, Flask 2.x
- **Database**: SQLite with Flask-Migrate
- **Frontend**: Bootstrap 5, ES6+ JavaScript
- **Authentication**: Flask-Login with TOTP/2FA
- **Deployment**: Gunicorn, Nginx

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