import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
import time
import os
import socket
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable

from .exceptions import BrowserError, BrowserInitializationError, LoginError
from .config import config
from .utils import wait_for_element, retry_with_backoff, get_credentials
from .database import AmebaDatabase

logger = logging.getLogger(__name__)

def check_chrome_running(debug_port: int = 9222) -> bool:
    """
    Chromeが指定されたデバッグポートで実行中かどうかをチェック
    
    Args:
        debug_port (int): デバッグポート番号（デフォルト: 9222）
        
    Returns:
        bool: Chromeが実行中の場合はTrue
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', debug_port))
        sock.close()
        return result == 0
    except Exception as e:
        logger.error(f"Chromeの実行状態チェック中にエラー: {e}")
        return False

class AmebaBrowserAutomation:
    """Amebaブログの自動操作を行うクラス"""
    
    def __init__(self, debug_port: Optional[int] = None):
        """
        Args:
            debug_port (Optional[int]): Chromeのデバッグポート番号
            
        Raises:
            BrowserInitializationError: ブラウザの初期化に失敗した場合
        """
        self.debug_port = debug_port or config.browser.debug_port
        self._initialize_components()
    
    def _initialize_components(self):
        """
        コンポーネントの初期化
        
        Raises:
            BrowserInitializationError: 初期化に失敗した場合
        """
        try:
            self._initialize_database()
            self._initialize_browser()
        except Exception as e:
            raise BrowserInitializationError(f"コンポーネントの初期化に失敗: {e}")
    
    def _initialize_database(self):
        """
        データベースの初期化
        
        Raises:
            DatabaseConnectionError: データベース接続に失敗した場合
        """
        self.db = AmebaDatabase()
    
    def _initialize_browser(self):
        """
        ブラウザの初期化
        
        Raises:
            BrowserInitializationError: ブラウザの初期化に失敗した場合
        """
        try:
            self._setup_chrome_options()
            self._create_driver()
            self.wait = WebDriverWait(self.driver, config.browser.timeout)
            logger.info("ブラウザを初期化しました")
        except Exception as e:
            raise BrowserInitializationError(f"ブラウザの初期化に失敗: {e}")
    
    def _setup_chrome_options(self):
        """Chromeのオプションを設定"""
        self.options = webdriver.ChromeOptions()
        self.options.debugger_address = f"127.0.0.1:{self.debug_port}"
        if config.browser.headless:
            self.options.add_argument("--headless")
        if config.browser.user_data_dir:
            self.options.add_argument(f"--user-data-dir={config.browser.user_data_dir}")
    
    def _create_driver(self):
        """Chromeドライバーを作成"""
        self.driver = webdriver.Chrome(options=self.options)
    
    @retry_with_backoff()
    def login(self):
        """
        Amebaブログにログイン
        
        Raises:
            LoginError: ログインに失敗した場合
        """
        try:
            if self.is_logged_in():
                logger.info("既にログインしています")
                return
            
            self.driver.get("https://ameblo.jp/login")
            username, password = get_credentials()
            
            # ユーザー名入力
            username_input = wait_for_element(self.driver, By.NAME, "username")
            username_input.send_keys(username)
            
            # パスワード入力
            password_input = wait_for_element(self.driver, By.NAME, "password")
            password_input.send_keys(password)
            
            # ログインボタンクリック
            login_button = wait_for_element(self.driver, By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            # ログイン完了を待機
            self.wait.until(EC.url_contains("ameblo.jp/my"))
            logger.info("ログインに成功しました")
        except Exception as e:
            raise LoginError(f"ログインに失敗: {e}")
    
    def is_logged_in(self) -> bool:
        """
        ログイン状態を確認
        
        Returns:
            bool: ログインしている場合はTrue
        """
        try:
            self.driver.get("https://ameblo.jp/my")
            return "login" not in self.driver.current_url
        except Exception:
            return False
    
    def get_post_list(self) -> List[Dict[str, Any]]:
        """
        投稿一覧を取得
        
        Returns:
            List[Dict[str, Any]]: 投稿データのリスト
            
        Raises:
            BrowserError: 投稿一覧の取得に失敗した場合
        """
        try:
            self.driver.get("https://ameblo.jp/my/entry.do")
            posts = []
            
            # 投稿一覧を取得
            post_elements = self.driver.find_elements(By.CSS_SELECTOR, ".skin-entryList-item")
            
            for element in post_elements:
                post = self._extract_post_data(element)
                if post:
                    posts.append(post)
            
            logger.info(f"{len(posts)}件の投稿を取得しました")
            return posts
        except Exception as e:
            raise BrowserError(f"投稿一覧の取得に失敗: {e}")
    
    def _extract_post_data(self, element) -> Optional[Dict[str, Any]]:
        """
        投稿要素からデータを抽出
        
        Args:
            element: 投稿要素
            
        Returns:
            Optional[Dict[str, Any]]: 投稿データ
        """
        try:
            title_element = element.find_element(By.CSS_SELECTOR, ".skin-entryList-text")
            date_element = element.find_element(By.CSS_SELECTOR, ".skin-entryList-date")
            url_element = element.find_element(By.CSS_SELECTOR, "a.skin-entryList-text")
            
            return {
                "id": url_element.get_attribute("href").split("/")[-1],
                "title": title_element.text,
                "url": url_element.get_attribute("href"),
                "date": date_element.text,
                "status": "取得済"
            }
        except NoSuchElementException:
            return None
    
    def get_post_content(self, post_id: str) -> Optional[str]:
        """
        投稿内容を取得
        
        Args:
            post_id (str): 投稿ID
            
        Returns:
            Optional[str]: 投稿内容
            
        Raises:
            BrowserError: 投稿内容の取得に失敗した場合
        """
        try:
            self.driver.get(f"https://blog.ameba.jp/ucs/entry/srventryupdateinput.do?id={post_id}")
            content_element = wait_for_element(self.driver, By.ID, "editor")
            return content_element.get_attribute("value")
        except Exception as e:
            raise BrowserError(f"投稿内容の取得に失敗: {e}")
    
    def create_post(self, title: str, content: str):
        """
        新規投稿を作成
        
        Args:
            title (str): タイトル
            content (str): 内容
            
        Raises:
            BrowserError: 投稿の作成に失敗した場合
        """
        try:
            self.driver.get("https://blog.ameba.jp/ucs/entry/srventryinsertinput.do")
            
            # タイトル入力
            title_input = wait_for_element(self.driver, By.NAME, "title")
            title_input.clear()
            title_input.send_keys(title)
            
            # 内容入力
            content_input = wait_for_element(self.driver, By.ID, "editor")
            content_input.clear()
            content_input.send_keys(content)
            
            # 投稿ボタンクリック
            submit_button = wait_for_element(self.driver, By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            logger.info(f"投稿を作成しました: {title}")
        except Exception as e:
            raise BrowserError(f"投稿の作成に失敗: {e}")
    
    def update_post(self, post_id: str, title: str, content: str):
        """
        投稿を更新
        
        Args:
            post_id (str): 投稿ID
            title (str): タイトル
            content (str): 内容
            
        Raises:
            BrowserError: 投稿の更新に失敗した場合
        """
        try:
            self.driver.get(f"https://blog.ameba.jp/ucs/entry/srventryupdateinput.do?id={post_id}")
            
            # タイトル入力
            title_input = wait_for_element(self.driver, By.NAME, "title")
            title_input.clear()
            title_input.send_keys(title)
            
            # 内容入力
            content_input = wait_for_element(self.driver, By.ID, "editor")
            content_input.clear()
            content_input.send_keys(content)
            
            # 更新ボタンクリック
            submit_button = wait_for_element(self.driver, By.CSS_SELECTOR, "button[type='submit']")
            submit_button.click()
            
            logger.info(f"投稿を更新しました: {title}")
        except Exception as e:
            raise BrowserError(f"投稿の更新に失敗: {e}")
    
    def delete_post(self, post_id: str):
        """
        投稿を削除
        
        Args:
            post_id (str): 投稿ID
            
        Raises:
            BrowserError: 投稿の削除に失敗した場合
        """
        try:
            self.driver.get(f"https://blog.ameba.jp/ucs/entry/srventrydeleteinput.do?id={post_id}")
            
            # 削除確認ボタンクリック
            delete_button = wait_for_element(self.driver, By.CSS_SELECTOR, "button[type='submit']")
            delete_button.click()
            
            logger.info(f"投稿を削除しました: {post_id}")
        except Exception as e:
            raise BrowserError(f"投稿の削除に失敗: {e}")
    
    def close(self):
        """ブラウザを閉じる"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
        except Exception as e:
            logger.error(f"ブラウザの終了に失敗: {e}")
    
    def get_blog_posts(self, max_months: int = 12, progress_callback: Optional[Callable] = None) -> List[Dict[str, Any]]:
        """
        ブログ記事一覧を取得
        
        Args:
            max_months (int): 取得する最大月数
            progress_callback (Optional[Callable]): 進捗状況を通知するコールバック関数
            
        Returns:
            List[Dict[str, Any]]: 記事データのリスト
        """
        try:
            # ログイン確認
            if not self.is_logged_in():
                self.login()
            
            posts = []
            current_month = 1
            
            while current_month <= max_months:
                # 進捗通知
                if progress_callback:
                    progress_callback(current_month, len(posts))
                
                # 記事一覧ページにアクセス
                self.driver.get(f"https://ameblo.jp/my/entry.do?page={current_month}")
                
                # 記事要素を取得
                post_elements = self.driver.find_elements(By.CSS_SELECTOR, ".skin-entryList-item")
                
                if not post_elements:
                    break
                
                # 記事データを抽出
                for element in post_elements:
                    post = self._extract_post_data(element)
                    if post:
                        posts.append(post)
                
                current_month += 1
            
            # 完了通知
            if progress_callback:
                progress_callback(current_month - 1, len(posts))
            
            return posts
            
        except Exception as e:
            logger.error(f"記事一覧の取得に失敗: {e}")
            raise BrowserError(f"記事一覧の取得に失敗: {e}")

def main():
    """テスト用のメイン関数"""
    import os
    from dotenv import load_dotenv
    
    # .env ファイルから認証情報を読み込む
    load_dotenv()
    
    username = os.getenv("AMEBA_USERNAME")
    password = os.getenv("AMEBA_PASSWORD")
    
    if not username or not password:
        logger.error("環境変数 AMEBA_USERNAME と AMEBA_PASSWORD を設定してください")
        return
    
    # テスト投稿の実行
    with AmebaBrowserAutomation() as automation:
        try:
            automation.login()
            automation.create_post(
                "テスト投稿",
                "これは自動投稿のテストです。\n\n自動化テストが成功しました！"
            )
            logger.info("テスト投稿が完了しました")
        except Exception as e:
            logger.error(f"テスト実行中にエラーが発生しました: {str(e)}")

if __name__ == "__main__":
    main() 