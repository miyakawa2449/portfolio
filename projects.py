"""
Projects Blueprint - プロジェクト機能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import current_user, login_required
from models import db, Project, Challenge, Article
from utils import generate_ogp_data
from datetime import datetime
import json

# プロジェクトBlueprint作成
projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/projects')
@projects_bp.route('/projects/page/<int:page>')
@projects_bp.route('/projects/challenge/<int:challenge_id>')
@projects_bp.route('/projects/challenge/<int:challenge_id>/page/<int:page>')
def projects_list(page=1, challenge_id=None):
    """プロジェクト一覧表示"""
    
    # ベースクエリ：アクティブなプロジェクトのみ
    query = Project.query.filter(Project.status == 'active')
    
    # チャレンジフィルター
    if challenge_id:
        challenge = Challenge.query.get_or_404(challenge_id)
        query = query.filter(Project.challenge_id == challenge_id)
    else:
        challenge = None
    
    # ページング（表示順 → 作成日順）
    per_page = 12  # グリッド表示で12個
    projects = query.order_by(
        Project.display_order.asc(),
        Project.created_at.desc()
    ).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # チャレンジ一覧（フィルター用）
    challenges = Challenge.query.order_by(Challenge.display_order.asc()).all()
    
    # 注目プロジェクト（is_featured=True）
    featured_projects = Project.query.filter(
        Project.status == 'active',
        Project.is_featured == True
    ).order_by(Project.display_order.asc()).limit(6).all()
    
    # SEO設定
    from seo import get_static_page_seo
    seo_data = get_static_page_seo('portfolio')
    
    return render_template('portfolio.html',
                         projects=projects,
                         challenges=challenges,
                         current_challenge=challenge,
                         featured_projects=featured_projects,
                         seo_data=seo_data)

@projects_bp.route('/project/<slug>/')
def project_detail(slug):
    """プロジェクト詳細表示（将来実装予定）"""
    
    # プロジェクト取得
    project = Project.query.filter_by(slug=slug, status='active').first_or_404()
    
    # 関連記事取得
    related_articles = project.related_articles
    
    # 技術スタック
    technologies = project.technology_list
    
    # デモURL一覧
    demo_urls = project.demo_url_list
    
    # スクリーンショット
    screenshots = project.screenshot_list
    
    # OGPデータ生成
    ogp_data = generate_ogp_data(
        title=project.title,
        description=project.description,
        image=project.featured_image,
        url=request.url
    )
    
    return render_template('project_detail.html',
                         project=project,
                         related_articles=related_articles,
                         technologies=technologies,
                         demo_urls=demo_urls,
                         screenshots=screenshots,
                         ogp_data=ogp_data)

# ProjectService クラス（サービス層実装）
class ProjectService:
    """プロジェクト関連ビジネスロジック"""
    
    @staticmethod
    def get_active_projects(challenge_id=None, featured_only=False, limit=None):
        """アクティブプロジェクト取得"""
        query = Project.query.filter(Project.status == 'active')
        
        if challenge_id:
            query = query.filter(Project.challenge_id == challenge_id)
        
        if featured_only:
            query = query.filter(Project.is_featured == True)
        
        query = query.order_by(
            Project.display_order.asc(),
            Project.created_at.desc()
        )
        
        if limit:
            return query.limit(limit).all()
        
        return query.all()
    
    @staticmethod
    def create_project(title, description, challenge_id=None, **kwargs):
        """新しいプロジェクト作成"""
        from slugify import slugify
        
        # スラッグ生成
        slug = slugify(title)
        
        # 重複チェック
        existing = Project.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d')}"
        
        # プロジェクト作成
        project = Project(
            title=title,
            slug=slug,
            description=description,
            challenge_id=challenge_id,
            **kwargs
        )
        
        db.session.add(project)
        db.session.commit()
        return project
    
    @staticmethod
    def update_project(project_id, **kwargs):
        """プロジェクト更新"""
        project = Project.query.get_or_404(project_id)
        
        for key, value in kwargs.items():
            if hasattr(project, key):
                setattr(project, key, value)
        
        project.updated_at = datetime.utcnow()
        db.session.commit()
        return project
    
    @staticmethod
    def add_technology(project_id, technology):
        """技術スタック追加"""
        project = Project.query.get_or_404(project_id)
        technologies = project.technology_list
        
        if technology not in technologies:
            technologies.append(technology)
            project.set_technologies(technologies)
            db.session.commit()
        
        return project
    
    @staticmethod
    def remove_technology(project_id, technology):
        """技術スタック削除"""
        project = Project.query.get_or_404(project_id)
        technologies = project.technology_list
        
        if technology in technologies:
            technologies.remove(technology)
            project.set_technologies(technologies)
            db.session.commit()
        
        return project
    
    @staticmethod
    def add_demo_url(project_id, name, url, demo_type="demo"):
        """デモURL追加"""
        project = Project.query.get_or_404(project_id)
        project.add_demo_url(name, url, demo_type)
        db.session.commit()
        return project
    
    @staticmethod
    def remove_demo_url(project_id, index):
        """デモURL削除"""
        project = Project.query.get_or_404(project_id)
        demo_urls = project.demo_url_list
        
        if 0 <= index < len(demo_urls):
            demo_urls.pop(index)
            project.set_demo_urls(demo_urls)
            db.session.commit()
        
        return project
    
    @staticmethod
    def link_to_article(project_id, article_id):
        """記事との関連付け"""
        project = Project.query.get_or_404(project_id)
        article = Article.query.get_or_404(article_id)
        
        # プロジェクト → 記事
        project.article_id = article_id
        
        # 記事 → プロジェクト
        article.add_project(project_id)
        
        db.session.commit()
        return project, article
    
    @staticmethod
    def unlink_from_article(project_id, article_id):
        """記事との関連付け解除"""
        project = Project.query.get_or_404(project_id)
        article = Article.query.get_or_404(article_id)
        
        # プロジェクト → 記事
        if project.article_id == article_id:
            project.article_id = None
        
        # 記事 → プロジェクト
        article.remove_project(project_id)
        
        db.session.commit()
        return project, article
    
    @staticmethod
    def search_projects(query, challenge_id=None, limit=50):
        """プロジェクト検索"""
        search_query = Project.query.filter(Project.status == 'active')
        
        if query:
            search_pattern = f"%{query}%"
            search_query = search_query.filter(
                db.or_(
                    Project.title.like(search_pattern),
                    Project.description.like(search_pattern),
                    Project.long_description.like(search_pattern)
                )
            )
        
        if challenge_id:
            search_query = search_query.filter(Project.challenge_id == challenge_id)
        
        return search_query.order_by(
            Project.display_order.asc(),
            Project.created_at.desc()
        ).limit(limit).all()
    
    @staticmethod
    def archive_project(project_id):
        """プロジェクトアーカイブ"""
        project = Project.query.get_or_404(project_id)
        project.status = 'archived'
        db.session.commit()
        return project
    
    @staticmethod
    def restore_project(project_id):
        """プロジェクト復元"""
        project = Project.query.get_or_404(project_id)
        project.status = 'active'
        db.session.commit()
        return project