from flask import Blueprint, render_template, abort, make_response
from flask_login import current_user, login_required
from sqlalchemy import select, func
from models import Article, Project, Category, Challenge, SiteSetting, User, db
from seo import get_static_page_seo
from datetime import datetime

landing_bp = Blueprint('landing', __name__)

@landing_bp.route('/')
def landing():
    """ビジネス・サービス中心のトップページ"""
    # 基本的なデータを取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 注目プロジェクト（最新実績として表示）
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('home')
    
    return render_template('landing.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         featured_projects=featured_projects,
                         page_seo=page_seo)

@landing_bp.route('/portfolio')
def portfolio():
    """ポートフォリオページ（100日チャレンジ）"""
    # アクティブなチャレンジを取得
    active_challenge = db.session.execute(
        select(Challenge).where(Challenge.is_active.is_(True))
    ).scalar_one_or_none()
    
    if not active_challenge:
        # アクティブなチャレンジがない場合、最新のチャレンジを取得
        active_challenge = db.session.execute(
            select(Challenge).order_by(Challenge.display_order.desc())
        ).scalar_one_or_none()
    
    # 最新記事を取得（アクティブチャレンジの記事を優先）
    if active_challenge:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(
            # アクティブチャレンジの記事を優先、その後公開日順
            (Article.challenge_id == active_challenge.id).desc(),
            Article.published_at.desc()
        ).limit(5)
    else:
        latest_articles_query = select(Article).where(
            Article.is_published.is_(True)
        ).order_by(Article.published_at.desc()).limit(5)
    
    latest_articles = db.session.execute(latest_articles_query).scalars().all()
    
    # 記事の総数を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    # スキルカテゴリを取得
    skill_categories = db.session.execute(
        select(Category).where(Category.parent_id.is_(None)).order_by(Category.name)
    ).scalars().all()
    
    # すべてのチャレンジを取得（一覧表示用）
    all_challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order)
    ).scalars().all()
    
    # 注目プロジェクトを取得（最大3件）
    featured_projects = db.session.execute(
        select(Project).where(
            Project.status == 'active',
            Project.is_featured.is_(True)
        ).order_by(Project.display_order).limit(3)
    ).scalars().all()
    
    # プロジェクト総数を取得
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # 現在の学習日数を計算（アクティブチャレンジベース）
    current_day = 0
    if active_challenge:
        current_day = active_challenge.days_elapsed
    
    return render_template('portfolio.html',
                         active_challenge=active_challenge,
                         latest_articles=latest_articles,
                         total_articles=total_articles,
                         total_projects=total_projects,
                         current_day=current_day,
                         skill_categories=skill_categories,
                         all_challenges=all_challenges,
                         featured_projects=featured_projects)

@landing_bp.route('/services')
def services():
    """サービス詳細ページ"""
    # 実績プロジェクト（詳細表示用）
    all_projects = db.session.execute(
        select(Project).where(Project.status == 'active')
        .order_by(Project.display_order)
    ).scalars().all()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('services')
    
    return render_template('services.html', 
                         projects=all_projects,
                         page_seo=page_seo)

@landing_bp.route('/story')
def story():
    """キャリアストーリーページ"""
    # 実際の数値を取得
    total_articles = db.session.execute(
        select(func.count(Article.id)).where(Article.is_published.is_(True))
    ).scalar()
    
    total_projects = db.session.execute(
        select(func.count(Project.id)).where(Project.status == 'active')
    ).scalar()
    
    # SEO設定を取得
    page_seo = get_static_page_seo('story')
    
    return render_template('story.html',
                         total_articles=total_articles,
                         total_projects=total_projects,
                         page_seo=page_seo)

@landing_bp.route('/about/')
def profile():
    """ユーザープロフィールページ（ポートフォリオ版）"""
    # 管理者ユーザーを取得（一人管理前提）
    user = db.session.execute(select(User).where(User.role == 'admin')).scalar_one_or_none()
    if not user:
        abort(404)
    
    # SEO設定を取得
    page_seo = get_static_page_seo('about')
    
    # 公開記事のみ取得
    articles = db.session.execute(
        select(Article).where(Article.author_id == user.id, Article.is_published.is_(True)).order_by(
            db.case(
                (Article.published_at.isnot(None), Article.published_at),
                else_=Article.created_at
            ).desc()
        )
    ).scalars().all()
    
    # プロジェクトを取得（作成者でフィルタ可能な場合）
    projects = db.session.execute(
        select(Project).order_by(Project.created_at.desc())
    ).scalars().all()
    
    # 注目プロジェクトを取得
    featured_projects = [p for p in projects if p.is_featured]
    
    # チャレンジ情報を取得
    challenges = db.session.execute(
        select(Challenge).order_by(Challenge.display_order, Challenge.id)
    ).scalars().all()
    
    return render_template('profile_portfolio.html', 
                           user=user, 
                           articles=articles,
                           projects=projects,
                           featured_projects=featured_projects,
                           challenges=challenges,
                           page_seo=page_seo)

@landing_bp.route('/download/resume/<int:user_id>')
@login_required
def download_resume(user_id):
    """履歴書PDFダウンロード（動的日付生成）"""
    from io import BytesIO
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    
    # 日本語フォント設定
    pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
    
    # ユーザー情報取得
    user = User.query.get_or_404(user_id)
    
    # アクセス権限チェック（本人または管理者のみ）
    if current_user.id != user.id and current_user.role != 'admin':
        abort(403)
    
    # PDFバッファー作成
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
    
    # スタイル設定
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#333333'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='HeiseiKakuGo-W5'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=12,
        fontName='HeiseiKakuGo-W5'
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        fontName='HeiseiKakuGo-W5'
    )
    
    # ドキュメント要素
    elements = []
    
    # タイトル
    elements.append(Paragraph("履歴書", title_style))
    elements.append(Spacer(1, 12))
    
    # 日付（動的生成）
    today = datetime.now().strftime('%Y年%m月%d日')
    elements.append(Paragraph(f"{today} 現在", normal_style))
    elements.append(Spacer(1, 20))
    
    # 基本情報テーブル
    basic_info = [
        ['氏名', user.handle_name or user.name],
        ['メールアドレス', user.portfolio_email or user.email],
        ['職種', user.job_title or '未設定']
    ]
    
    if user.birthplace:
        basic_info.append(['出身地', user.birthplace])
    
    basic_table = Table(basic_info, colWidths=[4*cm, 10*cm])
    basic_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'HeiseiKakuGo-W5'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    
    elements.append(basic_table)
    elements.append(Spacer(1, 30))
    
    # スキル情報
    if user.skills:
        elements.append(Paragraph("スキル・技術", heading_style))
        if isinstance(user.skills, dict):
            for category, skills_list in user.skills.items():
                skill_names = [f"{skill['name']} ({skill.get('years', 'N/A')}年)" for skill in skills_list]
                elements.append(Paragraph(f"<b>{category}:</b> {', '.join(skill_names)}", normal_style))
                elements.append(Spacer(1, 6))
        else:
            # リスト形式の場合の処理
            skill_names = [str(skill) for skill in user.skills]
            elements.append(Paragraph(f"<b>スキル:</b> {', '.join(skill_names)}", normal_style))
            elements.append(Spacer(1, 6))
        elements.append(Spacer(1, 20))
    
    # 職歴
    if user.career_history:
        elements.append(Paragraph("職歴", heading_style))
        try:
            for i, job in enumerate(user.career_history):
                if isinstance(job, dict):
                    elements.append(Paragraph(f"<b>{job.get('company', '未設定')}</b> - {job.get('position', '未設定')}", normal_style))
                    elements.append(Paragraph(f"期間: {job.get('period', '未設定')}", normal_style))
                    if job.get('description'):
                        elements.append(Paragraph(job['description'], normal_style))
                else:
                    elements.append(Paragraph(str(job), normal_style))
                if i < len(user.career_history) - 1:
                    elements.append(Spacer(1, 12))
        except Exception as e:
            elements.append(Paragraph(f"職歴情報の読み込みエラー: {str(e)}", normal_style))
    
    # PDF生成
    doc.build(elements)
    
    # レスポンス作成
    buffer.seek(0)
    response = make_response(buffer.read())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=resume_{user.id}_{datetime.now().strftime("%Y%m%d")}.pdf'
    
    return response