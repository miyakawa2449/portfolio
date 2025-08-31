"""
oEmbed Handler - SNS埋込の統一処理
python-oembedライブラリを使用した確実なSNS埋込実装
"""
import re
import logging
from urllib.parse import urlparse
from oembed import OEmbedError, OEmbedNoEndpoint, OEmbedInvalidRequest
import oembed
from flask import current_app
from seo import fetch_ogp_data, generate_ogp_card

logger = logging.getLogger(__name__)

# oEmbedプロバイダーのカスタム設定
OEMBED_PROVIDERS = {
    'youtube.com': {
        'endpoint': 'https://www.youtube.com/oembed',
        'schemes': ['https://www.youtube.com/watch?v=*', 'https://youtu.be/*']
    },
    'twitter.com': {
        'endpoint': 'https://publish.twitter.com/oembed',
        'schemes': ['https://twitter.com/*/status/*', 'https://x.com/*/status/*']
    },
    'instagram.com': {
        'endpoint': 'https://api.instagram.com/oembed',
        'schemes': ['https://www.instagram.com/p/*', 'https://www.instagram.com/reel/*']
    }
}

def process_urls_in_text(text):
    """
    テキスト内のURLを検出してoEmbed埋込HTMLに変換
    
    Args:
        text: 処理対象のテキスト
        
    Returns:
        URLが埋込HTMLに変換されたテキスト
    """
    if not text:
        return text
    
    # URL検出パターン（改行前後のURLも検出）
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+(?:[^\s<>"{}|\\^`\[\]]*[^\s<>"{}|\\^`\[\].,;:!?\'"）])?'
    
    def replace_url(match):
        url = match.group(0).strip()
        try:
            # oEmbedで埋込HTMLを取得
            embed_html = get_oembed_html(url)
            if embed_html:
                # 埋込HTMLをdivでラップ
                return f'<div class="sns-embed oembed-container">{embed_html}</div>'
        except Exception as e:
            logger.debug(f"oEmbed failed for {url}: {e}")
        
        # oEmbedが失敗した場合はOGPカードにフォールバック
        return generate_ogp_card(url)
    
    # URLを埋込HTMLに置換
    processed_text = re.sub(url_pattern, replace_url, text, flags=re.MULTILINE)
    
    return processed_text

def get_oembed_html(url):
    """
    URLからSNS埋込HTMLを取得
    各プラットフォームの標準的な埋込形式を生成
    
    Args:
        url: 埋込対象のURL
        
    Returns:
        埋込HTML文字列、取得できない場合はNone
    """
    # Twitter/X URLは直接ブロッククォート形式で生成
    if 'twitter.com' in url or 'x.com' in url:
        return generate_twitter_blockquote(url)
    
    # Instagram URLは直接埋込形式で生成
    if 'instagram.com' in url:
        return generate_instagram_embed(url)
    
    # YouTubeのみoEmbedを使用（安定している）
    if 'youtube.com' in url or 'youtu.be' in url:
        try:
            consumer = oembed.OEmbedConsumer()
            youtube_endpoint = oembed.OEmbedEndpoint('https://www.youtube.com/oembed',
                                                     ['https://www.youtube.com/watch?v=*', 
                                                      'https://youtu.be/*'])
            consumer.addEndpoint(youtube_endpoint)
            
            response = consumer.embed(url)
            if response and hasattr(response, 'getData'):
                data = response.getData()
                if data and 'html' in data:
                    html = data['html']
                    # YouTubeをレスポンシブに
                    html = html.replace('width="', 'width="100%" style="max-width:')
                    html = html.replace('height="', 'height="315" data-height="')
                    return html
        except Exception as e:
            logger.debug(f"YouTube oEmbed failed for {url}: {e}")
    
    return None

def generate_twitter_blockquote(url):
    """
    Twitter/X URLから標準的なブロッククォート埋込HTMLを生成
    """
    try:
        # URLからツイートIDを抽出
        import re
        tweet_match = re.search(r'/status/(\d+)', url)
        if not tweet_match:
            return None
        
        tweet_id = tweet_match.group(1)
        
        # ユーザー名を抽出
        user_match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/', url)
        username = user_match.group(1) if user_match else 'twitter'
        
        # Twitter公式埋込iframe（ツイートID指定）
        blockquote_html = f'<iframe border="0" frameborder="0" height="500" width="550" src="https://platform.twitter.com/embed/Tweet.html?id={tweet_id}"></iframe>'
        
        print(f"DEBUG: Generated Twitter HTML: {blockquote_html}")
        return blockquote_html
        
    except Exception as e:
        logger.error(f"Error generating Twitter blockquote for {url}: {e}")
        return None

def generate_instagram_embed(url):
    """
    Instagram URLから標準的な埋込HTMLを生成
    """
    try:
        import re
        # Instagram投稿IDを抽出
        post_match = re.search(r'/p/([A-Za-z0-9_-]+)/', url)
        reel_match = re.search(r'/reel/([A-Za-z0-9_-]+)/', url)
        
        if post_match:
            post_id = post_match.group(1)
        elif reel_match:
            post_id = reel_match.group(1)
        else:
            return None
        
        # Instagram埋込形式（コメント欄非表示、divラップなし）
        embed_html = f'<blockquote class="instagram-media" data-instgrm-captioned data-instgrm-permalink="{url}" data-instgrm-version="14"><a href="{url}" target="_blank">Instagramでこの投稿を見る</a></blockquote><script async src="https://www.instagram.com/embed.js"></script>'
        
        return embed_html
        
    except Exception as e:
        logger.error(f"Error generating Instagram embed for {url}: {e}")
        return None

def process_markdown_content(markdown_html):
    """
    マークダウン処理後のHTML内のURLを埋込に変換
    """
    # 処理状況の確認
    print(f"DEBUG: Processing markdown content, length: {len(markdown_html)}")
    print(f"DEBUG: Content preview: {markdown_html[:200]}...")
    
    # 既に処理済みの内容は再処理しない
    if 'sns-embed' in markdown_html or 'twitter-tweet' in markdown_html or 'instagram-media' in markdown_html:
        print("DEBUG: Already processed content detected, skipping...")
        return markdown_html
    
    # <p>タグ内の単独URLのみを検出
    p_url_pattern = r'<p>\s*(https?://[^\s<]+)\s*</p>'
    
    def replace_p_url(match):
        url = match.group(1).strip()
        print(f"DEBUG: Processing URL: {url}")
        
        # SNSプラットフォームを判定して直接埋込HTML生成
        if any(domain in url for domain in ['twitter.com', 'x.com']):
            embed_html = generate_twitter_blockquote(url)
            if embed_html:
                print(f"DEBUG: Direct Twitter embed generated, length: {len(embed_html)}")
                return f'<div class="sns-embed oembed-container">{embed_html}</div>'
        elif any(domain in url for domain in ['youtube.com', 'youtu.be']):
            embed_html = get_oembed_html(url)
            if embed_html:
                print(f"DEBUG: YouTube oEmbed SUCCESS - Length: {len(embed_html)}")
                return f'<div class="sns-embed oembed-container">{embed_html}</div>'
        elif 'instagram.com' in url:
            embed_html = generate_instagram_embed(url)
            if embed_html:
                print(f"DEBUG: Direct Instagram embed generated, length: {len(embed_html)}")
                return f'<div class="sns-embed oembed-container">{embed_html}</div>'
        
        # その他のURLはOGPカード
        print(f"DEBUG: Using OGP card for {url[:30]}...")
        return generate_ogp_card(url)
    
    # URLを埋込に置換
    result = re.sub(p_url_pattern, replace_p_url, markdown_html)
    return result