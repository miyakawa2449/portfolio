# filepath: c:\Users\tmiya\projects\100Day_new\016_miniBlog\forms.py (または適切な場所)
"""
フォーム定義
ユーザー入力フォームとバリデーション定義
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField, IntegerField, HiddenField, PasswordField, BooleanField, SelectField, SelectMultipleField, DateTimeField
from wtforms.validators import DataRequired, Optional, URL, Length, Email, ValidationError, NumberRange
import re
from wtforms.widgets import HiddenInput
from flask_wtf.file import FileAllowed, FileRequired

class StaticPageSEOForm(FlaskForm):
    """静的ページのSEO設定フォーム"""
    # SEO基本設定
    meta_title = StringField('メタタイトル', validators=[Optional(), Length(max=255)])
    meta_description = TextAreaField('メタディスクリプション', validators=[Optional(), Length(max=300)])
    meta_keywords = StringField('メタキーワード (カンマ区切り)', validators=[Optional(), Length(max=255)])
    
    # OGP設定
    ogp_title = StringField('OGPタイトル', validators=[Optional(), Length(max=255)])
    ogp_description = TextAreaField('OGP説明', validators=[Optional(), Length(max=300)])
    
    # OGP画像関連（カテゴリフォームと同様の実装）
    ogp_image = FileField('OGP画像', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイルのみアップロード可能です。')
    ])
    ogp_crop_x = HiddenField('OGP Crop X')
    ogp_crop_y = HiddenField('OGP Crop Y')
    ogp_crop_width = HiddenField('OGP Crop Width')
    ogp_crop_height = HiddenField('OGP Crop Height')
    ogp_crop_rotate = IntegerField('OGP Crop Rotate', widget=HiddenInput(), validators=[Optional()])
    ogp_crop_scale_x = IntegerField('OGP Crop ScaleX', widget=HiddenInput(), validators=[Optional()])
    ogp_crop_scale_y = IntegerField('OGP Crop ScaleY', widget=HiddenInput(), validators=[Optional()])
    ogp_image_alt = StringField('OGP画像のALT', validators=[Optional(), Length(max=255)])
    
    # その他のSEO設定
    canonical_url = StringField('正規URL', validators=[Optional(), URL(), Length(max=255)])
    robots = SelectField('検索エンジンロボット設定', 
                        choices=[('index,follow', 'index,follow (推奨)'),
                                ('noindex,follow', 'noindex,follow'),
                                ('index,nofollow', 'index,nofollow'),
                                ('noindex,nofollow', 'noindex,nofollow')],
                        default='index,follow')
    
    # JSON-LD構造化データ
    json_ld = TextAreaField('JSON-LD 構造化データ', validators=[Optional()])
    
    submit = SubmitField('保存')

class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[DataRequired(), Length(max=100)])
    slug = StringField('スラッグ', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('説明', validators=[Optional()])
    parent_id = IntegerField('親カテゴリID', validators=[Optional()])
    challenge_id = SelectField('チャレンジ', coerce=int, validators=[Optional()])

    # OGP画像関連
    ogp_image = FileField('OGP画像', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイルのみアップロード可能です。')
    ])
    ogp_crop_x = HiddenField('OGP Crop X')
    ogp_crop_y = HiddenField('OGP Crop Y')
    ogp_crop_width = HiddenField('OGP Crop Width')
    ogp_crop_height = HiddenField('OGP Crop Height')
    ogp_crop_rotate = IntegerField('OGP Crop Rotate', widget=HiddenInput(), validators=[Optional()])
    ogp_crop_scale_x = IntegerField('OGP Crop ScaleX', widget=HiddenInput(), validators=[Optional()])
    ogp_crop_scale_y = IntegerField('OGP Crop ScaleY', widget=HiddenInput(), validators=[Optional()])

    # SEO関連フィールド
    meta_title = StringField('メタタイトル', validators=[Optional(), Length(max=255)])
    meta_description = TextAreaField('メタディスクリプション', validators=[Optional()])
    meta_keywords = StringField('メタキーワード (カンマ区切り)', validators=[Optional(), Length(max=255)])
    canonical_url = StringField('正規URL', validators=[Optional(), URL(), Length(max=255)])
    json_ld = TextAreaField('JSON-LD 構造化データ', validators=[Optional()])
    ext_json = TextAreaField('拡張JSONデータ', validators=[Optional()])

    submit = SubmitField('更新')

class LoginForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    password = PasswordField('パスワード', validators=[DataRequired()])
    submit = SubmitField('ログイン')

class ArticleForm(FlaskForm):
    title = StringField('タイトル', validators=[DataRequired(), Length(max=255)])
    slug = StringField('スラッグ', validators=[DataRequired(), Length(max=255)])
    summary = TextAreaField('記事概要', validators=[Optional(), Length(max=500)])
    body = TextAreaField('本文', validators=[Optional()])
    
    # SEO関連フィールド
    meta_title = StringField('メタタイトル', validators=[Optional(), Length(max=255)])
    meta_description = TextAreaField('メタディスクリプション', validators=[Optional(), Length(max=300)])
    meta_keywords = StringField('メタキーワード', validators=[Optional(), Length(max=255)])
    canonical_url = StringField('正規URL', validators=[Optional(), URL(), Length(max=255)])
    json_ld = TextAreaField('構造化データ (JSON-LD)', validators=[Optional()])
    
    # 画像アップロード
    featured_image = FileField('アイキャッチ画像', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイルのみアップロード可能です。')
    ])
    
    # 公開設定
    category_id = SelectField('カテゴリ', coerce=int, validators=[Optional()])
    challenge_id = SelectField('チャレンジ', coerce=int, validators=[Optional()])
    challenge_day = IntegerField('チャレンジ日数', validators=[Optional(), NumberRange(min=1, max=1000)])
    is_published = BooleanField('公開する', validators=[Optional()])
    published_at = DateTimeField('公開日時', validators=[Optional()], format='%Y-%m-%d %H:%M')
    allow_comments = BooleanField('コメントを許可', validators=[Optional()])
    
    # プロジェクト関連（Multiple選択用のFieldListを使用）
    related_projects = SelectMultipleField('関連プロジェクト', coerce=int, validators=[Optional()])
    
    submit = SubmitField('保存')

def validate_password_strength(password):
    """パスワード強度チェック"""
    if len(password) < 8:
        raise ValidationError('パスワードは8文字以上である必要があります。')
    if not re.search(r'[A-Z]', password):
        raise ValidationError('パスワードには大文字を含む必要があります。')
    if not re.search(r'[a-z]', password):
        raise ValidationError('パスワードには小文字を含む必要があります。')
    if not re.search(r'\d', password):
        raise ValidationError('パスワードには数字を含む必要があります。')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]', password):
        raise ValidationError('パスワードには特殊文字を含む必要があります。')

class UserRegistrationForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    name = StringField('氏名', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('パスワード', validators=[DataRequired()])
    password_confirm = PasswordField('パスワード確認', validators=[DataRequired()])
    submit = SubmitField('登録')

    def validate_password(self, field):
        validate_password_strength(field.data)

    def validate_password_confirm(self, field):
        if field.data != self.password.data:
            raise ValidationError('パスワードが一致しません。')

class TOTPVerificationForm(FlaskForm):
    totp_code = StringField('認証コード', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('認証')

class TOTPSetupForm(FlaskForm):
    totp_code = StringField('認証コード', validators=[DataRequired(), Length(min=6, max=6)])
    submit = SubmitField('2段階認証を有効化')

class PasswordResetRequestForm(FlaskForm):
    email = StringField('メールアドレス', validators=[DataRequired(), Email()])
    submit = SubmitField('パスワードリセット要求')

class PasswordResetForm(FlaskForm):
    password = PasswordField('新しいパスワード', validators=[DataRequired()])
    password_confirm = PasswordField('パスワード確認', validators=[DataRequired()])
    submit = SubmitField('パスワードを変更')

    def validate_password(self, field):
        validate_password_strength(field.data)

    def validate_password_confirm(self, field):
        if field.data != self.password.data:
            raise ValidationError('パスワードが一致しません。')

class GoogleAnalyticsForm(FlaskForm):
    """Google Analytics設定フォーム"""
    google_analytics_enabled = BooleanField('Google Analyticsを有効にする', default=False)
    google_analytics_id = StringField('Google Analytics 4 Measurement ID', validators=[Optional(), Length(max=50)])
    google_tag_manager_id = StringField('Google Tag Manager Container ID', validators=[Optional(), Length(max=50)])
    custom_analytics_code = TextAreaField('カスタムアナリティクスコード', validators=[Optional()])
    analytics_track_admin = BooleanField('管理者のアクセスも追跡する', default=False)
    
    # GA4 Enhanced E-commerce設定
    enhanced_ecommerce_enabled = BooleanField('Enhanced E-commerce追跡を有効にする', default=False)
    
    # カスタムイベント設定
    track_scroll_events = BooleanField('スクロール追跡を有効にする', default=True)
    track_file_downloads = BooleanField('ファイルダウンロード追跡を有効にする', default=True)
    track_external_links = BooleanField('外部リンククリック追跡を有効にする', default=True)
    track_page_engagement = BooleanField('ページエンゲージメント追跡を有効にする', default=True)
    
    # 検索機能追跡
    track_site_search = BooleanField('サイト内検索追跡を有効にする', default=True)
    
    # ユーザープロパティ
    track_user_properties = BooleanField('ユーザープロパティ追跡を有効にする', default=False)
    
    # プライバシー・Cookie同意管理
    cookie_consent_enabled = BooleanField('Cookie同意バナーを有効にする', default=True)
    gdpr_mode = BooleanField('GDPR対応モードを有効にする', default=True)
    ccpa_mode = BooleanField('CCPA対応モードを有効にする', default=False)
    
    # Cookie同意設定
    consent_banner_text = TextAreaField('Cookie同意バナーテキスト', 
                                      default='このサイトではCookieを使用してサイトの利用状況を分析し、ユーザー体験を向上させています。')
    privacy_policy_url = StringField('プライバシーポリシーURL', validators=[Optional()])
    
    # 詳細なプライバシー設定
    analytics_storage = SelectField('Analytics Storage', 
                                  choices=[('granted', '許可'), ('denied', '拒否')], 
                                  default='denied')
    ad_storage = SelectField('Ad Storage', 
                           choices=[('granted', '許可'), ('denied', '拒否')], 
                           default='denied')
    
    submit = SubmitField('設定を保存')
    
    def validate_google_analytics_id(self, field):
        """Google Analytics IDの形式チェック"""
        if field.data and not field.data.startswith('G-'):
            raise ValidationError('Google Analytics IDは "G-" で始まる必要があります（例: G-XXXXXXXXXX）')
    
    def validate_google_tag_manager_id(self, field):
        """Google Tag Manager IDの形式チェック"""
        if field.data and not field.data.startswith('GTM-'):
            raise ValidationError('Google Tag Manager IDは "GTM-" で始まる必要があります（例: GTM-XXXXXXX）')

class ProjectForm(FlaskForm):
    """プロジェクト作成・編集フォーム"""
    title = StringField('プロジェクトタイトル', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('プロジェクト説明', validators=[Optional(), Length(max=500)])
    technologies = StringField('技術スタック', validators=[Optional(), Length(max=500)])
    
    # チャレンジ関連
    challenge_id = SelectField('チャレンジ', coerce=int, validators=[Optional()])
    challenge_day = IntegerField('チャレンジ日数', validators=[Optional(), NumberRange(min=1, max=100)])
    
    # URL情報
    github_url = StringField('GitHub URL', validators=[Optional(), URL(), Length(max=500)])
    demo_url = StringField('デモ URL', validators=[Optional(), URL(), Length(max=500)])
    
    # ステータス・設定
    status = SelectField('ステータス', 
                        choices=[('active', 'アクティブ'), ('private', 'プライベート'), ('archived', 'アーカイブ')],
                        default='active')
    is_featured = BooleanField('注目プロジェクト')
    
    # 画像アップロード
    featured_image = FileField('注目画像', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイルのみアップロード可能です。')
    ])
    
    submit = SubmitField('保存')

class PortfolioProfileForm(FlaskForm):
    """ポートフォリオプロフィール編集フォーム"""
    # 基本情報
    handle_name = StringField('表示名', validators=[Optional(), Length(max=100)])
    name_romaji = StringField('ローマ字読み', validators=[Optional(), Length(max=200)], 
                             render_kw={'placeholder': '例: Tsuyoshi Miyakawa'})
    job_title = StringField('職種・肩書き', validators=[Optional(), Length(max=255)])
    tagline = StringField('キャッチコピー', validators=[Optional(), Length(max=255)])
    introduction = TextAreaField('自己紹介', validators=[Optional(), Length(max=500)])
    
    # プロフィール写真
    profile_photo = FileField('プロフィール写真', validators=[
        FileAllowed(['jpg', 'jpeg', 'png'], '画像ファイル（JPG, PNG）のみアップロード可能です。')
    ])
    profile_photo_crop_x = HiddenField('Profile Photo Crop X')
    profile_photo_crop_y = HiddenField('Profile Photo Crop Y')
    profile_photo_crop_width = HiddenField('Profile Photo Crop Width')
    profile_photo_crop_height = HiddenField('Profile Photo Crop Height')
    
    # 連絡先情報
    portfolio_email = StringField('公開用メールアドレス', validators=[Optional(), Email(), Length(max=255)])
    linkedin_url = StringField('LinkedIn URL', validators=[Optional(), URL(), Length(max=255)])
    github_username = StringField('GitHubユーザー名', validators=[Optional(), Length(max=255)])
    
    # 履歴書PDF
    resume_pdf = FileField('履歴書PDF', validators=[
        FileAllowed(['pdf'], 'PDFファイルのみアップロード可能です。')
    ])
    
    submit = SubmitField('保存')

class SkillForm(FlaskForm):
    """スキル編集フォーム（JavaScript用）"""
    name = StringField('スキル名', validators=[DataRequired(), Length(max=100)])
    category = StringField('カテゴリ', validators=[DataRequired(), Length(max=50)])
    level = IntegerField('熟練度', validators=[Optional(), NumberRange(min=0, max=100)])
    years = IntegerField('経験年数', validators=[Optional(), NumberRange(min=0, max=50)])

class CareerForm(FlaskForm):
    """職歴編集フォーム（JavaScript用）"""
    company = StringField('会社名', validators=[DataRequired(), Length(max=255)])
    position = StringField('役職', validators=[DataRequired(), Length(max=255)])
    period = StringField('期間', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('業務内容', validators=[Optional(), Length(max=500)])

class EducationForm(FlaskForm):
    """学歴編集フォーム（JavaScript用）"""
    school = StringField('学校名', validators=[DataRequired(), Length(max=255)])
    degree = StringField('学位・専攻', validators=[DataRequired(), Length(max=255)])
    field = StringField('分野', validators=[DataRequired(), Length(max=255)])
    year = StringField('卒業年', validators=[DataRequired(), Length(max=20)])

class CertificationForm(FlaskForm):
    """資格編集フォーム（JavaScript用）"""
    name = StringField('資格名', validators=[DataRequired(), Length(max=255)])
    issuer = StringField('発行機関', validators=[DataRequired(), Length(max=255)])
    date = StringField('取得日', validators=[DataRequired(), Length(max=50)])

class CommentForm(FlaskForm):
    """コメント投稿フォーム"""
    name = StringField('お名前', validators=[DataRequired(), Length(max=100)])
    email = StringField('メールアドレス', validators=[DataRequired(), Email(), Length(max=255)])
    content = TextAreaField('コメント', validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField('コメントを投稿')