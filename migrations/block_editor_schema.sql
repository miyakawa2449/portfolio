-- ブロック型エディタ用のデータベーススキーマ設計
-- spec.mdに基づく記事ブロック管理システム

-- ブロックタイプテーブル（ブロックの種類を定義）
CREATE TABLE block_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type_name VARCHAR(50) NOT NULL UNIQUE, -- 'text', 'image', 'sns_embed', 'external_article'
    type_label VARCHAR(100) NOT NULL, -- 表示名（日本語）
    description TEXT, -- ブロックタイプの説明
    settings_schema TEXT, -- ブロック固有設定のJSONスキーマ
    template_name VARCHAR(100), -- レンダリング用テンプレート名
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 記事ブロックテーブル（記事を構成するブロックの実データ）
CREATE TABLE article_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    article_id INTEGER NOT NULL,
    block_type_id INTEGER NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0, -- ブロックの表示順序
    
    -- ブロック共通フィールド
    title VARCHAR(255), -- ブロックタイトル（オプション）
    content TEXT, -- メインコンテンツ（Markdown、URL、JSONなど）
    
    -- 画像ブロック用フィールド
    image_path VARCHAR(500), -- 画像ファイルパス
    image_alt_text VARCHAR(255), -- 画像の代替テキスト
    image_caption TEXT, -- 画像キャプション
    crop_data TEXT, -- トリミング情報（JSON）
    
    -- SNS埋込用フィールド
    embed_url VARCHAR(1000), -- 埋込元URL
    embed_platform VARCHAR(50), -- 'twitter', 'facebook', 'instagram', 'threads', 'youtube'
    embed_id VARCHAR(200), -- プラットフォーム固有のID
    embed_html TEXT, -- 埋込HTML（キャッシュ用）
    
    -- 外部記事埋込用フィールド
    ogp_title VARCHAR(500), -- OGPタイトル
    ogp_description TEXT, -- OGP説明文
    ogp_image VARCHAR(500), -- OGP画像URL
    ogp_site_name VARCHAR(200), -- サイト名
    ogp_url VARCHAR(1000), -- 記事URL
    ogp_cached_at TIMESTAMP, -- OGP情報取得日時
    
    -- ブロック設定・表示制御
    settings TEXT, -- ブロック固有設定（JSON）
    css_classes VARCHAR(500), -- 追加CSSクラス
    is_visible BOOLEAN DEFAULT TRUE, -- 表示/非表示
    
    -- メタデータ
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 外部キー制約
    FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
    FOREIGN KEY (block_type_id) REFERENCES block_types(id),
    
    -- インデックス
    INDEX idx_article_blocks_article_sort (article_id, sort_order),
    INDEX idx_article_blocks_type (block_type_id),
    INDEX idx_article_blocks_visible (is_visible)
);

-- 既存のarticlesテーブルに追加するカラム
ALTER TABLE articles ADD COLUMN use_block_editor BOOLEAN DEFAULT FALSE; -- ブロックエディタ使用フラグ
ALTER TABLE articles ADD COLUMN legacy_body_backup TEXT; -- 従来のbodyフィールドのバックアップ用

-- 初期ブロックタイプデータの挿入
INSERT INTO block_types (type_name, type_label, description, template_name) VALUES
('text', 'テキストブロック', 'Markdown対応のテキストコンテンツ', 'blocks/text_block.html'),
('image', '画像ブロック', '1:1比率700pxの画像ブロック', 'blocks/image_block.html'),
('sns_embed', 'SNS埋込', 'X/Facebook/Instagram/Threads/YouTube埋込', 'blocks/sns_embed_block.html'),
('external_article', '外部記事埋込', 'URL入力でOGPカード化', 'blocks/external_article_block.html'),
('featured_image', 'アイキャッチ画像', '16:9比率800pxのアイキャッチ画像（記事先頭専用）', 'blocks/featured_image_block.html');

-- ブロック型エディタへの移行用のビュー
CREATE VIEW article_block_summary AS
SELECT 
    a.id as article_id,
    a.title,
    a.use_block_editor,
    COUNT(ab.id) as block_count,
    GROUP_CONCAT(bt.type_label ORDER BY ab.sort_order) as block_types
FROM articles a
LEFT JOIN article_blocks ab ON a.id = ab.article_id AND ab.is_visible = TRUE
LEFT JOIN block_types bt ON ab.block_type_id = bt.id
GROUP BY a.id, a.title, a.use_block_editor;

-- ブロック管理用のトリガー（sort_orderの自動調整）
CREATE TRIGGER auto_sort_order_on_insert
AFTER INSERT ON article_blocks
FOR EACH ROW
WHEN NEW.sort_order = 0
BEGIN
    UPDATE article_blocks 
    SET sort_order = (
        SELECT COALESCE(MAX(sort_order), 0) + 1 
        FROM article_blocks 
        WHERE article_id = NEW.article_id AND id != NEW.id
    )
    WHERE id = NEW.id;
END;

-- ブロック削除時の順序再調整トリガー
CREATE TRIGGER reorder_blocks_on_delete
AFTER DELETE ON article_blocks
FOR EACH ROW
BEGIN
    UPDATE article_blocks 
    SET sort_order = sort_order - 1
    WHERE article_id = OLD.article_id 
    AND sort_order > OLD.sort_order;
END;