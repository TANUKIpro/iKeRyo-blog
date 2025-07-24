import logging
import json
import sys
from datetime import datetime
from pathlib import Path


class BlogLogger:
    """ブログ自動化用ログクラス"""
    
    def __init__(self, name: str = "blog_automation"):
        self.logger = logging.getLogger(name)
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定の初期化"""
        if self.logger.handlers:
            return  # 既に設定済みの場合はスキップ
        
        self.logger.setLevel(logging.INFO)
        
        # コンソール出力
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # ファイル出力（存在する場合のみ）
        log_dir = Path('logs')
        if log_dir.exists():
            file_handler = logging.FileHandler(log_dir / 'blog_automation.log')
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def info(self, message: str, **kwargs):
        """情報レベルログ"""
        self._log_with_context(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs):  
        """警告レベルログ"""
        self._log_with_context(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs):
        """エラーレベルログ"""
        self._log_with_context(logging.ERROR, message, kwargs)
    
    def debug(self, message: str, **kwargs):
        """デバッグレベルログ"""
        self._log_with_context(logging.DEBUG, message, kwargs)
    
    def _log_with_context(self, level: int, message: str, context: dict):
        """コンテキスト情報付きでログ出力"""
        if context:
            context_str = " | " + " | ".join([f"{k}={v}" for k, v in context.items()])
            full_message = message + context_str
        else:
            full_message = message
            
        self.logger.log(level, full_message)

# グローバルロガーインスタンス
logger = BlogLogger()

def log_processing_result(article_file: str, success: bool, **kwargs):
    """記事処理結果のログ出力"""
    status = "成功" if success else "失敗"
    logger.info(f"記事処理{status}: {Path(article_file).name}", **kwargs)