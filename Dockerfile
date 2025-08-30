# Python 3.13 公式イメージを使用
FROM python:3.13-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージの更新とインストール
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Pythonの依存関係ファイルをコピー
COPY requirements.txt .

# Pythonパッケージのインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションファイルをコピー
COPY . .

# 静的ファイル用ディレクトリを作成
RUN mkdir -p /app/static/uploads

# 環境変数を設定
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# ポート5001を公開
EXPOSE 5001

# アプリケーション起動コマンド
CMD ["python", "app.py"]