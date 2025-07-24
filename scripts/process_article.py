"""
記事処理メインスクリプト
各モジュールを組み合わせて記事をWordPressに投稿
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Dict

# パスを追加してモジュールをインポート
sys.path.append(str(Path(__file__).parent))

from utils.logger import logger, log_processing_result
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
            article_data['images'] = images
            
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
                        'caption': image_info['caption']
                    }
                    
                except Exception as e:
                    logger.error(f"画像処理エラー（スキップ）: {e}", 
                               file=image_info['original_filename'])
                    # 画像エラーでも処理を継続
            
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
                publish
            )
            
            # 7. WordPress投稿
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
                'image_mapping': image_mapping,
                'post_data': post_result
            }
            
            log_processing_result(
                markdown_file, 
                True, 
                url=post_result['link'],
                images=len(image_mapping),
                time_sec=f"{processing_time:.1f}"
            )
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"記事処理失敗: {e}", file=Path(markdown_file).name)
            
            log_processing_result(
                markdown_file,
                False,
                error=str(e),
                time_sec=f"{processing_time:.1f}"
            )
            
            return {
                'success': False,
                'article_file': markdown_file,
                'error': str(e),
                'processing_time_seconds': processing_time
            }
    
    def _build_post_data(self, metadata: Dict, html_content: str, publish: bool) -> Dict:
        """WordPress投稿データ構築"""
        # タイトル抽出
        title = self.markdown_parser.extract_title_from_html(html_content)
        
        # カテゴリー処理
        categories = []
        if 'param_category' in metadata:
            category_names = [cat.strip() for cat in metadata['param_category'].split(',')]
            for cat_name in category_names:
                cat_id = self.wordpress_api.get_or_create_category(cat_name)
                categories.append(cat_id)
        
        # タグ処理
        tags = []
        if 'param_tags' in metadata:
            tag_names = [tag.strip() for tag in metadata['param_tags'].split(',')]
            tags = self.wordpress_api.get_or_create_tags(tag_names)
        
        # 投稿データ
        post_data = {
            'title': title,
            'content': html_content,
            'status': 'publish' if publish else 'draft',
            'date': metadata.get('param_created', datetime.now().isoformat()),
            'categories': categories,
            'tags': tags,
            'meta': {
                'obsidian_guid': metadata.get('param_guid', ''),
                'original_markdown': True,
                'processed_at': datetime.now().isoformat()
            }
        }
        
        logger.debug("投稿データ構築完了", 
                    title=title,
                    categories=len(categories),
                    tags=len(tags))
        
        return post_data

def load_config():
    """設定を環境変数から読み込み"""
    config = {
        'wp_url': os.getenv('WP_URL'),
        'wp_username': os.getenv('WP_USERNAME'),
        'wp_app_password': os.getenv('WP_APP_PASSWORD'),
        'repo_root': os.getenv('GITHUB_WORKSPACE', '.')
    }
    
    # 必須設定チェック
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
    
    # 設定読み込み
    config = load_config()
    
    # ファイル存在チェック
    if not Path(markdown_file).exists():
        logger.error(f"ファイルが見つかりません: {markdown_file}")
        sys.exit(1)
    
    try:
        # 記事処理実行
        processor = ArticleProcessor(
            config['repo_root'],
            config['wp_url'],
            config['wp_username'],
            config['wp_app_password']
        )
        
        result = processor.process(markdown_file, publish)
        
        # 結果出力
        print(f"\n{'='*50}")
        if result['success']:
            print(f"✅ 処理成功!")
            print(f"📝 WordPress URL: {result['wordpress_url']}")
            print(f"🖼️ 処理画像数: {result['images_processed']}")
            print(f"⏱️ 処理時間: {result['processing_time_seconds']:.1f}秒")
        else:
            print(f"❌ 処理失敗: {result['error']}")
            sys.exit(1)
        
        # 結果をJSONで保存（GitHub Actions用）
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