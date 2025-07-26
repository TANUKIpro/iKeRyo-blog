"""
コードハイライトモジュール
Obsidian Code Styler風の機能を実装
"""

import re
import html
from typing import Dict, List, Tuple, Optional
from .logger import logger


class CodeHighlighter:
    """コードブロックの高度なハイライト処理"""
    
    # サポートする言語とPrism.jsでの名前のマッピング
    LANGUAGE_MAP = {
        'python': 'python',
        'py': 'python',
        'javascript': 'javascript',
        'js': 'javascript',
        'typescript': 'typescript',
        'ts': 'typescript',
        'java': 'java',
        'c': 'c',
        'cpp': 'cpp',
        'c++': 'cpp',
        'csharp': 'csharp',
        'cs': 'csharp',
        'php': 'php',
        'ruby': 'ruby',
        'rb': 'ruby',
        'go': 'go',
        'rust': 'rust',
        'rs': 'rust',
        'kotlin': 'kotlin',
        'swift': 'swift',
        'r': 'r',
        'sql': 'sql',
        'bash': 'bash',
        'shell': 'bash',
        'sh': 'bash',
        'powershell': 'powershell',
        'ps1': 'powershell',
        'html': 'html',
        'xml': 'xml',
        'css': 'css',
        'scss': 'scss',
        'sass': 'sass',
        'json': 'json',
        'yaml': 'yaml',
        'yml': 'yaml',
        'markdown': 'markdown',
        'md': 'markdown',
        'dockerfile': 'dockerfile',
        'docker': 'dockerfile',
        'makefile': 'makefile',
        'nginx': 'nginx',
        'apache': 'apache',
        'ini': 'ini',
        'toml': 'toml',
        'diff': 'diff',
        'plaintext': 'plaintext',
        'text': 'plaintext',
        'txt': 'plaintext'
    }
    
    # 行ハイライトのスタイル定義
    LINE_STYLES = {
        'error': {
            'background': '#fee',
            'border_left': '3px solid #f44336',
            'class': 'line-error'
        },
        'warning': {
            'background': '#fffbdd',
            'border_left': '3px solid #ff9800',
            'class': 'line-warning'
        },
        'success': {
            'background': '#e6ffed',
            'border_left': '3px solid #4caf50',
            'class': 'line-success'
        },
        'info': {
            'background': '#e3f2fd',
            'border_left': '3px solid #2196f3',
            'class': 'line-info'
        },
        'highlight': {
            'background': '#fff3cd',
            'border_left': '3px solid #ffc107',
            'class': 'line-highlight'
        },
        'add': {
            'background': '#e6ffed',
            'border_left': '3px solid #28a745',
            'class': 'line-add'
        },
        'remove': {
            'background': '#ffeef0',
            'border_left': '3px solid #dc3545',
            'class': 'line-remove'
        }
    }
    
    def __init__(self):
        self.logger = logger
    
    def process_code_block(self, code_block_match: re.Match) -> str:
        """コードブロック全体を処理"""
        full_match = code_block_match.group(0)
        info_string = code_block_match.group(1) or ""
        code_content = code_block_match.group(2) or ""
        
        # 情報文字列を解析
        language, line_highlights = self._parse_info_string(info_string)
        
        # 言語指定がない場合は plaintext として扱う
        if not language:
            language = 'plaintext'
        
        # コードをHTMLエスケープ
        code_content = html.escape(code_content)
        
        # コードを行に分割
        lines = code_content.split('\n')
        
        # 最後の空行を除去（Markdownパーサーが追加することがあるため）
        if lines and not lines[-1].strip():
            lines = lines[:-1]
        
        # 言語指定がない場合は、単純なpreタグで囲む
        if language == 'plaintext' and not line_highlights:
            # シンプルなコードブロック
            return (
                '<div class="code-block-wrapper">'
                '<pre><code class="language-plaintext">'
                + '\n'.join(lines) +
                '</code></pre></div>'
            )
        
        # 言語指定がある場合は、スタイル付きで処理
        # Prism.js用の言語名を取得
        prism_language = self.LANGUAGE_MAP.get(language.lower(), language)
        
        # 行番号付きのHTMLを生成
        html_lines = []
        for i, line in enumerate(lines, 1):
            line_html = self._create_line_html(i, line, line_highlights)
            html_lines.append(line_html)
        
        # 全体のHTMLを構築
        return self._create_code_block_html(
            prism_language,
            html_lines,
            language if language != 'plaintext' else '',
            bool(line_highlights)
        )
    
    def _parse_info_string(self, info_string: str) -> Tuple[str, Dict[str, List[int]]]:
        """
        情報文字列から言語と行ハイライト情報を抽出
        例: "python error:1-3,5 warning:7"
        """
        parts = info_string.strip().split()
        language = ''
        line_highlights = {}
        
        if parts:
            # 最初の部分は言語名
            language = parts[0]
            
            # 残りの部分から行ハイライト情報を抽出
            for part in parts[1:]:
                if ':' in part:
                    style, ranges = part.split(':', 1)
                    if style in self.LINE_STYLES:
                        line_highlights[style] = self._parse_line_ranges(ranges)
        
        return language, line_highlights
    
    def _parse_line_ranges(self, ranges_str: str) -> List[int]:
        """
        行範囲文字列を解析
        例: "1-3,5,7-9" -> [1, 2, 3, 5, 7, 8, 9]
        """
        lines = []
        for range_part in ranges_str.split(','):
            if '-' in range_part:
                start, end = map(int, range_part.split('-', 1))
                lines.extend(range(start, end + 1))
            else:
                lines.append(int(range_part))
        return lines
    
    def _create_line_html(self, line_number: int, line_content: str, 
                         line_highlights: Dict[str, List[int]]) -> str:
        """各行のHTMLを生成"""
        # ハイライトスタイルの確認
        if line_highlights:
            for style_name, line_numbers in line_highlights.items():
                if line_number in line_numbers:
                    selected_style = style_name
                    break
            else:
                selected_style = None
                
            if selected_style:
                style_info = self.LINE_STYLES[selected_style]
                return (f'<span class="code-line {style_info["class"]}" '
                       f'style="display: block; background: {style_info["background"]}; '
                       f'border-left: {style_info["border_left"]}; padding-left: 1rem; '
                       f'margin-left: -1rem; margin-right: -1rem; padding-right: 1rem;">'
                       f'<span class="line-number" style="display: inline-block; width: 3em; '
                       f'color: #999; text-align: right; padding-right: 1em; '
                       f'user-select: none;">{line_number}</span>'
                       f'{line_content}</span>')
        
        # 通常の行
        return (f'<span class="code-line" style="display: block;">'
               f'<span class="line-number" style="display: inline-block; width: 3em; '
               f'color: #999; text-align: right; padding-right: 1em; '
               f'user-select: none;">{line_number}</span>'
               f'{line_content}</span>')
    
    def _create_code_block_html(self, prism_language: str, html_lines: List[str], 
                               original_language: str, has_line_highlights: bool) -> str:
        """コードブロック全体のHTMLを生成"""
        # コードブロックのスタイル
        pre_style = (
            'background: #1e293b; '
            'color: #e2e8f0; '
            'padding: 1.5rem; '
            'border-radius: 8px; '
            'overflow-x: auto; '
            'margin: 1.5rem 0; '
            'position: relative; '
            'font-family: "Consolas", "Monaco", "Courier New", monospace; '
            'font-size: 0.9rem; '
            'line-height: 1.6;'
        )
        
        # 言語ラベル（オプション）
        language_label = ''
        if original_language and original_language != 'plaintext':
            language_label = (
                f'<div class="code-language-label" '
                f'style="position: absolute; top: 0; right: 0; '
                f'background: rgba(255,255,255,0.1); '
                f'padding: 0.25rem 0.75rem; '
                f'border-radius: 0 8px 0 8px; '
                f'font-size: 0.75rem; '
                f'color: #94a3b8; '
                f'text-transform: uppercase;">'
                f'{original_language}</div>'
            )
        
        # 行番号の表示制御用CSS
        line_number_css = ''
        if has_line_highlights:
            line_number_css = (
                '<style>'
                '.code-line:hover .line-number { color: #e2e8f0 !important; }'
                '</style>'
            )
        
        # 全体のHTML
        return (
            f'<div class="code-block-wrapper">'
            f'{language_label}'
            f'{line_number_css}'
            f'<pre class="language-{prism_language}" style="{pre_style}">'
            f'<code class="language-{prism_language}" style="display: block; padding: 0;">'
            f'{"".join(html_lines)}'
            f'</code></pre>'
            f'</div>'
        )
    
    def add_prism_plugins(self) -> str:
        """必要なPrism.jsプラグインのスクリプトタグを返す"""
        plugins = [
            'line-numbers',
            'line-highlight',
            'toolbar',
            'copy-to-clipboard'
        ]
        
        base_url = 'https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/plugins'
        scripts = []
        
        for plugin in plugins:
            scripts.append(
                f'<script src="{base_url}/{plugin}/prism-{plugin}.min.js"></script>'
            )
        
        # 追加のCSS
        scripts.append(
            f'<link href="{base_url}/line-numbers/prism-line-numbers.min.css" rel="stylesheet" />'
        )
        scripts.append(
            f'<link href="{base_url}/line-highlight/prism-line-highlight.min.css" rel="stylesheet" />'
        )
        scripts.append(
            f'<link href="{base_url}/toolbar/prism-toolbar.min.css" rel="stylesheet" />'
        )
        
        return '\n'.join(scripts)


def enhance_code_blocks_with_styler(html_content: str) -> str:
    """
    HTMLコンテンツ内のコードブロックをCode Styler風に拡張
    この関数は外部から呼び出される主要なインターフェース
    """
    highlighter = CodeHighlighter()
    
    # Markdownパーサーが生成した <pre><code> ブロックを検出
    # info stringも含めて取得するパターン
    pattern = r'```(\S+(?:\s+[^\n]+)?)?\n(.*?)```'
    
    # まず、Markdown形式のコードブロックを処理
    def process_markdown_code(match):
        return highlighter.process_code_block(match)
    
    # Markdown形式のコードブロックを変換
    html_content = re.sub(pattern, process_markdown_code, html_content, flags=re.DOTALL | re.MULTILINE)
    
    # 既にHTMLに変換されているコードブロックも処理
    html_pattern = r'<pre><code(?:\s+class="language-(\w+)")?>(.*?)</code></pre>'
    
    def process_html_code(match):
        language = match.group(1) or 'plaintext'
        code_content = match.group(2)
        
        # HTMLエンティティをデコード
        code_content = (code_content
                       .replace('&lt;', '<')
                       .replace('&gt;', '>')
                       .replace('&amp;', '&'))
        
        # 擬似的なMatchオブジェクトを作成
        class FakeMatch:
            def group(self, n):
                if n == 0:
                    return match.group(0)
                elif n == 1:
                    return language
                elif n == 2:
                    return code_content
        
        return highlighter.process_code_block(FakeMatch())
    
    html_content = re.sub(html_pattern, process_html_code, html_content, flags=re.DOTALL)
    
    return html_content