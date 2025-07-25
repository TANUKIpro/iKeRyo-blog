"""
記事処理メインスクリプト
各モジュールを組み合わせて記事をWordPressに投稿
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# パスを追加してモジュールをインポート
sys.path.append(str(Path(__file__).parent))

from utils.logger import logger
from utils.markdown_parser import MarkdownParser
from utils.obsidian_processor import ObsidianProcessor, ImageOptimizer
from wordpress_api import WordPressAPI

class ArticleProcessor:
    """記事処理統括クラス"""
    
    def __init__(self, repo_root: str, wp_url: str, wp_username: str, wp_app_password: str):
        self.repo_root = Path(repo_root)
        
        # コンポーネント初期化
        self.markdown_parser = MarkdownParser()
        self.obsidian_processor = ObsidianProcessor(repo_root)
        self.image_optimizer = ImageOptimizer(str(self.repo_root / "temp"))
        self.wordpress_api = WordPressAPI(wp_url, wp_username, wp_app_password)
        
        logger.info("記事処理システム初期化完了")
    
    def process(self, markdown_file: str, publish: bool = False) -> Dict:
        """記事処理メインフロー"""
        start_time = datetime.now()
        logger.info("記事処理開始", file=Path(markdown_file).name, publish=publish)
        
        try:
            # 1. Markdownファイル解析
            article_data = self.markdown_parser.parse_file(markdown_file)
            
            # 2. Obsidian固有処理
            base_dir = Path(markdown_file).parent
            images = self.obsidian_processor.extract_images(article_data['content'], base_dir)
            
            # Obsidian記法変換
            processed_content = self.obsidian_processor.process_obsidian_syntax(
                article_data['content']
            )
            
            # 3. 画像処理・アップロード
            image_mapping = {}
            
            for image_info in images:
                try:
                    # 画像最適化
                    optimized = self.image_optimizer.optimize(
                        image_info['local_path'],
                        image_info['width']
                    )
                    
                    # WordPressにアップロード
                    wp_image = self.wordpress_api.upload_image(
                        optimized['optimized_path'],
                        image_info['alt_text'],
                        image_info['caption']
                    )
                    
                    image_mapping[image_info['match_text']] = {
                        'url': wp_image['url'],
                        'id': wp_image['id'],
                        'alt_text': image_info['alt_text'],
                        'caption': image_info['caption'],
                        'width': image_info['width']
                    }
                    
                except Exception as e:
                    logger.error(f"画像処理エラー（スキップ）: {e}", 
                               file=image_info['original_filename'])
            
            # 4. 画像参照更新
            updated_content = self.obsidian_processor.update_image_references(
                processed_content, image_mapping
            )
            
            # 5. HTML変換
            html_content = self.markdown_parser.to_html(updated_content)
            
            # 6. WordPress投稿データ構築
            post_data = self._build_post_data(
                article_data['metadata'], 
                html_content,
                article_data['file_stem'],
                publish
            )
            
            # 7. 既存投稿の確認と更新/作成
            existing_post = self._find_existing_post(post_data['title'], article_data['metadata'])
            
            if existing_post:
                logger.info("既存投稿を更新", id=existing_post['id'], title=post_data['title'])
                post_result = self.wordpress_api.update_post(existing_post['id'], post_data)
            else:
                post_result = self.wordpress_api.create_post(post_data)
            
            # 処理時間計算
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = {
                'success': True,
                'article_file': markdown_file,
                'wordpress_url': post_result['link'],
                'wordpress_id': post_result['id'],
                'images_processed': len(image_mapping),
                'processing_time_seconds': processing_time,
                'updated': existing_post is not None
            }
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"記事処理失敗: {e}", file=Path(markdown_file).name)
            
            return {
                'success': False,
                'article_file': markdown_file,
                'error': str(e),
                'processing_time_seconds': processing_time
            }
    
    def _find_existing_post(self, title: str, metadata: Dict) -> Optional[Dict]:
        """既存の投稿を検索"""
        # GUIDで検索（Obsidianのユニークキー）
        if 'param_guid' in metadata:
            existing = self.wordpress_api.find_post_by_meta('obsidian_guid', metadata['param_guid'])
            if existing:
                return existing
        
        # タイトルで検索（下書き状態のみ）
        return self.wordpress_api.find_draft_by_title(title)
    
    def _build_post_data(self, metadata: Dict, html_content: str, file_stem: str, publish: bool) -> Dict:
        """WordPress投稿データ構築"""
        # タイトル決定
        title = metadata.get('title', '').strip()
        if not title:
            title = self.markdown_parser.suggest_title_from_content("", file_stem)
        if title == "Untitled":
            title = self.markdown_parser.extract_title_from_html(html_content)
        if title == "Untitled":
            title = file_stem
        
        # カテゴリー・タグ処理
        categories = self._process_categories(metadata)
        tags = self._process_tags(metadata)
        
        # 投稿データ
        return {
            'title': title,
            'content': html_content,
            'status': 'publish' if publish else 'draft',
            'date': str(metadata.get('param_created', datetime.now().isoformat())),
            'categories': categories,
            'tags': tags,
            'meta': {
                'obsidian_guid': str(metadata.get('param_guid', '')),
                'original_markdown': True,
                'processed_at': datetime.now().isoformat()
            }
        }
    
    def _process_categories(self, metadata: Dict) -> list:
        """カテゴリー処理"""
        value = metadata.get('param_category')
        if not value:
            return []

        category_names = [c.strip() for c in str(value).split(',') if c.strip()]
        return [self.wordpress_api.get_or_create_category(name) for name in category_names]
    
    def _process_tags(self, metadata: Dict) -> list:
        """タグ処理"""
        value = metadata.get('param_tags')
        if not value:
            return []

        tag_names = [t.strip() for t in str(value).split(',') if t.strip()]
        return self.wordpress_api.get_or_create_tags(tag_names)

def load_config():
    """設定を環境変数から読み込み"""
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_username': os.getenv('WP_USERNAME'),
        'wp_app_password': os.getenv('WP_APP_PASSWORD'),
        'repo_root': os.getenv('GITHUB_WORKSPACE', '.')
    }
    
    missing = [k for k, v in config.items() if not v and k != 'repo_root']
    if missing:
        logger.error(f"必須環境変数が未設定: {', '.join(missing)}")
        sys.exit(1)
    
    return config

def main():
    """メイン処理"""
    if len(sys.argv) < 2:
        print("使用方法: python process_article.py <markdown_file> [--publish]")
        sys.exit(1)
    
    markdown_file = sys.argv[1]
    publish = '--publish' in sys.argv
    
    config = load_config()
    
    if not Path(markdown_file).exists():
        logger.error(f"ファイルが見つかりません: {markdown_file}")
        sys.exit(1)
    
    try:
        processor = ArticleProcessor(
            config['repo_root'],
            config['wp_url'],
            config['wp_username'],
            config['wp_app_password']
        )
        
        result = processor.process(markdown_file, publish)
        
        print(f"\n{'='*50}")
        if result['success']:
            action = "更新" if result.get('updated') else "作成"
            print(f"✅ 処理成功! ({action})")
            print(f"📝 WordPress URL: {result['wordpress_url']}")
            print(f"🖼️ 処理画像数: {result['images_processed']}")
            print(f"⏱️ 処理時間: {result['processing_time_seconds']:.1f}秒")
        else:
            print(f"❌ 処理失敗: {result['error']}")
            sys.exit(1)
        
        with open('output.json', 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
    except KeyboardInterrupt:
        logger.info("処理が中断されました")
        sys.exit(1)
    except Exception as e:
        logger.error(f"予期しないエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()