#!/bin/bash
# AWS Lightsail Ubuntu 24.04 初期セットアップスクリプト

echo "🚀 ポートフォリオサーバーセットアップ開始..."

# 1. システム更新
echo "📦 システムパッケージ更新中..."
sudo apt update && sudo apt upgrade -y

# 2. 必要なパッケージインストール
echo "🔧 必要なツールをインストール中..."
sudo apt install -y \
    docker.io \
    docker-compose \
    git \
    nginx \
    certbot \
    python3-certbot-nginx \
    ufw

# 3. Dockerユーザー権限設定
echo "🐳 Docker権限設定中..."
sudo usermod -aG docker $USER

# 4. ファイアウォール設定
echo "🔒 ファイアウォール設定中..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 5. プロジェクトディレクトリ作成
echo "📁 プロジェクトディレクトリ作成中..."
mkdir -p ~/apps
cd ~/apps

# 6. Nginxデフォルト設定削除
echo "🌐 Nginx設定準備中..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx

echo "✅ 初期セットアップ完了!"
echo "🔄 次の手順："
echo "1. 再ログインしてDocker権限を有効化"
echo "2. GitHubからプロジェクトをクローン"
echo "3. SSL証明書を取得"
echo "4. docker-compose.prod.yml で起動"