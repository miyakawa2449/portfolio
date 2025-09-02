"""
コメント管理のためのサービスクラス
ビジネスロジックを集約し、Blueprint層から分離
"""
import re
import bleach
from datetime import datetime
from flask import current_app
from sqlalchemy import select, func
from models import db, Comment, Article, SiteSetting, User
from encryption_utils import EncryptionService


class CommentService:
    """コメント関連ビジネスロジック"""
    
    @staticmethod
    def create_comment(article_id, form_data, ip_address=None, user_agent=None):
        """新しいコメントを作成"""
        try:
            # 記事の存在確認
            article = db.session.get(Article, article_id)
            if not article:
                return None, "記事が見つかりません"
            
            # コメント機能の有効性確認
            if not CommentService.is_comments_enabled_for_article(article):
                return None, "この記事ではコメントが無効になっています"
            
            # バリデーション
            errors = CommentService.validate_comment_data(form_data)
            if errors:
                return None, errors[0]
            
            # データ抽出
            name = form_data.get('name', '').strip()
            email = form_data.get('email', '').strip()
            website = form_data.get('website', '').strip()
            content = form_data.get('content', '').strip()
            
            # 個人情報暗号化
            encrypted_name = EncryptionService.encrypt(name)
            encrypted_email = EncryptionService.encrypt(email)
            
            # コンテンツのサニタイゼーション
            sanitized_content = CommentService.sanitize_content(content)
            
            # コメント作成
            comment = Comment(
                article_id=article_id,
                author_name=encrypted_name,
                author_email=encrypted_email,
                author_website=website,
                content=sanitized_content,
                ip_address=ip_address,
                user_agent=user_agent,
                created_at=datetime.utcnow()
            )
            
            db.session.add(comment)
            db.session.commit()
            
            # 通知送信（必要に応じて）
            CommentService._send_notification(article, comment)
            
            return comment, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"コメント作成エラー: {str(e)}")
            return None, "コメントの保存中にエラーが発生しました"
    
    @staticmethod
    def approve_comment(comment_id, approver_id=None):
        """コメントを承認"""
        try:
            comment = db.session.get(Comment, comment_id)
            if not comment:
                return None, "コメントが見つかりません"
            
            comment.is_approved = True
            comment.approved_at = datetime.utcnow()
            comment.approved_by = approver_id
            
            db.session.commit()
            return comment, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"コメント承認エラー: {str(e)}")
            return None, "コメントの承認中にエラーが発生しました"
    
    @staticmethod
    def reject_comment(comment_id, reason=None):
        """コメントを拒否"""
        try:
            comment = db.session.get(Comment, comment_id)
            if not comment:
                return None, "コメントが見つかりません"
            
            comment.is_approved = False
            comment.rejection_reason = reason
            
            db.session.commit()
            return comment, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"コメント拒否エラー: {str(e)}")
            return None, "コメントの拒否中にエラーが発生しました"
    
    @staticmethod
    def delete_comment(comment_id):
        """コメントを削除"""
        try:
            comment = db.session.get(Comment, comment_id)
            if not comment:
                return False, "コメントが見つかりません"
            
            db.session.delete(comment)
            db.session.commit()
            return True, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"コメント削除エラー: {str(e)}")
            return False, "コメントの削除中にエラーが発生しました"
    
    @staticmethod
    def bulk_approve_comments(comment_ids, approver_id=None):
        """コメント一括承認"""
        try:
            updated = Comment.query.filter(Comment.id.in_(comment_ids)).update(
                {
                    'is_approved': True,
                    'approved_at': datetime.utcnow(),
                    'approved_by': approver_id
                }, 
                synchronize_session=False
            )
            db.session.commit()
            return updated, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"一括承認エラー: {str(e)}")
            return 0, "一括承認中にエラーが発生しました"
    
    @staticmethod
    def bulk_reject_comments(comment_ids):
        """コメント一括拒否"""
        try:
            updated = Comment.query.filter(Comment.id.in_(comment_ids)).update(
                {'is_approved': False}, 
                synchronize_session=False
            )
            db.session.commit()
            return updated, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"一括拒否エラー: {str(e)}")
            return 0, "一括拒否中にエラーが発生しました"
    
    @staticmethod
    def bulk_delete_comments(comment_ids):
        """コメント一括削除"""
        try:
            deleted = Comment.query.filter(Comment.id.in_(comment_ids)).delete(
                synchronize_session=False
            )
            db.session.commit()
            return deleted, None
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"一括削除エラー: {str(e)}")
            return 0, "一括削除中にエラーが発生しました"
    
    @staticmethod
    def get_approved_comments(article_id):
        """承認済みコメント取得"""
        return Comment.query.filter(
            Comment.article_id == article_id,
            Comment.is_approved == True
        ).order_by(Comment.created_at.asc()).all()
    
    @staticmethod
    def get_pending_comments(limit=None):
        """未承認コメント取得"""
        query = Comment.query.filter(
            Comment.is_approved == False
        ).order_by(Comment.created_at.desc())
        
        if limit:
            query = query.limit(limit)
        
        return query.all()
    
    @staticmethod
    def get_comment_stats():
        """コメント統計情報取得"""
        try:
            stats = {
                'total': Comment.query.count(),
                'approved': Comment.query.filter(Comment.is_approved == True).count(),
                'pending': Comment.query.filter(Comment.is_approved == False).count(),
                'today': Comment.query.filter(
                    func.date(Comment.created_at) == datetime.utcnow().date()
                ).count()
            }
            return stats
        except Exception as e:
            current_app.logger.error(f"統計取得エラー: {str(e)}")
            return {
                'total': 0,
                'approved': 0,
                'pending': 0,
                'today': 0
            }
    
    @staticmethod
    def is_comments_enabled_for_article(article):
        """記事のコメント機能有効性チェック"""
        site_enabled = SiteSetting.get_setting('comments_enabled', 'true') == 'true'
        return site_enabled and article.allow_comments
    
    @staticmethod
    def validate_comment_data(form_data):
        """コメントデータのバリデーション"""
        errors = []
        
        # 必須項目チェック
        name = form_data.get('name', '').strip()
        email = form_data.get('email', '').strip()
        content = form_data.get('content', '').strip()
        
        if not name:
            errors.append("名前は必須です")
        if not email:
            errors.append("メールアドレスは必須です")
        if not content:
            errors.append("コメント内容は必須です")
        
        # メールアドレス形式チェック
        if email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, email):
                errors.append("有効なメールアドレスを入力してください")
        
        # 文字数チェック
        if len(name) > 100:
            errors.append("名前は100文字以内で入力してください")
        if len(content) > 5000:
            errors.append("コメントは5000文字以内で入力してください")
        
        # URL形式チェック（websiteが入力されている場合）
        website = form_data.get('website', '').strip()
        if website:
            url_pattern = r'^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&\/\/=]*)$'
            if not re.match(url_pattern, website):
                errors.append("有効なURLを入力してください")
        
        return errors
    
    @staticmethod
    def sanitize_content(content):
        """コンテンツのサニタイゼーション"""
        allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'ol', 'ul', 'li', 'blockquote', 'code', 'pre']
        allowed_attributes = {}
        return bleach.clean(content, tags=allowed_tags, attributes=allowed_attributes, strip=True)
    
    @staticmethod
    def get_decrypted_comment_data(comment):
        """コメントデータを復号化して返す"""
        try:
            return {
                'id': comment.id,
                'author_name': EncryptionService.decrypt(comment.author_name),
                'author_email': EncryptionService.decrypt(comment.author_email),
                'author_website': comment.author_website,
                'content': comment.content,
                'created_at': comment.created_at,
                'is_approved': comment.is_approved,
                'article': comment.article
            }
        except Exception as e:
            current_app.logger.error(f"復号化エラー: {str(e)}")
            return None
    
    @staticmethod
    def search_comments(query, status=None):
        """コメント検索"""
        try:
            # 基本クエリ
            q = Comment.query
            
            # ステータスフィルター
            if status == 'approved':
                q = q.filter(Comment.is_approved == True)
            elif status == 'pending':
                q = q.filter(Comment.is_approved == False)
            
            # 検索（コンテンツのみ検索可能）
            if query:
                q = q.filter(Comment.content.contains(query))
            
            return q.order_by(Comment.created_at.desc()).all()
            
        except Exception as e:
            current_app.logger.error(f"コメント検索エラー: {str(e)}")
            return []
    
    @staticmethod
    def _send_notification(article, comment):
        """コメント通知送信"""
        try:
            # 記事著者への通知
            if article.author and article.author.notify_on_comment:
                # TODO: メール送信実装
                pass
            
            # 管理者への通知
            admins = User.query.filter(
                User.role == 'admin',
                User.notify_on_comment == True
            ).all()
            
            for admin in admins:
                # TODO: メール送信実装
                pass
                
        except Exception as e:
            current_app.logger.error(f"通知送信エラー: {str(e)}")
    
    @staticmethod
    def export_comments(format='csv', status=None):
        """コメントエクスポート"""
        try:
            # コメント取得
            q = Comment.query
            if status == 'approved':
                q = q.filter(Comment.is_approved == True)
            elif status == 'pending':
                q = q.filter(Comment.is_approved == False)
            
            comments = q.order_by(Comment.created_at.desc()).all()
            
            if format == 'csv':
                import csv
                import io
                
                output = io.StringIO()
                writer = csv.writer(output)
                
                # ヘッダー
                writer.writerow([
                    'ID', '投稿日時', '記事タイトル', '名前', 'メールアドレス', 
                    'ウェブサイト', 'コメント', '承認状態', 'IPアドレス'
                ])
                
                # データ
                for comment in comments:
                    writer.writerow([
                        comment.id,
                        comment.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                        comment.article.title,
                        EncryptionService.decrypt(comment.author_name),
                        EncryptionService.decrypt(comment.author_email),
                        comment.author_website or '',
                        comment.content,
                        '承認済み' if comment.is_approved else '未承認',
                        comment.ip_address or ''
                    ])
                
                return output.getvalue(), None
                
        except Exception as e:
            current_app.logger.error(f"エクスポートエラー: {str(e)}")
            return None, "エクスポート中にエラーが発生しました"