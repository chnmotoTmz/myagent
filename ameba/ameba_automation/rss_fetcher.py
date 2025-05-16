import requests
import logging
import re
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import time
from .utils import LinkTransformer, LinkInfo

logger = logging.getLogger(__name__)

class RSSCache:
    """RSSデータのキャッシュを管理するクラス"""
    
    def __init__(self, cache_dir: str = "cache", cache_duration: int = 24):
        """
        初期化
        
        Args:
            cache_dir: キャッシュディレクトリ
            cache_duration: キャッシュの有効期間（時間）
        """
        self.cache_dir = Path(cache_dir)
        self.cache_duration = timedelta(hours=cache_duration)
        
        # キャッシュディレクトリがなければ作成
        if not self.cache_dir.exists():
            self.cache_dir.mkdir(parents=True)
    
    def get_cache_path(self, url: str) -> Path:
        """URLからキャッシュファイルのパスを取得"""
        # URLをファイル名に変換（特殊文字を除去）
        filename = re.sub(r'[\\/*?:"<>|]', '_', url)
        # さらにスラッシュとコロンを変換
        filename = filename.replace('/', '_').replace(':', '_')
        return self.cache_dir / f"{filename}.json"
    
    def get(self, url: str) -> Optional[Dict]:
        """キャッシュからデータを取得"""
        cache_path = self.get_cache_path(url)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # キャッシュの有効期限をチェック
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.cache_duration:
                logger.info(f"キャッシュの有効期限切れ: {url}")
                return None
            
            return data
        except Exception as e:
            logger.error(f"キャッシュ読み込みエラー: {e}")
            return None
    
    def save(self, url: str, data: Dict) -> None:
        """データをキャッシュに保存"""
        cache_path = self.get_cache_path(url)
        
        try:
            # タイムスタンプを追加
            data['timestamp'] = datetime.now().isoformat()
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"キャッシュを保存しました: {url}")
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")


class RSSFetcher:
    """RSSフィードを取得・解析するクラス"""
    
    def __init__(self, link_transformer=None, cache_dir="cache", logger=None):
        """
        初期化
        
        Args:
            link_transformer: リンク変換器
            cache_dir: キャッシュディレクトリ
            logger: ロガー
        """
        self.logger = logger or logging.getLogger(__name__)
        self.cache = RSSCache(cache_dir=cache_dir)
        self.link_transformer = link_transformer or LinkTransformer(self.logger)
    
    def fetch_rss(self, url: str) -> Dict:
        """
        RSSフィードを取得して解析
        
        Args:
            url: RSSフィードのURL
            
        Returns:
            Dict: 解析結果
        """
        # キャッシュをチェック
        cached_data = self.cache.get(url)
        if cached_data:
            logger.info(f"キャッシュから読み込み: {url}")
            return cached_data
        
        try:
            # RSSフィードを取得
            logger.info(f"RSSフィードを取得: {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            # XMLを解析
            root = ET.fromstring(response.content)
            
            # 名前空間を取得
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}
            if root.tag.startswith('{'):
                ns_uri = root.tag[1:].split('}')[0]
                namespaces['default'] = ns_uri
            
            # フィード情報を抽出
            title = self._find_text(root, './/channel/title', namespaces)
            if not title:
                title = self._find_text(root, './/default:title', namespaces)
            
            # 記事情報を抽出
            items = []
            
            # RSS 2.0形式の場合
            for item in root.findall('.//item'):
                items.append(self._parse_rss_item(item))
            
            # Atom形式の場合
            for entry in root.findall('.//default:entry', namespaces):
                items.append(self._parse_atom_entry(entry, namespaces))
            
            # 結果を作成
            result = {
                'title': title,
                'url': url,
                'items': items,
                'count': len(items)
            }
            
            # キャッシュに保存
            self.cache.save(url, result)
            
            return result
            
        except Exception as e:
            logger.error(f"RSSフィード取得エラー: {e}")
            return {'error': str(e), 'url': url, 'items': [], 'count': 0}
    
    def _find_text(self, element, path, namespaces=None):
        """要素内のテキストを検索"""
        try:
            found = element.find(path, namespaces)
            return found.text if found is not None else ""
        except:
            return ""
    
    def _parse_rss_item(self, item) -> Dict:
        """RSS 2.0形式の記事情報を解析"""
        title = self._find_text(item, 'title')
        link = self._find_text(item, 'link')
        pub_date = self._find_text(item, 'pubDate')
        description = self._find_text(item, 'description')
        
        # リンクを変換
        transformed_link = self.link_transformer.transform_hatena_link(link)
        
        return {
            'title': title,
            'original_url': link,
            'url': transformed_link,
            'pub_date': pub_date,
            'description': description
        }
    
    def _parse_atom_entry(self, entry, namespaces) -> Dict:
        """Atom形式の記事情報を解析"""
        title = self._find_text(entry, 'default:title', namespaces)
        
        # リンクを取得 (Atomでは複数のリンクがある場合がある)
        link = ""
        for link_elem in entry.findall('default:link', namespaces):
            rel = link_elem.get('rel', 'alternate')
            if rel == 'alternate':
                link = link_elem.get('href', '')
                break
        
        if not link:
            link = self._find_text(entry, 'default:id', namespaces)
        
        pub_date = self._find_text(entry, 'default:published', namespaces)
        if not pub_date:
            pub_date = self._find_text(entry, 'default:updated', namespaces)
        
        content = self._find_text(entry, 'default:content', namespaces)
        if not content:
            content = self._find_text(entry, 'default:summary', namespaces)
        
        # リンクを変換
        transformed_link = self.link_transformer.transform_hatena_link(link)
        
        return {
            'title': title,
            'original_url': link,
            'url': transformed_link,
            'pub_date': pub_date,
            'description': content
        }
    
    def get_all_links_from_rss(self, feed_url: str) -> Dict[str, List[LinkInfo]]:
        """RSSフィードからブログ記事のURLを取得します
        
        Args:
            feed_url: RSSフィードのURL
            
        Returns:
            key: 記事タイトル, value: リンク情報のリスト
        """
        data = self.fetch_rss(feed_url)
        if not data or 'items' not in data:
            self.logger.error(f"RSSフィードの取得に失敗しました: {feed_url}")
            return {}
            
        article_links = {}
        
        for item in data['items']:
            title = item.get('title', '')
            link = item.get('link')
            
            if not link:
                continue
                
            # 記事リンクを変換して状態をチェック
            link_info = self.link_transformer.process_link(link)
            article_links[title] = [link_info]
        
        self.logger.info(f"{len(article_links)}件のブログ記事リンクを取得しました")
        return article_links


def main():
    """RSSフェッチャーの単体テスト用メイン関数"""
    import logging
    import json
    from pathlib import Path
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('rss_fetcher')
    
    # RSSフェッチャーの初期化
    cache_dir = Path('cache')
    cache_dir.mkdir(exist_ok=True)
    
    from utils import LinkTransformer
    link_transformer = LinkTransformer(logger)
    rss_fetcher = RSSFetcher(link_transformer, cache_dir, logger)
    
    # テスト用RSSフィード
    test_feeds = [
        "https://motochan1969.hatenablog.com/rss",
        # 他のRSSフィードを追加
    ]
    
    # 各フィードからリンクを取得
    for feed_url in test_feeds:
        print(f"\n===== フィード: {feed_url} =====")
        article_links = rss_fetcher.get_all_links_from_rss(feed_url)
        
        # 結果を表示
        print(f"記事数: {len(article_links)}")
        for title, links in article_links.items():
            print(f"\n記事: {title}")
            for link in links:
                print(f"  オリジナルURL: {link.original_url}")
                print(f"  変換後URL: {link.transformed_url}")
                print(f"  ステータス: {'生存' if link.is_alive else '死亡'}")
                if not link.is_alive and link.similar_url:
                    print(f"  代替URL: {link.similar_url}")
        
        # キャッシュに保存
        cache_file = cache_dir / f"rss_cache_{hash(feed_url)}.json"
        print(f"\nキャッシュ保存: {cache_file}")
    
    print("\nテスト完了")

if __name__ == "__main__":
    main() 