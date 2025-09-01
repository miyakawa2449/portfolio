"""
暗号化ユーティリティ
個人情報（名前・メールアドレス）を暗号化して保存
"""
from cryptography.fernet import Fernet
import base64
import os
from flask import current_app

class EncryptionService:
    """暗号化・復号化サービス"""
    
    _cipher_suite = None
    
    @classmethod
    def get_cipher_suite(cls):
        """暗号化キーから暗号化スイートを取得"""
        if cls._cipher_suite is None:
            # 環境変数またはアプリケーション設定から暗号化キーを取得
            encryption_key = current_app.config.get('ENCRYPTION_KEY')
            
            if not encryption_key:
                # キーが設定されていない場合は新しく生成（本番環境では必ず環境変数から取得すること）
                encryption_key = Fernet.generate_key().decode()
                current_app.logger.warning("ENCRYPTION_KEY not found in config. Generated new key (for development only!)")
                # .envファイルに保存する指示を出力
                print(f"\n⚠️  Add this to your .env file:\nENCRYPTION_KEY={encryption_key}\n")
            
            # 文字列の場合はバイトに変換
            if isinstance(encryption_key, str):
                encryption_key = encryption_key.encode()
                
            cls._cipher_suite = Fernet(encryption_key)
            
        return cls._cipher_suite
    
    @classmethod
    def encrypt(cls, plaintext):
        """文字列を暗号化"""
        if not plaintext:
            return None
            
        try:
            cipher_suite = cls.get_cipher_suite()
            encrypted = cipher_suite.encrypt(plaintext.encode())
            # Base64エンコードして文字列として保存
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            current_app.logger.error(f"Encryption error: {e}")
            # エラーの場合は平文を返す（データ損失を防ぐため）
            return plaintext
    
    @classmethod
    def decrypt(cls, encrypted_text):
        """暗号化された文字列を復号化"""
        if not encrypted_text:
            return None
            
        try:
            # 暗号化されたデータかどうかを判定（Base64エンコードされている場合）
            if not cls._is_encrypted_data(encrypted_text):
                # 暗号化されていない平文データの場合はそのまま返す
                return encrypted_text
                
            cipher_suite = cls.get_cipher_suite()
            # Base64デコード
            encrypted_bytes = base64.b64decode(encrypted_text.encode())
            decrypted = cipher_suite.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception as e:
            current_app.logger.error(f"Decryption error: {e}")
            # 復号化に失敗した場合は元のテキストを返す（後方互換性のため）
            return encrypted_text
    
    @classmethod
    def _is_encrypted_data(cls, data):
        """データが暗号化されているかどうかを判定"""
        try:
            # 暗号化されたデータは通常Base64エンコードされて長い文字列になる
            # また特定の文字パターンを持つ
            if len(data) < 50:  # 暗号化データは通常50文字以上
                return False
            
            # Base64文字のみで構成されているかチェック
            import re
            base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
            if not base64_pattern.match(data):
                return False
                
            # Base64デコードできるかテスト
            base64.b64decode(data.encode())
            return True
        except:
            return False