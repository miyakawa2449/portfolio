#!/bin/bash
# デプロイメントスクリプト

echo "🚀 ポートフォリオデプロイ開始..."

# 1. 環境変数チェック
if [ ! -f .env ]; then
    echo "❌ .envファイルが見つかりません"
    echo "📝 .env.exampleをコピーして編集してください"
    cp .env.example .env
    exit 1
fi

# 2. 最新コードを取得
echo "📥 最新コードを取得中..."
git pull origin main

# 3. Docker環境停止（既存の場合）
echo "🛑 既存のコンテナを停止中..."
docker-compose -f docker-compose.prod.yml down

# 4. Dockerイメージ再ビルド
echo "🔨 Dockerイメージをビルド中..."
docker-compose -f docker-compose.prod.yml build

# 5. データベースバックアップ（既存の場合）
if [ "$(docker ps -aq -f name=portfolio-mysql)" ]; then
    echo "💾 データベースバックアップ中..."
    docker exec portfolio-mysql-1 mysqldump -u root -p$MYSQL_ROOT_PASSWORD portfolio_db > backup_$(date +%Y%m%d_%H%M%S).sql
fi

# 6. コンテナ起動
echo "🚀 新しいコンテナを起動中..."
docker-compose -f docker-compose.prod.yml up -d

# 7. ヘルスチェック
echo "🏥 ヘルスチェック中..."
sleep 10
if curl -f http://localhost:5001/ > /dev/null 2>&1; then
    echo "✅ アプリケーションが正常に起動しました！"
else
    echo "❌ アプリケーションの起動に失敗しました"
    docker-compose -f docker-compose.prod.yml logs
    exit 1
fi

# 8. Nginx設定適用
echo "🌐 Nginx設定を適用中..."
sudo nginx -t && sudo systemctl reload nginx

echo "🎉 デプロイ完了！"