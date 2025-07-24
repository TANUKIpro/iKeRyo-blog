# 基本的なロガーは常にインポート
from .logger import logger

# 条件付きインポート（エラーを避けるため）
__all__ = ['logger']

try:
    from .markdown_parser import MarkdownParser
    __all__.append('MarkdownParser')
except ImportError:
    MarkdownParser = None

try:
    from .obsidian_processor import ObsidianProcessor, ImageOptimizer
    __all__.extend(['ObsidianProcessor', 'ImageOptimizer'])
except ImportError:
    ObsidianProcessor = None
    ImageOptimizer = None

# 個別インポートも可能にする
def get_image_optimizer():
    """ImageOptimizerのみを取得（他の依存関係なし）"""
    if ImageOptimizer is None:
        from .obsidian_processor import ImageOptimizer
    return ImageOptimizer