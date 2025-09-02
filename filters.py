"""
Template Filters - Jinja2テンプレートフィルター
"""
import json
import re
import markdown
import bleach
from markupsafe import Markup
from flask import current_app
from seo import process_sns_auto_embed, process_general_url_embeds
from utils import add_heading_anchors

def register_filters(app):
    """アプリケーションにテンプレートフィルターを登録"""
    
    @app.template_filter('from_json')
    def from_json_filter(text):
        """JSON文字列をPythonオブジェクトに変換するフィルター"""
        if not text:
            return {}
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return {}

    @app.template_filter('markdown')
    def markdown_filter(text):
        """MarkdownテキストをHTMLに変換するフィルター（SNS埋込自動検出付き）"""
        if not text:
            return ''
        
        # SNS URLの自動埋込処理（Markdown変換前）
        # oEmbedハンドラーを使用するため、ここでは実行しない
        # text = process_sns_auto_embed(text)
        
        # Markdownの拡張機能を設定
        md = markdown.Markdown(
            extensions=['extra', 'codehilite', 'toc', 'nl2br'],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False
                }
            },
            tab_length=2  # タブ長を短く設定
        )
        
        # MarkdownをHTMLに変換
        html = md.convert(text)
        
        # セキュリティのためHTMLをサニタイズ（SNS埋込用タグを追加）
        allowed_tags = [
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'p', 'br', 'strong', 'em', 'u', 'del',
            'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
            'a', 'img', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
            # SNS埋込用タグ
            'div', 'iframe', 'script', 'blockquote', 'noscript'
        ]
        allowed_attributes = {
            'a': ['href', 'title', 'target', 'rel'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'code': ['class'],
            'pre': ['class'],
            'h1': ['id'], 'h2': ['id'], 'h3': ['id'], 'h4': ['id'], 'h5': ['id'], 'h6': ['id'],
            # SNS埋込用属性
            'div': ['class', 'id', 'style', 'data-href', 'data-width', 'data-instgrm-permalink'],
            'iframe': ['src', 'width', 'height', 'frameborder', 'allow', 'allowfullscreen', 'title', 'style'],
            'script': ['src', 'async', 'defer', 'charset', 'crossorigin'],
            'blockquote': ['class', 'style', 'data-instgrm-permalink'],
            'noscript': []
        }
        
        # SNS埋込HTMLがある場合はbleachを適用しない（安全なHTMLのため）
        if any(cls in html for cls in ['sns-embed', 'youtube-embed', 'twitter-embed', 'instagram-embed', 'facebook-embed', 'threads-embed']):
            clean_html = html
        else:
            # 通常のMarkdownコンテンツのみサニタイズ
            clean_html = bleach.clean(html, tags=allowed_tags, attributes=allowed_attributes)
        
        # 見出しにアンカーIDを追加
        clean_html = add_heading_anchors(clean_html)
        
        return Markup(clean_html)

    @app.template_filter('nl2br')
    def nl2br(value):
        """改行をHTMLの<br>タグに変換"""
        if value:
            return Markup(value.replace('\n', '<br>'))
        return value

    @app.template_filter('striptags')
    def striptags(value):
        """HTMLタグを除去"""
        if value:
            return re.sub(r'<[^>]*>', '', value)
        return value

    @app.template_filter('oembed_process')
    def oembed_process_filter(html_content):
        """oEmbedを使用してHTML内のURLを埋込に変換"""
        if not html_content:
            return html_content
        
        try:
            from oembed_handler import process_markdown_content
            result = process_markdown_content(html_content)
            return Markup(result)
        except Exception as e:
            current_app.logger.error(f"oEmbed processing error: {e}")
            # エラー時は元のHTMLを返す
            return Markup(html_content)