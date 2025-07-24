"""
ログ処理モジュール
ブログ自動化システム用の統一ログ機能
"""

import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


class BlogLogger:
    """ブログ自動化用ログクラス"""
    
    def __init__(self, name: str = "blog_automation"):
        self.logger = logging.getLogger(name)
        self.setup_logging()
    
    def setup_logging(self):
        """ログ設定の初期化"""
        if self.logger.handlers:
            return
        
        self.logger.setLevel(logging.INFO)
        
        # コンソール出力
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # ファイル出力（logsディレクトリが存在する場合のみ）
        log_dir = Path('logs')
        if log_dir.exists():
            try:
                file_handler = logging.FileHandler(
                    log_dir / 'blog_automation.log',
                    encoding='utf-8'
                )
                file_formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                self.logger.addHandler(file_handler)
            except Exception as e:
                # ファイルログ設定エラーは無視（コンソールログは継続）
                self.logger.warning(f"ファイルログ設定失敗: {e}")
    
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
    
    def _log_with_context(self, level: int, message: str, context: Dict[str, Any]):
        """コンテキスト情報付きでログ出力"""
        if context:
            # コンテキスト情報を読みやすい形式で整形
            context_parts = []
            for key, value in context.items():
                # 値を適切な文字列に変換
                if isinstance(value, (list, dict)):
                    value_str = str(len(value)) if hasattr(value, '__len__') else str(value)
                else:
                    value_str = str(value)
                
                context_parts.append(f"{key}={value_str}")
            
            context_str = " | " + " | ".join(context_parts)
            full_message = message + context_str
        else:
            full_message = message
            
        self.logger.log(level, full_message)
    
    def set_level(self, level: str):
        """ログレベルを動的に変更"""
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR
        }
        
        if level.upper() in level_map:
            self.logger.setLevel(level_map[level.upper()])
        else:
            self.warning(f"無効なログレベル: {level}")


# グローバルロガーインスタンス
logger = BlogLogger()


def log_processing_result(article_file: str, success: bool, **kwargs):
    """記事処理結果のログ出力"""
    status = "成功" if success else "失敗"
    filename = Path(article_file).name
    
    if success:
        logger.info(f"記事処理{status}: {filename}", **kwargs)
    else:
        logger.error(f"記事処理{status}: {filename}", **kwargs)


def set_debug_mode(enabled: bool = True):
    """デバッグモードの有効/無効切り替え"""
    if enabled:
        logger.set_level('DEBUG')
        logger.debug("デバッグモード有効")
    else:
        logger.set_level('INFO')
        logger.info("デバッグモード無効")