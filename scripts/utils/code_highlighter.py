"""
コードブロックのスタイリング機能
ObsidianのCode Styler風の見た目を実現
"""

import re
from typing import Dict, List, Tuple
from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeHighlighter:
    """コードブロックをスタイリングするクラス"""
    
    # 言語名のマッピング（Obsidian→Prism.js）
    LANGUAGE_MAP = {
        'python': 'python',
        'javascript': 'javascript', 
        'js': 'javascript',
        'typescript': 'typescript',
        'ts': 'typescript',
        'jsx': 'jsx',
        'tsx': 'tsx',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'csharp': 'csharp',
        'cs': 'csharp',
        'php': 'php',
        'ruby': 'ruby',
        'go': 'go',
        'rust': 'rust',
        'kotlin': 'kotlin',
        'swift': 'swift',
        'html': 'markup',
        'xml': 'markup',
        'css': 'css',
        'scss': 'scss',
        'sass': 'sass',
        'less': 'less',
        'sql': 'sql',
        'bash': 'bash',
        'shell': 'bash',
        'sh': 'bash',
        'powershell': 'powershell',
        'ps1': 'powershell',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'toml': 'toml',
        'markdown': 'markdown',
        'md': 'markdown',
        'plaintext': 'plaintext',
        'text': 'plaintext'
    }
    
    # 行スタイルの定義
    LINE_STYLES = {
        'error': {
            'background': 'rgba(220, 53, 69, 0.1)',
            'border_left': '3px solid #dc3545',
            'class': 'line-error'
        },
        'warning': {
            'background': 'rgba(255, 193, 7, 0.1)',
            'border_left': '3px solid #ffc107',
            'class': 'line-warning'
        },
        'highlight': {
            'background': 'rgba(255, 243, 205, 0.1)',
            'border_left': '3px solid #ffc107',
            'class': 'line-highlight'
        },
        'add': {
            'background': 'rgba(40, 167, 69, 0.1)',
            'border_left': '3px solid #28a745',
            'class': 'line-add'
        },
        'remove': {
            'background': 'rgba(220, 53, 69, 0.1)',
            'border_left': '3px solid #dc3545',
            'class': 'line-remove'
        }
    }
    
    def __init__(self):
        self.logger = logger
    
    def process_code_block(self, code_block_match: re.Match) -> str:
        """コードブロック全体を処理（Prism.js互換）"""
        info_string = code_block_match.group(1) or ""
        code_content = code_block_match.group(2)
        
        # 情報文字列を解析
        language, line_highlights = self._parse_info_string(info_string)
        
        # Prism.js用の言語名を取得
        prism_language = self.LANGUAGE_MAP.get(language.lower(), 'plaintext')
        
        # コードを行に分割
        lines = code_content.split('\n')
        
        # 最後の空行を除去
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        
        # Prism.js互換のHTMLを生成
        if line_highlights:
            # 行ハイライトがある場合はカスタムHTMLを使用
            return self._create_custom_code_block_html(
                prism_language, lines, language, line_highlights
            )
        else:
            # 通常のPrism.js形式
            return self._create_prism_code_block_html(
                prism_language, code_content, language
            )
    
    def _parse_info_string(self, info_string: str) -> Tuple[str, Dict[str, List[int]]]:
        """情報文字列から言語と行ハイライト情報を抽出"""
        parts = info_string.strip().split()
        language = 'plaintext'
        line_highlights = {}
        
        if parts:
            language = parts[0]
            
            # 行ハイライト情報を抽出
            for part in parts[1:]:
                if ':' in part:
                    style, ranges = part.split(':', 1)
                    if style in self.LINE_STYLES:
                        line_highlights[style] = self._parse_line_ranges(ranges)
        
        return language, line_highlights
    
    def _parse_line_ranges(self, ranges_str: str) -> List[int]:
        """範囲文字列から行番号リストを生成"""
        line_numbers = []
        
        for range_part in ranges_str.split(','):
            range_part = range_part.strip()
            if '-' in range_part:
                start, end = range_part.split('-', 1)
                try:
                    start_num = int(start.strip())
                    end_num = int(end.strip())
                    line_numbers.extend(range(start_num, end_num + 1))
                except ValueError:
                    pass
            else:
                try:
                    line_numbers.append(int(range_part))
                except ValueError:
                    pass
        
        return sorted(set(line_numbers))
    
    def _create_prism_code_block_html(self, prism_language: str, 
                                      code_content: str, original_language: str) -> str:
        """通常のPrism.js形式のコードブロックを生成"""
        # HTMLエスケープ
        code_content = (code_content
                       .replace('&', '&amp;')
                       .replace('<', '&lt;')
                       .replace('>', '&gt;'))
        
        # 言語ラベル
        language_label = ''
        if original_language and original_language != 'plaintext':
            language_label = f'<div class="code-language-label">{original_language}</div>'
        
        # Prism.js標準形式
        return (
            f'<div class="code-block-wrapper">'
            f'{language_label}'
            f'<pre class="language-{prism_language} line-numbers"><code class="language-{prism_language}">'
            f'{code_content}'
            f'</code></pre>'
            f'</div>'
        )
    
    def _create_custom_code_block_html(self, prism_language: str, lines: List[str],
                                       original_language: str, line_highlights: Dict[str, List[int]]) -> str:
        """カスタムハイライト付きコードブロックを生成"""
        # 行ごとのHTMLを生成
        html_lines = []
        for i, line in enumerate(lines, 1):
            line_html = self._create_line_html(i, line, line_highlights)
            html_lines.append(line_html)
        
        # 言語ラベル
        language_label = ''
        if original_language and original_language != 'plaintext':
            language_label = f'<div class="code-language-label">{original_language}</div>'
        
        # 全体のHTML
        return (
            f'<div class="code-block-wrapper">'
            f'{language_label}'
            f'<pre class="language-{prism_language} custom-highlights"><code class="language-{prism_language}">'
            f'{"".join(html_lines)}'
            f'</code></pre>'
            f'</div>'
        )
    
    def _create_line_html(self, line_number: int, line_content: str,
                          line_highlights: Dict[str, List[int]]) -> str:
        """単一行のHTMLを生成"""
        # HTMLエスケープ
        line_content = (line_content
                       .replace('&', '&amp;')
                       .replace('<', '&lt;')
                       .replace('>', '&gt;'))
        
        # ハイライトスタイルの確認
        for style, line_numbers in line_highlights.items():
            if line_number in line_numbers:
                style_info = self.LINE_STYLES[style]
                return (
                    f'<span class="code-line {style_info["class"]}">'
                    f'<span class="line-number">{line_number}</span>'
                    f'{line_content}\n</span>'
                )
        
        # 通常の行
        return (
            f'<span class="code-line">'
            f'<span class="line-number">{line_number}</span>'
            f'{line_content}\n</span>'
        )


def enhance_code_blocks_with_styler(html_content: str) -> str:
    """HTMLコンテンツ内のコードブロックを拡張"""
    highlighter = CodeHighlighter()
    
    # Markdown形式のコードブロックを検出して処理
    pattern = r'```(\S+(?:\s+[^\n]+)?)\n(.*?)```'
    html_content = re.sub(
        pattern, 
        lambda m: highlighter.process_code_block(m), 
        html_content, 
        flags=re.DOTALL | re.MULTILINE
    )
    
    return html_content