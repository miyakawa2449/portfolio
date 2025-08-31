"""
Utility Functions - 一般的なユーティリティ関数
"""
import bleach
from flask import current_app

def sanitize_html(content):
    """HTMLコンテンツをサニタイズ"""
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'a', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']
    allowed_attributes = {'a': ['href', 'title']}
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)

def clear_ogp_cache():
    """OGPキャッシュをクリアする関数"""
    from app import ogp_cache
    ogp_cache.clear()
    current_app.logger.info("🗑️ OGP cache cleared")

def perform_search(query, search_filter='all'):
    """サイト内検索を実行"""
    from models import Article, Project, db
    from sqlalchemy import select, or_
    
    if not query or len(query.strip()) < 2:
        return {'articles': [], 'projects': [], 'total': 0}
    
    query = query.strip()
    results = {'articles': [], 'projects': [], 'total': 0}
    
    try:
        if search_filter in ['all', 'articles']:
            # 記事検索（LIKE演算子使用）
            article_query = select(Article).where(
                Article.status == 'published'
            ).where(
                or_(
                    Article.title.like(f'%{query}%'),
                    Article.summary.like(f'%{query}%'),
                    Article.content.like(f'%{query}%')
                )
            ).order_by(Article.published_at.desc())
            
            articles = db.session.execute(article_query).scalars().all()
            results['articles'] = articles
        
        if search_filter in ['all', 'projects']:
            # プロジェクト検索
            project_query = select(Project).where(
                Project.status == 'active'
            ).where(
                or_(
                    Project.title.like(f'%{query}%'),
                    Project.description.like(f'%{query}%'),
                    Project.summary.like(f'%{query}%')
                )
            ).order_by(Project.created_at.desc())
            
            projects = db.session.execute(project_query).scalars().all()
            results['projects'] = projects
        
        results['total'] = len(results['articles']) + len(results['projects'])
        current_app.logger.info(f"🔍 Search completed: query='{query}', filter='{search_filter}', total={results['total']}")
        
    except Exception as e:
        current_app.logger.error(f"❌ Search error: {e}")
        results = {'articles': [], 'projects': [], 'total': 0, 'error': str(e)}
    
    return results

def generate_table_of_contents(markdown_content):
    """Markdownから目次を生成"""
    import re
    
    if not markdown_content:
        return None
    
    # 見出しを抽出するパターン（# ## ### #### ##### ######）
    heading_pattern = r'^(#{1,6})\s+(.+)'
    headings = []
    heading_counter = 0
    
    for line_num, line in enumerate(markdown_content.split('\n'), 1):
        line = line.strip()
        match = re.match(heading_pattern, line)
        if match:
            heading_counter += 1  # 見出しの順番をカウント
            level = len(match.group(1))  # # の数
            title = match.group(2).strip()
            
            # アンカー用のIDを生成（日本語対応）
            anchor_id = re.sub(r'[^\w\-_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '-', title.lower())
            anchor_id = re.sub(r'-+', '-', anchor_id).strip('-')
            anchor_id = f"heading-{heading_counter}-{anchor_id}" if anchor_id else f"heading-{heading_counter}"
            
            headings.append({
                'level': level,
                'title': title,
                'anchor': anchor_id,
                'line': line_num
            })
    
    return headings if headings else None

def add_heading_anchors(html_content):
    """HTML見出しにアンカーIDを追加（目次と一致させる）"""
    if not html_content:
        return html_content
    
    import re
    from bs4 import BeautifulSoup
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        heading_counter = 0
        
        # h1〜h6タグを順番に検索してIDを追加
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            heading_counter += 1
            title = heading.get_text().strip()
            
            # 目次生成と同じロジックでアンカーIDを生成
            anchor_id = re.sub(r'[^\w\-_\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', '-', title.lower())
            anchor_id = re.sub(r'-+', '-', anchor_id).strip('-')
            anchor_id = f"heading-{heading_counter}-{anchor_id}" if anchor_id else f"heading-{heading_counter}"
            
            heading['id'] = anchor_id
            current_app.logger.debug(f"Added anchor: {anchor_id} for heading: {title}")
        
        return str(soup)
        
    except Exception as e:
        current_app.logger.error(f"Error adding heading anchors: {e}")
        return html_content

def generate_article_structured_data(article):
    """記事用のJSON-LD構造化データを生成"""
    import json
    from datetime import datetime
    
    try:
        # 作成者情報を安全に取得
        author_name = "Unknown Author"  # デフォルト値
        if hasattr(article, 'user') and article.user:
            if hasattr(article.user, 'display_name') and article.user.display_name:
                author_name = article.user.display_name
            elif hasattr(article.user, 'email') and article.user.email:
                author_name = article.user.email
        
        # カテゴリ情報を取得
        categories = []
        if hasattr(article, 'categories') and article.categories:
            categories = [cat.name for cat in article.categories if hasattr(cat, 'name')]
        
        # 記事の文字数を計算
        word_count = len(article.content) if article.content else 0
        
        # 公開日の処理
        published_date = article.published_at if article.published_at else article.created_at
        if published_date:
            published_iso = published_date.isoformat()
        else:
            published_iso = datetime.now().isoformat()
        
        # JSON-LD構造化データ
        structured_data = {
            "@context": "https://schema.org",
            "@type": "BlogPosting",
            "headline": article.title or "Untitled",
            "description": article.summary or article.title or "No description available",
            "author": {
                "@type": "Person",
                "name": author_name
            },
            "datePublished": published_iso,
            "dateModified": article.updated_at.isoformat() if article.updated_at else published_iso,
            "wordCount": word_count,
            "articleSection": categories,
            "keywords": categories,
            "publisher": {
                "@type": "Organization",
                "name": "Miyakawa.codes",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://miyakawa.codes/static/images/logo.png"
                }
            }
        }
        
        # アイキャッチ画像が設定されている場合
        if hasattr(article, 'featured_image_url') and article.featured_image_url:
            structured_data["image"] = {
                "@type": "ImageObject",
                "url": f"https://miyakawa.codes{article.featured_image_url}"
            }
        
        return json.dumps(structured_data, ensure_ascii=False, indent=2)
        
    except Exception as e:
        current_app.logger.error(f"Error generating structured data: {e}")
        return None