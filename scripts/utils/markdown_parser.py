"""
Markdown解析モジュール
YAML front matterの解析とMarkdown→HTML変換
"""

import re
import yaml
import markdown
from typing import Dict, Tuple
from pathlib import Path
from utils.logger import logger


class MarkdownParser:
    """汎用Markdown解析クラス"""
    
    def __init__(self):
        self.md = markdown.Markdown(
            extensions=[
                'codehilite',
                'fenced_code', 
                'tables',
                'toc',
                'footnotes',
                'attr_list'
            ],
            extension_configs={
                'codehilite': {
                    'css_class': 'highlight',
                    'use_pygments': False
                },
                'tables': {}
            }
        )
    
    def parse_file(self, file_path: str) -> Dict:
        """Markdownファイルを解析"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"ファイルが見つかりません: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.debug("Markdownファイル読み込み完了", file=str(file_path))
        
        # YAML front matterと本文を分離
        metadata, markdown_content = self._split_front_matter(content)
        
        return {
            'metadata': metadata,
            'content': markdown_content,
            'source_file': str(file_path),
            'file_stem': file_path.stem
        }
    
    def _split_front_matter(self, content: str) -> Tuple[Dict, str]:
        """YAML front matterと本文を分離"""
        if not content.startswith('---'):
            return {}, content
        
        parts = content.split('---', 2)
        if len(parts) < 3:
            return {}, content
        
        try:
            metadata = yaml.safe_load(parts[1])
            markdown_content = parts[2].strip()
            logger.debug("YAML front matter解析完了", keys=list(metadata.keys()) if metadata else [])
            return metadata or {}, markdown_content
        except yaml.YAMLError as e:
            logger.warning(f"YAML解析エラー: {e}")
            return {}, content
    
    def to_html(self, markdown_content: str) -> str:
        """Markdown→HTML変換"""
        # リセット（前回の変換状態をクリア）
        self.md.reset()
        
        # 打消し記法の前処理
        markdown_content = self._process_strikethrough(markdown_content)
        
        # 基本HTML変換
        html = self.md.convert(markdown_content)
        
        # カスタム処理
        html = self._process_code_diff_syntax(html)
        html = self._process_url_cards(html)
        
        logger.debug("HTML変換完了", length=len(html))
        return html
    
    def _process_strikethrough(self, content: str) -> str:
        """打消し記法（~~text~~）を<del>タグに変換"""
        pattern = r'~~([^~\n]+)~~'
        replacement = r'<del>\1</del>'
        
        processed = re.sub(pattern, replacement, content)
        
        if processed != content:
            logger.debug("打消し記法を変換", count=len(re.findall(pattern, content)))
        
        return processed
    
    def _process_code_diff_syntax(self, html: str) -> str:
        """コードブロック差分表示記法の処理"""
        pattern = r'<code class="([^"]*language-\w+[^"]*)"([^>]*)>'
        
        def process_code_tag(match):
            classes = match.group(1)
            attributes = match.group(2) or ""
            
            # 差分情報を検出
            add_lines = self._extract_line_numbers(attributes, 'add')
            error_lines = self._extract_line_numbers(attributes, 'error')
            
            # クラスとデータ属性を追加
            if add_lines:
                classes += " has-additions"
                attributes += f' data-add-lines="{",".join(map(str, add_lines))}"'
            
            if error_lines:
                classes += " has-errors"  
                attributes += f' data-error-lines="{",".join(map(str, error_lines))}"'
            
            return f'<code class="{classes}"{attributes}>'
        
        return re.sub(pattern, process_code_tag, html)
    
    def _extract_line_numbers(self, text: str, prefix: str) -> list:
        """行番号範囲を抽出"""
        pattern = rf'{prefix}:([\d,-]+)'
        match = re.search(pattern, text)
        
        if not match:
            return []
        
        ranges = match.group(1).split(',')
        lines = []
        
        for range_str in ranges:
            if '-' in range_str:
                start, end = map(int, range_str.split('-'))
                lines.extend(range(start, end + 1))
            else:
                lines.append(int(range_str))
        
        return lines
    
    def _process_url_cards(self, html: str) -> str:
        """URLカード用のクラス付与"""
        # 単独行のURLにクラスを付与
        pattern = r'<p><a href="(https?://[^"]+)"[^>]*>([^<]+)</a></p>'
        replacement = r'<p><a href="\1" class="url-card-target">\2</a></p>'
        
        return re.sub(pattern, replacement, html)
    
    def extract_title_from_html(self, html: str) -> str:
        """HTMLから最初のH1タグをタイトルとして抽出"""
        h1_match = re.search(r'<h1[^>]*>(.*?)</h1>', html)
        if h1_match:
            # HTMLタグを除去
            title = re.sub(r'<[^>]+>', '', h1_match.group(1)).strip()
            return title
        
        return "Untitled"
    
    def suggest_title_from_content(self, markdown_content: str, file_stem: str = None) -> str:
        """コンテンツからタイトルを推測"""
        # ファイル名を優先
        if file_stem and file_stem.lower() not in ['untitled', 'new', 'draft']:
            # ファイル名を整形
            title = file_stem.replace('-', ' ').replace('_', ' ')
            # 各単語の先頭を大文字に
            title = ' '.join(word.capitalize() for word in title.split())
            logger.debug("ファイル名からタイトル生成", original=file_stem, title=title)
            return title
        
        # 最初のH1タグから抽出
        h1_match = re.search(r'^#\s+(.+)', markdown_content, re.MULTILINE)
        if h1_match:
            title = h1_match.group(1).strip()
            logger.debug("H1タグからタイトル抽出", title=title)
            return title
        
        return "Untitled"