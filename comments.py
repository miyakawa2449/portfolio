"""
Comments Blueprint - コメント機能
"""
from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import current_user
from models import db, Article
from comment_service import CommentService

# コメントBlueprint作成
comments_bp = Blueprint('comments', __name__)

@comments_bp.route('/add_comment/<int:article_id>', methods=['POST'])
def add_comment(article_id):
    """コメント投稿処理"""
    
    # サービス層でコメント作成
    comment, error = CommentService.create_comment(
        article_id=article_id,
        form_data=request.form,
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    # 記事取得（リダイレクト用）
    article = db.session.get(Article, article_id)
    if not article:
        flash('記事が見つかりません。', 'error')
        return redirect(url_for('landing.home'))
    
    # エラー処理
    if error:
        flash(error, 'error')
    else:
        flash('コメントが投稿されました。管理者の承認後に表示されます。', 'success')
    
    return redirect(url_for('articles.article_detail', slug=article.slug))

# ヘルパー関数（互換性のため残す）
def get_approved_comments(article_id):
    """承認済みコメント取得"""
    return CommentService.get_approved_comments(article_id)

def is_comments_enabled_for_article(article):
    """記事のコメント機能有効性チェック"""
    return CommentService.is_comments_enabled_for_article(article)