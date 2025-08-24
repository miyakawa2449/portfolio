#!/usr/bin/env python
"""
Day 2のNumpy基礎記事をベースにデータ分析サンプルプロジェクトを作成するスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Project, Article
from app import app
from datetime import datetime
import json

def create_numpy_project():
    """Numpyデータ分析プロジェクトを作成"""
    with app.app_context():
        # Day 2の記事を取得
        article = Article.query.filter_by(challenge_day=2).first()
        if not article:
            print("❌ Day 2の記事が見つかりません")
            return
        
        # 既存のプロジェクトを確認
        existing_project = Project.query.filter_by(slug='numpy-data-analysis-basics').first()
        if existing_project:
            print("✅ Numpyデータ分析プロジェクトは既に存在します")
            return
        
        print("📊 Numpy データ分析基礎プロジェクトを作成中...")
        
        # プロジェクトデータ
        project = Project(
            title="Numpy データ分析基礎",
            slug="numpy-data-analysis-basics",
            description="Numpyを活用した数値計算・配列操作の基礎プロジェクト。データサイエンスの基盤となる数値処理テクニックを学習。",
            long_description="""## 概要

Python 100日チャレンジのDay 2で学習したNumpyの基礎概念を実践的なプロジェクトにまとめました。
データサイエンスの基盤となる数値計算ライブラリNumpyの重要な機能を網羅的に学習できます。

## 学習内容

### 1. 配列の基本操作
- 1次元・多次元配列の作成
- 配列の形状変更とスライシング
- インデックスとブールインデックス

### 2. 数値計算
- 要素ごとの演算と行列演算
- 統計関数（平均・標準偏差・合計など）
- 三角関数・指数関数などの数学関数

### 3. 配列操作
- 配列の結合・分割
- 条件に基づくフィルタリング
- ソートと検索

### 4. 実践的な応用
- データの前処理テクニック
- 欠損値の処理
- パフォーマンス最適化

## 技術的特徴

- 高効率な数値計算
- メモリ効率的なデータ処理
- 科学計算ライブラリとの連携
- ベクトル化による処理速度向上

このプロジェクトは、データサイエンス・機械学習の学習に不可欠な基礎知識を習得できます。""",
            technologies='["Python", "Numpy", "データサイエンス", "数値計算", "配列操作", "統計処理"]',
            github_url="https://github.com/username/numpy-data-analysis-basics",
            demo_url="https://colab.research.google.com/drive/numpy-basics-demo",
            challenge_id=article.challenge_id,
            challenge_day=2,
            article_id=article.id,
            status="active",
            is_featured=False,
            display_order=2,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # プロジェクトを保存
        db.session.add(project)
        db.session.commit()
        
        # 記事にプロジェクトIDを関連付け
        if not article.project_ids or article.project_ids == '[]':
            article.project_ids = json.dumps([project.id])
        else:
            project_ids = json.loads(article.project_ids)
            if project.id not in project_ids:
                project_ids.append(project.id)
                article.project_ids = json.dumps(project_ids)
        
        db.session.commit()
        
        print("✅ プロジェクトが作成されました!")
        print(f"   プロジェクトID: {project.id}")
        print(f"   タイトル: {project.title}")
        print(f"   スラッグ: {project.slug}")
        print(f"   関連記事: Day {article.challenge_day} - {article.title}")
        print(f"   技術スタック: {', '.join(json.loads(project.technologies))}")

if __name__ == '__main__':
    create_numpy_project()