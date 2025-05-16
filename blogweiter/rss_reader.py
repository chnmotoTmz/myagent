import feedparser
from datetime import datetime, timezone
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import re
import ssl
import warnings
from dateutil import parser

class RSSReader:
    def __init__(self):
        self.feeds = {
            'hatena': [
                'https://motochan1969.hatenablog.com/rss',
                'https://lifehacking1919.hatenablog.jp/rss',
                'https://arafo40tozan.hatenadiary.jp/rss'
            ],
            'ameblo': [
                'http://rssblog.ameba.jp/motochan1969/rss.html'
            ]
        }
        
        # 警告を無視
        warnings.filterwarnings('ignore')
        
        # SSL証明書の検証を無効化（開発環境用）
        if hasattr(ssl, '_create_unverified_context'):
            ssl._create_default_https_context = ssl._create_unverified_context

    def _generate_post_id(self, entry: Dict[str, Any], platform: str) -> str:
        date_str = entry.get('published', datetime.now(timezone.utc).isoformat())
        dt = self._parse_date(date_str)
        title_slug = re.sub(r'[^\w\-]', '-', entry.get('title', '').lower())
        return f"{dt.strftime('%Y%m%d')}-{title_slug}"

    def _parse_date(self, date_str: str) -> datetime:
        if not date_str:
            return datetime.now(timezone.utc)
        
        try:
            # python-dateutilを使用して柔軟に日付をパース
            dt = parser.parse(date_str)
            # タイムゾーン情報がない場合はUTCとして扱う
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except:
            return datetime.now(timezone.utc)

    def _clean_html(self, html_content: str) -> str:
        if not html_content:
            return ''
        soup = BeautifulSoup(html_content, 'html.parser')
        # スクリプトとスタイルタグを削除
        for script in soup(['script', 'style']):
            script.decompose()
        return ' '.join(soup.stripped_strings)

    def _extract_tags(self, entry: Dict[str, Any]) -> List[str]:
        tags = []
        if 'tags' in entry:
            tags = [tag.get('term', '') for tag in entry.get('tags', [])]
        return [tag for tag in tags if tag]  # 空のタグを除外

    def _extract_category(self, entry: Dict[str, Any]) -> str:
        if 'category' in entry:
            return entry['category']
        if 'tags' in entry and entry['tags']:
            return entry['tags'][0].get('term', 'uncategorized')
        return 'uncategorized'

    def _extract_author(self, entry: Dict[str, Any], feed: Dict[str, Any]) -> Dict[str, str]:
        author_name = entry.get('author', feed.get('author', '名無し'))
        return {
            "id": re.sub(r'[^\w\-]', '-', author_name.lower()),
            "name": author_name,
            "image_url": ""
        }

    def _fetch_feed(self, feed_url: str) -> Dict:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(feed_url, headers=headers, timeout=10, verify=False)
            response.raise_for_status()
            
            # エンコーディングを明示的に設定
            if 'charset' in response.headers.get('content-type', '').lower():
                response.encoding = response.apparent_encoding
            
            feed = feedparser.parse(response.content)
            
            if feed.get('bozo', 0) == 1:
                print(f"Warning: Feed {feed_url} has format issues")
            
            return feed
        except Exception as e:
            print(f"Error fetching feed {feed_url}: {str(e)}")
            return {'entries': []}

    def get_entries(self) -> List[Dict[str, Any]]:
        all_entries = []
        
        for platform, feed_urls in self.feeds.items():
            for feed_url in feed_urls:
                try:
                    feed = self._fetch_feed(feed_url)
                    
                    for entry in feed.entries:
                        try:
                            created_at = self._parse_date(entry.get('published', ''))
                            updated_at = self._parse_date(entry.get('updated', entry.get('published', '')))
                            
                            processed_entry = {
                                "post_id": self._generate_post_id(entry, platform),
                                "platform": platform,
                                "status": "published",
                                "visibility": "public",
                                "created_at": created_at.isoformat(),
                                "updated_at": updated_at.isoformat(),
                                "published_at": created_at.isoformat(),
                                
                                "meta": {
                                    "title": entry.get('title', '無題'),
                                    "description": self._clean_html(entry.get('summary', '')),
                                    "permalink": entry.get('link', ''),
                                    "category": self._extract_category(entry),
                                    "tags": self._extract_tags(entry),
                                    "author": self._extract_author(entry, feed),
                                    "thumbnail": {
                                        "url": "",
                                        "alt": "",
                                        "width": 0,
                                        "height": 0,
                                        "type": ""
                                    },
                                    "seo": {
                                        "focus_keyword": ", ".join(self._extract_tags(entry)),
                                        "custom_title": "",
                                        "custom_description": "",
                                        "no_index": False,
                                        "canonical_url": entry.get('link', '')
                                    }
                                },
                                
                                "content": {
                                    "format": "html",
                                    "body": entry.get('description', '')
                                }
                            }
                            all_entries.append(processed_entry)
                        except Exception as e:
                            print(f"Error processing entry: {str(e)}")
                            continue
                        
                except Exception as e:
                    print(f"Error processing feed {feed_url}: {str(e)}")
                    continue
        
        # 日付でソート（エラーの場合は現在時刻を使用）
        return sorted(all_entries, 
                     key=lambda x: x.get('created_at', datetime.now(timezone.utc).isoformat()), 
                     reverse=True)

    def get_feed_stats(self) -> Dict[str, int]:
        stats = {
            'total_entries': 0,
            'hatena_entries': 0,
            'ameblo_entries': 0
        }
        
        entries = self.get_entries()
        stats['total_entries'] = len(entries)
        stats['hatena_entries'] = len([e for e in entries if e['platform'] == 'hatena'])
        stats['ameblo_entries'] = len([e for e in entries if e['platform'] == 'ameblo'])
        
        return stats 