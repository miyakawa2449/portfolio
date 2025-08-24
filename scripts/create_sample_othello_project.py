#!/usr/bin/env python
"""
Day 5のシンプルオセロゲーム記事をベースにサンプルプロジェクトを作成するスクリプト
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, Project, Article
from app import app
from datetime import datetime
import json

def create_othello_project():
    """オセロゲームプロジェクトを作成"""
    with app.app_context():
        # Day 5の記事を取得
        article = Article.query.filter_by(challenge_day=5).first()
        if not article:
            print("❌ Day 5の記事が見つかりません")
            return
        
        # 既存のプロジェクトを確認
        existing_project = Project.query.filter_by(slug='simple-othello-game').first()
        if existing_project:
            print("✅ オセロゲームプロジェクトは既に存在します")
            return
        
        print("🎮 シンプルオセロゲームプロジェクトを作成中...")
        
        # プロジェクトデータ
        project = Project(
            title="シンプルオセロゲーム",
            slug="simple-othello-game",
            description="Pythonで作成したグラフィカルなオセロゲーム。8x8の盤面でAIまたは対人戦が楽しめる2Dゲームです。",
            long_description="""## 概要

Python 100日チャレンジのDay 5で作成したシンプルなオセロゲームです。
tkinterを使用してグラフィカルなインターフェースを実装し、マウス操作で石を配置できます。

## 主な機能

- **8x8のゲーム盤**: 緑色の盤面に黒い格子線
- **石の配置と反転**: クリックで石を配置、ルールに従って自動反転
- **スコア表示**: リアルタイムでの石数表示
- **勝敗判定**: ゲーム終了時の勝者判定
- **直感的操作**: マウスクリックによる簡単操作

## 技術的特徴

- tkinterによるGUI実装
- オブジェクト指向プログラミング
- ゲームロジックの実装
- リアルタイム盤面更新

このプロジェクトは、ゲーム開発の基本概念とPythonのGUIプログラミングを学ぶのに最適です。""",
            technologies='["Python", "tkinter", "ゲーム開発", "GUI プログラミング", "オブジェクト指向"]',
            github_url="https://github.com/username/python-othello-game",
            demo_url=None,  # ローカルアプリケーションのためデモURLなし
            challenge_id=article.challenge_id,
            challenge_day=5,
            article_id=article.id,
            status="active",
            is_featured=True,  # サンプルプロジェクトとしてフィーチャーに
            display_order=1,
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
    create_othello_project()