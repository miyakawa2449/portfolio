#!/usr/bin/env python3
"""
ポートフォリオサンプルデータ作成スクリプト
宮川剛氏の実際の履歴書・職務経歴書のデータを参考にサンプルデータを作成
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db
from models import User
import json

def create_portfolio_sample_data():
    """宮川剛氏の履歴書を基にしたサンプルデータを作成"""
    
    with app.app_context():
        # 管理者ユーザーを取得
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user:
            print("管理者ユーザーが見つかりません")
            return
        
        # プロフェッショナル情報の更新
        admin_user.handle_name = "Tsuyoshi"
        admin_user.job_title = "シニアITエンジニア / プロジェクトマネージャー"
        admin_user.tagline = "20年以上の経験を持つフルスタックエンジニア・教育のプロ"
        admin_user.introduction = "20年以上のIT業界経験を持つシニアエンジニア兼プロジェクトマネージャーです。パソコン講師として16年間、人材育成に携わりながら、放送・通販・物販・公的機関など多様な業界でWebシステムの設計・開発に従事してきました。教育現場や企業研修からWebシステム開発、プロジェクトマネジメントまで幅広い経験があり、現場での実践力とチームを率いるリーダーシップを発揮してきました。"
        admin_user.portfolio_email = "tsuyoshi@miyakawa.me"
        admin_user.github_username = "miyakawa2449"
        admin_user.linkedin_url = "https://linkedin.com/in/tsuyoshi-miyakawa"
        
        # スキルデータの作成
        skills_data = {
            "プログラミング言語": [
                {"name": "Python", "level": 85, "years": 2},
                {"name": "PHP", "level": 90, "years": 15},
                {"name": "JavaScript", "level": 85, "years": 12},
                {"name": "HTML/CSS", "level": 95, "years": 20},
                {"name": "C言語", "level": 70, "years": 5}
            ],
            "フレームワーク・ライブラリ": [
                {"name": "Flask", "level": 80, "years": 1},
                {"name": "WordPress", "level": 95, "years": 10},
                {"name": "WebObjects (Java)", "level": 85, "years": 8},
                {"name": "Bootstrap", "level": 90, "years": 8}
            ],
            "データベース": [
                {"name": "MySQL", "level": 90, "years": 15},
                {"name": "PostgreSQL", "level": 85, "years": 10},
                {"name": "MariaDB", "level": 85, "years": 8}
            ],
            "ツール・環境": [
                {"name": "Git", "level": 85, "years": 10},
                {"name": "Xcode", "level": 75, "years": 8},
                {"name": "Figma", "level": 70, "years": 1},
                {"name": "Adobe Photoshop", "level": 80, "years": 15},
                {"name": "Adobe Illustrator", "level": 75, "years": 12}
            ],
            "プロジェクト管理": [
                {"name": "要求定義・仕様書作成", "level": 95, "years": 18},
                {"name": "プロジェクト計画・進捗管理", "level": 95, "years": 20},
                {"name": "チームリーダーシップ", "level": 90, "years": 18},
                {"name": "ガントチャート作成", "level": 85, "years": 15}
            ]
        }
        
        # 職歴データの作成
        career_data = [
            {
                "company": "日本アイ・ビー・エム株式会社（インターンシップ）",
                "position": "研修生・チームリーダー",
                "period": "2024年8月～2025年1月",
                "description": "最先端IT技術の研究開発とデータ分析を駆使したITソリューション及びコンサルティングに関する研修プログラムに参加。グループワークではチームリーダーとして課題分析、データ収集・分析、ソリューション企画、仮想クライアントへの提案プレゼンを主導。要求定義からDB設計、プロトタイプ開発まで一貫して担当し、チーム全体を牽引。"
            },
            {
                "company": "ミヤカワプロデザイン",
                "position": "代表・プロデューサー/ディレクター",
                "period": "2018年7月～2024年7月",
                "description": "中小企業向けウェブサイト開発・保守、パソコン研修事業を運営。WordPressを中心としたコンテンツ制作および保守メンテナンス事業、企業研修・雇用訓練（Microsoft Office製品の指導）を手がける。企画立案から進行管理、受講生管理まで一貫して担当。"
            },
            {
                "company": "株式会社ビットストリーム",
                "position": "プロデューサー/PM/SE",
                "period": "2015年1月～2018年6月",
                "description": "中小企業向けCMSの受託システム開発を担当。いしかわ結婚支援センターの婚活支援ポータルサイト、ヤマキシリフォームのB to Cサイト、ブリヂストンタイヤ館のサイトリニューアルなど、要件定義から基本設計、受け入れテストまでを一貫して担当。PM・SEだけでなくプロデューサーとしての経験も積む。"
            },
            {
                "company": "株式会社フィックス インターメディア事業部",
                "position": "PM/SE",
                "period": "2006年1月～2013年6月",
                "description": "ネットショップ金沢屋システム保守・管理、放送局番組用CMS、受託開発を担当。PiTENTRY2のバージョンアップ（UX・UI改善、データ放送対応）、選挙速報テレビ放送システムの構築、ECサイト「金沢屋」のフルリニューアルなど、大規模プロジェクトのPM・SEとして活躍。本番放送の運営も担当。"
            },
            {
                "company": "株式会社大栄総合教育システム",
                "position": "パソコン講師・進行管理",
                "period": "1994年4月～2000年1月",
                "description": "社会人教育サービス（簿記・宅建・公務員・パソコンなど）において、Microsoft Word、Excel、ワープロ・表計算検定、初級システムアドミニストレータ試験対策を担当。講座説明会、スケジュール管理、受講生募集、受講生管理まで一貫して担当し、多くの合格者を輩出。"
            }
        ]
        
        # 学歴データの作成
        education_data = [
            {
                "school": "デジタルハリウッド金沢校",
                "degree": "Webデザイン科",
                "field": "Web技術・デザイン",
                "year": "2002年卒業"
            },
            {
                "school": "小松短期大学",
                "degree": "産業情報科",
                "field": "C言語専攻",
                "year": "1994年卒業"
            },
            {
                "school": "金沢龍谷高等学校（当時 私立尾山台高等学校）",
                "degree": "普通科",
                "field": "普通教育",
                "year": "1992年卒業"
            }
        ]
        
        # 資格データの作成
        certifications_data = [
            {
                "name": "Agile Explorer",
                "issuer": "IBM SkillsBuild",
                "date": "2024年12月"
            },
            {
                "name": "Project Management Fundamentals",
                "issuer": "IBM SkillsBuild",
                "date": "2024年11月"
            },
            {
                "name": "Artificial Intelligence Fundamentals",
                "issuer": "IBM SkillsBuild",
                "date": "2024年11月"
            },
            {
                "name": "Python3エンジニア認定基礎試験",
                "issuer": "一般社団法人Pythonエンジニア育成推進協会",
                "date": "2024年2月"
            },
            {
                "name": "コンピュータサービス技能評価試験 表計算Excel 2級",
                "issuer": "中央職業能力開発協会",
                "date": "2019年4月"
            },
            {
                "name": "初級システムアドミニストレータ（ITパスポートの前身）",
                "issuer": "経済産業省",
                "date": "1998年12月"
            },
            {
                "name": "コンピュータサービス技能評価試験 ワープロ検定 1級",
                "issuer": "中央職業能力開発協会",
                "date": "1994年6月"
            }
        ]
        
        # データベースに保存
        admin_user.skills = skills_data
        admin_user.career_history = career_data
        admin_user.education = education_data
        admin_user.certifications = certifications_data
        
        try:
            db.session.commit()
            print("ポートフォリオサンプルデータを正常に作成しました")
            print(f"ユーザー: {admin_user.handle_name}")
            print(f"職種: {admin_user.job_title}")
            print(f"スキルカテゴリ数: {len(skills_data)}")
            print(f"職歴数: {len(career_data)}")
            print(f"学歴数: {len(education_data)}")
            print(f"資格数: {len(certifications_data)}")
            
        except Exception as e:
            db.session.rollback()
            print(f"エラーが発生しました: {str(e)}")
            
if __name__ == "__main__":
    create_portfolio_sample_data()