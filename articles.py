"""
Articles Blueprint - 記事機能
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort, current_app
from flask_login import current_user, login_required
from models import db, Article, Category, Challenge, Project, Comment, SiteSetting
from article_service import ArticleService
from comment_service import CommentService
from forms import CommentForm
from utils import process_markdown, generate_ogp_data
from seo import get_static_page_seo
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
    
    # チャレンジ情報取得
    challenge = None
    if challenge_id:
        challenge = Challenge.query.get_or_404(challenge_id)
    
    # サービス層で記事取得
    per_page = int(SiteSetting.get_setting('posts_per_page', '10'))
    articles = ArticleService.get_published_articles(
        page=page, 
        per_page=per_page, 
        challenge_id=challenge_id
    )
    
    # チャレンジ一覧（ナビゲーション用）
    challenges = Challenge.query.order_by(Challenge.display_order.asc()).all()
    
    # 統計情報取得
    stats = ArticleService.get_article_stats()
    
    # SEO設定
    seo_data = get_static_page_seo('blog')
    
    return render_template('home.html', 
                         articles=articles.items,
                         pagination=articles,
                         challenges=challenges,
                         current_challenge=challenge,
                         total_articles=stats['published'],
                         seo_data=seo_data)

@articles_bp.route('/article/<slug>/')
def article_detail(slug):
    """記事詳細表示"""
    
    # サービス層で記事取得
    article = ArticleService.get_article_by_slug(slug)
    if not article:
        abort(404)
    
    # Markdownを処理してHTMLに変換
    processed_body = process_markdown(article.body)
    
    # 関連記事取得
    related_articles = ArticleService.get_related_articles(article, limit=5)
    
    # 関連プロジェクト取得
    related_projects = article.related_projects
    
    # 承認済みコメント取得
    approved_comments = CommentService.get_approved_comments(article.id)
    
    # コメント機能の有効性確認
    comments_enabled = CommentService.is_comments_enabled_for_article(article)
    
    # コメントフォーム
    comment_form = CommentForm() if comments_enabled else None
    
    # SEOデータ生成
    seo_data = ArticleService.generate_article_seo_data(article)
    
    # OGPデータ生成
    ogp_data = generate_ogp_data(
        title=seo_data['title'],
        description=seo_data['description'],
        image_url=article.featured_image,
        url=request.url
    )
    
    return render_template('article_detail.html',
                         article=article,
                         processed_body=processed_body,
                         related_articles=related_articles,
                         related_projects=related_projects,
                         approved_comments=approved_comments,
                         comment_form=comment_form,
                         comments_enabled=comments_enabled,
                         structured_data=seo_data['structured_data'],
                         ogp_data=ogp_data)