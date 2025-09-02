from flask import Blueprint, render_template_string, request, current_app
from seo import process_sns_auto_embed, fetch_ogp_data, generate_ogp_card, ogp_cache
import os

debug_bp = Blueprint('debug', __name__)

@debug_bp.route('/debug_ogp')
def debug_ogp():
    """OGP取得のデバッグページ"""
    if not current_app.debug:
        return "Debug mode is disabled", 403
    
    url = request.args.get('url', 'https://example.com')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    try:
        current_app.logger.info(f"🔍 Debug OGP test for URL: {url}")
        ogp_data = fetch_ogp_data(url, force_refresh=force_refresh)
        
        # OGPカード生成も試す
        if url.startswith('http'):
            card_html = generate_ogp_card(url)
        else:
            card_html = "Invalid URL"
        
        result = f"OGP Data: {ogp_data}\n\nGenerated Card: {card_html}"
    except Exception as e:
        current_app.logger.error(f"🚨 OGP Debug Error: {str(e)}")
        result = f"Error: {str(e)}"
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OGP Debug Tool</title>
        <style>
        .debug-info { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
    <h1>OGP Debug Tool</h1>
    
    <div class="debug-info">
        <h3>Current Test</h3>
        <p><strong>URL:</strong> {{ url }}</p>
        <p><strong>Force Refresh:</strong> {{ force_refresh }}</p>
    </div>
    
    <div class="debug-info">
        <h3>Result</h3>
        <pre>{{ result }}</pre>
    </div>
    
    <div class="debug-info">
        <h3>Test URLs</h3>
        <ul>
            <li><a href="/debug_ogp?url=https://docs.python.org/&force_refresh=true">Python Docs (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://github.com/&force_refresh=true">GitHub (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp&force_refresh=true">Threads Post (force refresh)</a></li>
            <li><a href="/debug_ogp?url=https://invalid-url-test.com&force_refresh=true">Invalid URL Test</a></li>
        </ul>
    </div>
    
    </body>
    </html>
    """, url=url, force_refresh=force_refresh, result=result)

@debug_bp.route('/debug_filter')
def debug_filter():
    """テンプレートフィルターのデバッグページ"""
    if not current_app.debug:
        return "Debug mode is disabled", 403
    
    test_content = request.args.get('content', 
        'これはテストです。\n'
        'https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp\n'
        '普通のテキスト\n'
        'https://miyakawa.me/2018/09/13/3865/\n'
        '最後のテキスト')
    
    current_app.logger.info("🔍 Debug Filter: フィルターテスト開始")
    try:
        result = process_sns_auto_embed(test_content)
        current_app.logger.info(f"✅ Debug Filter: 処理完了、結果の長さ {len(result)} 文字")
    except Exception as e:
        current_app.logger.error(f"🚨 Debug Filter Error: {str(e)}")
        result = f"Error: {str(e)}"
    
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Filter Debug Tool</title>
        <style>
        .debug-info { background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 15px 0; }
        </style>
    </head>
    <body>
    <h1>Template Filter Debug Tool</h1>
    
    <div class="debug-info">
        <h3>Input</h3>
        <p>{{ content }}</p>
    </div>
    
    <div class="debug-info">
        <h3>Output</h3>
        <pre>{{ result }}</pre>
    </div>
    
    <div class="debug-info">
        <h3>Test</h3>
        <form method="GET">
            <textarea name="content" rows="5" cols="80">{{ content }}</textarea><br>
            <button type="submit">Test Filter</button>
        </form>
    </div>
    
    </body>
    </html>
    """, content=test_content, result=result)

@debug_bp.route('/debug/sns-test')
def debug_sns_test():
    """SNS埋込のデバッグテスト"""
    if not current_app.debug:
        return "Debug mode is disabled", 403
    
    # OGPキャッシュをクリア
    ogp_cache.clear()
    current_app.logger.debug("🗑️ OGP cache cleared")
    
    test_content = """TwitterのURL:
https://x.com/miyakawa2449/status/1953377889820561624

ブログのURL:
https://miyakawa.me/2023/03/27/9324/

YouTubeのURL:
https://www.youtube.com/watch?v=xvFZjo5PgG0"""
    
    current_app.logger.debug(f"🔍 SNS test input: {test_content}")
    result = process_sns_auto_embed(test_content)
    current_app.logger.debug(f"✅ SNS test output length: {len(result)}")
    
    return f"""<html><head><title>SNS Test</title></head><body>
    <h1>SNS Embed Test (Cache Cleared)</h1>
    <h2>Original:</h2><pre>{test_content}</pre>
    <h2>Processed:</h2><div>{result}</div>
    </body></html>"""

@debug_bp.route('/test_ogp')
def test_ogp():
    """開発用：OGPカード表示のテスト"""
    if not current_app.debug:
        return "Not available in production", 404
    
    test_content = """テスト記事

一般的なWebサイトのOGPカード表示をテスト：

https://docs.python.org/

Threadsの投稿も表示：

https://www.threads.com/@nasubi8848/post/DMPx1RkT3wp

終了。"""
    
    processed_content = process_sns_auto_embed(test_content)
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <title>OGP Test</title>
    <meta charset="utf-8">
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
        .content {{ line-height: 1.6; }}
    </style>
</head>
<body>
    <h1>OGP Card Test</h1>
    <div class="content">
        {processed_content.replace(chr(10), '<br>')}
    </div>
</body>
</html>"""