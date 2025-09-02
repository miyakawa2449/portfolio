from flask import Blueprint, render_template, abort
from sqlalchemy import select, func
from models import Article, Project, Category, Challenge, SiteSetting, User, db
from seo import get_static_page_seo

landing_bp = Blueprint('landing', __name__)

@landing_bp.route('/')
def landing():
    """ビジネス・サービス中心のトップページ"""
    # 基本的なデータを取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 注目プロジェクト（最新実績として表示）
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('home')
    
    return render_template('landing.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         featured_projects=featured_projects,
                         page_seo=page_seo)

@landing_bp.route('/portfolio')
def portfolio():
    """ポートフォリオページ（100日チャレンジ）"""
    # アクティブなチャレンジを取得
    active_challenge = db.session.execute(
        select(Challenge).where(Challenge.is_active.is_(True))
    ).scalar_one_or_none()
    
    if not active_challenge:
        # アクティブなチャレンジがない場合、最新のチャレンジを取得
        active_challenge = db.session.execute(
            select(Challenge).order_by(Challenge.display_order.desc())
        ).scalar_one_or_none()
    
    # 最新記事を取得（アクティブチャレンジの記事を優先）
    if active_challenge:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(
            # アクティブチャレンジの記事を優先、その後公開日順
            (Article.challenge_id == active_challenge.id).desc(),
            Article.published_at.desc()
        ).limit(5)
    else:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(Article.published_at.desc()).limit(5)
    
    latest_articles = db.session.execute(latest_articles_query).scalars().all()
    
    # 記事の総数を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    # スキルカテゴリを取得
    skill_categories = db.session.execute(
        select(Category).where(Category.parent_id.is_(None)).order_by(Category.name)
    ).scalars().all()
    
    # すべてのチャレンジを取得（一覧表示用）
    all_challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order)
    ).scalars().all()
    
    # 注目プロジェクトを取得（最大3件）
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # プロジェクト総数を取得
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 現在の学習日数を計算（アクティブチャレンジベース）
    current_day = 0
    if active_challenge:
        current_day = active_challenge.days_elapsed
    
    return render_template('portfolio.html',
                         active_challenge=active_challenge,
                         latest_articles=latest_articles,
                         total_articles=total_articles,
                         total_projects=total_projects,
                         current_day=current_day,
                         skill_categories=skill_categories,
                         all_challenges=all_challenges,
                         featured_projects=featured_projects)

@landing_bp.route('/services')
def services():
    """サービス詳細ページ"""
    # 実績プロジェクト（詳細表示用）
    all_projects = db.session.execute(
        select(Project).where(Project.status == 'active')
        .order_by(Project.display_order)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('services')
    
    return render_template('services.html', 
                         projects=all_projects,
                         page_seo=page_seo)

@landing_bp.route('/story')
def story():
    """キャリアストーリーページ"""
    # 実際の数値を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('story')
    
    return render_template('story.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         page_seo=page_seo)

@landing_bp.route('/about/')
def profile():
    """ユーザープロフィールページ（ポートフォリオ版）"""
    # 管理者ユーザーを取得（一人管理前提）
    user = db.session.execute(select(User).where(User.role == 'admin')).scalar_one_or_none()
    if not user:
        abort(404)
    
    # SEO設定を取得
    page_seo = get_static_page_seo('about')
    
    # 公開記事のみ取得
    articles = db.session.execute(
        select(Article).where(Article.author_id == user.id, Article.is_published.is_(True)).order_by(
            db.case(
                (Article.published_at.isnot(None), Article.published_at),
                else_=Article.created_at
            ).desc()
        )
    ).scalars().all()
    
    # プロジェクトを取得（作成者でフィルタ可能な場合）
    projects = db.session.execute(
        select(Project).order_by(Project.created_at.desc())
    ).scalars().all()
    
    # 注目プロジェクトを取得
    featured_projects = [p for p in projects if p.is_featured]
    
    # チャレンジ情報を取得
    challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order, Challenge.id)
    ).scalars().all()
    
    return render_template('profile_portfolio.html', 
                           user=user, 
                           articles=articles,
                           projects=projects,
                           featured_projects=featured_projects,
                           challenges=challenges,
                           page_seo=page_seo)