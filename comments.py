"""
Comments Blueprint - コメント機能
"""
from flask import Blueprint, request, redirect, url_for, flash, current_app
from flask_login import current_user
from models import db, Article, Comment, SiteSetting
from forms import CommentForm
from encryption_utils import EncryptionService
from datetime import datetime
import bleach

# コメントBlueprint作成
comments_bp = Blueprint('comments', __name__)

@comments_bp.route('/add_comment/<int:article_id>', methods=['POST'])
def add_comment(article_id):
    """コメント投稿処理"""
    
    # 記事の存在確認
    article = Article.query.get_or_404(article_id)
    
    # コメント機能の有効性確認
    site_comments_enabled = SiteSetting.get_setting('comments_enabled', 'true') == 'true'
    if not site_comments_enabled or not article.allow_comments:
        flash('この記事ではコメントが無効になっています。', 'warning')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # フォームデータ取得（フィールド名をテンプレートに合わせる）
    author_name = request.form.get('name', '').strip()  # comment_form.name
    author_email = request.form.get('email', '').strip()  # comment_form.email
    author_website = request.form.get('website', '').strip() 
    content = request.form.get('content', '').strip()
    
    # バリデーション
    if not author_name or not author_email or not content:
        flash('必須項目を入力してください。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # メールアドレス形式チェック
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, author_email):
        flash('有効なメールアドレスを入力してください。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # コンテンツのサニタイゼーション
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 'code', 'pre']
    allowed_attributes = {}
    content = bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    
    # 個人情報暗号化
    try:
        encrypted_name = EncryptionService.encrypt(author_name)
        encrypted_email = EncryptionService.encrypt(author_email)
    except Exception as e:
        current_app.logger.error(f"暗号化エラー: {e}")
        flash('コメントの保存中にエラーが発生しました。', 'error')
        return redirect(url_for('article_detail', slug=article.slug))
    
    # コメント作成
    comment = Comment(
        article_id=article_id,
        author_name=encrypted_name,
        author_email=encrypted_email,
        author_website=author_website,
        content=content,
        ip_address=request.environ.get('REMOTE_ADDR'),
        user_agent=request.headers.get('User-Agent')
    )
    
    try:
        db.session.add(comment)
        db.session.commit()
        flash('コメントが投稿されました。管理者の承認後に表示されます。', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"コメント保存エラー: {e}")
        flash('コメントの保存中にエラーが発生しました。', 'error')
    
    return redirect(url_for('article_detail', slug=article.slug))

def get_approved_comments(article_id):
    """承認済みコメント取得"""
    return Comment.query.filter(
        Comment.article_id == article_id,
        Comment.is_approved == True
    ).order_by(Comment.created_at.asc()).all()

def is_comments_enabled_for_article(article):
    """記事のコメント機能有効性チェック"""
    site_enabled = SiteSetting.get_setting('comments_enabled', 'true') == 'true'
    return site_enabled and article.allow_comments

# CommentService クラス（将来のサービス層実装準備）
class CommentService:
    """コメント関連ビジネスロジック"""
    
    @staticmethod
    def create_comment(article_id, name, email, website, content, ip_address=None, user_agent=None):
        """新しいコメントを作成"""
        # 暗号化
        encrypted_name = EncryptionService.encrypt(name)
        encrypted_email = EncryptionService.encrypt(email)
        
        # サニタイゼーション
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 'code', 'pre']
        content = bleach.clean(content, tags=allowed_tags, attributes={}, strip=True)
        
        # コメント作成
        comment = Comment(
            article_id=article_id,
            author_name=encrypted_name,
            author_email=encrypted_email,
            author_website=website,
            content=content,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(comment)
        db.session.commit()
        return comment
    
    @staticmethod
    def approve_comment(comment_id):
        """コメントを承認"""
        comment = Comment.query.get_or_404(comment_id)
        comment.is_approved = True
        db.session.commit()
        return comment
    
    @staticmethod
    def reject_comment(comment_id):
        """コメントを拒否"""
        comment = Comment.query.get_or_404(comment_id)
        comment.is_approved = False
        db.session.commit()
        return comment
    
    @staticmethod
    def delete_comment(comment_id):
        """コメントを削除"""
        comment = Comment.query.get_or_404(comment_id)
        db.session.delete(comment)
        db.session.commit()
        return True
    
    @staticmethod
    def bulk_approve_comments(comment_ids):
        """コメント一括承認"""
        Comment.query.filter(Comment.id.in_(comment_ids)).update(
            {'is_approved': True}, synchronize_session=False
        )
        db.session.commit()
    
    @staticmethod
    def bulk_reject_comments(comment_ids):
        """コメント一括拒否"""
        Comment.query.filter(Comment.id.in_(comment_ids)).update(
            {'is_approved': False}, synchronize_session=False
        )
        db.session.commit()
    
    @staticmethod
    def bulk_delete_comments(comment_ids):
        """コメント一括削除"""
        Comment.query.filter(Comment.id.in_(comment_ids)).delete(synchronize_session=False)
        db.session.commit()