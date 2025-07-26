"""
Markdownパーサーモジュール
Obsidian記法を含むMarkdownをHTML変換
"""

import re
import markdown
from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from typing import Dict, Tuple
import yaml
from .logger import logger
from .code_highlighter import CodeHighlighter


class ObsidianLinkPreprocessor(Preprocessor):
    """Obsidian形式のリンクを処理するプリプロセッサ"""
    
    def run(self, lines):
        """各行を処理してObsidianリンクを変換"""
        new_lines = []
        for line in lines:
            # [[リンク]] 形式を変換（![[画像]] は除外）
            line = re.sub(
                r'(?<!\!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',
                lambda m: f'[{m.group(2) or m.group(1)}]({self._wiki_to_url(m.group(1))})',
                line
            )
            new_lines.append(line)
        return new_lines
    
    def _wiki_to_url(self, page_name: str) -> str:
        """wikilink をブログ内URLに変換"""
        slug = re.sub(r'[^\w\s-]', '', page_name).strip()
        slug = re.sub(r'[\s_-]+', '-', slug).lower()
        return f"/articles/{slug}"


class ObsidianExtension(Extension):
    """Obsidian記法を処理するMarkdown拡張"""
    
    def extendMarkdown(self, md):
        md.preprocessors.register(ObsidianLinkPreprocessor(md), 'obsidian_link', 175)


class MarkdownParser:
    """Markdown→HTML変換クラス"""
    
    def __init__(self):
        """パーサーの初期化"""
        self.md = markdown.Markdown(extensions=[
            'markdown.extensions.extra',
            'markdown.extensions.codehilite',
            'markdown.extensions.toc',
            'markdown.extensions.nl2br',
            'markdown.extensions.sane_lists',
            'markdown.extensions.footnotes',
            'markdown.extensions.meta',
            'markdown.extensions.smarty',
            ObsidianExtension()
        ])
        logger.debug("MarkdownParser初期化完了")
    
    def parse_frontmatter(self, content: str) -> Tuple[Dict, str]:
        """YAMLフロントマターを解析"""
        if not content.startswith('---'):
            return {}, content
        
        try:
            # フロントマターの終了位置を見つける
            end_match = re.search(r'\n---\s*\n', content[3:])
            if not end_match:
                return {}, content
            
            yaml_content = content[3:end_match.start() + 3]
            markdown_content = content[end_match.end() + 3:]
            
            # YAML解析
            metadata = yaml.safe_load(yaml_content) or {}
            logger.debug("フロントマター解析完了", keys=list(metadata.keys()))
            return metadata, markdown_content
            
        except yaml.YAMLError as e:
            logger.warning(f"YAML解析エラー: {e}")
            return {}, content
    
    def to_html(self, markdown_content: str) -> str:
        """Markdown→HTML変換"""
        # Code Styler記法を先に処理
        markdown_content = self._process_code_blocks_simple(markdown_content)
        
        # リセット（前回の変換状態をクリア）
        self.md.reset()
        
        # 打消し記法の前処理
        markdown_content = self._process_strikethrough(markdown_content)
        
        # プレーンURLを自動リンク化
        markdown_content = self._process_plain_urls(markdown_content)
        
        # 基本HTML変換
        html = self.md.convert(markdown_content)
        
        # カスタム処理
        html = self._enhance_tables(html)
        html = self._process_url_cards(html)
        
        # 特殊マーカーを実際のHTMLに戻す
        html = html.replace('%%%CODEBLOCK_START%%%', '').replace('%%%CODEBLOCK_END%%%', '')
        
        logger.debug("HTML変換完了", length=len(html))
        return html
    
    def _process_plain_urls(self, content: str) -> str:
        """プレーンURLを自動的にリンクに変換"""
        # 行頭または空白文字の後のURLを検出
        # コードブロック内は除外するため、コードブロックを一時的に置換
        code_blocks = []
        
        # コードブロックを一時的に保存
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f'%%%CODEBLOCK_{len(code_blocks)-1}%%%'
        
        # コードブロックを一時的に置換
        content = re.sub(r'```[\s\S]*?```', save_code_block, content)
        content = re.sub(r'`[^`]+`', save_code_block, content)
        
        # URLパターン
        url_pattern = r'(?:^|\s)(https?://[^\s<>"{}|\\^`\[\]]+)'
        
        def replace_url(match):
            url = match.group(1)
            # URLの前の空白文字を保持
            prefix = match.group(0)[:-len(url)]
            return f'{prefix}[{url}]({url})'
        
        # URLを置換
        content = re.sub(url_pattern, replace_url, content, flags=re.MULTILINE)
        
        # コードブロックを復元
        for i, block in enumerate(code_blocks):
            content = content.replace(f'%%%CODEBLOCK_{i}%%%', block)
        
        return content
    
    def _process_code_blocks_simple(self, content: str) -> str:
        """コードブロックをシンプルに処理"""
        code_highlighter = CodeHighlighter()
        
        # すべてのコードブロックを一度に検索して処理
        def process_code_block(match):
            full_text = match.group(0)
            
            # ```で始まり```で終わることを確認
            if not full_text.startswith('```') or not full_text.endswith('```'):
                return full_text
            
            # 最初の```の後から最初の改行までを言語情報として取得
            first_line_end = full_text.find('\n')
            if first_line_end == -1:
                # 改行がない場合（空のコードブロック）
                return full_text
            
            # 言語情報を抽出（```の3文字後から改行まで）
            lang_info = full_text[3:first_line_end].strip()
            
            # コード内容を抽出（最初の改行の後から、最後の```の前まで）
            code_content = full_text[first_line_end + 1:-3]
            
            # 最後の改行を削除（```が独立した行にある場合）
            if code_content.endswith('\n'):
                code_content = code_content[:-1]
            
            # デバッグ情報
            logger.debug(f"コードブロック処理: 言語='{lang_info}', コード長={len(code_content)}")
            
            # 仮のMatchオブジェクトを作成
            class FakeMatch:
                def __init__(self, lang, code):
                    self.lang = lang
                    self.code = code
                
                def group(self, n):
                    if n == 0:
                        return full_text
                    elif n == 1:
                        return self.lang
                    elif n == 2:
                        return self.code
            
            # CodeHighlighterで処理してHTMLを生成
            fake_match = FakeMatch(lang_info, code_content)
            html = code_highlighter.process_code_block(fake_match)
            
            # 特殊マーカーで囲む
            return '\n\n' + html + '\n\n'
        
        # ```で始まり```で終わるブロックをすべて処理
        pattern = r'```[\s\S]*?```'
        return re.sub(pattern, process_code_block, content)
    
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
        # 単独行のURLのみを対象とし、インラインリンクは除外
        pattern = r'<p><a href="(https?://[^"]+)">([^<]+)</a></p>'
        
        def create_url_card(match):
            url = match.group(1)
            text = match.group(2)
            
            # URLとテキストが同じ場合のみカード化（プレーンURLの場合）
            if url == text:
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
            else:
                # URLとテキストが異なる場合は、そのまま返す（通常のリンク）
                return match.group(0)
        
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