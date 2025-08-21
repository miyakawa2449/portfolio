"""
アクセスログ分析モジュール
Flaskアプリケーションのアクセスログを解析し、統計情報を提供
"""
import re
import os
from datetime import datetime, timedelta
from collections import defaultdict, Counter, OrderedDict
from urllib.parse import urlparse, parse_qs
import json


class AccessLogAnalyzer:
    """アクセスログ分析クラス"""
    
    def __init__(self, log_file):
        """
        初期化
        :param log_file: 分析対象のログファイルパス
        """
        self.log_file = log_file
        self.log_entries = []
        self.stats = {}
        
        # 一般的なログフォーマットのパターン（OrderedDictで順序保証）
        self.log_patterns = OrderedDict([
            # Apache Combined Log Format（先に試行）
            ('combined', re.compile(
                r'(?P<ip>\S+) \S+ \S+ \[(?P<datetime>[^\]]+)\] '
                r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" '
                r'(?P<status>\d+) (?P<size>\S+) "(?P<referer>[^"]*)" "(?P<user_agent>[^"]*)"'
            )),
            # Apache Common Log Format
            ('common', re.compile(
                r'(?P<ip>\S+) \S+ \S+ \[(?P<datetime>[^\]]+)\] '
                r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" '
                r'(?P<status>\d+) (?P<size>\S+)'
            )),
            # Flask default format
            ('flask', re.compile(
                r'(?P<datetime>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) '
                r'(?P<level>\w+) in (?P<module>\w+): (?P<ip>\S+) - - '
                r'\[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" '
                r'(?P<status>\d+) -'
            )),
            # Nginx access log
            ('nginx', re.compile(
                r'(?P<ip>\S+) - \S+ \[(?P<datetime>[^\]]+)\] '
                r'"(?P<method>\S+) (?P<path>\S+) (?P<protocol>\S+)" '
                r'(?P<status>\d+) (?P<size>\d+) "(?P<referer>[^"]*)" '
                r'"(?P<user_agent>[^"]*)"'
            ))
        ])
    
    def analyze_logs(self, max_lines=None):
        """
        ログファイルを分析
        :param max_lines: 分析する最大行数
        :return: 分析統計
        """
        if not os.path.exists(self.log_file):
            raise FileNotFoundError(f"ログファイルが見つかりません: {self.log_file}")
        
        self.log_entries = []
        processed_lines = 0
        
        try:
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                
                # 最新の行から処理（ファイルの末尾から）
                if max_lines:
                    lines = lines[-max_lines:]
                
                for line in lines:
                    if max_lines and processed_lines >= max_lines:
                        break
                    
                    entry = self._parse_log_line(line.strip())
                    if entry:
                        self.log_entries.append(entry)
                        processed_lines += 1
        
        except Exception as e:
            raise Exception(f"ログファイル読み込みエラー: {str(e)}")
        
        # 統計情報を計算
        self._calculate_stats()
        return self.stats
    
    def _parse_log_line(self, line):
        """
        ログ行をパース
        :param line: ログ行
        :return: パース結果の辞書
        """
        # 各パターンを試行
        for pattern_name, pattern in self.log_patterns.items():
            match = pattern.match(line)
            if match:
                entry = match.groupdict()
                entry['pattern'] = pattern_name
                
                # 日時をパース
                entry['parsed_datetime'] = self._parse_datetime(
                    entry.get('datetime', ''), pattern_name
                )
                
                # パスからクエリパラメータを分離
                if 'path' in entry:
                    entry['path_clean'], entry['query_params'] = self._parse_path(entry['path'])
                
                return entry
        
        # パターンにマッチしない場合は簡易パース
        return self._fallback_parse(line)
    
    def _parse_datetime(self, datetime_str, pattern_name):
        """
        日時文字列をdatetimeオブジェクトに変換
        """
        try:
            if pattern_name == 'flask':
                return datetime.strptime(datetime_str.split(',')[0], '%Y-%m-%d %H:%M:%S')
            elif pattern_name in ['common', 'combined', 'nginx']:
                # タイムゾーン付き日時をパースして、ナイーブなdatetimeに変換
                dt_with_tz = datetime.strptime(datetime_str, '%d/%b/%Y:%H:%M:%S %z')
                return dt_with_tz.replace(tzinfo=None)
            else:
                # フォールバック
                return datetime.now()
        except Exception as e:
            # デバッグ用
            print(f"DateTime parse error for '{datetime_str}': {e}")
            return datetime.now()
    
    def _parse_path(self, path):
        """
        パスからクエリパラメータを分離
        """
        try:
            parsed = urlparse(path)
            query_params = parse_qs(parsed.query) if parsed.query else {}
            return parsed.path, query_params
        except:
            return path, {}
    
    def _fallback_parse(self, line):
        """
        フォールバックパース（基本的な情報のみ抽出）
        """
        # IPアドレスを抽出
        ip_pattern = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')
        ip_match = ip_pattern.search(line)
        
        # HTTPメソッドを抽出
        method_pattern = re.compile(r'\b(GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\b')
        method_match = method_pattern.search(line)
        
        # ステータスコードを抽出
        status_pattern = re.compile(r'\b(200|201|204|301|302|400|401|403|404|500|502|503)\b')
        status_match = status_pattern.search(line)
        
        return {
            'ip': ip_match.group() if ip_match else 'unknown',
            'method': method_match.group() if method_match else 'unknown',
            'status': status_match.group() if status_match else 'unknown',
            'path': 'unknown',
            'path_clean': 'unknown',
            'query_params': {},
            'parsed_datetime': datetime.now(),
            'pattern': 'fallback',
            'raw_line': line
        }
    
    def _calculate_stats(self):
        """統計情報を計算"""
        if not self.log_entries:
            self.stats = {
                'total_requests': 0,
                'unique_ips': 0,
                'bot_requests': 0,
                'admin_requests': 0,
                'static_requests': 0,
                'status_codes': {},
                'methods': {},
                'top_pages': {},
                'top_ips': {},
                'errors': {},
                'hourly_stats': {},
                'daily_stats': {},
                'user_agents': {},
                'referers': {},
                'analysis_period': {
                    'start': None,
                    'end': None,
                    'duration': '0 minutes'
                }
            }
            return
        
        # 基本統計
        total_requests = len(self.log_entries)
        unique_ips = len(set(entry.get('ip', 'unknown') for entry in self.log_entries))
        
        # カウンター初期化
        status_codes = Counter()
        methods = Counter()
        pages = Counter()
        ips = Counter()
        errors = Counter()
        hourly_stats = defaultdict(int)
        daily_stats = defaultdict(int)
        user_agents = Counter()
        referers = Counter()
        
        # 時間範囲
        timestamps = [entry['parsed_datetime'] for entry in self.log_entries if entry['parsed_datetime']]
        start_time = min(timestamps) if timestamps else datetime.now()
        end_time = max(timestamps) if timestamps else datetime.now()
        
        # 各エントリーを処理
        bot_requests = 0
        admin_requests = 0
        static_requests = 0
        
        for entry in self.log_entries:
            # ステータスコード
            status = entry.get('status', 'unknown')
            status_codes[status] += 1
            
            # HTTPメソッド
            method = entry.get('method', 'unknown')
            methods[method] += 1
            
            # ページ（静的ファイルを除外）
            path = entry.get('path_clean', entry.get('path', 'unknown'))
            if not self._is_static_file(path):
                pages[path] += 1
            
            # IPアドレス
            ip = entry.get('ip', 'unknown')
            ips[ip] += 1
            
            # エラー（4xx, 5xx）
            if status.startswith(('4', '5')):
                error_key = f"{status} {path}"
                errors[error_key] += 1
            
            # ボットアクセス検出
            ua = entry.get('user_agent', 'unknown')
            if self._is_bot_user_agent(ua):
                bot_requests += 1
            
            # 管理画面アクセス検出
            if self._is_admin_path(path):
                admin_requests += 1
            
            # 静的ファイルアクセス検出
            if self._is_static_file(path):
                static_requests += 1
            
            # 時間別統計
            dt = entry['parsed_datetime']
            hour_key = dt.strftime('%H')  # 00-23の形式
            day_key = dt.strftime('%Y-%m-%d')
            hourly_stats[hour_key] += 1
            daily_stats[day_key] += 1
            
            # ユーザーエージェント
            if ua != 'unknown':
                user_agents[ua] += 1
            
            # リファラー
            referer = entry.get('referer', 'unknown')
            if referer and referer not in ['unknown', '-']:
                referers[referer] += 1
        
        # 結果を統計として保存
        self.stats = {
            'total_requests': total_requests,
            'unique_ips': unique_ips,
            'bot_requests': bot_requests,
            'admin_requests': admin_requests,
            'static_requests': static_requests,
            'status_codes': dict(status_codes.most_common()),
            'methods': dict(methods.most_common()),
            'top_pages': dict(pages.most_common(20)),
            'top_ips': dict(ips.most_common(20)),
            'errors': dict(errors.most_common(20)),
            'hourly_stats': dict(hourly_stats),
            'daily_stats': dict(daily_stats),
            'user_agents': dict(user_agents.most_common(10)),
            'referers': dict(referers.most_common(10)),
            'analysis_period': {
                'start': start_time.isoformat() if start_time else None,
                'end': end_time.isoformat() if end_time else None,
                'duration': str(end_time - start_time) if timestamps else '0 minutes'
            }
        }
    
    def generate_report(self):
        """
        分析レポートを生成
        :return: レポート辞書
        """
        if not self.stats:
            return {'error': '分析データがありません'}
        
        # エラー率を計算
        total_requests = self.stats['total_requests']
        error_requests = sum(count for status, count in self.stats['status_codes'].items() 
                           if status.startswith(('4', '5')))
        error_rate = (error_requests / total_requests * 100) if total_requests > 0 else 0
        
        # 最も多いエラー
        top_error = None
        if self.stats['errors']:
            top_error = list(self.stats['errors'].items())[0]
        
        # 最も多いページ
        top_page = None
        if self.stats['top_pages']:
            top_page = list(self.stats['top_pages'].items())[0]
        
        # 最も多いIP
        top_ip = None
        if self.stats['top_ips']:
            top_ip = list(self.stats['top_ips'].items())[0]
        
        report = {
            'summary': {
                'total_requests': total_requests,
                'unique_visitors': self.stats['unique_ips'],
                'bot_requests': self.stats['bot_requests'],
                'admin_requests': self.stats['admin_requests'],
                'static_requests': self.stats['static_requests'],
                'error_rate': round(error_rate, 2),
                'analysis_period': self.stats['analysis_period'],
                'log_file': self.log_file
            },
            'highlights': {
                'top_page': top_page,
                'top_ip': top_ip,
                'top_error': top_error
            },
            'detailed_stats': self.stats,
            'recommendations': self._generate_recommendations(),
            # テンプレート用の追加フィールド
            'hourly_traffic': self.stats['hourly_stats'],
            'daily_traffic': self.stats['daily_stats'],
            'popular_pages': dict(list(self.stats['top_pages'].items())[:10]),
            'status_codes': self.stats['status_codes'],
            'browsers': self._extract_browsers(),
            'operating_systems': self._extract_operating_systems()
        }
        
        return report
    
    def _generate_recommendations(self):
        """
        分析結果に基づく推奨事項を生成
        """
        recommendations = []
        
        # エラー率チェック
        error_requests = sum(count for status, count in self.stats['status_codes'].items() 
                           if status.startswith(('4', '5')))
        error_rate = (error_requests / self.stats['total_requests'] * 100) if self.stats['total_requests'] > 0 else 0
        
        if error_rate > 10:
            recommendations.append({
                'type': 'warning',
                'title': '高エラー率',
                'message': f'エラー率が{error_rate:.1f}%と高いです。404エラーや500エラーの原因を調査することをお勧めします。'
            })
        
        # 404エラーチェック
        error_404_count = sum(count for error, count in self.stats['errors'].items() 
                             if error.startswith('404'))
        if error_404_count > self.stats['total_requests'] * 0.05:
            recommendations.append({
                'type': 'info',
                'title': '404エラー多発',
                'message': f'404エラーが{error_404_count}件発生しています。リンク切れやURL変更を確認してください。'
            })
        
        # アクセス集中チェック
        if self.stats['top_ips']:
            top_ip, top_ip_count = list(self.stats['top_ips'].items())[0]
            if top_ip_count > self.stats['total_requests'] * 0.3:
                recommendations.append({
                    'type': 'warning',
                    'title': 'アクセス集中',
                    'message': f'IP {top_ip} からのアクセスが全体の{top_ip_count/self.stats["total_requests"]*100:.1f}%を占めています。ボット行為の可能性があります。'
                })
        
        # パフォーマンス推奨
        if self.stats['total_requests'] > 1000:
            recommendations.append({
                'type': 'success',
                'title': 'アクティブなサイト',
                'message': 'サイトへのアクセスが活発です。キャッシュ設定やCDN導入を検討してパフォーマンスを向上させましょう。'
            })
        
        if not recommendations:
            recommendations.append({
                'type': 'success',
                'title': '正常稼働中',
                'message': 'アクセスログに特に問題は見つかりませんでした。サイトは正常に稼働しています。'
            })
        
        return recommendations
    
    def export_stats_json(self, output_file=None):
        """
        統計をJSONファイルとしてエクスポート
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f'access_log_analysis_{timestamp}.json'
        
        report = self.generate_report()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)
        
        return output_file
    
    def _is_bot_user_agent(self, user_agent):
        """
        ユーザーエージェントがボットかどうかを判定
        """
        if not user_agent or user_agent == 'unknown':
            return False
        
        bot_keywords = [
            'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl',
            'googlebot', 'bingbot', 'slurp', 'facebookexternalhit',
            'twitterbot', 'linkedinbot', 'whatsapp', 'telegram',
            'python-requests', 'java/', 'okhttp', 'apache-httpclient'
        ]
        
        ua_lower = user_agent.lower()
        return any(keyword in ua_lower for keyword in bot_keywords)
    
    def _is_admin_path(self, path):
        """
        パスが管理画面へのアクセスかどうかを判定
        """
        if not path or path == 'unknown':
            return False
        
        admin_patterns = [
            '/admin', '/management-panel', '/wp-admin', '/administrator',
            '/login', '/auth', '/dashboard', '/panel'
        ]
        
        return any(pattern in path.lower() for pattern in admin_patterns)
    
    def _is_static_file(self, path):
        """
        パスが静的ファイルへのアクセスかどうかを判定
        """
        if not path or path == 'unknown':
            return False
        
        static_extensions = [
            '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg',
            '.woff', '.woff2', '.ttf', '.eot', '.pdf', '.zip', '.txt',
            '.xml', '.json', '.map', '.webp', '.mp3', '.mp4', '.avi'
        ]
        
        path_lower = path.lower()
        return any(path_lower.endswith(ext) for ext in static_extensions) or '/static/' in path_lower
    
    def _extract_browsers(self):
        """
        ユーザーエージェントからブラウザ情報を抽出
        """
        browser_counts = Counter()
        
        for ua in self.stats['user_agents'].keys():
            browser = self._parse_browser(ua)
            browser_counts[browser] += self.stats['user_agents'][ua]
        
        return dict(browser_counts.most_common(10))
    
    def _extract_operating_systems(self):
        """
        ユーザーエージェントからOS情報を抽出
        """
        os_counts = Counter()
        
        for ua in self.stats['user_agents'].keys():
            os = self._parse_os(ua)
            os_counts[os] += self.stats['user_agents'][ua]
        
        return dict(os_counts.most_common(10))
    
    def _parse_browser(self, user_agent):
        """
        ユーザーエージェントからブラウザ名を抽出
        """
        if not user_agent or user_agent == 'unknown':
            return 'Unknown'
        
        ua_lower = user_agent.lower()
        
        # より正確なブラウザ判定（順序重要）
        if 'edg/' in ua_lower or 'edge/' in ua_lower:
            return 'Edge'
        elif 'opr/' in ua_lower or 'opera' in ua_lower:
            return 'Opera'
        elif 'firefox' in ua_lower:
            return 'Firefox'
        elif 'chrome' in ua_lower:
            return 'Chrome'
        elif 'safari' in ua_lower:
            return 'Safari'
        elif 'msie' in ua_lower or 'trident' in ua_lower:
            return 'Internet Explorer'
        else:
            return 'Other'
    
    def _parse_os(self, user_agent):
        """
        ユーザーエージェントからOS名とバージョンを抽出
        """
        if not user_agent or user_agent == 'unknown':
            return 'Unknown'
        
        ua_lower = user_agent.lower()
        
        # Windows詳細バージョン検出
        if 'windows' in ua_lower:
            if 'windows nt 10.0' in ua_lower:
                return 'Windows 10/11'
            elif 'windows nt 6.3' in ua_lower:
                return 'Windows 8.1'
            elif 'windows nt 6.2' in ua_lower:
                return 'Windows 8'
            elif 'windows nt 6.1' in ua_lower:
                return 'Windows 7'
            elif 'windows nt 6.0' in ua_lower:
                return 'Windows Vista'
            else:
                return 'Windows (Other)'
        
        # macOS詳細バージョン検出
        elif 'macintosh' in ua_lower or 'mac os' in ua_lower:
            import re
            # "Mac OS X 10_15_7" のようなパターンを検出
            mac_version_match = re.search(r'mac os x (\d+)_(\d+)(?:_(\d+))?', ua_lower)
            if mac_version_match:
                major = int(mac_version_match.group(1))
                minor = int(mac_version_match.group(2))
                patch = mac_version_match.group(3) if mac_version_match.group(3) else '0'
                
                # macOSのコードネーム付きバージョン名
                if major == 10:
                    if minor >= 15:
                        return f'macOS Catalina (10.{minor}.{patch})'
                    elif minor == 14:
                        return f'macOS Mojave (10.{minor}.{patch})'
                    elif minor == 13:
                        return f'macOS High Sierra (10.{minor}.{patch})'
                    elif minor == 12:
                        return f'macOS Sierra (10.{minor}.{patch})'
                    elif minor == 11:
                        return f'macOS El Capitan (10.{minor}.{patch})'
                    else:
                        return f'macOS (10.{minor}.{patch})'
                elif major >= 11:
                    return f'macOS {major}.{minor}.{patch}'
                else:
                    return f'macOS {major}.{minor}.{patch}'
            else:
                return 'macOS (Version Unknown)'
        
        # Linux詳細検出
        elif 'linux' in ua_lower:
            if 'ubuntu' in ua_lower:
                return 'Ubuntu Linux'
            elif 'fedora' in ua_lower:
                return 'Fedora Linux'
            elif 'centos' in ua_lower:
                return 'CentOS Linux'
            elif 'debian' in ua_lower:
                return 'Debian Linux'
            else:
                return 'Linux'
        
        # Android詳細バージョン検出
        elif 'android' in ua_lower:
            import re
            android_version_match = re.search(r'android (\d+(?:\.\d+)?)', ua_lower)
            if android_version_match:
                version = android_version_match.group(1)
                return f'Android {version}'
            else:
                return 'Android'
        
        # iOS詳細バージョン検出
        elif 'ios' in ua_lower or 'iphone' in ua_lower or 'ipad' in ua_lower:
            import re
            ios_version_match = re.search(r'os (\d+)_(\d+)(?:_(\d+))?', ua_lower)
            if ios_version_match:
                major = ios_version_match.group(1)
                minor = ios_version_match.group(2)
                patch = ios_version_match.group(3) if ios_version_match.group(3) else '0'
                device = 'iPad' if 'ipad' in ua_lower else 'iPhone'
                return f'iOS {major}.{minor}.{patch} ({device})'
            else:
                device = 'iPad' if 'ipad' in ua_lower else 'iPhone'
                return f'iOS ({device})'
        
        else:
            return 'Other'