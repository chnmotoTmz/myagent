import os
import hashlib
import random
import base64
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup

class HatenaService:
    def __init__(self, hatena_id: str, blog_domain: str, api_key: str, debug_dir: str = "debug"):
        """
        はてなブログサービスの初期化
        
        Args:
            hatena_id: はてなID
            blog_domain: ブログドメイン
            api_key: APIキー
            debug_dir: デバッグ情報保存ディレクトリ
        """
        self.hatena_id = hatena_id
        self.blog_domain = blog_domain
        self.api_key = api_key
        self.logger = logging.getLogger(__name__)
        self.root_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_domain}/atom"
        
        # デバッグディレクトリの設定
        self.debug_dir = Path(debug_dir)
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"デバッグディレクトリ: {self.debug_dir}")

    def _generate_wsse(self) -> str:
        """WSSE認証ヘッダーを生成"""
        created = datetime.now().isoformat() + "Z"
        b_nonce = hashlib.sha1(str(random.random()).encode()).digest()
        b_digest = hashlib.sha1(b_nonce + created.encode() + self.api_key.encode()).digest()
        return 'UsernameToken Username="{0}", PasswordDigest="{1}", Nonce="{2}", Created="{3}"'.format(
            self.hatena_id,
            base64.b64encode(b_digest).decode(),
            base64.b64encode(b_nonce).decode(),
            created
        )

    def _find_next_link(self, root: ET.Element) -> Optional[str]:
        """次のページのリンクを取得"""
        for link in root.findall('{http://www.w3.org/2005/Atom}link'):
            if link.get('rel') == 'next':
                return link.get('href')
        return None

    def _process_entry(self, entry: ET.Element) -> Optional[Dict]:
        """
        エントリーの処理
        
        Args:
            entry: エントリーのXML要素
        Returns:
            処理済みエントリー情報（ドラフトの場合はNone）
        """
        try:
            # ドラフトチェック
            draft_elem = entry.find('.//{http://www.w3.org/2007/app}draft')
            if draft_elem is not None and draft_elem.text == 'yes':
                return None

            # 必要な情報を抽出
            title = entry.find('{http://www.w3.org/2005/Atom}title').text
            content = entry.find('{http://www.w3.org/2005/Atom}content').text
            updated = entry.find('{http://www.w3.org/2005/Atom}updated').text
            
            # URLの取得
            url = None
            edit_url = None
            for link in entry.findall('{http://www.w3.org/2005/Atom}link'):
                if link.get('rel') == 'alternate' and link.get('type') == 'text/html':
                    url = link.get('href')
                elif link.get('rel') == 'edit':
                    edit_url = link.get('href')
            
            # HTMLの処理
            soup = BeautifulSoup(content, 'html.parser')
            text_content = soup.get_text(separator=' ', strip=True)

            return {
                'title': title,
                'content': content,
                'text_content': text_content,
                'url': url,
                'edit_url': edit_url,
                'updated': updated
            }

        except Exception as e:
            self.logger.error(f"エントリー処理エラー: {str(e)}")
            return None

    def get_entries(self) -> List[Dict]:
        """
        ブログ記事を全件取得（ページネーション対応）
        
        Returns:
            取得した記事のリスト
        """
        entries = []
        next_url = f"{self.root_endpoint}/entry"
        page = 1

        while next_url:
            try:
                self.logger.info(f"==== ページ {page} の取得開始 ====")
                self.logger.info(f"URL: {next_url}")
                
                # APIリクエスト
                headers = {'X-WSSE': self._generate_wsse()}
                response = requests.get(next_url, headers=headers)
                response.raise_for_status()
                
                # レスポンスの確認
                self.logger.info(f"ステータスコード: {response.status_code}")
                
                # デバッグ用にレスポンスを保存
                debug_file = self.debug_dir / f"response_page_{page}.xml"
                debug_file.write_text(response.text, encoding="utf-8")
                
                # XMLの解析
                root = ET.fromstring(response.content)
                current_page_entries = root.findall('{http://www.w3.org/2005/Atom}entry')
                self.logger.info(f"このページの記事数: {len(current_page_entries)}")
                
                # エントリーの処理
                processed_count = 0
                for entry in current_page_entries:
                    entry_data = self._process_entry(entry)
                    if entry_data:
                        entries.append(entry_data)
                        processed_count += 1
                
                self.logger.info(f"処理した記事数: {processed_count}")
                
                # 次のページのURLを取得
                next_url = self._find_next_link(root)
                if next_url:
                    self.logger.info(f"次のページURL: {next_url}")
                else:
                    self.logger.info("次のページはありません")
                    break
                
                self.logger.info(f"現在の総記事数: {len(entries)}")
                page += 1
                
            except Exception as e:
                self.logger.error(f"ページ {page} の取得中にエラー: {str(e)}")
                break
        
        self.logger.info(f"==== 取得完了 ====")
        self.logger.info(f"最終的な総記事数: {len(entries)}")
        return entries
