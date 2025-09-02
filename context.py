"""
Context Processors - テンプレートコンテキスト処理
"""
from flask import current_app
from flask_login import current_user
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup
from sqlalchemy import select
from models import db, SiteSetting, User

def register_context_processors(app):
    """アプリケーションにコンテキストプロセッサーを登録"""
    
    @app.context_processor
    def inject_csrf_token():
        """CSRFトークンをテンプレートで利用可能にする"""
        def csrf_token():
            token = generate_csrf()
            return Markup(f'<input type="hidden" name="csrf_token" value="{token}"/>')
        
        def csrf_token_value():
            return generate_csrf()
        
        return dict(csrf_token=csrf_token, csrf_token_value=csrf_token_value)

    @app.context_processor
    def inject_analytics():
        """Google Analyticsの設定をテンプレートに注入"""
        def google_analytics_code():
            """Enhanced Google Analytics トラッキングコードを生成"""
            from ga4_analytics import GA4AnalyticsManager
            
            analytics_manager = GA4AnalyticsManager()
            
            # ユーザーを追跡すべきかチェック
            user = current_user if current_user.is_authenticated else None
            
            # トラッキングコードを生成
            tracking_code = analytics_manager.generate_tracking_code(user)
            
            # カスタムアナリティクスコード
            custom_code = SiteSetting.get_setting('custom_analytics_code', '')
            if custom_code:
                tracking_code = Markup(str(tracking_code) + f'\n<!-- Custom Analytics Code -->\n{custom_code}')
            
            return tracking_code
        
        def google_tag_manager_noscript():
            """Enhanced Google Tag Manager noscript 部分"""
            from ga4_analytics import GA4AnalyticsManager
            
            analytics_manager = GA4AnalyticsManager()
            
            # ユーザーを追跡すべきかチェック
            user = current_user if current_user.is_authenticated else None
            
            # GTM noscript部分を生成
            return analytics_manager.generate_gtm_noscript(user)
        
        return dict(
            google_analytics_code=google_analytics_code,
            google_tag_manager_noscript=google_tag_manager_noscript
        )

    @app.context_processor
    def inject_site_settings():
        """サイト設定をすべてのテンプレートで利用可能にする"""
        import json
        
        def get_site_settings():
            """公開設定のみを取得（キャッシュ機能付き）"""
            try:
                # 公開設定のみを取得
                public_settings = db.session.execute(
                    select(SiteSetting).where(SiteSetting.is_public == True)
                ).scalars().all()
                
                settings = {}
                for setting in public_settings:
                    value = setting.value
                    
                    # 設定タイプに応じて値を変換
                    if setting.setting_type == 'boolean':
                        value = value.lower() == 'true'
                    elif setting.setting_type == 'number':
                        try:
                            value = float(value) if '.' in value else int(value)
                        except ValueError:
                            value = 0
                    elif setting.setting_type == 'json':
                        try:
                            value = json.loads(value) if value else {}
                        except json.JSONDecodeError:
                            value = {}
                    
                    settings[setting.key] = value
                
                return settings
            except Exception as e:
                current_app.logger.error(f"Error loading site settings: {e}")
                return {}
        
        def get_setting(key, default=None):
            """個別設定値を取得"""
            try:
                return SiteSetting.get_setting(key, default)
            except Exception as e:
                current_app.logger.error(f"Error getting setting {key}: {e}")
                return default
        
        def get_admin_user():
            """管理者ユーザー情報を取得"""
            try:
                admin_user = db.session.execute(
                    select(User).where(User.role == 'admin').limit(1)
                ).scalar_one_or_none()
                if admin_user:
                    pass
                else:
                    current_app.logger.warning("No admin user found")
                return admin_user
            except Exception as e:
                current_app.logger.error(f"Error loading admin user: {e}")
                return None
        
        return dict(
            site_settings=get_site_settings(),
            get_setting=get_setting,
            admin_user=get_admin_user()
        )