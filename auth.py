"""
Authentication Blueprint - 認証関連機能
"""
import os
import io
import base64
import qrcode
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from flask_login import current_user, login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from sqlalchemy import select
from models import db, User
from forms import LoginForm, TOTPVerificationForm, TOTPSetupForm

# 認証ブループリント作成
auth_bp = Blueprint('auth', __name__)

# 環境変数でログインURLをカスタマイズ可能
LOGIN_URL_PATH = os.environ.get('LOGIN_URL_PATH', 'login')

@auth_bp.route(f'/{LOGIN_URL_PATH}/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        user = db.session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user and check_password_hash(user.password_hash, password):
            # 2段階認証が有効な場合はTOTP画面へ
            if user.totp_enabled:
                session['temp_user_id'] = user.id
                return redirect(url_for('auth.totp_verify'))
            else:
                login_user(user)
                session['user_id'] = user.id
                flash('ログインしました。', 'success')
                next_page = request.args.get('next')
                return redirect(next_page or url_for('landing'))
        else:
            # ログイン失敗をログに記録（セキュリティ監視用）
            current_app.logger.warning(f"Failed login attempt for email: {email}")
            flash('メールアドレスまたはパスワードが正しくありません。', 'danger')
    
    return render_template('login.html', form=form)

@auth_bp.route('/totp_verify/', methods=['GET', 'POST'])
def totp_verify():
    if current_user.is_authenticated:
        return redirect(url_for('landing'))
    
    temp_user_id = session.get('temp_user_id')
    if not temp_user_id:
        flash('不正なアクセスです。', 'danger')
        return redirect(url_for('auth.login'))
    
    user = db.session.get(User, temp_user_id)
    if not user or not user.totp_enabled:
        flash('2段階認証が設定されていません。', 'danger')
        return redirect(url_for('auth.login'))
    
    form = TOTPVerificationForm()
    if form.validate_on_submit():
        totp_code = form.totp_code.data
        if user.verify_totp(totp_code):
            login_user(user)
            session['user_id'] = user.id
            session.pop('temp_user_id', None)
            flash('ログインしました。', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('landing'))
        else:
            flash('認証コードが正しくありません。', 'danger')
    
    return render_template('totp_verify.html', form=form)

@auth_bp.route('/logout/')
@login_required
def logout():
    logout_user()
    session.pop('user_id', None)
    session.pop('temp_user_id', None)
    flash('ログアウトしました。', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/totp_setup/', methods=['GET', 'POST'])
@login_required
def totp_setup():
    if current_user.totp_enabled:
        flash('2段階認証は既に有効になっています。', 'info')
        return redirect(url_for('admin.dashboard'))
    
    form = TOTPSetupForm()
    
    # QRコード生成
    if not current_user.totp_secret:
        current_user.generate_totp_secret()
        db.session.commit()
    
    totp_uri = current_user.get_totp_uri()
    
    # QRコード画像をBase64エンコードで生成
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    
    qr_code_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    
    if form.validate_on_submit():
        totp_code = form.totp_code.data
        if current_user.verify_totp(totp_code):
            current_user.totp_enabled = True
            db.session.commit()
            flash('2段階認証が有効になりました。', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('認証コードが正しくありません。', 'danger')
    
    return render_template('totp_setup.html', form=form, qr_code=qr_code_base64, secret=current_user.totp_secret)

@auth_bp.route('/totp_disable/', methods=['GET', 'POST'])
@login_required
def totp_disable():
    if not current_user.totp_enabled:
        flash('2段階認証は有効になっていません。', 'info')
        return redirect(url_for('admin.dashboard'))
    
    form = TOTPVerificationForm()
    if form.validate_on_submit():
        totp_code = form.totp_code.data
        if current_user.verify_totp(totp_code):
            current_user.totp_enabled = False
            current_user.totp_secret = None
            db.session.commit()
            flash('2段階認証を無効にしました。', 'info')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('認証コードが正しくありません。', 'danger')
    
    return render_template('totp_disable.html', form=form)