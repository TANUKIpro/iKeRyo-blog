"""
WordPress REST API操作モジュール
投稿・メディア・カテゴリー・タグ管理
"""

import requests
import base64
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
from utils.logger import logger

class WordPressAPI:
    """WordPress REST API クライアント"""
    
    def __init__(self, wp_url: str, username: str, app_password: str):
        self.wp_url = wp_url.rstrip('/')
        self.auth = base64.b64encode(f"{username}:{app_password}".encode()).decode()
        self.headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Type': 'application/json'
        }
        
        logger.info("WordPress API初期化", url=self.wp_url, user=username)
    
    def upload_image(self, image_path: str, alt_text: str = "", caption: str = "") -> Dict:
        """メディアライブラリに画像をアップロード"""
        url = f"{self.wp_url}/wp-json/wp/v2/media"
        image_path = Path(image_path)
        
        if not image_path.exists():
            raise FileNotFoundError(f"画像ファイルが見つかりません: {image_path}")
        
        with open(image_path, 'rb') as f:
            files = {
                'file': (image_path.name, f, 'image/webp')
            }
            
            data = {
                'alt_text': alt_text,
                'caption': caption,  
                'description': f'自動アップロード: {datetime.now()}'
            }
            
            headers = {'Authorization': f'Basic {self.auth}'}
            response = requests.post(url, headers=headers, files=files, data=data)
        
        if response.status_code == 201:
            media_data = response.json()
            logger.info("画像アップロード成功", 
                       file=image_path.name,
                       media_id=media_data['id'],
                       url=media_data['source_url'])
            
            return {
                'id': media_data['id'],
                'url': media_data['source_url'],
                'wordpress_data': media_data
            }
        else:
            error_msg = f"画像アップロード失敗: {response.status_code}"
            logger.error(error_msg, file=image_path.name, response=response.text[:200])
            raise Exception(f"{error_msg} - {response.text}")
    
    def get_or_create_category(self, category_name: str) -> int:
        """カテゴリーIDを取得（存在しない場合は作成）"""
        url = f"{self.wp_url}/wp-json/wp/v2/categories"
        
        # 既存カテゴリー検索
        params = {'search': category_name, 'per_page': 100}
        response = requests.get(url, headers=self.headers, params=params)
        
        if response.status_code == 200:
            categories = response.json()
            for cat in categories:
                if cat['name'] == category_name:
                    logger.debug("既存カテゴリー発見", name=category_name, id=cat['id'])
                    return cat['id']
        
        # カテゴリー作成
        create_data = {'name': category_name}
        response = requests.post(url, headers=self.headers, json=create_data)
        
        if response.status_code == 201:
            new_category = response.json()
            logger.info("カテゴリー作成", name=category_name, id=new_category['id'])
            return new_category['id']
        
        raise Exception(f"カテゴリー操作失敗: {category_name} - {response.status_code}")
    
    def get_or_create_tags(self, tag_names: List[str]) -> List[int]:
        """タグIDリストを取得（存在しない場合は作成）"""
        tag_ids = []
        
        for tag_name in tag_names:
            url = f"{self.wp_url}/wp-json/wp/v2/tags"
            
            # 既存タグ検索
            params = {'search': tag_name, 'per_page': 100}
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 200:
                tags = response.json()
                found = False
                for tag in tags:
                    if tag['name'] == tag_name:
                        tag_ids.append(tag['id'])
                        found = True
                        break
                
                if not found:
                    # タグ作成
                    create_data = {'name': tag_name}
                    response = requests.post(url, headers=self.headers, json=create_data)
                    
                    if response.status_code == 201:
                        new_tag = response.json()
                        tag_ids.append(new_tag['id'])
                        logger.info("タグ作成", name=tag_name, id=new_tag['id'])
        
        return tag_ids
    
    def create_post(self, post_data: Dict) -> Dict:
        """記事を投稿"""
        url = f"{self.wp_url}/wp-json/wp/v2/posts"
        
        response = requests.post(url, headers=self.headers, json=post_data)
        
        if response.status_code == 201:
            post_result = response.json()
            logger.info("記事投稿成功",
                       title=post_result['title']['rendered'],
                       status=post_result['status'],
                       url=post_result['link'])
            
            return {
                'id': post_result['id'],
                'link': post_result['link'],
                'status': post_result['status'],
                'title': post_result['title']['rendered'],
                'wordpress_data': post_result
            }
        else:
            error_msg = f"記事投稿失敗: {response.status_code}"
            logger.error(error_msg, response=response.text[:200])
            raise Exception(f"{error_msg} - {response.text}")
    
    def test_connection(self) -> bool:
        """WordPress API接続テスト"""
        try:
            url = f"{self.wp_url}/wp-json/wp/v2/posts?per_page=1"
            response = requests.get(url, headers=self.headers, timeout=10)
            
            success = response.status_code == 200
            if success:
                logger.info("WordPress API接続成功")
            else:
                logger.error("WordPress API接続失敗", status=response.status_code)
            
            return success
        except Exception as e:
            logger.error(f"WordPress API接続エラー: {e}")
            return False