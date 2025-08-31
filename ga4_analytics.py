"""
Google Analytics 4 (GA4) 統合管理システム
プライバシー準拠（GDPR/CCPA）対応を含む高度なアナリティクス機能
"""
from markupsafe import Markup
from flask import current_app
from models import db, SiteSetting


class GA4AnalyticsManager:
    """GA4とGTMの統合管理クラス"""
    
    def __init__(self):
        """設定を初期化"""
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """データベースから設定を読み込み"""
        settings = {}
        try:
            # GA4基本設定
            settings['ga4_measurement_id'] = self._get_setting('google_analytics_id', '')
            settings['ga4_enabled'] = self._get_setting('google_analytics_enabled', 'false') == 'true'
            
            # GTM設定
            settings['gtm_container_id'] = self._get_setting('google_tag_manager_id', '')
            settings['gtm_enabled'] = self._get_setting('google_tag_manager_id', '') != ''
            
            # Enhanced E-commerce
            settings['enhanced_ecommerce'] = self._get_setting('enhanced_ecommerce', 'false') == 'true'
            
            # カスタムイベント追跡
            settings['track_scroll_depth'] = self._get_setting('track_scroll_depth', 'false') == 'true'
            settings['track_file_downloads'] = self._get_setting('track_file_downloads', 'false') == 'true'
            settings['track_outbound_links'] = self._get_setting('track_outbound_links', 'false') == 'true'
            settings['track_page_engagement'] = self._get_setting('track_page_engagement', 'false') == 'true'
            settings['track_site_search'] = self._get_setting('track_site_search', 'false') == 'true'
            
            # プライバシー設定
            settings['enable_consent_mode'] = True  # 常にConsent Modeを有効
            settings['default_analytics_storage'] = self._get_setting('analytics_storage_consent', 'denied')
            settings['default_ad_storage'] = self._get_setting('ad_storage_consent', 'denied')
            settings['cookie_banner_enabled'] = self._get_setting('cookie_banner_enabled', 'false') == 'true'
            settings['cookie_banner_text'] = self._get_setting('cookie_banner_text', 
                'このサイトではCookieを使用してユーザーエクスペリエンスを向上させています。')
            
            # 追跡除外設定
            settings['exclude_admin_tracking'] = self._get_setting('exclude_admin_tracking', 'true') == 'true'
            
        except Exception as e:
            current_app.logger.error(f"GA4設定読み込みエラー: {str(e)}")
        
        return settings
    
    def _get_setting(self, key, default=None):
        """個別設定値を取得"""
        try:
            setting = db.session.execute(
                db.select(SiteSetting).where(SiteSetting.key == key)
            ).scalar_one_or_none()
            return setting.value if setting else default
        except:
            return default
    
    def should_track_user(self, user):
        """ユーザーを追跡すべきか判定"""
        # 管理者除外設定確認
        if self.settings.get('exclude_admin_tracking') and user and user.is_authenticated and user.role == 'admin':
            return False
        return True
    
    def generate_tracking_code(self, user=None):
        """GA4トラッキングコードを生成"""
        # 追跡すべきでないユーザーの場合は空文字を返す
        if not self.should_track_user(user):
            return Markup('')
        
        # GA4もGTMも無効な場合
        if not self.settings['ga4_enabled'] and not self.settings['gtm_enabled']:
            return Markup('')
        
        code_parts = []
        
        # Google Consent Mode
        if self.settings['enable_consent_mode']:
            code_parts.append(self._generate_consent_mode())
        
        # GTMコード（GA4より先に読み込む）
        if self.settings['gtm_enabled'] and self.settings['gtm_container_id']:
            code_parts.append(self._generate_gtm_head())
        
        # GA4コード
        if self.settings['ga4_enabled'] and self.settings['ga4_measurement_id']:
            code_parts.append(self._generate_ga4_code())
        
        # カスタムイベント追跡
        if any([self.settings['track_scroll_depth'], 
                self.settings['track_file_downloads'],
                self.settings['track_outbound_links'],
                self.settings['track_page_engagement'],
                self.settings['track_site_search']]):
            code_parts.append(self._generate_custom_events())
        
        # Cookie同意バナー
        if self.settings['cookie_banner_enabled']:
            code_parts.append(self._generate_cookie_banner())
        
        return Markup('\n'.join(code_parts))
    
    def generate_gtm_noscript(self, user=None):
        """GTM noscript部分を生成"""
        if not self.should_track_user(user):
            return Markup('')
        
        if not self.settings['gtm_enabled'] or not self.settings['gtm_container_id']:
            return Markup('')
        
        return Markup(f'''
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id={self.settings['gtm_container_id']}"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
        ''')
    
    def _generate_consent_mode(self):
        """Google Consent Modeコード生成"""
        return f'''
<script>
  // Google Consent Mode v2
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  
  gtag('consent', 'default', {{
    'analytics_storage': '{self.settings['default_analytics_storage']}',
    'ad_storage': '{self.settings['default_ad_storage']}',
    'ad_user_data': 'denied',
    'ad_personalization': 'denied',
    'wait_for_update': 500
  }});
</script>
        '''
    
    def _generate_gtm_head(self):
        """GTM headコード生成"""
        return f'''
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){{w[l]=w[l]||[];w[l].push({{'gtm.start':
new Date().getTime(),event:'gtm.js'}});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
}})(window,document,'script','dataLayer','{self.settings['gtm_container_id']}');</script>
<!-- End Google Tag Manager -->
        '''
    
    def _generate_ga4_code(self):
        """GA4トラッキングコード生成"""
        enhanced_config = ''
        if self.settings['enhanced_ecommerce']:
            enhanced_config = ",\n    'send_page_view': true"
        
        return f'''
<!-- Google Analytics 4 -->
<script async src="https://www.googletagmanager.com/gtag/js?id={self.settings['ga4_measurement_id']}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  
  gtag('config', '{self.settings['ga4_measurement_id']}'{enhanced_config});
</script>
<!-- End Google Analytics 4 -->
        '''
    
    def _generate_custom_events(self):
        """カスタムイベント追跡コード生成"""
        events = []
        
        # スクロール深度追跡
        if self.settings['track_scroll_depth']:
            events.append('''
  // スクロール深度追跡
  let scrollDepths = {25: false, 50: false, 75: false, 100: false};
  window.addEventListener('scroll', function() {
    let scrollPercent = Math.round((window.scrollY + window.innerHeight) / document.documentElement.scrollHeight * 100);
    
    for (let depth in scrollDepths) {
      if (scrollPercent >= depth && !scrollDepths[depth]) {
        scrollDepths[depth] = true;
        gtag('event', 'scroll', {
          'event_category': 'engagement',
          'event_label': depth + '%',
          'value': depth
        });
      }
    }
  });
            ''')
        
        # ファイルダウンロード追跡
        if self.settings['track_file_downloads']:
            events.append('''
  // ファイルダウンロード追跡
  document.addEventListener('click', function(e) {
    let link = e.target.closest('a');
    if (link && link.href) {
      let fileTypes = /\\.(pdf|doc|docx|xls|xlsx|zip|rar|txt|csv|mp3|mp4|avi|mov|ppt|pptx)$/i;
      if (fileTypes.test(link.href)) {
        gtag('event', 'file_download', {
          'event_category': 'download',
          'event_label': link.href.split('/').pop(),
          'transport_type': 'beacon'
        });
      }
    }
  });
            ''')
        
        # 外部リンク追跡
        if self.settings['track_outbound_links']:
            events.append('''
  // 外部リンク追跡
  document.addEventListener('click', function(e) {
    let link = e.target.closest('a');
    if (link && link.href && link.hostname !== window.location.hostname) {
      gtag('event', 'click', {
        'event_category': 'outbound',
        'event_label': link.href,
        'transport_type': 'beacon'
      });
    }
  });
            ''')
        
        # ページエンゲージメント追跡
        if self.settings['track_page_engagement']:
            events.append('''
  // ページエンゲージメント追跡
  let startTime = new Date().getTime();
  let isEngaged = false;
  
  // ユーザーインタラクション検出
  ['mousedown', 'keydown', 'scroll', 'touchstart'].forEach(function(event) {
    window.addEventListener(event, function() {
      if (!isEngaged) {
        isEngaged = true;
        let engagementTime = Math.round((new Date().getTime() - startTime) / 1000);
        gtag('event', 'user_engagement', {
          'event_category': 'engagement',
          'value': engagementTime
        });
      }
    }, {once: true});
  });
            ''')
        
        # サイト内検索追跡
        if self.settings['track_site_search']:
            events.append('''
  // サイト内検索追跡
  let searchForm = document.querySelector('form[action*="search"]');
  if (searchForm) {
    searchForm.addEventListener('submit', function(e) {
      let searchInput = searchForm.querySelector('input[type="search"], input[type="text"]');
      if (searchInput && searchInput.value) {
        gtag('event', 'search', {
          'search_term': searchInput.value
        });
      }
    });
  }
            ''')
        
        if events:
            return f'''
<script>
  // カスタムイベント追跡
  document.addEventListener('DOMContentLoaded', function() {{
    {''.join(events)}
  }});
</script>
            '''
        
        return ''
    
    def _generate_cookie_banner(self):
        """Cookie同意バナー生成"""
        return f'''
<style>
  #cookie-consent-banner {{
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background-color: #2d3748;
    color: white;
    padding: 1rem;
    display: none;
    z-index: 9999;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
  }}
  
  #cookie-consent-banner.show {{
    display: block;
    animation: slideUp 0.3s ease-out;
  }}
  
  @keyframes slideUp {{
    from {{ transform: translateY(100%); }}
    to {{ transform: translateY(0); }}
  }}
  
  .cookie-consent-content {{
    max-width: 1200px;
    margin: 0 auto;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 1rem;
  }}
  
  .cookie-consent-text {{
    flex: 1;
    min-width: 300px;
  }}
  
  .cookie-consent-buttons {{
    display: flex;
    gap: 0.5rem;
  }}
  
  .cookie-consent-button {{
    padding: 0.5rem 1.5rem;
    border: none;
    border-radius: 0.25rem;
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  }}
  
  .cookie-consent-accept {{
    background-color: #48bb78;
    color: white;
  }}
  
  .cookie-consent-accept:hover {{
    background-color: #38a169;
  }}
  
  .cookie-consent-reject {{
    background-color: #4a5568;
    color: white;
  }}
  
  .cookie-consent-reject:hover {{
    background-color: #2d3748;
  }}
</style>

<div id="cookie-consent-banner">
  <div class="cookie-consent-content">
    <div class="cookie-consent-text">
      {self.settings['cookie_banner_text']}
    </div>
    <div class="cookie-consent-buttons">
      <button class="cookie-consent-button cookie-consent-reject" onclick="rejectCookies()">拒否</button>
      <button class="cookie-consent-button cookie-consent-accept" onclick="acceptCookies()">同意する</button>
    </div>
  </div>
</div>

<script>
  // Cookie同意管理
  function getCookie(name) {{
    let value = "; " + document.cookie;
    let parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
  }}
  
  function setCookie(name, value, days) {{
    let expires = "";
    if (days) {{
      let date = new Date();
      date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
      expires = "; expires=" + date.toUTCString();
    }}
    document.cookie = name + "=" + value + expires + "; path=/; SameSite=Lax";
  }}
  
  function acceptCookies() {{
    setCookie('cookie_consent', 'accepted', 365);
    if (typeof gtag !== 'undefined') {{
      gtag('consent', 'update', {{
        'analytics_storage': 'granted',
        'ad_storage': 'granted'
      }});
    }}
    document.getElementById('cookie-consent-banner').classList.remove('show');
  }}
  
  function rejectCookies() {{
    setCookie('cookie_consent', 'rejected', 365);
    if (typeof gtag !== 'undefined') {{
      gtag('consent', 'update', {{
        'analytics_storage': 'denied',
        'ad_storage': 'denied'
      }});
    }}
    document.getElementById('cookie-consent-banner').classList.remove('show');
  }}
  
  // 初期表示判定
  document.addEventListener('DOMContentLoaded', function() {{
    let consent = getCookie('cookie_consent');
    if (!consent) {{
      setTimeout(function() {{
        document.getElementById('cookie-consent-banner').classList.add('show');
      }}, 1000);
    }} else if (consent === 'accepted' && typeof gtag !== 'undefined') {{
      gtag('consent', 'update', {{
        'analytics_storage': 'granted',
        'ad_storage': 'granted'
      }});
    }}
  }});
</script>
        '''