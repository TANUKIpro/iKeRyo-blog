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
from utils.code_highlighter import CodeHighlighter, enhance_code_blocks_with_styler


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
        # Code Styler記法を先に処理
        markdown_content = self._process_code_styler_blocks(markdown_content)
        
        # リセット（前回の変換状態をクリア）
        self.md.reset()
        
        # 打消し記法の前処理
        markdown_content = self._process_strikethrough(markdown_content)
        
        # 基本HTML変換
        html = self.md.convert(markdown_content)
        
        # カスタム処理
        html = self._enhance_tables(html)
        html = self._process_url_cards(html)
        
        # 特殊マーカーを実際のHTMLに戻す
        html = html.replace('%%%CODEBLOCK_START%%%', '').replace('%%%CODEBLOCK_END%%%', '')
        
        logger.debug("HTML変換完了", length=len(html))
        return html
    
    def _process_code_styler_blocks(self, content: str) -> str:
        """Code Styler記法のコードブロックを処理"""
        code_highlighter = CodeHighlighter()
        
        # ```言語名 スタイル:行番号 の形式を検出
        pattern = r'```(\S+(?:\s+[^\n]+)?)\n(.*?)```'
        
        def replace_code_block(match):
            # CodeHighlighterで処理してHTMLを生成
            html = code_highlighter.process_code_block(match)
            # Markdownパーサーがさらに処理しないよう、特殊なマーカーで囲む
            return f'%%%CODEBLOCK_START%%%{html}%%%CODEBLOCK_END%%%'
        
        # コードブロックを置換
        content = re.sub(pattern, replace_code_block, content, flags=re.DOTALL | re.MULTILINE)
        
        return content
    
    def _process_strikethrough(self, content: str) -> str:
        """打消し記法（~~text~~）を<del>タグに変換"""
        pattern = r'~~([^~\n]+)~~'
        replacement = r'<del>\1</del>'
        
        processed = re.sub(pattern, replacement, content)
        
        if processed != content:
            logger.debug("打消し記法を変換", count=len(re.findall(pattern, content)))
        
        return processed
    
    def _enhance_tables(self, html: str) -> str:
        """テーブルにWordPress標準のスタイルを追加"""
        # シンプルな<table>タグを検出して拡張
        pattern = r'<table>'
        
        # WordPress標準のテーブルスタイル
        table_style = '''style="width: 100%; margin: 1.5rem 0; border-collapse: collapse; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);"'''
        
        replacement = f'<table class="wp-table" {table_style}>'
        html = re.sub(pattern, replacement, html)
        
        # th要素のスタイル
        html = re.sub(
            r'<th>',
            '<th style="padding: 12px 16px; text-align: left; font-weight: 600; color: #1f2937; font-size: 0.9rem; background: #f8fafc; border-bottom: 2px solid #e5e7eb;">',
            html
        )
        
        # td要素のスタイル
        html = re.sub(
            r'<td>',
            '<td style="padding: 12px 16px; border-bottom: 1px solid #f3f4f6; font-size: 0.95rem;">',
            html
        )
        
        # thead要素のスタイル
        html = re.sub(
            r'<thead>',
            '<thead style="background: #f8fafc;">',
            html
        )
        
        return html
    
    def _process_url_cards(self, html: str) -> str:
        """URLカード用のクラス付与"""
        # 単独行のURLにクラスを付与
        pattern = r'<p><a href="(https?://[^"]+)"[^>]*>([^<]+)</a></p>'
        
        def create_url_card(match):
            url = match.group(1)
            text = match.group(2)
            
            # URLカードのHTML（スタイル込み）
            card_html = f'''<a href="{url}" class="url-card" target="_blank" rel="noopener noreferrer" style="display: flex; align-items: center; gap: 12px; margin: 1.5rem 0; padding: 12px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; text-decoration: none; color: #374151; transition: all 0.2s ease;">
    <div class="url-card-image" style="width: 48px; height: 48px; background: #e5e7eb; border-radius: 6px; flex-shrink: 0; display: flex; align-items: center; justify-content: center;">
        <span style="color: #9ca3af; font-size: 1.2rem;">🔗</span>
    </div>
    <div class="url-card-content" style="flex: 1; min-width: 0;">
        <div class="url-card-title" style="font-weight: 600; color: #1f2937; margin-bottom: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{text}</div>
        <div class="url-card-url" style="color: #6b7280; font-size: 0.8rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{url}</div>
    </div>
</a>'''
            
            return card_html
        
        return re.sub(pattern, create_url_card, html)
    
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