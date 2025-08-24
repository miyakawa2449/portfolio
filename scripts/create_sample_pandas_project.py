#!/usr/bin/env python
"""
Day 3のPandas基礎記事をベースにデータ処理サンプルプロジェクトを作成するスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Project, Article
from app import app
from datetime import datetime
import json

def create_pandas_project():
    """Pandasデータ処理プロジェクトを作成"""
    with app.app_context():
        # Day 3の記事を取得
        article = Article.query.filter_by(challenge_day=3).first()
        if not article:
            print("❌ Day 3の記事が見つかりません")
            return
        
        # 既存のプロジェクトを確認
        existing_project = Project.query.filter_by(slug='pandas-data-processing-basics').first()
        if existing_project:
            print("✅ Pandasデータ処理プロジェクトは既に存在します")
            return
        
        print("🐼 Pandas データ処理基礎プロジェクトを作成中...")
        
        # プロジェクトデータ
        project = Project(
            title="Pandas データ処理基礎",
            slug="pandas-data-processing-basics",
            description="PandasによるDataFrame操作・データ前処理の実践プロジェクト。CSVファイルの読み書きから高度な集計処理まで習得。",
            long_description="""## 概要

Python 100日チャレンジのDay 3で学習したPandasの基礎概念を実践的なプロジェクトとして構築。
データ分析・機械学習における重要なデータ前処理スキルを体系的に学習できます。

## 主な機能

### 1. データの読み込みと保存
- CSV、Excel、JSONファイルの読み書き
- データベース連携
- Web上のデータ取得

### 2. DataFrame操作
- 列・行の選択とフィルタリング
- データのソートと並び替え
- 結合・マージ・連結操作

### 3. データクリーニング
- 欠損値の検出と処理
- 重複データの除去
- データ型変換とバリデーション

### 4. 集計・分析
- グループ化と集計処理
- ピボットテーブル作成
- 時系列データ処理

### 5. データ可視化連携
- Matplotlib・Seabornとの連携
- 統計サマリーの生成
- 探索的データ分析

## 技術的特徴

- 大容量データの効率的処理
- 柔軟なデータ変換機能
- SQLライクなデータ操作
- NumPyとの完全な連携

実際のビジネスデータを想定したサンプルデータセットを使用し、実践的なデータ分析スキルを習得できます。""",
            technologies='["Python", "Pandas", "データ処理", "データクリーニング", "CSV操作", "DataFrame", "データ分析"]',
            github_url="https://github.com/username/pandas-data-processing-basics",
            demo_url="https://colab.research.google.com/drive/pandas-basics-demo",
            challenge_id=article.challenge_id,
            challenge_day=3,
            article_id=article.id,
            status="active",
            is_featured=False,
            display_order=3,
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
    create_pandas_project()