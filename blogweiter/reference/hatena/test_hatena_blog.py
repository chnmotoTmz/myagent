import unittest
from unittest.mock import patch, MagicMock
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import base64
from bs4 import BeautifulSoup

# テスト対象のモジュールをインポート
from hatena_post import (
    load_credentials,
    wsse,
    create_post_data,
    post_to_hatena,
    retrieve_hatena_blog_entries,
    extract_japanese_text,
    is_japanese,
    get_public_link
)

class TestHatenaBlogFunctions(unittest.TestCase):
    def setUp(self):
        """テストの前準備"""
        self.username = "test_user"
        self.api_key = "test_api_key"
        self.blog_domain = "test.hatenablog.com"

    def test_load_credentials(self):
        """load_credentials関数のテスト"""
        with patch.dict(os.environ, {'HATENA_BLOG_ATOMPUB_KEY_1': 'test_key'}):
            username, auth_token = load_credentials("test_user")
            self.assertEqual(username, "test_user")
            self.assertEqual(auth_token, "test_key")

        # 環境変数が設定されていない場合のテスト
        with patch.dict(os.environ, clear=True):
            with self.assertRaises(AssertionError):
                load_credentials("test_user")

    def test_wsse(self):
        """wsse関数のテスト"""
        wsse_header = wsse(self.username, self.api_key)
        
        # WSSEヘッダーの形式を確認
        self.assertIn('UsernameToken', wsse_header)
        self.assertIn('Username="test_user"', wsse_header)
        self.assertIn('PasswordDigest="', wsse_header)
        self.assertIn('Nonce="', wsse_header)
        self.assertIn('Created="', wsse_header)

    def test_create_post_data(self):
        """create_post_data関数のテスト"""
        title = "Test Title"
        body = "<p>Test Body</p>"
        
        data = create_post_data(title, body, self.username)
        
        # XMLの形式を確認
        root = ET.fromstring(data)
        
        # タイトルのテスト
        self.assertEqual(root.find("{http://www.w3.org/2005/Atom}title").text, title)
        
        # 著者名のテスト
        self.assertEqual(root.find("{http://www.w3.org/2005/Atom}author/{http://www.w3.org/2005/Atom}name").text, self.username)
        
        # コンテンツのテスト
        content_elem = root.find("{http://www.w3.org/2005/Atom}content")
        # コンテンツの属性チェック
        self.assertEqual(content_elem.get('type'), 'text/html')
        
        # ドラフトステータスのテスト
        data_draft = create_post_data(title, body, self.username, draft='yes')
        root_draft = ET.fromstring(data_draft)
        self.assertEqual(
            root_draft.find("{http://www.w3.org/2007/app}control/{http://www.w3.org/2007/app}draft").text,
            'yes'
        )

    @patch('requests.post')
    def test_post_to_hatena(self, mock_post):
        """post_to_hatena関数のテスト"""
        # モックの設定
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.text = "Created"
        mock_post.return_value = mock_response

        status_code, response_text = post_to_hatena(
            self.username,
            self.blog_domain,
            self.api_key,
            "Test Title",
            "<p>Test Body</p>"
        )

        self.assertEqual(status_code, 201)
        self.assertEqual(response_text, "Created")
        
        # リクエストの検証
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn(f'http://blog.hatena.ne.jp/{self.username}/{self.blog_domain}/atom/entry', args)
        self.assertIn('X-WSSE', kwargs['headers'])

    def test_extract_japanese_text(self):
        """extract_japanese_text関数のテスト"""
        html_content = """
        <div>
            <p>こんにちは World! テスト Test 漢字 かな カナ</p>
            <p>1234 あいうえお</p>
        </div>
        """
        result = extract_japanese_text(html_content)
        expected = "こんにちはテスト漢字かなカナあいうえお"
        self.assertEqual(result, expected)

    def test_is_japanese(self):
        """is_japanese関数のテスト"""
        # 平仮名のテスト
        self.assertTrue(is_japanese('あ'))
        self.assertTrue(is_japanese('ん'))
        
        # カタカナのテスト
        self.assertTrue(is_japanese('ア'))
        self.assertTrue(is_japanese('ン'))
        
        # 漢字のテスト
        self.assertTrue(is_japanese('漢'))
        self.assertTrue(is_japanese('字'))
        
        # 記号のテスト
        self.assertTrue(is_japanese('。'))
        self.assertTrue(is_japanese('、'))
        
        # 英数字のテスト
        self.assertFalse(is_japanese('a'))
        self.assertFalse(is_japanese('Z'))
        self.assertFalse(is_japanese('1'))

    def test_get_public_link(self):
        """get_public_link関数のテスト"""
        # テスト用のXMLエントリーを作成
        entry_xml = """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <link rel="alternate" type="text/html" href="https://example.com/entry/1" />
            <link rel="edit" type="application/atom+xml" href="https://example.com/edit/1" />
        </entry>
        """
        entry = ET.fromstring(entry_xml)
        
        # 正常系テスト
        link = get_public_link(entry)
        self.assertEqual(link, "https://example.com/entry/1")
        
        # 該当するリンクが存在しない場合
        entry_xml_no_alternate = """
        <entry xmlns="http://www.w3.org/2005/Atom">
            <link rel="edit" type="application/atom+xml" href="https://example.com/edit/1" />
        </entry>
        """
        entry_no_alternate = ET.fromstring(entry_xml_no_alternate)
        link_none = get_public_link(entry_no_alternate)
        self.assertIsNone(link_none)

    @patch('requests.get')
    def test_retrieve_hatena_blog_entries(self, mock_get):
        """retrieve_hatena_blog_entries関数のテスト"""
        mock_response = MagicMock()
        mock_response.text = "<feed xmlns='http://www.w3.org/2005/Atom'></feed>"
        mock_get.return_value = mock_response

        result = retrieve_hatena_blog_entries(
            "https://blog.hatena.ne.jp/test_user/test.hatenablog.com/atom/entry",
            ("test_user", "test_key")
        )
        
        self.assertEqual(result, mock_response.text)
        mock_get.assert_called_once()

if __name__ == '__main__':
    unittest.main()
