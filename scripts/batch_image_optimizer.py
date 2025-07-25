import sys
import json
import os
import re
from pathlib import Path
from typing import Dict, Optional
from PIL import Image

class StandaloneImageOptimizer:
    """スタンドアロン版の画像最適化クラス"""
    
    def __init__(self, temp_dir: str):
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
    
    def optimize(self, image_path: str, target_width: Optional[int] = None) -> Dict:
        """画像最適化実行"""
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        print(f"画像最適化開始: {image_path.name}")
        
        try:
            # ファイル名正規化
            is_gif = image_path.suffix.lower() == '.gif'
            
            if is_gif:
                # GIF画像の場合は変換せずにファイル名のみ正規化
                normalized_name = self._normalize_filename(image_path.name, keep_extension=True)
                output_path = self.temp_dir / normalized_name
                
                # GIFファイルをそのままコピー
                output_path.write_bytes(image_path.read_bytes())
                
                print(f"GIF画像をそのままコピー: {normalized_name}")
                
                return {
                    'original_path': str(image_path),
                    'optimized_path': str(output_path),
                    'normalized_filename': normalized_name,
                    'size_reduction': 0,
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
                        print(f"画像リサイズ: {original_size} -> {img.size}")
                    
                    # WebP変換
                    img.save(output_path, 'WebP', quality=85, optimize=True)
                    
                    # サイズ削減率計算
                    reduction = self._calculate_size_reduction(image_path, output_path)
                    
                    print(f"画像最適化完了: {normalized_name} (削減率: {reduction:.1f}%)")
                    
                    return {
                        'original_path': str(image_path),
                        'optimized_path': str(output_path),
                        'normalized_filename': normalized_name,
                        'size_reduction': reduction,
                        'original_size': original_size,
                        'is_gif': False
                    }
            
        except Exception as e:
            print(f"画像最適化エラー: {e}")
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

def optimize_images(image_files):
    optimizer = StandaloneImageOptimizer("temp")
    results = []
    
    for image_file in image_files:
        if not Path(image_file).exists():
            continue
            
        try:
            print(f"🔄 最適化中: {image_file}")
            result = optimizer.optimize(image_file)
            
            # 元のファイルを最適化されたファイルで置き換え
            if not result.get('is_gif') and 'error' not in result:
                optimized_path = Path(result['optimized_path'])
                original_path = Path(result['original_path'])
                
                # バックアップ作成
                backup_path = original_path.with_suffix('.backup' + original_path.suffix)
                original_path.rename(backup_path)
                
                # 最適化ファイルを元の場所に移動
                optimized_path.rename(original_path)
                
                # バックアップ削除
                backup_path.unlink()
                
                results.append({
                    'file': image_file,
                    'size_reduction': result['size_reduction'],
                    'status': 'optimized'
                })
            else:
                results.append({
                    'file': image_file,
                    'size_reduction': 0,
                    'status': 'skipped' if result.get('is_gif') else 'error'
                })
                
        except Exception as e:
            print(f"❌ エラー: {image_file} - {str(e)}")
            results.append({
                'file': image_file,
                'error': str(e),
                'status': 'error'
            })
    
    # レポート保存
    with open('optimization_report.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return results

if __name__ == "__main__":
    files = sys.argv[1:]
    results = optimize_images(files)
    
    # サマリー出力
    optimized = len([r for r in results if r['status'] == 'optimized'])
    skipped = len([r for r in results if r['status'] == 'skipped'])
    errors = len([r for r in results if r['status'] == 'error'])
    
    print(f"\n📊 最適化完了: {optimized}件成功, {skipped}件スキップ, {errors}件エラー")
