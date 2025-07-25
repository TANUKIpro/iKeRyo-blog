import sys
import re
import json
from pathlib import Path
from typing import Dict, List
from utils.markdown_parser import MarkdownParser
from utils.obsidian_processor import ObsidianProcessor

class QualityChecker:
    def __init__(self):
        self.parser = MarkdownParser()
        self.processor = ObsidianProcessor('.')
        self.issues = []

    def check_article(self, markdown_file: str) -> Dict:
        article_data = self.parser.parse_file(markdown_file)
        content = article_data['content']
        metadata = article_data['metadata']

        results = {
            'file': markdown_file,
            'checks': {},
            'statistics': {},
            'issues': []
        }

        # 1. メタデータチェック
        results['checks']['metadata'] = self._check_metadata(metadata)

        # 2. 画像チェック
        results['checks']['images'] = self._check_images(content, Path(markdown_file).parent)

        # 3. リンクチェック
        results['checks']['links'] = self._check_links(content)

        # 4. 記事統計
        results['statistics'] = self._calculate_statistics(content)

        # 5. フォーマットチェック
        results['checks']['format'] = self._check_format(content)

        return results

    def _check_metadata(self, metadata: Dict) -> Dict:
        issues = []
        required_fields = ['param_category', 'param_tags']
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                issues.append(f"必須フィールド '{field}' が未設定")
        if 'param_created' in metadata:
            date_pattern = r'^\d{4}-\d{2}-\d{2}'
            if not re.match(date_pattern, str(metadata['param_created'])):
                issues.append("日付フォーマットが不正（YYYY-MM-DD形式を使用）")
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }

    def _check_images(self, content: str, base_dir: Path) -> Dict:
        issues = []
        images = self.processor.extract_images(content, base_dir)
        for img in images:
            if not Path(img['local_path']).exists():
                issues.append(f"画像ファイルが見つかりません: {img['original_filename']}")
            if Path(img['local_path']).exists():
                size_mb = Path(img['local_path']).stat().st_size / (1024 * 1024)
                if size_mb > 5:
                    issues.append(
                        f"画像サイズが大きすぎます: {img['original_filename']} ({size_mb:.1f}MB)"
                    )
        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'image_count': len(images)
        }

    def _check_links(self, content: str) -> Dict:
        issues = []
        url_pattern = r'https?://[^\s\)"]+'
        urls = re.findall(url_pattern, content)
        wiki_pattern = r'\[\[([^\]|]+)'
        wiki_links = re.findall(wiki_pattern, content)
        return {
            'passed': True,
            'external_links': len(urls),
            'internal_links': len(wiki_links),
            'issues': issues
        }

    def _calculate_statistics(self, content: str) -> Dict:
        text_only = re.sub(r'^#+\s+.*$', '', content, flags=re.MULTILINE)
        text_only = re.sub(r'```[\s\S]*?```', '', text_only)
        text_only = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text_only)
        char_count = len(text_only)
        word_count = len(re.findall(r'\w+|[^\x00-\x7F]+', text_only))
        reading_time = max(1, round(char_count / 400))
        return {
            'character_count': char_count,
            'word_count': word_count,
            'reading_time_minutes': reading_time
        }

    def _check_format(self, content: str) -> Dict:
        issues = []
        headings = re.findall(r'^(#+)\s+', content, flags=re.MULTILINE)
        if headings and headings[0] != '#':
            issues.append("最初の見出しはH1（#）を使用してください")
        if '\n\n\n' in content:
            issues.append("3行以上の連続空行があります")
        return {
            'passed': len(issues) == 0,
            'issues': issues
        }

if __name__ == "__main__":
    checker = QualityChecker()
    results = []
    for file in sys.argv[1:]:
        if Path(file).exists():
            result = checker.check_article(file)
            results.append(result)
    with open('quality_report.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
