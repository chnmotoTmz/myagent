"""
ユーティリティ関数を提供するモジュール
"""
import os
import logging
import time
import re
import requests
from functools import wraps
from typing import Optional, Any, Callable, Tuple, List
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from dataclasses import dataclass

from .exceptions import URLTransformError

# ロガーの設定
logger = logging.getLogger(__name__)

@dataclass
class LinkInfo:
    original_url: str
    transformed_url: str
    is_alive: bool
    similar_url: Optional[str] = None
    error_message: Optional[str] = None

class LinkTransformer:
    def __init__(self, logger=None):
        """初期化"""
        self.logger = logger or logging.getLogger(__name__)
        self.search_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
    def transform_hatena_link(self, url: str) -> str:
        """はてなブログのatom形式のURLを通常の記事URLに変換します"""
        # atom形式のURLパターン
        atom_pattern = r'https://blog\.hatena\.ne\.jp/([^/]+)/([^/]+)/atom/entry/(\d+)'
        # 通常の記事URLパターン
        entry_pattern = r'https://([^/]+)/entry/(\d+)'
        
        if re.match(atom_pattern, url):
            match = re.match(atom_pattern, url)
            if match:
                username, domain, entry_id = match.groups()
                return f'https://{domain}/entry/{entry_id}'
        return url

    def check_link_alive(self, url: str) -> Tuple[bool, Optional[str]]:
        """URLの生死を確認します"""
        try:
            response = requests.head(url, timeout=5, allow_redirects=True)
            return response.status_code == 200, None
        except Exception as e:
            return False, str(e)

    def find_similar_link_by_text(self, link_text: str, original_url: str) -> Optional[str]:
        """リンクテキストを使って類似リンクを検索
        
        Args:
            link_text: <a>タグ内のテキスト
            original_url: 元のURL（ドメイン情報の参考用）
            
        Returns:
            検索で見つかった関連URL
        """
        if not link_text or len(link_text.strip()) < 3:
            return None  # テキストが短すぎる場合は検索しない
            
        self.logger.info(f"リンクテキスト「{link_text}」で検索します")
        
        try:
            # 元URLのドメインを抽出
            domain_match = re.search(r'https?://([^/]+)', original_url)
            original_domain = domain_match.group(1) if domain_match else ""
            
            # Amebaブログ内の場合の特別処理
            if 'ameblo.jp' in original_url:
                # ブログ名を抽出
                blog_id_match = re.search(r'ameblo\.jp/([^/]+)', original_url)
                if blog_id_match:
                    blog_id = blog_id_match.group(1)
                    # 同じブログ内で検索するURLを構築
                    search_url = f"https://ameblo.jp/{blog_id}/entry-list.html"
                    return search_url
            
            # Google検索を使用
            query = f"{link_text}"
            if original_domain:
                # ドメイン情報も検索に含める
                if "rakuten" in original_domain:
                    query += " site:rakuten.co.jp"
                elif "amazon" in original_domain:
                    query += " site:amazon.co.jp"
                elif "yahoo" in original_domain:
                    query += " site:yahoo.co.jp"
                elif "ameblo.jp" in original_domain:
                    query += " site:ameblo.jp"
                
            # 検索URL
            search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}"
            
            # 検索実行
            response = requests.get(search_url, headers=self.search_headers, timeout=10)
            if response.status_code != 200:
                return None
                
            # 検索結果からURLを抽出
            urls = re.findall(r'<a href="(https?://[^"]+)"', response.text)
            filtered_urls = []
            
            # 検索結果をフィルタリング
            for url in urls:
                # Googleの内部URLは除外
                if "google.com" in url:
                    continue
                    
                # 元のドメインと一致するURLを優先
                if original_domain and original_domain in url:
                    self.logger.info(f"元のドメインと一致するURLを発見: {url}")
                    return url
                    
                filtered_urls.append(url)
                
            # 最初の検索結果を返す
            if filtered_urls:
                self.logger.info(f"テキスト検索で類似リンクを発見: {filtered_urls[0]}")
                return filtered_urls[0]
                
            return None
            
        except Exception as e:
            self.logger.warning(f"テキスト検索中にエラー: {str(e)}")
            return None

    def find_similar_link(self, url: str, link_text: Optional[str] = None) -> Optional[str]:
        """死んでいるリンクの類似URLを検索します"""
        try:
            # リンクテキストがある場合は、テキスト検索を試みる
            if link_text and len(link_text.strip()) > 2:
                text_search_result = self.find_similar_link_by_text(link_text, url)
                if text_search_result:
                    return text_search_result
            
            # 楽天リンクの特殊処理
            if 'rakuten.co.jp' in url:
                self.logger.info(f"楽天リンクを変換: {url}")
                return "https://www.rakuten.co.jp/"
            
            # 1. Internet Archiveのウェイバックマシンを試す
            wayback_url = f"https://web.archive.org/web/{url}"
            response = requests.head(wayback_url, timeout=10, allow_redirects=True)  # タイムアウトを10秒に増加
            if response.status_code == 200:
                self.logger.info(f"Wayback Machine上で類似リンクを発見: {wayback_url}")
                return wayback_url
                
            # 2. はてなブログのパターンを変更して試す可能性
            if "hatenablog.com/entry/" in url:
                # 6桁のIDを7桁に変換して試す可能性
                pattern = r'(https://[^/]+/entry/)(\d+)'
                match = re.match(pattern, url)
                if match:
                    domain, entry_id = match.groups()
                    # 1桁増やした類似IDを試す
                    for i in range(10):
                        similar_id = entry_id + str(i)
                        similar_url = f"{domain}{similar_id}"
                        response = requests.head(similar_url, timeout=5, allow_redirects=True)
                        if response.status_code == 200:
                            self.logger.info(f"類似IDで生きているリンクを発見: {similar_url}")
                            return similar_url
            
            # 3. ドメインのルートを試す
            domain_pattern = r'(https?://[^/]+)'
            match = re.match(domain_pattern, url)
            if match:
                domain = match.group(1)
                response = requests.head(domain, timeout=5, allow_redirects=True)
                if response.status_code == 200:
                    self.logger.info(f"ドメインのルートは生存しています: {domain}")
                    return domain
            
            return None
        except Exception as e:
            self.logger.warning(f"類似リンク検索中にエラー: {str(e)}")
            return None

    def process_link(self, url: str, link_text: Optional[str] = None) -> LinkInfo:
        """リンクを処理して情報を返します"""
        # URLの変換
        transformed_url = self.transform_url(url)
        
        # リンクの生死確認
        is_alive, error_message = self.check_link_alive(transformed_url)
        
        # 死んでいる場合は類似リンクを検索
        similar_url = None
        if not is_alive:
            similar_url = self.find_similar_link(transformed_url, link_text)
            self.logger.warning(f"Dead link found: {transformed_url}")
            if similar_url:
                self.logger.info(f"Similar link found: {similar_url}")
        
        return LinkInfo(
            original_url=url,
            transformed_url=transformed_url,
            is_alive=is_alive,
            similar_url=similar_url,
            error_message=error_message
        )

    def process_content(self, content: str) -> Tuple[str, List[LinkInfo]]:
        """記事本文中のリンクを処理します"""
        # HTMLコンテンツの場合はHTML処理を使用
        if '<a ' in content and '</a>' in content:
            return self.process_html_content(content)
            
        # 通常のテキストコンテンツの場合
        link_infos = []
        
        # URLを検出して処理
        url_pattern = r'https?://[^\s<>"\']+'
        
        def replace_url(match):
            url = match.group(0)
            link_info = self.process_link(url)
            link_infos.append(link_info)
            
            # 生きているリンクか類似リンクを使用
            if link_info.is_alive:
                return link_info.transformed_url
            elif link_info.similar_url:
                return link_info.similar_url
            return link_info.transformed_url  # 代替がない場合は変換後のURLをそのまま使用
        
        processed_content = re.sub(url_pattern, replace_url, content)
        return processed_content, link_infos

    def transform_url(self, url: str) -> str:
        """URLを変換します
        
        以下のタイプのURLを変換します：
        1. はてなブログのリンク
        2. 楽天アフィリエイトリンク
        3. Amazonアフィリエイトリンク
        4. AmebaブログのULID記事リンク
        """
        try:
            # はてなブログのリンク変換
            hatena_result = self.transform_hatena_link(url)
            if hatena_result != url:
                return hatena_result
                
            # 楽天アフィリエイトリンク
            if "a.r10.to" in url or "hb.afl.rakuten.co.jp" in url:
                return self._transform_rakuten_link(url)
                
            # Amazonアフィリエイトリンク
            if "amzn.to" in url or "amazon.co.jp/gp/product" in url:
                return self._transform_amazon_link(url)
                
            # AmebaブログのULIDリンク
            ameba_pattern = r'https?://ameblo\.jp/([^/]+)/entry-(\d+).html'
            if re.match(ameba_pattern, url):
                return url  # そのまま返す
                
            return url
        except Exception as e:
            self.logger.error(f"URL変換エラー: {str(e)}")
            return url
            
    def _transform_rakuten_link(self, url: str) -> str:
        """楽天アフィリエイトリンクを変換します"""
        try:
            if "a.r10.to" in url:
                response = requests.head(url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return response.url
            elif "hb.afl.rakuten.co.jp" in url:
                response = requests.head(url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return response.url
            return url
        except Exception as e:
            self.logger.error(f"楽天リンク変換エラー: {str(e)}")
            return url
            
    def _transform_amazon_link(self, url: str) -> str:
        """Amazonアフィリエイトリンクを変換します"""
        try:
            if "amzn.to" in url:
                response = requests.head(url, allow_redirects=True, timeout=10)
                if response.status_code == 200:
                    return response.url
            
            # 商品リンクからアフィリエイトパラメータを削除
            amazon_pattern = r'(https?://www\.amazon\.co\.jp/[^?]+).*'
            match = re.match(amazon_pattern, url)
            if match:
                return match.group(1)
                
            return url
        except Exception as e:
            self.logger.error(f"Amazonリンク変換エラー: {str(e)}")
            return url

    def process_html_content(self, content: str) -> Tuple[str, List[LinkInfo]]:
        """HTMLコンテンツ内のリンクを処理します"""
        link_infos = []
        
        # <a>タグを検出して処理
        a_tag_pattern = r'<a\s+[^>]*href=["\'](https?://[^"\']+)["\'][^>]*>(.*?)</a>'
        
        def replace_link(match):
            url = match.group(1)
            link_text = match.group(2)
            
            # HTMLタグを除去してプレーンテキスト化
            plain_text = re.sub(r'<[^>]+>', '', link_text).strip()
            
            # リンク情報を処理
            link_info = self.process_link(url, plain_text)
            link_infos.append(link_info)
            
            # 置換後のURLを決定
            replacement_url = link_info.transformed_url
            if not link_info.is_alive and link_info.similar_url:
                replacement_url = link_info.similar_url
            
            # 元の<a>タグの属性を保持しつつ、URLだけを置換
            return match.group(0).replace(url, replacement_url)
        
        processed_content = re.sub(a_tag_pattern, replace_link, content)
        return processed_content, link_infos

class URLTransformer:
    """URLの変換を行うクラス"""
    
    BASE_EDIT_URL = "https://blog.ameba.jp/ucs/entry/srventryupdateinput.do"
    
    @classmethod
    def transform_edit_url(cls, edit_url: str) -> Optional[str]:
        """
        編集URLを標準形式に変換
        
        Args:
            edit_url (str): 変換対象のURL
            
        Returns:
            Optional[str]: 標準形式のURL、変換失敗時はNone
            
        Raises:
            URLTransformError: URL変換に失敗した場合
        """
        if not edit_url:
            return None
            
        if cls._is_standard_format(edit_url):
            return edit_url
            
        try:
            entry_id = cls._extract_entry_id(edit_url)
            return cls._create_standard_url(entry_id)
        except Exception as e:
            raise URLTransformError(f"URL変換エラー: {e}")
    
    @classmethod
    def _is_standard_format(cls, url: str) -> bool:
        """URLが標準形式かどうかを判定"""
        return url.startswith(cls.BASE_EDIT_URL)
    
    @classmethod
    def _extract_entry_id(cls, url: str) -> str:
        """URLからエントリーIDを抽出"""
        if "entry-" in url:
            return url.split("entry-")[1].split(".")[0]
        elif "srvedit.do?entry_id=" in url:
            entry_id = url.split("entry_id=")[1]
            return entry_id.split("&")[0] if "&" in entry_id else entry_id
        elif "ameblo.jp" in url and "/" in url:
            for part in url.split("/"):
                if part.isdigit() and len(part) > 5:
                    return part
        raise URLTransformError(f"エントリーIDが見つかりません: {url}")
    
    @classmethod
    def _create_standard_url(cls, entry_id: str) -> str:
        """標準形式のURLを生成"""
        return f"{cls.BASE_EDIT_URL}?id={entry_id}"

def get_credentials() -> tuple[str, str]:
    """
    環境変数から認証情報を取得
    
    Returns:
        tuple[str, str]: ユーザー名とパスワード
        
    Raises:
        ValueError: 環境変数が設定されていない場合
    """
    username = os.getenv("AMEBA_USERNAME")
    password = os.getenv("AMEBA_PASSWORD")
    
    if not username or not password:
        raise ValueError("環境変数 AMEBA_USERNAME と AMEBA_PASSWORD を設定してください")
        
    return username, password

def retry_with_backoff(max_retries: int = 3, initial_delay: float = 1.0, 
                      backoff_factor: float = 2.0) -> Callable:
    """
    リトライ処理を行うデコレータ
    
    Args:
        max_retries (int): 最大リトライ回数
        initial_delay (float): 初回のリトライまでの待機時間（秒）
        backoff_factor (float): 待機時間の増加係数
        
    Returns:
        Callable: デコレータ関数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    logger.warning(f"試行 {attempt + 1}/{max_retries} が失敗: {str(e)}")
                    if attempt < max_retries - 1:
                        time.sleep(delay)
                        delay *= backoff_factor
            
            raise last_exception
        return wrapper
    return decorator

def wait_for_element(driver: Any, by: str, value: str, timeout: int = 10) -> Any:
    """
    要素が表示されるまで待機
    
    Args:
        driver: Seleniumのドライバーインスタンス
        by (str): 要素の検索方法
        value (str): 要素の検索値
        timeout (int): タイムアウト時間（秒）
        
    Returns:
        Any: 見つかった要素
        
    Raises:
        TimeoutException: 要素が見つからない場合
    """
    wait = WebDriverWait(driver, timeout)
    return wait.until(EC.presence_of_element_located((by, value)))

def find_element_with_fallback(driver, selectors, timeout=5):
    """複数のセレクタを試して要素を見つける"""
    for by, selector in selectors:
        try:
            return wait_for_element(driver, by, selector, timeout)
        except:
            continue
    raise ValueError(f"要素が見つかりませんでした: {selectors}")

def format_error_message(error, default="不明なエラー"):
    """例外からエラーメッセージを取得"""
    return str(error) if str(error) else default

def create_progress_callback(callback_type="cli"):
    """進捗表示用のコールバック関数を生成"""
    if callback_type == "cli":
        def cli_progress(current, total, **kwargs):
            if "month_str" in kwargs:
                print(f"\r進捗: {kwargs.get('month_str')} - {current}/{total} 件", end="")
            else:
                print(f"\r進捗: {current}/{total} 件", end="")
            return True
        return cli_progress
    return None

def handle_browser_session(username, password, existing_automation=None, headless=True):
    """ブラウザセッションを管理し、新規作成または既存のものを再利用"""
    from .browser_automation import AmebaBrowserAutomation
    
    need_to_close = False
    automation = existing_automation
    
    if automation is None:
        logger.info("新しいブラウザインスタンスを作成します")
        automation = AmebaBrowserAutomation(headless=headless).__enter__()
        automation.login(username, password)
        need_to_close = True
    elif not automation.is_browser_alive():
        logger.warning("既存のブラウザインスタンスが無効です。新しいインスタンスを作成します")
        try:
            if need_to_close:
                automation.__exit__(None, None, None)
        except Exception as e:
            logger.warning(f"ブラウザクローズ中にエラー: {format_error_message(e)}")
        automation = AmebaBrowserAutomation(headless=headless).__enter__()
        automation.login(username, password)
        need_to_close = True
        
    return automation, need_to_close 

def main():
    """LinkTransformerの単体テスト用メイン関数"""
    import logging
    import sys
    
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger('link_transformer')
    
    # LinkTransformerの初期化
    transformer = LinkTransformer(logger)
    
    # テスト用のURL
    test_urls = [
        # はてなブログ
        "https://motochan1969.hatenablog.com/entry/2021/10/28/235958",
        "https://b.hatena.ne.jp/entry/s/motochan1969.hatenablog.com/entry/2021/10/28/235958",
        
        # 楽天アフィリエイト
        "https://hb.afl.rakuten.co.jp/hgc/g00q0727.waxyc671.g00q0727.waxyd848/?pc=https%3A%2F%2Fitem.rakuten.co.jp%2Fbook%2F1234567%2F",
        
        # Amazonアフィリエイト
        "https://amzn.to/3abcdef",
        
        # Amebaブログ
        "https://ameblo.jp/username/entry-12345678901.html",
        
        # 死んでいるリンク
        "https://example.com/nonexistent",
    ]
    
    # リンクテキスト検索のテスト
    test_link_texts = [
        "楽天市場で買える商品",
        "Amazonで買える本",
        "ブログの記事タイトル",
    ]
    
    # HTMLコンテンツのテスト
    test_html = """
    <p>これはテスト段落です。<a href="https://motochan1969.hatenablog.com/entry/2021/10/28/235958">はてなブログの記事</a>と
    <a href="https://ameblo.jp/username/entry-12345678901.html">Amebaブログの記事</a>へのリンクがあります。</p>
    <p>また、<a href="https://example.com/nonexistent">死んでいるリンク</a>もテストします。</p>
    """
    
    # コマンドライン引数があればそのURLをテスト
    if len(sys.argv) > 1:
        test_urls = sys.argv[1:]
    
    # URLの変換とステータスチェック
    print("\n===== URLの変換とステータスチェック =====")
    for url in test_urls:
        print(f"\nURL: {url}")
        
        # URL変換
        transformed_url = transformer.transform_url(url)
        print(f"変換後URL: {transformed_url}")
        
        # リンク処理
        info = transformer.process_link(url)
        print(f"生存状態: {'生存' if info.is_alive else '死亡'}")
        
        if not info.is_alive:
            print(f"エラー: {info.error_message}")
            
            # 類似リンク検索
            similar = transformer.find_similar_link(transformed_url)
            if similar:
                print(f"類似リンク: {similar}")
    
    # リンクテキスト検索のテスト
    print("\n===== リンクテキスト検索のテスト =====")
    for i, (url, text) in enumerate(zip(test_urls[:3], test_link_texts)):
        result = transformer.find_similar_link_by_text(text, url)
        print(f"\nリンクテキスト: {text}")
        print(f"元URL: {url}")
        print(f"検索結果: {result}")
    
    # HTMLコンテンツ処理のテスト
    print("\n===== HTMLコンテンツ処理のテスト =====")
    processed_html, link_infos = transformer.process_html_content(test_html)
    print("\n処理前HTML:")
    print(test_html)
    print("\n処理後HTML:")
    print(processed_html)
    print("\n検出されたリンク:")
    for i, info in enumerate(link_infos):
        print(f"\nリンク {i+1}:")
        print(f"元URL: {info.original_url}")
        print(f"変換後URL: {info.transformed_url}")
        print(f"生存状態: {'生存' if info.is_alive else '死亡'}")
        if not info.is_alive and info.similar_url:
            print(f"類似リンク: {info.similar_url}")

if __name__ == "__main__":
    main() 