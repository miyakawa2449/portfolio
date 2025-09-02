"""
Articles Blueprint - 記事機能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import current_user, login_required
from models import db, Article, Category, Challenge, Project, Comment, SiteSetting
from comments import get_approved_comments, is_comments_enabled_for_article
from forms import CommentForm
from utils import process_markdown, generate_ogp_data
from seo import generate_article_structured_data
from datetime import datetime
import json

# 記事Blueprint作成
articles_bp = Blueprint('articles', __name__)

@articles_bp.route('/blog')
@articles_bp.route('/blog/page/<int:page>')
@articles_bp.route('/blog/challenge/<int:challenge_id>')
@articles_bp.route('/blog/challenge/<int:challenge_id>/page/<int:page>')
def blog(page=1, challenge_id=None):
    """ブログ記事一覧表示"""
    
    # ベースクエリ：公開済み記事のみ
    query = Article.query.filter(Article.is_published == True)
    
    # チャレンジフィルター
    if challenge_id:
        challenge = Challenge.query.get_or_404(challenge_id)
        query = query.filter(Article.challenge_id == challenge_id)
    else:
        challenge = None
    
    # ページング（公開日順でソート）
    per_page = 10
    articles = query.order_by(
        Article.published_at.desc(),
        Article.created_at.desc()
    ).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # チャレンジ一覧（ナビゲーション用）
    challenges = Challenge.query.order_by(Challenge.display_order.asc()).all()
    
    # SEO設定
    from seo import get_static_page_seo
    seo_data = get_static_page_seo('blog')
    
    return render_template('home.html', 
                         articles=articles.items,
                         pagination=articles,
                         challenges=challenges,
                         current_challenge=challenge,
                         seo_data=seo_data)

@articles_bp.route('/article/<slug>/')
def article_detail(slug):
    """記事詳細表示"""
    
    # 記事取得
    article = Article.query.filter_by(slug=slug, is_published=True).first_or_404()
    
    # Markdownを処理してHTMLに変換
    processed_body = process_markdown(article.body)
    
    # 関連プロジェクト取得
    related_projects = article.related_projects
    
    # 承認済みコメント取得
    approved_comments = get_approved_comments(article.id)
    
    # コメント機能の有効性確認
    comments_enabled = is_comments_enabled_for_article(article)
    
    # コメントフォーム
    comment_form = CommentForm() if comments_enabled else None
    
    # JSON-LD構造化データ生成
    json_ld_data = generate_article_structured_data(article)
    
    # OGPデータ生成
    ogp_data = generate_ogp_data(
        title=article.meta_title or article.title,
        description=article.meta_description or article.summary,
        image_url=article.featured_image,
        url=request.url
    )
    
    return render_template('article_detail.html',
                         article=article,
                         processed_body=processed_body,
                         related_projects=related_projects,
                         approved_comments=approved_comments,
                         comment_form=comment_form,
                         comments_enabled=comments_enabled,
                         json_ld_data=json_ld_data,
                         ogp_data=ogp_data)


# ArticleService クラス（将来のサービス層実装）
class ArticleService:
    """記事関連ビジネスロジック"""
    
    @staticmethod
    def get_published_articles(challenge_id=None, category_id=None, limit=None):
        """公開済み記事取得"""
        query = Article.query.filter(Article.is_published == True)
        
        if challenge_id:
            query = query.filter(Article.challenge_id == challenge_id)
        
        if category_id:
            category = Category.query.get(category_id)
            if category:
                query = query.filter(Article.categories.contains(category))
        
        query = query.order_by(
            Article.published_at.desc(),
            Article.created_at.desc()
        )
        
        if limit:
            return query.limit(limit).all()
        
        return query.all()
    
    @staticmethod
    def get_related_articles(article, limit=5):
        """関連記事取得"""
        # 同じチャレンジ・同じカテゴリの記事を取得
        related = Article.query.filter(
            Article.is_published == True,
            Article.id != article.id
        )
        
        # 同じチャレンジを優先
        if article.challenge_id:
            related = related.filter(Article.challenge_id == article.challenge_id)
        
        # 同じカテゴリがある場合はそれも考慮
        if article.categories:
            category_ids = [cat.id for cat in article.categories]
            related = related.filter(Article.categories.any(Category.id.in_(category_ids)))
        
        return related.order_by(Article.published_at.desc()).limit(limit).all()
    
    @staticmethod
    def create_article(title, body, author_id, challenge_id=None, category_ids=None, **kwargs):
        """新しい記事作成"""
        from slugify import slugify
        
        # スラッグ生成
        slug = slugify(title)
        
        # 重複チェック
        existing = Article.query.filter_by(slug=slug).first()
        if existing:
            slug = f"{slug}-{datetime.now().strftime('%Y%m%d')}"
        
        # 記事作成
        article = Article(
            title=title,
            slug=slug,
            body=body,
            author_id=author_id,
            challenge_id=challenge_id,
            **kwargs
        )
        
        db.session.add(article)
        db.session.flush()  # IDを取得するため
        
        # カテゴリ関連付け
        if category_ids:
            categories = Category.query.filter(Category.id.in_(category_ids)).all()
            article.categories = categories
        
        db.session.commit()
        return article
    
    @staticmethod
    def update_article(article_id, **kwargs):
        """記事更新"""
        article = Article.query.get_or_404(article_id)
        
        for key, value in kwargs.items():
            if hasattr(article, key):
                setattr(article, key, value)
        
        article.updated_at = datetime.utcnow()
        db.session.commit()
        return article
    
    @staticmethod
    def publish_article(article_id):
        """記事公開"""
        article = Article.query.get_or_404(article_id)
        article.is_published = True
        article.published_at = datetime.utcnow()
        db.session.commit()
        return article
    
    @staticmethod
    def unpublish_article(article_id):
        """記事非公開"""
        article = Article.query.get_or_404(article_id)
        article.is_published = False
        db.session.commit()
        return article
    
    @staticmethod
    def delete_article(article_id):
        """記事削除"""
        article = Article.query.get_or_404(article_id)
        
        # 関連コメントは CASCADE で自動削除
        db.session.delete(article)
        db.session.commit()
        return True
    
    @staticmethod
    def search_articles(query, challenge_id=None, limit=50):
        """記事検索"""
        search_query = Article.query.filter(Article.is_published == True)
        
        if query:
            search_pattern = f"%{query}%"
            search_query = search_query.filter(
                db.or_(
                    Article.title.like(search_pattern),
                    Article.body.like(search_pattern),
                    Article.summary.like(search_pattern)
                )
            )
        
        if challenge_id:
            search_query = search_query.filter(Article.challenge_id == challenge_id)
        
        return search_query.order_by(
            Article.published_at.desc()
        ).limit(limit).all()