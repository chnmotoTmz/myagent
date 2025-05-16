from dataclasses import dataclass
from logger import log_debug
from datetime import datetime
from typing import List, Optional, Dict
import requests
import xml.etree.ElementTree as ET
from blog_content import BlogContent, Platform, Status, Visibility, Meta, Author, Content, ContentSection

@dataclass
class BlogImportConfig:
    hatena_id: str
    blog_domain: str
    api_key: str

class BlogImporter:
    def __init__(self, config: BlogImportConfig):
        self.config = config
        self.auth = (config.hatena_id, config.api_key)
        self.root_endpoint = f"https://blog.hatena.ne.jp/{config.hatena_id}/{config.blog_domain}/atom"

    def get_blog_entries(self) -> List[BlogContent]:
        """
        はてなブログからすべての記事を取得します
        """
        entries = []
        blog_entries_uri = f"{self.root_endpoint}/entry"

        while blog_entries_uri:
            entries_xml = self._retrieve_entries(blog_entries_uri)
            root = ET.fromstring(entries_xml)
            
            # 次のページのURIを取得
            links = root.findall("{http://www.w3.org/2005/Atom}link")
            blog_entries_uri = next(
                (link.attrib["href"] for link in links if link.attrib["rel"] == "next"),
                None
            )

            # エントリーを解析
            entry_elements = root.findall("{http://www.w3.org/2005/Atom}entry")
            for entry in entry_elements:
                if not self._is_draft(entry):
                    blog_content = self._convert_to_blog_content(entry)
                    if blog_content:
                        entries.append(blog_content)

        return entries

    def _retrieve_entries(self, uri: str) -> str:
        """
        指定されたURIから記事データを取得します
        """
        response = requests.get(uri, auth=self.auth)
        response.raise_for_status()
        return response.text

    def _is_draft(self, entry: ET.Element) -> bool:
        """
        記事がドラフトかどうかを判定します
        """
        draft_element = entry.find(".//{http://www.w3.org/2007/app}draft")
        return draft_element is not None and draft_element.text == "yes"

    def _convert_to_blog_content(self, entry: ET.Element) -> Optional[BlogContent]:
        """
        XMLエントリーをBlogContentオブジェクトに変換します
        """
        try:
            # タイトルと本文を取得
            title = entry.find("{http://www.w3.org/2005/Atom}title").text
            content_element = entry.find("{http://www.w3.org/2005/Atom}content")
            body = content_element.text if content_element is not None else ""

            # 公開URLを取得
            public_url = next(
                (link.get("href") for link in entry.findall("{http://www.w3.org/2005/Atom}link")
                 if link.get("rel") == "alternate" and link.get("type") == "text/html"),
                None
            )

            # カテゴリー（タグ）を取得
            categories = [
                category.get("term")
                for category in entry.findall("{http://www.w3.org/2005/Atom}category")
            ]

            # 作成日時と更新日時を取得
            created = entry.find("{http://www.w3.org/2005/Atom}published")
            updated = entry.find("{http://www.w3.org/2005/Atom}updated")
            
            created_at = datetime.fromisoformat(created.text) if created is not None else datetime.utcnow()
            updated_at = datetime.fromisoformat(updated.text) if updated is not None else datetime.utcnow()

            # 著者情報を取得
            author_element = entry.find("{http://www.w3.org/2005/Atom}author")
            author_name = author_element.find("{http://www.w3.org/2005/Atom}name").text if author_element is not None else ""
            
            # BlogContentオブジェクトを作成
            return BlogContent(
                platform=Platform.HATENA_BLOG,
                status=Status.PUBLISHED,
                visibility=Visibility.PUBLIC,
                created_at=created_at,
                updated_at=updated_at,
                published_at=created_at,
                meta=Meta(
                    title=title,
                    description="",  # メタディスクリプションは別途取得が必要
                    permalink=public_url.split("/")[-1] if public_url else "",
                    category=categories[0] if categories else "",
                    tags=categories,
                    author=Author(
                        id=self.config.hatena_id,
                        name=author_name,
                        image_url=""  # 著者画像URLは別途取得が必要
                    ),
                    thumbnail=None,  # サムネイルは別途取得が必要
                    seo=None  # SEO情報は別途取得が必要
                ),
                content=Content(
                    format="html",
                    body=body,
                    sections=[
                        ContentSection(
                            type="body",
                            content=body
                        )
                    ]
                )
            )
        except Exception as e:
            print(f"Error converting entry: {e}")
            return None

    def import_all_entries(self) -> Dict[str, List[BlogContent]]:
        """
        すべてのブログ記事をインポートし、結果を返します
        """
        try:
            entries = self.get_blog_entries()
            return {
                "success": entries,
                "errors": []
            }
        except Exception as e:
            return {
                "success": [],
                "errors": [str(e)]
            }
