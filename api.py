"""
API Blueprint - RESTful API エンドポイント
"""
from flask import Blueprint, jsonify
from models import Project, Category
import os
import glob
from datetime import datetime

# APIブループリント作成
api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/projects/by-challenge/<int:challenge_id>')
def projects_by_challenge(challenge_id):
    """チャレンジIDに基づくプロジェクトリストを返すAPI"""
    projects = Project.query.filter_by(
        challenge_id=challenge_id, 
        status='active'
    ).order_by(Project.created_at.desc()).all()
    
    return jsonify({
        'projects': [{
            'id': p.id,
            'title': p.title,
            'challenge_day': p.challenge_day
        } for p in projects]
    })

@api_bp.route('/categories/by-challenge/<int:challenge_id>')
def categories_by_challenge(challenge_id):
    """チャレンジIDに基づくカテゴリリストを返すAPI"""
    categories = Category.query.filter_by(
        challenge_id=challenge_id
    ).order_by(Category.name).all()
    
    return jsonify({
        'categories': [{
            'id': c.id,
            'name': c.name
        } for c in categories]
    })

@api_bp.route('/images/gallery')
def images_gallery():
    """アップロード済み画像のギャラリーを返すAPI"""
    images = []
    upload_dirs = [
        ('articles', 'static/uploads/articles/'),
        ('projects', 'static/uploads/projects/'),
        ('categories', 'static/uploads/categories/'),
        ('content', 'static/uploads/content/')
    ]
    
    for category, upload_path in upload_dirs:
        if os.path.exists(upload_path):
            # 画像ファイルを取得
            image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
            for ext in image_extensions:
                for filepath in glob.glob(os.path.join(upload_path, ext)):
                    filename = os.path.basename(filepath)
                    # ファイル情報を取得
                    stat = os.stat(filepath)
                    
                    images.append({
                        'filename': filename,
                        'url': f'/static/uploads/{category}/{filename}',
                        'category': category,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                        'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
    
    # 更新日時で降順ソート
    images.sort(key=lambda x: x['modified_at'], reverse=True)
    
    return jsonify({
        'images': images,
        'total': len(images)
    })