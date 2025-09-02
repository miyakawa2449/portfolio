"""
Error Handlers - アプリケーションエラーハンドラー
"""
from flask import Blueprint, render_template, current_app, request
from werkzeug.exceptions import HTTPException

errors_bp = Blueprint('errors', __name__)

@errors_bp.app_errorhandler(404)
def not_found_error(error):
    """404 Not Found エラーハンドラー"""
    current_app.logger.warning(f"404 Error: {request.url}")
    return render_template('errors/404.html'), 404

@errors_bp.app_errorhandler(500)
def internal_error(error):
    """500 Internal Server Error エラーハンドラー"""
    current_app.logger.error(f"500 Error: {str(error)}")
    return render_template('errors/500.html'), 500

@errors_bp.app_errorhandler(403)
def forbidden_error(error):
    """403 Forbidden エラーハンドラー"""
    current_app.logger.warning(f"403 Error: {request.url}")
    return render_template('errors/403.html'), 403

@errors_bp.app_errorhandler(Exception)
def handle_exception(error):
    """一般的な例外ハンドラー"""
    # HTTPExceptionの場合は元のハンドラーに委ねる
    if isinstance(error, HTTPException):
        return error
    
    # 予期しない例外をログに記録
    current_app.logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
    return render_template('errors/500.html'), 500