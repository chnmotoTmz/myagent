import pickle
import os
from datetime import datetime
import logging
from dotenv import load_dotenv
import sys
import socket
from .browser_automation import AmebaBrowserAutomation
from .database import AmebaDatabase
from .utils import get_credentials, transform_edit_url, retry_with_backoff, format_error_message, handle_browser_session
import time

# .env ファイルから環境変数を読み込む
load_dotenv()

def check_chrome_running():
    """Chromeブラウザが起動しているか確認"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            # 9222ポートへの接続を試みる
            return s.connect_ex(('127.0.0.1', 9222)) == 0
    except:
        return False

class AmebaAutomation:
    def __init__(self):
        """SQLiteデータベースを使用するように初期化"""
        self.db = AmebaDatabase()
        
        # 認証情報をクラス変数として保持
        try:
            self.username, self.password = get_credentials()
        except ValueError:
            # ログイン情報がない場合は警告だけ出して続行
            self.username, self.password = None, None
            logging.warning("環境変数 AMEBA_USERNAME と AMEBA_PASSWORD が設定されていません")
            
        # 既存のpickleファイルがあれば移行
        script_dir = os.path.dirname(os.path.abspath(__file__))
        pickle_path = os.path.join(script_dir, "ameba_data.pkl")
        if os.path.exists(pickle_path):
            try:
                count = self.db.import_from_pickle(pickle_path)
                logging.info(f"{count}件の記事をpickleファイルからインポートしました")
                # バックアップを作成してから削除
                backup_path = pickle_path + ".bak"
                import shutil
                shutil.copy2(pickle_path, backup_path)
                os.remove(pickle_path)
                logging.info(f"pickleファイルをバックアップし、削除しました: {backup_path}")
            except Exception as e:
                logging.error(f"pickleファイルの移行中にエラー: {str(e)}")
            
    def add_post(self, title, content):
        """新しい記事を追加"""
        return self.db.add_local_post(title, content)
        
    def get_unposted(self):
        """未投稿の記事一覧を取得"""
        return self.db.get_local_posts(include_posted=False)

    @retry_with_backoff(max_retries=3)
    def post_to_ameba(self, post_id):
        """AMEBAブログに投稿を公開する（リトライ機能付き）"""
        post = self.db.get_local_post(post_id)
        if not post:
            raise ValueError("指定された記事が見つかりません")

        if post['posted']:
            raise ValueError("この投稿は既に公開されています")

        # 認証情報を確認
        if not self.username or not self.password:
            self.username, self.password = get_credentials()

        # ブラウザ自動化で投稿
        with AmebaBrowserAutomation(headless=True) as automation:
            automation.login(self.username, self.password)
            automation.create_post(post['title'], post['content'])
            
        # 投稿完了をマーク
        self.db.update_local_post(post_id, posted=True)

    @retry_with_backoff(max_retries=2)
    def edit_post(self, post_id, new_title=None, new_content=None):
        """既存の投稿を編集する（リトライ機能付き）"""
        post = self.db.get_local_post(post_id)
        if not post:
            raise ValueError("指定された記事が見つかりません")
        
        # 新しいタイトルと本文を設定
        title = new_title if new_title is not None else post['title']
        content = new_content if new_content is not None else post['content']
        
        # 認証情報を確認
        if not self.username or not self.password:
            self.username, self.password = get_credentials()

        # ブラウザ自動化で編集
        with AmebaBrowserAutomation(headless=True) as automation:
            automation.login(self.username, self.password)
            if post['remote_id']:
                # リモート記事の情報を取得
                remote_post = self.db.get_post_content(post['remote_id'])
                if remote_post and remote_post['edit_url']:
                    automation.edit_post(remote_post['edit_url'], title, content)
                else:
                    # 記事URLを検索して編集
                    post_url = automation.get_post_url(post['title'])
                    automation.edit_post(post_url, title, content)
            else:
                # 記事URLを検索して編集
                post_url = automation.get_post_url(post['title'])
                automation.edit_post(post_url, title, content)
            
        # 投稿情報を更新
        self.db.update_local_post(post_id, title=new_title, content=new_content)

    def fetch_blog_posts(self, max_months=12, progress_callback=None, target_year=None, target_month=None):
        """アメーバブログから記事一覧のみを取得する（内容は取得しない）
        
        Args:
            max_months (int): 取得する最大月数（デフォルト12ヶ月＝1年分）
            progress_callback (callable): 進捗を通知するコールバック関数
            target_year (int): 特定の年の記事を取得する場合、その年を指定
            target_month (int): 特定の月の記事を取得する場合、その月を指定
        
        Returns:
            tuple: (記事リスト, 自動化インスタンス)
        """
        # 認証情報を確認
        if not self.username or not self.password:
            self.username, self.password = get_credentials()

        # ブラウザ自動化で記事一覧を取得
        with AmebaBrowserAutomation(headless=True) as automation:
            automation.login(self.username, self.password)
            
            # 特定の年月が指定されている場合、その年月に移動
            if target_year:
                if target_month:
                    if not automation.go_to_specific_year(target_year, target_month):
                        raise ValueError(f"{target_year}年{target_month}月への移動に失敗しました。サポートされている年月かどうか確認してください。")
                else:
                    if not automation.go_to_specific_year(target_year):
                        raise ValueError(f"{target_year}年への移動に失敗しました。サポートされている年かどうか確認してください。")
            
            # CLIでの進捗表示用の標準コールバック
            if progress_callback is None and sys.stdout.isatty():
                def cli_progress(current_month, total_posts, current_page=None, month_str=None):
                    if target_year:
                        month_info = f"{month_str} " if month_str else f"{current_month}ヶ月目 "
                        page_info = f"ページ{current_page} " if current_page else ""
                        year_month_text = f"{target_year}年"
                        if target_month:
                            year_month_text += f"{target_month}月"
                        print(f"\r{year_month_text}の記事一覧を取得中: {month_info}{page_info}/ 取得済み: {total_posts}件", end="")
                    else:
                        print(f"\r記事一覧取得中: {current_month}ヶ月目 / 取得済み: {total_posts}件", end="")
                    return True
                progress_callback = cli_progress
                
            # 記事一覧の取得（内容は取得しない）
            # 特定の年月が指定されている場合は、その月のみを取得
            if target_year and target_month:
                posts = automation.get_blog_posts_specific_month(target_year, target_month, progress_callback=progress_callback)
            else:
                posts = automation.get_blog_posts(max_months=max_months, progress_callback=progress_callback)
            
            # CLI用の改行
            if sys.stdout.isatty() and progress_callback == cli_progress:
                print()  # 最後に改行を入れる
                
            # データベースに記事一覧を保存
            self.db.add_posts_to_list(posts)
                
            return posts, automation

    def fetch_post_contents(self, post_ids, progress_callback=None):
        """指定された記事IDリストの記事内容を取得する
        
        Args:
            post_ids (list): 取得する記事IDのリスト（post_listテーブルのID）
            progress_callback (callable): 進捗を通知するコールバック関数
            
        Returns:
            list: 内容を取得した記事リスト
        """
        # 記事IDが指定されていない場合はエラー
        if not post_ids:
            raise ValueError("記事IDが指定されていません")
            
        # 認証情報を確認
        if not self.username or not self.password:
            self.username, self.password = get_credentials()

        # 記事情報を取得
        posts = []
        for post_id in post_ids:
            post_info = self.db.get_post_list_item(post_id)
            if post_info:
                posts.append(post_info)

        # 記事がない場合はエラー
        if not posts:
            raise ValueError("指定されたIDの記事が見つかりません")

        # ブラウザ自動化で記事内容を取得
        updated_posts = []
        with AmebaBrowserAutomation(headless=True) as automation:
            automation.login(self.username, self.password)
            
            # CLIでの進捗表示用の標準コールバック
            if progress_callback is None and sys.stdout.isatty():
                def cli_progress(current, total):
                    print(f"\r記事内容取得中: {current}/{total} 件", end="")
                    return True
                progress_callback = cli_progress
            
            # 各記事の内容を取得
            for i, post in enumerate(posts):
                try:
                    # 進捗コールバック
                    if progress_callback:
                        continue_process = progress_callback(i+1, len(posts))
                        if not continue_process:
                            logging.info("ユーザーによって処理が中断されました")
                            break
                    
                    # 記事内容を取得
                    if 'edit_url' in post and post['edit_url']:
                        # URLを標準形式に変換
                        post['edit_url'] = transform_edit_url(post['edit_url'])
                        post_data = automation.get_post_content(post['edit_url'])
                        
                        # 404エラーや接続エラーの処理
                        if "取得失敗" in post_data['title'] and "404エラー" in post_data['title']:
                            logging.error(f"記事ID {post['id']} は404エラーが発生しました: {post['title']}")
                            post['content'] = f"この記事は取得できませんでした（404エラー）。\n\n元の記事URL: {post.get('url', '不明')}\n編集URL: {post['edit_url']}"
                            post['error'] = True
                            post['error_type'] = '404_error'
                        elif "取得失敗" in post_data['title'] and "接続エラー" in post_data['title']:
                            logging.error(f"記事ID {post['id']} は接続エラーが発生しました: {post['title']}")
                            post['content'] = f"この記事は接続エラーのため取得できませんでした。\n\n元の記事URL: {post.get('url', '不明')}\n編集URL: {post['edit_url']}"
                            post['error'] = True
                            post['error_type'] = 'connection_error'
                        else:
                            post['content'] = post_data.get('content', '')
                    else:
                        logging.error(f"記事ID {post['id']} には編集URLが設定されていません: {post['title']}")
                        post['content'] = "編集URLが設定されていないため、記事内容を取得できません。"
                        post['error'] = True
                        post['error_type'] = 'no_edit_url'
                    
                    # データベースに記事内容を保存
                    self.db.add_post_content(
                        post['id'],
                        post.get('title', '無題'),
                        post.get('content', ''),
                        error=post.get('error', False),
                        error_type=post.get('error_type', None)
                    )
                    
                    updated_posts.append(post)
                    
                except Exception as e:
                    logging.error(f"記事ID {post['id']} の内容取得中にエラー: {str(e)}")
                    post['content'] = f"記事内容の取得中にエラーが発生しました: {str(e)}"
                    post['error'] = True
                    post['error_type'] = 'fetch_error'
                    
                    # エラー情報を保存
                    self.db.add_post_content(
                        post['id'],
                        post.get('title', '無題'),
                        post['content'],
                        error=True,
                        error_type='fetch_error',
                        error_message=str(e)
                    )
                    
                    updated_posts.append(post)
            
            # CLI用の改行
            if sys.stdout.isatty() and progress_callback == cli_progress:
                print()  # 最後に改行を入れる
        
        return updated_posts

    def import_remote_post(self, remote_post, existing_automation=None):
        """リモートの投稿をローカルにインポートする
        
        Args:
            remote_post: インポートする記事情報
            existing_automation: 既存のブラウザ自動化インスタンス（オプション）
        
        Returns:
            int: 追加された記事のID
        """
        # 認証情報を確認
        if not self.username or not self.password:
            self.username, self.password = get_credentials()

        # ブラウザセッション処理（新規作成または既存再利用）
        automation, need_to_close = handle_browser_session(
            self.username, self.password, existing_automation
        )
        
        try:
            # タイトルと編集URLを検証
            if not remote_post.get('title'):
                raise ValueError("記事情報にタイトルが含まれていません")
                
            if not remote_post.get('edit_url'):
                raise ValueError("記事情報に編集URLが含まれていません")
            
            # 編集URLの形式を確認と変換
            remote_post['edit_url'] = transform_edit_url(remote_post['edit_url'])
            
            # 記事内容を取得（複数回試行）
            max_retries = 3
            for retry in range(max_retries):
                try:
                    logging.info(f"記事内容の取得を試行します（{retry+1}/{max_retries}）: {remote_post['title']}")
                    post_data = automation.get_post_content(remote_post['edit_url'])
                    
                    # 404エラーや接続エラーがあった場合の処理
                    if "取得失敗" in post_data['title'] and "404エラー" in post_data['title']:
                        logging.error(f"この記事は404エラーが発生しました。記事が削除されたか、移動された可能性があります: {remote_post['title']}")
                        
                        # 404エラーでも記事情報を保存
                        error_content = f"この記事は取得できませんでした（404エラー）。\n\n元の記事URL: {remote_post.get('url', '不明')}\n編集URL: {remote_post['edit_url']}"
                        
                        # データベースに保存
                        post_list_id = self.db.add_posts_to_list([remote_post])
                        self.db.add_post_content(
                            post_list_id,
                            remote_post['title'],
                            error_content,
                            error=True,
                            error_type='404_error'
                        )
                        
                        return post_list_id
                    
                    # 接続エラーがあった場合は再試行
                    if "取得失敗" in post_data['title'] and "接続エラー" in post_data['title']:
                        if retry < max_retries - 1:
                            logging.warning(f"接続エラーが発生しました。再試行します ({retry+1}/{max_retries})")
                            time.sleep(3)  # 少し待機
                            continue
                        else:
                            # 最大試行回数に達した場合
                            logging.error(f"接続エラーが{max_retries}回連続で発生しました。インポートをスキップします: {remote_post['title']}")
                            
                            # エラー情報を保存
                            error_content = f"この記事は接続エラーのため取得できませんでした。\n\n元の記事URL: {remote_post.get('url', '不明')}\n編集URL: {remote_post['edit_url']}"
                            
                            # データベースに保存
                            post_list_id = self.db.add_posts_to_list([remote_post])
                            self.db.add_post_content(
                                post_list_id,
                                remote_post['title'],
                                error_content,
                                error=True,
                                error_type='connection_error'
                            )
                            
                            return post_list_id
                    
                    break
                except ConnectionError as e:
                    # 接続エラーの場合は再接続を試みる
                    error_msg = format_error_message(e, "不明な接続エラー")
                    logging.warning(f"接続エラーが発生しました: {error_msg}")
                    
                    # 最後の試行でなければ再接続を試みる
                    if retry < max_retries - 1:
                        logging.info(f"再接続を試みます...")
                        # ブラウザセッションを再初期化
                        automation, need_to_close = handle_browser_session(
                            self.username, self.password, None, headless=True
                        )
                        # 少し待機してから再試行
                        time.sleep(3)
                    else:
                        # 最大試行回数に達したらエラー情報を保存
                        logging.error(f"記事内容の取得に{max_retries}回失敗しました: {error_msg}")
                        
                        # エラー情報を保存
                        error_content = f"この記事は接続エラーのため取得できませんでした。\n\n元の記事URL: {remote_post.get('url', '不明')}\n編集URL: {remote_post['edit_url']}\n\nエラー詳細: {error_msg}"
                        
                        # データベースに保存
                        post_list_id = self.db.add_posts_to_list([remote_post])
                        self.db.add_post_content(
                            post_list_id,
                            remote_post['title'],
                            error_content,
                            error=True,
                            error_type='connection_error',
                            error_message=error_msg
                        )
                        
                        return post_list_id
                except Exception as e:
                    # その他のエラーは再試行しない
                    error_msg = format_error_message(e, "不明なエラー")
                    logging.error(f"記事内容の取得中にエラーが発生しました: {error_msg}")
                    
                    # エラー情報を保存
                    error_content = f"この記事はエラーのため取得できませんでした。\n\n元の記事URL: {remote_post.get('url', '不明')}\n編集URL: {remote_post['edit_url']}\n\nエラー詳細: {error_msg}"
                    
                    # データベースに保存
                    post_list_id = self.db.add_posts_to_list([remote_post])
                    self.db.add_post_content(
                        post_list_id,
                        remote_post['title'],
                        error_content,
                        error=True,
                        error_type='general_error',
                        error_message=error_msg
                    )
                    
                    return post_list_id
            
            # タイトルと内容の検証
            if not post_data.get('title') or post_data.get('title') == "タイトル取得失敗":
                logging.warning(f"記事タイトルの取得に失敗しました: {remote_post.get('title', '無題')}")
                post_data['title'] = remote_post.get('title', '無題')
                
            if not post_data.get('content') or post_data.get('content') == "本文取得失敗":
                logging.warning("記事内容の取得に失敗しました")
                post_data['content'] = f"本文取得に失敗しました。元の記事を確認してください: {remote_post.get('url', '不明')}"
            
            # データベースに保存
            post_list_id = self.db.add_posts_to_list([remote_post])
            self.db.add_post_content(
                post_list_id,
                post_data['title'],
                post_data['content']
            )
            
            return post_list_id
            
        except Exception as e:
            error_msg = format_error_message(e, "不明なエラー")
            logging.error(f"記事インポート中にエラーが発生しました: {error_msg}")
            logging.error(f"例外の詳細: {repr(e)}")
            
            # エラーが発生しても記事情報を保存
            try:
                error_content = f"この記事のインポート中にエラーが発生しました。\n\n元の記事URL: {remote_post.get('url', '不明')}\n編集URL: {remote_post.get('edit_url', '不明')}\n\nエラー詳細: {error_msg}"
                
                # データベースに保存
                post_list_id = self.db.add_posts_to_list([remote_post])
                self.db.add_post_content(
                    post_list_id,
                    f"[インポート失敗] {remote_post.get('title', '不明')}",
                    error_content,
                    error=True,
                    error_type='import_error',
                    error_message=error_msg
                )
                
                return post_list_id
            except:
                # 最終的なエラーハンドリング
                raise ValueError(f"記事「{remote_post.get('title', '不明')}」のインポートに失敗しました: {error_msg}")
        finally:
            # 新しく作成したブラウザインスタンスの場合のみクローズ
            if need_to_close and automation:
                try:
                    automation.__exit__(None, None, None)
                except Exception as e:
                    error_msg = format_error_message(e, "不明なエラー")
                    logging.warning(f"ブラウザクローズ中にエラーが発生しました: {error_msg}")

    def __del__(self):
        """デストラクタ：データベース接続をクローズ"""
        try:
            self.db.close()
        except:
            pass

import argparse

def main():
    # Chromeブラウザが起動しているか確認
    if not check_chrome_running():
        print("\n⚠️ 警告: Chromeブラウザが見つかりません")
        print("このツールを使用するには、Chromeブラウザを特定のモードで起動する必要があります。")
        print("\n以下の手順でChromeを起動してください：")
        print("1. すべてのChromeウィンドウを閉じる")
        print("2. コマンドプロンプトを起動して以下のコマンドを実行：")
        print("   chrome.exe --remote-debugging-port=9222")
        print("   または")
        print("   \"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe\" --remote-debugging-port=9222")
        print("\n※ Chromeが起動したら、ブラウザウィンドウは閉じずに開いたままにしておいてください。")
        print("※ 最初のアクセス時には必要に応じて手動でログインしてください。")
        print("\n続行すると失敗する可能性があります。続行しますか？ (y/N): ", end="")
        response = input().lower()
        if response != 'y':
            print("処理を中止します。")
            sys.exit(1)
        else:
            print("\n✓ 処理を続行します。エラーが発生した場合は、上記の手順を再確認してください。")
    
    automation = AmebaAutomation()
    parser = argparse.ArgumentParser(description="Ameba Blog Automation Tool")
    
    parser.add_argument('--add', nargs=2, metavar=('TITLE', 'CONTENT'),
                       help='Add a new post')
    parser.add_argument('--list', action='store_true',
                       help='List all posts')
    parser.add_argument('--unposted', action='store_true',
                       help='List unposted entries')
    parser.add_argument('--mark-posted', type=int,
                       help='Mark a post as posted by index')
    parser.add_argument('--export', type=int,
                       help='Export post to text file by index')
    parser.add_argument('--post', type=int,
                       help='Post the entry to Ameba blog by index')
    
    parser.add_argument('--edit', type=int,
                       help='Edit a post by index')
    parser.add_argument('--new-title',
                       help='New title for editing')
    parser.add_argument('--new-content',
                       help='New content for editing')
    
    parser.add_argument('--fetch-posts', nargs='?', const=3, type=int, metavar='MONTHS',
                       help='Fetch posts from Ameba Blog (specify number of months, default: 3)')
    
    parser.add_argument('--fetch-year', type=int, metavar='YEAR',
                       help='Fetch all posts from a specific year (e.g. 2024)')
    
    args = parser.parse_args()
    
    if args.add:
        title, content = args.add
        automation.add_post(title, content)
        print(f"Added post: {title}")
        
    if args.list:
        print("\nAll Posts:")
        for i, post in enumerate(automation.db.get_post_list()):
            status = "Posted" if post.get('posted') else "Unposted"
            content_preview = post.get('content', '本文なし')
            if len(content_preview) > 50:
                content_preview = content_preview[:50] + "..."
            print(f"{i}. [{status}] {post['title']} ({post.get('date', '日付なし')})")
            print(f"   {content_preview}")
            print()
            
    if args.unposted:
        unposted = automation.get_unposted()
        print("\nUnposted Entries:")
        for i, post in enumerate(unposted):
            print(f"{i}. {post['title']} ({post['created_at']})")
            
    if args.mark_posted is not None:
        if 0 <= args.mark_posted < len(automation.db.get_local_posts()):
            automation.db.update_local_post(args.mark_posted, posted=True)
            print(f"Marked post {args.mark_posted} as posted")
        else:
            print("Invalid post index")
            
    if args.export is not None:
        if 0 <= args.export < len(automation.db.get_local_posts()):
            post = automation.db.get_local_post(args.export)
            filename = f"post_{args.export}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Title: {post['title']}\n")
                f.write(f"Date: {post['created_at']}\n\n")
                f.write(post['content'])
            print(f"Exported post {args.export} to {filename}")
        else:
            print("Invalid post index")
            
    if args.post is not None:
        try:
            automation.post_to_ameba(args.post)
            print(f"Successfully posted entry {args.post} to Ameba blog")
        except Exception as e:
            print(f"Error posting to Ameba: {str(e)}")

    if args.edit is not None:
        try:
            if not (args.new_title or args.new_content):
                print("新しいタイトルまたは本文を指定してください")
                return
            automation.edit_post(args.edit, args.new_title, args.new_content)
            print(f"Successfully edited entry {args.edit}")
        except Exception as e:
            print(f"Error editing post: {str(e)}")
            
    if args.fetch_year is not None:
        try:
            year = args.fetch_year
            print(f"アメーバブログから{year}年の記事を取得します...")
            
            remote_posts, automation_instance = automation.fetch_blog_posts(max_months=12, target_year=year)
            
            if not remote_posts:
                print(f"{year}年の記事が見つかりませんでした。")
                return
                
            print(f"\n合計{len(remote_posts)}件の記事を取得しました。")
            
            process_import_selection(remote_posts, automation, automation_instance)
                
        except Exception as e:
            error_msg = format_error_message(e, "不明なエラー")
            print(f"記事取得中にエラーが発生しました: {error_msg}")
            logging.error(f"記事取得中の例外詳細: {repr(e)}")
            
    if args.fetch_posts is not None:
        try:
            print(f"アメーバブログから過去{args.fetch_posts}ヶ月分の記事を取得します...")
            remote_posts, automation_instance = automation.fetch_blog_posts(max_months=args.fetch_posts)
            
            if not remote_posts:
                print("記事が見つかりませんでした。")
                return
                
            print(f"\n合計{len(remote_posts)}件の記事を取得しました。")
            
            process_import_selection(remote_posts, automation, automation_instance)
            
        except Exception as e:
            error_msg = format_error_message(e, "不明なエラー")
            print(f"記事取得中にエラーが発生しました: {error_msg}")
            logging.error(f"記事取得中の例外詳細: {repr(e)}")
            
def process_import_selection(remote_posts, automation, automation_instance=None):
    """記事インポート用の選択肢を表示し処理する"""
    # インポートする記事を選択
    print("\n取得した記事一覧:")
    for i, post in enumerate(remote_posts):
        print(f"{i+1}. [{post['date']}] {post['title']}")
        
    print("\nインポートする記事番号を入力してください（カンマ区切りで複数指定可能）:")
    print("例: 1,3,5  または 'all'ですべてインポート):")
    selection = input("> ")
    
    indices = []
    if selection.lower() == 'all':
        indices = list(range(len(remote_posts)))
    else:
        for idx in selection.split(','):
            try:
                idx = int(idx.strip()) - 1  # 1から始まる入力を0から始まるインデックスに変換
                if 0 <= idx < len(remote_posts):
                    indices.append(idx)
            except:
                pass
    
    if not indices:
        print("有効な記事番号が指定されませんでした。")
        return
        
    print(f"\n{len(indices)}件の記事をインポートします...")
    
    # 選択した記事をインポート
    # 認証情報の取得
    try:
        username, password = get_credentials()
    except ValueError as e:
        print(f"エラー: {str(e)}")
        return
        
    # ブラウザセッション処理（既存か新規作成）
    need_new_browser = automation_instance is None
    
    if need_new_browser:
        # 新しいブラウザインスタンスを作成
        automation_instance = AmebaBrowserAutomation(headless=True).__enter__()
        automation_instance.login(username, password)
    
    try:
        for i, idx in enumerate(indices):
            post = remote_posts[idx]
            print(f"[{i+1}/{len(indices)}] {post['title']} をインポート中...")
            
            try:
                post_list_id = automation.import_remote_post(post, automation_instance)
                print(f"✓ インポート成功: ローカルID={post_list_id}")
            except Exception as e:
                error_msg = format_error_message(e, "不明なエラー")
                print(f"✗ インポート失敗: {error_msg}")
                
        print("\nインポート処理が完了しました。")
    finally:
        # 新しく作成したブラウザインスタンスの場合のみクローズ
        if need_new_browser and automation_instance:
            try:
                automation_instance.__exit__(None, None, None)
            except:
                pass

if __name__ == "__main__":
    main()
