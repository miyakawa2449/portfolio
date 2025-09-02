from flask import Blueprint, render_template, request, abort
from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload
from models import Category, Article, article_categories, db
from utils import generate_ogp_data

categories_bp = Blueprint('categories', __name__)

@categories_bp.route('/category/<slug>/')
def category_page(slug):
    """カテゴリページ表示"""
    
    # カテゴリ取得
    category = Category.query.filter_by(slug=slug).first_or_404()
    
    # ページング設定
    page = request.args.get('page', 1, type=int)
    per_page = 10
    
    # カテゴリに属する公開記事を取得（relationshipを使用）
    articles_pagination = Article.query.filter(
        Article.is_published == True,
        Article.categories.any(Category.id == category.id)
    ).order_by(
        Article.published_at.desc(),
        Article.created_at.desc()
    ).paginate(
        page=page, 
        per_page=per_page, 
        error_out=False
    )
    
    # 子カテゴリ取得
    child_categories = Category.query.filter_by(parent_id=category.id).all()
    
    # パンくずナビゲーション用の親カテゴリ階層取得
    breadcrumbs = []
    current_cat = category
    while current_cat:
        breadcrumbs.insert(0, current_cat)
        current_cat = current_cat.parent
    
    # OGPデータ生成
    ogp_data = generate_ogp_data(
        title=category.meta_title or f"{category.name} - カテゴリ",
        description=category.meta_description or category.description,
        image_url=category.ogp_image,
        url=request.url
    )
    
    return render_template('category_page.html',
                         category=category,
                         articles_pagination=articles_pagination,
                         child_categories=child_categories,
                         breadcrumbs=breadcrumbs,
                         ogp_data=ogp_data)