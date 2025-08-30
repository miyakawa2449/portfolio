# サーバーセキュリティ設定レポート

**日付**: 2025年8月30日  
**サーバー**: miyakawa.codes  
**環境**: AWS Lightsail (Ubuntu, Bitnami NGINX)  
**管理者**: tsuyoshi

## 概要

AWS Lightsailサーバーにおける包括的なセキュリティ強化と監視システムの構築。自動脅威検知、メール通知、日次レポートシステムの実装を完了。

## システム構成

### 基本サーバー設定
- **ホスト名**: `ip-172-26-0-125`から`miyakawa-codes`に変更
- **タイムゾーン**: Asia/Tokyo (JST)に設定
- **ユーザー管理**: SSH鍵認証でsudo権限ユーザー`tsuyoshi`を作成
- **システム更新**: すべてのセキュリティアップデートを適用

### ネットワーク構成
- **静的IP**: 52.198.3.169 (事前設定済み)
- **ドメイン**: miyakawa.codes
- **SSL証明書**: Let's Encrypt (2025年11月4日まで有効)

## セキュリティ実装

### 1. Fail2Ban設定

#### インストールとセットアップ
```bash
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

#### 設定内容 (`/etc/fail2ban/jail.local`)
```ini
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
sender = logwatch@miyakawa.codes
sendername = Fail2Ban-miyakawa.codes

[sshd]
enabled = true
port = 22
filter = sshd
backend = systemd
journalmatch = _SYSTEMD_UNIT=ssh.service + _COMM=sshd
```

#### 機能
- SSHブルートフォース攻撃の検知
- 自動IP禁止機能（1時間の禁止期間）
- セキュリティイベントのリアルタイムメール通知
- systemdジャーナルとの統合によるログ監視

### 2. Logwatch設定

#### インストール
```bash
sudo apt install logwatch
```

#### 設定内容 (`/etc/logwatch/conf/logwatch.conf`)
```
MailTo = aws.admin2449@miyakawa.me
MailFrom = logwatch@miyakawa.codes
Detail = Med
Service = All
Range = yesterday
Format = html
TmpDir = /var/cache/logwatch
LogDir = /var/log
```

#### 機能
- 日次システムログ分析の包括的レポート
- HTML形式での見やすいレポート作成
- 全システムサービスとセキュリティイベントをカバー

## メール通知システム

### AWS SES連携

#### Postfix設定 (`/etc/postfix/main.cf`)
```bash
# ドメイン設定
mydomain = miyakawa.codes

# AWS SES設定
relayhost = [email-smtp.ap-northeast-1.amazonaws.com]:587
smtp_sasl_auth_enable = yes
smtp_sasl_security_options = noanonymous
smtp_sasl_password_maps = hash:/etc/postfix/sasl_passwd
smtp_use_tls = yes
smtp_tls_security_level = encrypt
smtp_sasl_mechanism_filter = plain, login
```

#### SASL認証
- AWS SES SMTP認証情報を`/etc/postfix/sasl_passwd`に設定
- 認証サポートのため`libsasl2-modules`をインストール
- 安全なメール送信のためTLS暗号化を有効化

### メールルーティング
- **送信サーバー**: email-smtp.ap-northeast-1.amazonaws.com:587
- **認証方式**: AWS SES認証情報によるSASL認証
- **暗号化**: TLS必須
- **送信者ドメイン**: miyakawa.codes (AWS SESで認証済み)

## 自動レポートスケジュール

### Cron設定
```bash
# 毎朝6:00 JST logwatchレポート
0 6 * * * /usr/sbin/logwatch --output mail --mailto aws.admin2449@miyakawa.me --detail med --service all --range yesterday --format html

# 毎朝6:05 JST fail2banステータスレポート
5 6 * * * /usr/bin/fail2ban-client status | mail -s "Daily Fail2ban Status - miyakawa.codes" aws.admin2449@miyakawa.me
```

### レポートの種類
1. **日次システムレポート** (6:00 AM)
   - システムリソース使用状況
   - サービス稼働状態
   - セキュリティイベント
   - ネットワーク活動
   - エラーログ

2. **日次セキュリティステータス** (6:05 AM)
   - Fail2banジェイル状態
   - 禁止IPアドレス一覧
   - 攻撃統計情報

3. **リアルタイムセキュリティアラート**
   - IPアドレス禁止時の即座通知
   - 攻撃元IPのWHOIS情報を含む
   - 認証失敗試行の詳細情報

## テストと検証

### メール配信テスト
- AWS SES経由でテストメッセージの送信に成功
- aws.admin2449@miyakawa.me への配信を確認
- 適切な送信者識別を確認: `logwatch@miyakawa.codes`

### Fail2Banテスト
- 手動IP禁止・解除テストを実行 (192.0.2.1)
- リアルタイムメール通知を確認
- WHOIS検索機能の動作を確認

### システム統合テスト
- 再起動時の全サービス自動開始を確認
- cronジョブスケジュールの動作確認
- ログローテーションとクリーンアップをテスト

## 実現されたセキュリティ効果

### 自動脅威検知
- リアルタイムSSHブルートフォース攻撃防止
- 繰り返し攻撃者の自動IPブラックリスト化
- 包括的監視のためsystemdログとの統合

### プロアクティブ監視
- 日次システムヘルスレポート
- セキュリティイベントの履歴追跡
- システム問題の早期警告

### インシデント対応
- セキュリティイベントの即座通知
- 調査用の詳細攻撃者情報
- 一般的攻撃パターンへの自動対応

## 設定ファイルの場所

### 主要ファイル
- Fail2Ban: `/etc/fail2ban/jail.local`
- Logwatch: `/etc/logwatch/conf/logwatch.conf`
- Postfix: `/etc/postfix/main.cf`
- SASL認証: `/etc/postfix/sasl_passwd`
- Cronジョブ: `sudo crontab -l`

### ログファイル
- システムログ: `sudo journalctl`
- Fail2Ban: `sudo journalctl -u fail2ban`
- Postfix: `sudo journalctl -u postfix`
- SSH: `sudo journalctl -u ssh`

## 運用状況

### 稼働サービス
- fail2ban.service: 稼働中・監視中
- postfix.service: 稼働中・AWS SES設定済み
- logwatch: cron経由でスケジュール済み
- nginx: SSL/TLS対応で稼働中

### 監視対象
- SSH接続試行と失敗
- システムリソース使用率
- サービス稼働状況とエラー
- ネットワークセキュリティイベント
- メールシステム機能

## メンテナンス要件

### 定期作業
- 日次メールレポートの異常監視
- 月次禁止IPリストのレビュー
- 定期的なシステムパッケージ更新
- SSL証明書の更新確認

### 設定更新
- AWS SES認証情報の更新（必要時）
- 攻撃パターンに基づくFail2Banルール調整
- 新サービス追加時のLogwatch設定調整

## トラブルシューティング参考

### よくある問題の解決
- SASL認証失敗: AWS SES認証情報の確認
- メール配信問題: postfixログとAWS SESコンソールの確認
- レポート未送信: cronジョブとメール設定の確認
- Fail2Ban禁止失敗: systemdジャーナル統合の確認

### 監視コマンド
```bash
# fail2ban状態確認
sudo fail2ban-client status sshd

# 最近のセキュリティイベント表示
sudo journalctl --since "1 hour ago" | grep -E "(sshd|fail2ban)"

# メール配信テスト
echo "Test" | mail -s "Test" aws.admin2449@miyakawa.me

# メールキュー確認
mailq
```

## セキュリティ体制まとめ

サーバーは以下を提供する包括的なセキュリティ監視・警告システムを維持しています：
- リアルタイム脅威検知と対応
- 日次運用可視性
- 自動インシデント通知
- セキュリティイベントの履歴追跡
- プロアクティブなシステムヘルス監視

この設定により、セキュリティインシデントへの迅速な対応を確保しつつ、システム運用と潜在的脅威に対する詳細な可視性を維持します。