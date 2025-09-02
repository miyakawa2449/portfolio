# 環境設定仕様書

**プロジェクト**: Python 100 Days Challenge Portfolio  
**作成日**: 2025-09-01  
**バージョン**: v1.0  

## 概要

本ドキュメントは、開発・本番環境での環境変数設定と構成管理の仕様を定義します。

## 環境変数一覧

### Flask基本設定

| 変数名 | 型 | デフォルト値 | 説明 | 必須 |
|--------|----|-----------|----- |------|
| `SECRET_KEY` | string | - | Flaskアプリケーションの秘密鍵（32文字以上推奨） | ✅ |
| `FLASK_ENV` | string | `production` | 実行環境（development/production） | ❌ |

### データベース設定

| 変数名 | 型 | 説明 | 例 | 必須 |
|--------|----|----- |----|----- |
| `DATABASE_URL` | string | データベース接続URL | `mysql+pymysql://user:pass@host:3306/db` | ✅ |

**接続URL形式**:
```bash
# ローカル開発（MySQL）
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/portfolio_db?charset=utf8mb4

# AWS RDS本番環境
DATABASE_URL=mysql+pymysql://admin:password@portfolio.cluster-xxx.ap-northeast-1.rds.amazonaws.com:3306/portfolio_db?charset=utf8mb4
```

### セキュリティ設定

| 変数名 | 型 | デフォルト値 | 説明 | 必須 |
|--------|----|-----------|----- |------|
| `ADMIN_URL_PREFIX` | string | `admin` | 管理画面URLプレフィックス | ✅ |
| `LOGIN_URL_PATH` | string | `login` | ログインページURL | ✅ |
| `ENCRYPTION_KEY` | string | 自動生成 | Fernet暗号化キー（44文字Base64） | ✅ |
| `SESSION_COOKIE_SECURE` | boolean | `False` | HTTPS必須（本番はTrue） | ❌ |
| `SESSION_COOKIE_HTTPONLY` | boolean | `True` | JavaScriptアクセス無効 | ❌ |
| `SESSION_COOKIE_SAMESITE` | string | `Lax` | SameSite属性 | ❌ |

### CSRF保護設定

| 変数名 | 型 | デフォルト値 | 説明 | 必須 |
|--------|----|-----------|----- |------|
| `WTF_CSRF_ENABLED` | boolean | `true` | CSRF保護有効化 | ✅ |
| `WTF_CSRF_TIME_LIMIT` | integer | `3600` | CSRFトークン有効期限（秒） | ❌ |

### ファイルアップロード設定

| 変数名 | 型 | デフォルト値 | 説明 | 必須 |
|--------|----|-----------|----- |------|
| `MAX_CONTENT_LENGTH` | integer | `16777216` | 最大ファイルサイズ（16MB） | ❌ |
| `UPLOAD_FOLDER` | string | `static/uploads` | アップロードディレクトリ | ❌ |

### Google Analytics設定

| 変数名 | 型 | 説明 | 例 | 必須 |
|--------|----|-----|----|----- |
| `GA4_MEASUREMENT_ID` | string | GA4測定ID | `G-XXXXXXXXXX` | ❌ |

### AWS設定（将来使用）

| 変数名 | 型 | 説明 | 必須 |
|--------|----|-----|----- |
| `AWS_ACCESS_KEY_ID` | string | AWSアクセスキー | ❌ |
| `AWS_SECRET_ACCESS_KEY` | string | AWSシークレットキー | ❌ |
| `AWS_S3_BUCKET` | string | S3バケット名 | ❌ |
| `AWS_REGION` | string | AWSリージョン | ❌ |

## 環境別設定

### 開発環境（.env）

```env
# Flask設定
SECRET_KEY=development-secret-key-32-chars-min
FLASK_ENV=development

# データベース
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/portfolio_db?charset=utf8mb4

# セキュリティ（開発用）
ADMIN_URL_PREFIX=management-panel-2024
LOGIN_URL_PATH=auth-signin-2fa
ENCRYPTION_KEY=KaG31px_xtJQiub9yP6Tgyld_IXlYubCvoMJaTy5siU=
SESSION_COOKIE_SECURE=False

# CSRF
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600

# アップロード
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=static/uploads

# Analytics（開発用）
GA4_MEASUREMENT_ID=G-7WC6W8YG6B
```

### 本番環境（.env.production）

```env
# Flask設定
SECRET_KEY=production-secret-key-64-chars-cryptographically-secure
FLASK_ENV=production

# データベース
DATABASE_URL=mysql+pymysql://admin:secure-password@rds-endpoint:3306/portfolio_db?charset=utf8mb4

# セキュリティ（本番用）
ADMIN_URL_PREFIX=secure-admin-panel-random-string-2024
LOGIN_URL_PATH=secure-auth-signin-random-string
ENCRYPTION_KEY=production-encryption-key-base64-44-chars
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Strict

# CSRF
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=1800

# アップロード
MAX_CONTENT_LENGTH=8388608  # 8MB
UPLOAD_FOLDER=static/uploads

# Analytics（本番用）
GA4_MEASUREMENT_ID=G-PRODUCTION-ID

# AWS（本番用）
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=portfolio-static-assets
AWS_REGION=ap-northeast-1
```

## 設定の管理

### .env ファイル構造

```
portfolio/
├── .env                    # 開発環境設定
├── .env.example           # 設定テンプレート
├── .env.production        # 本番環境設定（Git管理外）
└── .env.testing          # テスト環境設定
```

### 設定テンプレート（.env.example）

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=development

# Database Configuration
DATABASE_URL=mysql+pymysql://username:password@localhost:3306/portfolio_db?charset=utf8mb4

# Security Configuration
ADMIN_URL_PREFIX=your-admin-prefix
LOGIN_URL_PATH=your-login-path
ENCRYPTION_KEY=your-encryption-key-here

# Session Configuration  
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_HTTPONLY=True
SESSION_COOKIE_SAMESITE=Lax

# CSRF Protection
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600

# Upload Configuration
MAX_CONTENT_LENGTH=16777216
UPLOAD_FOLDER=static/uploads

# Google Analytics (optional)
GA4_MEASUREMENT_ID=G-XXXXXXXXXX

# AWS Settings (for future use)
# AWS_ACCESS_KEY_ID=your-access-key
# AWS_SECRET_ACCESS_KEY=your-secret-key
# AWS_S3_BUCKET=your-s3-bucket-name
# AWS_REGION=ap-northeast-1
```

## 設定検証

### 起動時チェック

```python
# app.py での設定検証例
import os
from flask import Flask

def validate_config():
    """環境設定の検証"""
    required_vars = [
        'SECRET_KEY',
        'DATABASE_URL', 
        'ADMIN_URL_PREFIX',
        'LOGIN_URL_PATH'
    ]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        raise ValueError(f"必須環境変数が設定されていません: {missing}")
    
    # 暗号化キー自動生成
    if not os.environ.get('ENCRYPTION_KEY'):
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        print(f"ENCRYPTION_KEY={key}")
        raise ValueError("ENCRYPTION_KEYを.envファイルに設定してください")
```

## セキュリティベストプラクティス

### 秘密鍵管理
1. **SECRET_KEY**: 32文字以上のランダム文字列
2. **ENCRYPTION_KEY**: Fernet.generate_key()で生成
3. **パスワード**: 環境変数で管理、コードにハードコード禁止

### 本番環境特別設定
1. **HTTPS必須**: `SESSION_COOKIE_SECURE=True`
2. **管理URL難読化**: 推測困難な長いランダム文字列
3. **CSRFタイムアウト短縮**: `WTF_CSRF_TIME_LIMIT=1800`（30分）

### 開発・本番分離
```python
# 環境判定
FLASK_ENV = os.environ.get('FLASK_ENV', 'production')
DEBUG = FLASK_ENV == 'development'

# 環境別設定
if FLASK_ENV == 'production':
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)
else:
    app.config['SESSION_COOKIE_SECURE'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
```

## トラブルシューティング

### よくある設定問題

1. **データベース接続エラー**
   ```bash
   # MySQL サービス確認
   sudo systemctl status mysql
   brew services list | grep mysql
   ```

2. **暗号化キーエラー**
   ```python
   # 新しいキー生成
   from cryptography.fernet import Fernet
   print(Fernet.generate_key().decode())
   ```

3. **CSRF トークンエラー**
   ```bash
   # タイムアウト値確認
   echo $WTF_CSRF_TIME_LIMIT
   ```

### 設定確認コマンド

```bash
# 環境変数確認
env | grep -E "(SECRET_KEY|DATABASE_URL|ADMIN_URL)"

# データベース接続テスト
python -c "
import os
from sqlalchemy import create_engine
engine = create_engine(os.environ['DATABASE_URL'])
print('DB接続成功')
"

# 暗号化テスト
python -c "
import os
from cryptography.fernet import Fernet
key = os.environ['ENCRYPTION_KEY']
f = Fernet(key.encode())
print('暗号化キー有効')
"
```

---

**最終更新**: 2025-09-01  
**本番デプロイ前**: 必ず本番環境用の.envファイル作成と設定検証を実施