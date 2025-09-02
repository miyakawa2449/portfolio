# CLAUDE.md

This file provides guidance to Claude Code when working with the Python 100 Days Challenge Portfolio project.

## Project Overview

This is a **Python 100 Days Challenge Portfolio Site** built on top of a Flask-based CMS system. The project showcases a 100-day Python programming journey with daily learning records, projects, and progress tracking.

**Current Status**: Initial setup phase - migrating from mini-blog base with customizations for portfolio functionality.

## Technology Stack

- **Backend**: Python 3.10+, Flask 2.x, SQLAlchemy ORM
- **Database**: MySQL 8.0+ with Flask-Migrate (database: `portfolio_db`)
- **Frontend**: Bootstrap 5, ES6+ JavaScript
- **Security**: Flask-Login, TOTP/2FA
- **Content**: Markdown processing, Syntax highlighting for code
- **Deployment**: Gunicorn WSGI server, Nginx reverse proxy

## Project Goals

1. **Document 100 Days of Python Learning**: Daily blog posts with code examples and learnings
2. **Showcase Projects**: Dedicated section for completed projects with demos
3. **Track Progress**: Visual progress tracking (days completed, skills acquired)
4. **Portfolio Presentation**: Professional presentation for potential employers

## Database Configuration

**IMPORTANT**: This project uses MySQL database `portfolio_db` instead of SQLite.

Current configuration in `.env`:
```
DATABASE_URL=mysql+pymysql://root:sa19qiZ-dq9iZ6p-@localhost:3306/portfolio_db?charset=utf8mb4
```

## Key Features to Implement

### 1. Landing Page
- Hero section with challenge overview
- Current progress (X/100 days)
- Skills and technologies showcase
- Latest learning highlights
- GitHub integration

### 2. Learning Blog
- Day-by-day learning records
- Category filtering (Data Science, Web Dev, Automation, etc.)
- Code syntax highlighting
- Search functionality (needs fixing)

### 3. Projects Showcase
- Dedicated project gallery
- Live demos where applicable
- Technical documentation
- GitHub repository links

### 4. Progress Tracking
- Challenge day counter in articles
- Visual progress calendar
- Statistics dashboard
- Learning streaks

## Directory Structure
```
portfolio/
├── app.py              # Main application (update DB name)
├── admin.py            # Admin panel
├── models.py           # Database models
├── templates/          # HTML templates
├── static/             # CSS, JS, images
├── migrations/         # Database migrations
├── scripts/            # Utility scripts
└── reports/            # Documentation
```

## Removed Features (from mini-blog)
- WordPress import functionality
- Generic CMS features not relevant to portfolio

## Development Workflow

1. Update database configuration
2. Create new migrations for portfolio-specific models
3. Implement landing page
4. Fix search functionality
5. Add progress tracking features
6. Create project showcase system

## Environment Variables

**Important**: Check `/Users/tsuyoshi/development/mini-blog/.env` for complete reference.

Essential `.env` settings:
```
# Database
DATABASE_URL=mysql+pymysql://root:sa19qiZ-dq9iZ6p-@localhost:3306/portfolio_db?charset=utf8mb4

# Security
SECRET_KEY=your-secret-key
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600

# URLs
ADMIN_URL_PREFIX=management-panel-2024
LOGIN_URL_PATH=auth-signin-2fa
```

## Common Commands

```bash
# Development server
python app.py

# Database migrations
flask db init
flask db migrate -m "description"
flask db upgrade

# Create admin user
python scripts/create_admin.py
```

## Notes for Claude Code

- Always use `portfolio.db` for database operations
- Focus on portfolio and learning showcase features
- Maintain clean, professional design suitable for recruiters
- Ensure all code examples have proper syntax highlighting
- Keep the 100-day challenge progress as the central theme
- **Environment Variables**: When a required .env setting is missing, always check `/Users/tsuyoshi/development/mini-blog/.env` for reference before implementing fixes

## Specification Reference Rule

**IMPORTANT**: Before making any code modifications or debugging issues, ALWAYS check the relevant specification documents in the `spec/` folder:

- `spec/database_specification.md` - For database schema, relationships, field types
- `spec/api_specification.md` - For endpoint routing, Blueprint structure, URL patterns
- `spec/environment_configuration.md` - For environment variables, configuration settings
- `spec/system_architecture.md` - For overall system design, Blueprint organization

### When to Check Specifications

1. **Blueprint modifications** - Check `api_specification.md` for correct endpoint patterns
2. **Database queries** - Check `database_specification.md` for relationship definitions
3. **Template url_for() changes** - Check `api_specification.md` for Blueprint endpoint names
4. **Environment issues** - Check `environment_configuration.md` for required variables
5. **Architecture decisions** - Check `system_architecture.md` for design patterns

### Specification Update Rule

When making architectural changes (Blueprint creation, endpoint modifications, etc.), update the relevant specification files to maintain documentation accuracy.

## Debugging Memories

- **Twitter oEmbed Debugging**: Captured Twitter HTML embedding process with debug logs showing successful retrieval and processing of tweet URLs
  - Successfully handled Twitter status URL: https://x.com/miyakawa2449/status/1953377889820561624
  - Debug logs show oEmbed success with HTML generation
  - Demonstrated dynamic content retrieval and embedding capabilities

- **Anchor Generation Logs**: Captured debug logs for automatic anchor generation for headings
  - Successfully created anchors for multiple headings:
    - `heading-1-見出し` for "見出し"
    - `heading-2-見出し2` for "見出し2"
    - `heading-3-見出し3` for "見出し3"

- **URL Processing Debugging**: Logs show successful processing of multiple URL types
  - Twitter URL processing
  - YouTube URL oEmbed (https://youtu.be/LmHB5I_o5K4?si=Umug8tt_qrFFgn_z)
  - Instagram URL oEmbed
  - Blog post URL with OGP card generation (https://miyakawa.me/2023/03/27/9324/)

- **Server Request Logging**: Captured local server request logs showing successful resource retrievals
  - CSS, JS, image, and content file requests
  - 200 OK status for most resources
  - 404 for favicon.ico (expected)

## Development Best Practices

### Code Organization Rules (2025年9月学習済み)

**重要**: 以下の教訓に基づき、今後の開発では最初から適切なファイル分離を行うこと。

#### 1. Blueprint-First Development
- 新機能は最初からBlueprint作成（app.pyに直接追加しない）
- 50行を超える機能は即座に分離検討
- テンプレートでは最初からBlueprint前提のurl_for()使用

#### 2. 巨大ファイル分割の教訓
- **1252行ファイルの分割** = 2日間の集中作業が必要
- **url_for()修正** = 全テンプレートの修正が必要
- **段階的テスト** = エラー切り分けのため必須

#### 3. 推奨ファイル構成
```
├── app.py              # アプリ初期化のみ（300-400行以下）
├── blueprints/
│   ├── auth.py         # 認証関連
│   ├── admin.py        # 管理機能
│   ├── articles.py     # 記事機能
│   ├── projects.py     # プロジェクト機能
│   ├── search.py       # 検索機能
│   ├── categories.py   # カテゴリ機能
│   └── landing.py      # ランディングページ
├── filters.py          # テンプレートフィルター
├── errors.py           # エラーハンドラー
└── context.py          # コンテキストプロセッサー
```

#### 4. 予防的開発ルール
- **機能追加時**: 即座に適切なBlueprint配置
- **50行ルール**: 関数が50行超えたら分離検討
- **テンプレート**: Blueprint endpoint使用必須
- **テスト**: 機能追加毎に段階的テスト実行

## Translation and Verification Memories

- 10番の確認メモ: 10 ですが、私がやりたいこと正確に伝わっているか確認したいです。