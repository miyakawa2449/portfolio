# filepath: c:\Users\tmiya\projects\100Day_new\016_miniBlog\forms.py (または適切な場所)
"""
フォーム定義
ユーザー入力フォームとバリデーション定義
"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField, FileField, IntegerField, HiddenField, PasswordField, BooleanField, SelectField
from wtforms.validators import DataRequired, Optional, URL, Length, Email, ValidationError
import re
from wtforms.widgets import HiddenInput
from flask_wtf.file import FileAllowed, FileRequired

class CategoryForm(FlaskForm):
    name = StringField('カテゴリ名', validators=[DataRequired(), Length(max=100)])
    slug = StringField('スラッグ', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('説明', validators=[Optional()])
    parent_id = IntegerField('親カテゴリID', validators=[Optional()])

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
    
    # 画像アップロード
    featured_image = FileField('アイキャッチ画像', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'gif'], '画像ファイルのみアップロード可能です。')
    ])
    
    # 公開設定
    category_id = SelectField('カテゴリ', coerce=int, validators=[Optional()])
    is_published = BooleanField('公開する', validators=[Optional()])
    allow_comments = BooleanField('コメントを許可', validators=[Optional()])
    
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

class WordPressImportForm(FlaskForm):
    """WordPress インポートフォーム"""
    xml_file = FileField('WordPress エクスポートファイル (XML)', validators=[
        FileRequired('XMLファイルを選択してください'),
        FileAllowed(['xml'], 'XMLファイルのみアップロード可能です')
    ])
    author_id = SelectField('記事の著者', coerce=int, validators=[DataRequired()])
    dry_run = BooleanField('テスト実行（実際にはインポートしない）', default=False)
    
    # 詳細オプション
    import_categories = BooleanField('カテゴリをインポート', default=True)
    import_images = BooleanField('画像をダウンロード', default=True)
    skip_duplicates = BooleanField('重複データをスキップ', default=True)
    
    submit = SubmitField('インポート開始')
    
    def __init__(self, *args, **kwargs):
        super(WordPressImportForm, self).__init__(*args, **kwargs)
        # 著者選択肢を動的に設定
        from models import User
        self.author_id.choices = [(user.id, f"{user.name} ({user.email})") 
                                  for user in User.query.filter_by(role='admin').all()]
        if not self.author_id.choices:
            # 管理者がいない場合は全ユーザーから選択
            self.author_id.choices = [(user.id, f"{user.name} ({user.email})") 
                                      for user in User.query.all()]

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