"""
Utility Functions - 一般的なユーティリティ関数
"""
import bleach
import markdown
import re
from markupsafe import Markup
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

def process_markdown(text):
    """MarkdownテキストをHTMLに変換する関数（SNS埋込自動検出付き）"""
    if not text:
        return ''
    
    # Markdownの拡張機能を設定
    md = markdown.Markdown(
        extensions=['extra', 'codehilite', 'toc', 'nl2br'],
        extension_configs={
            'codehilite': {
                'css_class': 'highlight',
                'use_pygments': False
            }
        },
        tab_length=2  # タブ長を短く設定
    )
    
    # MarkdownをHTMLに変換
    html = md.convert(text)
    
    # セキュリティのためHTMLをサニタイズ（SNS埋込用タグを追加）
    allowed_tags = [
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'br', 'strong', 'em', 'u', 'del',
        'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
        'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        # SNS埋込用タグ
        'div', 'iframe', 'script', 'blockquote', 'noscript'
    ]
    allowed_attributes = {
        'a': ['href', 'title', 'target', 'rel'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'code': ['class'],
        'pre': ['class'],
        'h1': ['id'], 'h2': ['id'], 'h3': ['id'], 'h4': ['id'], 'h5': ['id'], 'h6': ['id'],
        # SNS埋込用属性
        'div': ['class', 'id', 'style', 'data-href', 'data-width', 'data-instgrm-permalink'],
        'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'title', 'style'],
        'script': ['src', 'async', 'defer', 'charset', 'crossorigin'],
        'blockquote': ['class', 'style', 'data-instgrm-permalink'],
        'noscript': []
    }
    
    # SNS埋込HTMLがある場合はbleachを適用しない（安全なHTMLのため）
    if any(cls in html for cls in ['sns-embed', 'youtube-embed', 'twitter-embed', 'instagram-embed', 'facebook-embed', 'threads-embed']):
        clean_html = html
    else:
        # 通常のMarkdownコンテンツのみサニタイズ
        clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes)
    
    # 見出しにアンカーIDを追加
    clean_html = add_heading_anchors(clean_html)
    
    return Markup(clean_html)

def generate_ogp_data(title, description=None, image_url=None, url=None):
    """OGPデータを生成する関数"""
    ogp_data = {
        'title': title,
        'description': description or '記事の詳細はこちらをご覧ください',
        'image': image_url,
        'url': url
    }
    return ogp_data

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

