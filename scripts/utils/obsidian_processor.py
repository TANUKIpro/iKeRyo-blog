"""
Obsidian固有処理モジュール
画像抽出・最適化・記法変換
"""

import re
import os
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime
from PIL import Image
from .logger import logger


class ObsidianProcessor:
    """Obsidian固有処理クラス"""
    
    def __init__(self, repo_root: str):
        self.repo_root = Path(repo_root)
        self.assets_dir = self.repo_root / "assets" / "images"
        self.temp_dir = self.repo_root / "temp"
        self.temp_dir.mkdir(exist_ok=True)
    
    def extract_images(self, content: str, base_dir: Path) -> List[Dict]:
        """Obsidian画像記法から画像情報を抽出"""
        images = []
        
        # Obsidian画像記法: ![[image.png | caption | width]]
        pattern = r'!\[\[([^\]]+?)(?:\s*\|\s*([^|\]]+?))?(?:\s*\|\s*(\d+))?\]\]'
        
        for match in re.finditer(pattern, content):
            # パイプ記号で分割して最初の部分をファイル名として取得
            parts = match.group(1).split('|')
            filename = parts[0].strip()
            
            # キャプションと幅の処理
            if match.group(2):
                caption = match.group(2).strip()
            elif len(parts) > 1:
                caption = parts[1].strip()
            else:
                caption = ""
            
            width = int(match.group(3)) if match.group(3) else None
            
            # デバッグログ
            logger.debug(f"画像記法発見: {match.group(0)}")
            logger.debug(f"  ファイル名: {filename}")
            logger.debug(f"  キャプション: {caption}")
            logger.debug(f"  幅: {width}")
            
            # ファイルパスを解決
            image_path = self._resolve_image_path(filename, base_dir)
            
            if image_path and image_path.exists():
                images.append({
                    'original_filename': filename,
                    'local_path': str(image_path),
                    'caption': caption,
                    'width': width,
                    'match_text': match.group(0),
                    'alt_text': self._generate_alt_text(filename, caption)
                })
                logger.info(f"画像検出成功: {match.group(0)} -> {image_path}")
            else:
                logger.warning(f"画像ファイル未発見: {filename}")
        
        return images
    
    def _generate_alt_text(self, filename: str, caption: str) -> str:
        """alt text自動生成（<br>タグは除去）"""
        if caption:
            # HTMLタグを除去してalt textとして使用
            alt_text = re.sub(r'<[^>]+>', ' ', caption)
            return alt_text.strip()
        
        # ファイル名からalt text生成
        base_name = Path(filename).stem
        alt_text = re.sub(r'[-_]', ' ', base_name)
        alt_text = re.sub(r'\d{8}|\d{4}-\d{2}-\d{2}', '', alt_text)
        
        return alt_text.strip() or 'image'
    
    def _resolve_image_path(self, filename: str, base_dir: Path) -> Optional[Path]:
        """画像ファイルパスを解決"""
        logger.debug(f"画像パス解決開始: {filename}")
        
        # ファイル名の正規化（先頭・末尾の空白、スラッシュを削除）
        filename = filename.strip().strip('/')
        
        # 拡張子の確認
        if '.' not in Path(filename).name:
            possible_extensions = ['.png', '.jpg', '.jpeg', '.webp', '.gif']
        else:
            possible_extensions = ['']
        
        for ext in possible_extensions:
            test_filename = filename if ext == '' else f"{filename}{ext}"
            
            # 検索パス候補
            search_candidates = [
                base_dir / test_filename,
                self.assets_dir / test_filename,
                self.repo_root / test_filename,
            ]
            
            # 年月ディレクトリ構造も検索
            if '/' not in test_filename:
                # 現在の年月ディレクトリも検索対象に含める
                now = datetime.now()
                year = f"{now.year:04d}"
                month = f"{now.month:02d}"

                search_candidates.extend([
                    self.assets_dir / year / month / test_filename,
                    base_dir / f"{base_dir.stem}_assets" / test_filename,
                ])
            
            for path in search_candidates:
                if path.exists() and path.is_file():
                    logger.info(f"画像発見: {filename} -> {path}")
                    return path
        
        # 最後の手段：ファイル名のみで全体検索
        filename_only = Path(filename).name
        for ext in possible_extensions:
            test_filename = filename_only if ext == '' else f"{filename_only}{ext}"
            
            # assetsディレクトリを優先的に検索
            for path in self.assets_dir.rglob(test_filename):
                if path.is_file():
                    logger.info(f"画像発見（assets内検索）: {filename} -> {path}")
                    return path
            
            # プロジェクト全体で検索
            for path in self.repo_root.rglob(test_filename):
                if path.is_file() and '.git' not in str(path):
                    logger.info(f"画像発見（全体検索）: {filename} -> {path}")
                    return path
        
        logger.warning(f"画像ファイル未発見: {filename}")
        return None
    
    def process_obsidian_syntax(self, content: str) -> str:
        """Obsidian固有記法を標準記法に変換"""
        # wikilink [[page]] → [page](URL) 変換
        # 重要: 画像記法 ![[...]] は除外する
        content = re.sub(
            r'(?<!\!)\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',
            lambda m: f'[{m.group(2) or m.group(1)}]({self._wiki_to_url(m.group(1))})',
            content
        )
        
        # チェックボックス変換
        content = re.sub(r'- \[ \]', '☐', content)
        content = re.sub(r'- \[x\]', '☑', content)
        
        logger.debug("Obsidian記法変換完了")
        return content
    
    def _wiki_to_url(self, page_name: str) -> str:
        """wikilink をブログ内URLに変換"""
        slug = re.sub(r'[^\w\s-]', '', page_name).strip()
        slug = re.sub(r'[\s_-]+', '-', slug).lower()
        return f"/articles/{slug}"
    
    def update_image_references(self, content: str, image_mapping: Dict) -> str:
        """画像参照をWordPress URLに更新"""
        updated_content = content
        
        for match_text, wp_info in image_mapping.items():
            # Obsidian記法を<figure>構造のHTMLに変換
            figure_html = self._create_figure_html(wp_info)
            
            # 置換前後をログ出力
            if match_text in updated_content:
                logger.debug(f"画像置換: {match_text} -> WordPress URL")
                updated_content = updated_content.replace(match_text, figure_html)
            else:
                logger.warning(f"置換対象が見つかりません: {match_text}")
        
        logger.info("画像参照更新完了", count=len(image_mapping))
        return updated_content
    
    def _create_figure_html(self, wp_info: Dict) -> str:
        """WordPress画像から<figure>構造のHTMLを生成（中央寄せ対応）"""
        img_attrs = [
            f'src="{wp_info["url"]}"',
            f'alt="{wp_info["alt_text"]}"'
        ]
        
        # 画像のスタイル（常に中央寄せ）
        img_style_parts = ['display: block', 'margin: 0 auto']
        
        # 幅指定がある場合
        size_class = ""
        if wp_info.get('width'):
            width = wp_info['width']
            img_attrs.append(f'width="{width}"')
            img_style_parts.append(f'max-width: {width}px')
            
            # WordPressのサイズクラスを決定
            if width <= 150:
                size_class = " size-thumbnail"
            elif width <= 300:
                size_class = " size-medium"
            elif width <= 1024:
                size_class = " size-large"
            else:
                size_class = " size-full"
        else:
            # 幅指定がない場合は最大幅100%
            img_style_parts.append('max-width: 100%')
            size_class = " size-full"
        
        # imgタグにスタイルを追加
        img_attrs.append(f'style="{"; ".join(img_style_parts)}"')
        img_tag = f'<img {" ".join(img_attrs)} />'
        
        # figure要素のスタイル（中央寄せ）
        figure_style = 'text-align: center; margin: 1.5rem auto;'
        
        # キャプションがある場合は<figure>で囲む
        if wp_info.get('caption'):
            # aligncenterクラスとWordPress標準のクラスを追加
            figure_html = f'''<figure class="wp-block-image aligncenter{size_class}" style="{figure_style}">
    {img_tag}
    <figcaption class="wp-element-caption" style="margin-top: 0.5rem; font-size: 0.875rem; color: #666;">{wp_info["caption"]}</figcaption>
</figure>'''
        else:
            # キャプションがない場合も中央寄せ
            figure_html = f'<figure class="wp-block-image aligncenter{size_class}" style="{figure_style}">{img_tag}</figure>'
        
        return figure_html


class ImageOptimizer:
    """画像最適化クラス"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
    
    def optimize(self, image_path: str, target_width: Optional[int] = None) -> Dict:
        """画像最適化実行"""
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        logger.info("画像最適化開始", file=image_path.name)
        
        try:
            # ファイル名正規化
            is_gif = image_path.suffix.lower() == '.gif'
            
            if is_gif:
                # GIF画像の場合は変換せずにファイル名のみ正規化
                normalized_name = self._normalize_filename(image_path.name, keep_extension=True)
                output_path = self.temp_dir / normalized_name
                
                # GIFファイルをそのままコピー
                output_path.write_bytes(image_path.read_bytes())
                
                logger.info("GIF画像をそのままコピー", 
                           original=image_path.name,
                           output=normalized_name)
                
                return {
                    'original_path': str(image_path),
                    'optimized_path': str(output_path),
                    'normalized_filename': normalized_name,
                    'size_reduction': 0,
                    'original_size': None,
                    'is_gif': True
                }
            else:
                # GIF以外の画像は通常の最適化処理
                normalized_name = self._normalize_filename(image_path.name)
                output_path = self.temp_dir / normalized_name
                
                with Image.open(image_path) as img:
                    # RGBA → RGB変換（WebPのため）
                    if img.mode in ('RGBA', 'LA'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                        img = background
                    elif img.mode not in ('RGB', 'L'):
                        img = img.convert('RGB')
                    
                    original_size = img.size
                    
                    # リサイズ（必要な場合）
                    if target_width and img.width > target_width:
                        ratio = target_width / img.width
                        new_height = int(img.height * ratio)
                        img = img.resize((target_width, new_height), Image.Resampling.LANCZOS)
                        logger.debug("画像リサイズ", original=original_size, new_size=img.size)
                    
                    # WebP変換
                    img.save(output_path, 'WebP', quality=85, optimize=True)
                    
                    # サイズ削減率計算
                    reduction = self._calculate_size_reduction(image_path, output_path)
                    
                    logger.info("画像最適化完了", 
                               original=image_path.name,
                               optimized=normalized_name,
                               reduction_percent=f"{reduction:.1f}%")
                    
                    return {
                        'original_path': str(image_path),
                        'optimized_path': str(output_path),
                        'normalized_filename': normalized_name,
                        'size_reduction': reduction,
                        'original_size': original_size,
                        'is_gif': False
                    }
                
        except Exception as e:
            logger.error(f"画像最適化エラー: {e}", file=image_path.name)
            # エラー時は元ファイルをコピー
            fallback_path = self.temp_dir / image_path.name
            fallback_path.write_bytes(image_path.read_bytes())
            
            return {
                'original_path': str(image_path),
                'optimized_path': str(fallback_path),
                'normalized_filename': image_path.name,
                'size_reduction': 0,
                'error': str(e)
            }
    
    def _normalize_filename(self, filename: str, keep_extension: bool = False) -> str:
        """SEO最適化ファイル名に正規化"""
        name, ext = os.path.splitext(filename)
        
        # 特殊文字除去・置換
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '-', name.strip())
        name = name.lower()
        
        # 日付パターン正規化
        name = re.sub(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', r'\1\2\3', name)
        
        # 連続ハイフン正規化
        name = re.sub(r'-+', '-', name).strip('-')
        
        # 拡張子の決定
        if keep_extension:
            return f"{name}{ext.lower()}"
        else:
            return f"{name}.webp"
    
    def _calculate_size_reduction(self, original_path: Path, optimized_path: Path) -> float:
        """ファイルサイズ削減率計算"""
        try:
            original_size = original_path.stat().st_size
            optimized_size = optimized_path.stat().st_size
            return (1 - optimized_size / original_size) * 100
        except:
            return 0.0