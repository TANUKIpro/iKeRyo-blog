"""
Obsidian固有処理モジュール
画像抽出・最適化・記法変換
"""

import re
import os
from typing import Dict, List, Optional
from pathlib import Path
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
        pattern = r'!\[\[([^|\]]+)(?:\s*\|\s*([^|\]]+))?(?:\s*\|\s*(\d+))?\]\]'
        
        for match in re.finditer(pattern, content):
            filename = match.group(1).strip()
            caption = match.group(2).strip() if match.group(2) else ""
            width = int(match.group(3)) if match.group(3) else None
            
            # ファイルパスを解決
            image_path = self._resolve_image_path(filename, base_dir)
            
            if image_path and image_path.exists():
                images.append({
                    'original_filename': filename,
                    'local_path': str(image_path),
                    'caption': caption,  # キャプションをそのまま保持
                    'width': width,
                    'match_text': match.group(0),
                    'alt_text': self._generate_alt_text(filename, caption)
                })
                logger.debug("画像検出", filename=filename, caption=caption, width=width)
            else:
                logger.warning(f"画像ファイル未発見: {filename}")
        
        return images
    
    def _generate_alt_text(self, filename: str, caption: str) -> str:
        """alt text自動生成（HTMLタグ変換なし）"""
        if caption:
            # キャプションをそのまま使用（HTMLタグ変換しない）
            return caption.strip()
        
        # ファイル名からalt text生成
        base_name = Path(filename).stem
        alt_text = re.sub(r'[-_]', ' ', base_name)
        alt_text = re.sub(r'\d{8}|\d{4}-\d{2}-\d{2}', '', alt_text)
        
        return alt_text.strip() or 'image'
    
    def _resolve_image_path(self, filename: str, base_dir: Path) -> Optional[Path]:
        """画像ファイルパスを解決"""
        logger.debug(f"画像検索開始: {filename}")
        
        # 検索パス候補
        search_candidates = [
            # 1. 同一ディレクトリ
            base_dir / filename,
            # 2. assets/images 直下
            self.assets_dir / filename,
            # 3. assets/images の年/月構造
            self.assets_dir / "2025" / "07" / filename,
            # 4. 記事名ベースのフォルダ
            base_dir / f"{base_dir.stem}_assets" / filename,
        ]
        
        # 候補パスをチェック
        for path in search_candidates:
            logger.debug(f"検索中: {path}")
            if path.exists() and path.is_file():
                logger.info(f"画像発見: {filename} -> {path}")
                return path
        
        # 再帰検索（重い処理なので最後に実行）
        logger.debug("再帰検索開始...")
        for path in self.assets_dir.rglob(filename):
            if path.is_file():
                logger.info(f"画像発見（再帰検索）: {filename} -> {path}")
                return path
        
        # プロジェクト全体での検索（最後の手段）
        logger.debug("プロジェクト全体検索...")
        for path in self.repo_root.rglob(filename):
            if path.is_file() and not str(path).startswith('.git'):
                logger.info(f"画像発見（全体検索）: {filename} -> {path}")
                return path
        
        logger.warning(f"画像ファイル未発見: {filename}")
        return None
    
    def _generate_alt_text(self, filename: str, caption: str) -> str:
        """alt text自動生成"""
        if caption:
            # HTMLタグを除去
            clean_caption = re.sub(r'<[^>]+>', '', caption)
            return clean_caption.replace('<br>', ' ').strip()
        
        # ファイル名からalt text生成
        base_name = Path(filename).stem
        alt_text = re.sub(r'[-_]', ' ', base_name)
        alt_text = re.sub(r'\d{8}|\d{4}-\d{2}-\d{2}', '', alt_text)
        
        return alt_text.strip() or 'image'
    
    def process_obsidian_syntax(self, content: str) -> str:
        """Obsidian固有記法を標準記法に変換"""
        # wikilink [[page]] → [page](URL) 変換
        content = re.sub(
            r'\[\[([^\]|]+)(?:\|([^\]]+))?\]\]',
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
        for match_text, wp_info in image_mapping.items():
            # Obsidian記法を<figure>構造のHTMLに変換
            figure_html = self._create_figure_html(wp_info)
            content = content.replace(match_text, figure_html)
        
        logger.debug("画像参照更新完了", count=len(image_mapping))
        return content
    
    def _create_figure_html(self, wp_info: Dict) -> str:
        """WordPress画像から<figure>構造のHTMLを生成"""
        img_attrs = [
            f'src="{wp_info["url"]}"',
            f'alt="{wp_info["alt_text"]}"'
        ]
        
        # 幅指定がある場合
        if wp_info.get('width'):
            img_attrs.append(f'width="{wp_info["width"]}"')
        
        img_tag = f'<img {" ".join(img_attrs)} />'
        
        # キャプションがある場合は<figure>で囲む
        if wp_info.get('caption'):
            figure_html = f'''<figure class="wp-block-image">
    {img_tag}
    <figcaption class="wp-element-caption">{wp_info["caption"]}</figcaption>
</figure>'''
        else:
            # キャプションがない場合は<img>タグのみ
            figure_html = img_tag
        
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
            normalized_name = self._normalize_filename(image_path.name)
            output_path = self.temp_dir / normalized_name
            
            with Image.open(image_path) as img:
                original_size = img.size
                
                # リサイズ（必要な場合）
                if target_width and img.width > target_width:
                    img.thumbnail((target_width, target_width), Image.Resampling.LANCZOS)
                    logger.debug("画像リサイズ", original=original_size, target_width=target_width)
                
                # WebP変換
                img.save(output_path, 'WebP', quality=85, optimize=True)
                
                # レスポンシブサイズ生成
                responsive_sizes = self._generate_responsive_sizes(img, Path(normalized_name).stem)
                
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
                    'responsive_sizes': responsive_sizes,
                    'size_reduction': reduction,
                    'original_size': original_size
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
                'responsive_sizes': {},
                'error': str(e)
            }
    
    def _normalize_filename(self, filename: str) -> str:
        """SEO最適化ファイル名に正規化"""
        name, _ = os.path.splitext(filename)
        
        # 特殊文字除去・置換
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'\s+', '-', name.strip())
        name = name.lower()
        
        # 日付パターン正規化
        name = re.sub(r'(\d{4})[-_]?(\d{2})[-_]?(\d{2})', r'\1\2\3', name)
        
        # 連続ハイフン正規化
        name = re.sub(r'-+', '-', name).strip('-')
        
        return f"{name}.webp"
    
    def _generate_responsive_sizes(self, img: Image.Image, base_name: str) -> Dict:
        """レスポンシブ画像サイズ生成"""
        responsive = {}
        sizes = [400, 800, 1200, 1600]
        
        for size in sizes:
            if img.width > size:
                resized = img.copy()
                resized.thumbnail((size, size), Image.Resampling.LANCZOS)
                
                responsive_path = self.temp_dir / f"{base_name}_{size}w.webp"
                resized.save(responsive_path, 'WebP', quality=85, optimize=True)
                responsive[size] = str(responsive_path)
        
        return responsive
    
    def _calculate_size_reduction(self, original_path: Path, optimized_path: Path) -> float:
        """ファイルサイズ削減率計算"""
        try:
            original_size = original_path.stat().st_size
            optimized_size = optimized_path.stat().st_size
            return (1 - optimized_size / original_size) * 100
        except:
            return 0.0