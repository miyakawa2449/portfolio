from flask import Blueprint, render_template, request
from sqlalchemy import func, or_, and_
from models import Article, Category, Project, db
from utils import process_markdown
from article_service import ArticleService
import logging

search_bp = Blueprint('search', __name__)
logger = logging.getLogger(__name__)

@search_bp.route('/search')
def search():
    """サイト内検索ページ"""
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')  # all, articles, projects
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    if not query:
        return render_template('search_results.html', 
                             query='', 
                             articles=[], 
                             projects=[], 
                             search_type=search_type,
                             total_count=0)
    
    results = perform_search(query, search_type, page, per_page)
    
    return render_template('search_results.html', 
                         query=query,
                         articles=results['articles'],
                         projects=results['projects'],
                         search_type=search_type,
                         article_pagination=results['article_pagination'],
                         project_pagination=results['project_pagination'],
                         total_count=results['total_count'])

def perform_search(query, search_type='all', page=1, per_page=10):
    """検索実行関数"""
    results = {
        'articles': [],
        'projects': [],
        'article_pagination': None,
        'project_pagination': None,
        'total_count': 0
    }
    
    # 記事検索
    if search_type in ['all', 'articles']:
        article_query = Article.query.filter(
            Article.is_published == True,
            or_(
                Article.title.contains(query),
                Article.summary.contains(query),
                Article.body.contains(query)
            )
        ).order_by(Article.published_at.desc())
        
        if search_type == 'all':
            # 全体検索の場合は5件まで
            results['articles'] = article_query.limit(5).all()
        else:
            # 記事のみ検索の場合はページング
            pagination = article_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            results['articles'] = pagination.items
            results['article_pagination'] = pagination
        
        results['total_count'] += article_query.count()
    
    # プロジェクト検索
    if search_type in ['all', 'projects']:
        project_query = Project.query.filter(
            Project.status == 'active',
            or_(
                Project.title.contains(query),
                Project.description.contains(query),
                Project.long_description.contains(query)
            )
        ).order_by(Project.created_at.desc())
        
        if search_type == 'all':
            # 全体検索の場合は5件まで
            results['projects'] = project_query.limit(5).all()
        else:
            # プロジェクトのみ検索の場合はページング
            pagination = project_query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            results['projects'] = pagination.items
            results['project_pagination'] = pagination
        
        results['total_count'] += project_query.count()
    
    return results