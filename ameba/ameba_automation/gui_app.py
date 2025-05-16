"""
GUIアプリケーションを管理するモジュール
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import queue
import logging
from datetime import datetime
from .browser_automation import AmebaBrowserAutomation as AmebaAutomation, check_chrome_running
import os
import sys
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Callable

from .exceptions import GUIError, WidgetError
from .config import config
from .database import AmebaDatabase

logger = logging.getLogger(__name__)

class AmebaGUI:
    """Amebaブログ管理ツールのGUIクラス"""
    
    def __init__(self, root):
        """GUIの初期化"""
        self.root = root
        self.root.title("Ameba Blog Manager")
        
        # 環境変数を読み込む
        load_dotenv()
        
        # メインのAutomationインスタンスを作成
        self.automation = AmebaAutomation()
        
        # 選択状態管理用の変数
        self.selected_remote_posts = {}
        self.selected_local_posts = {}
        
        # GUIコンポーネントの初期化
        self.setup_gui()
        
        # ログ表示用のキュー
        self.log_queue = queue.Queue()
        self.setup_logging()
        
        # 定期的なログ更新
        self.root.after(100, self.check_log_queue)
        
        # 記事一覧の更新（データベースから読み込み）
        self.update_remote_list()
        self.update_local_list()
        
        # 起動メッセージ
        self.log_text.insert(tk.END, "アプリケーションを起動しました。データベースから記事一覧を読み込みました。\n")
        self.log_text.see(tk.END)
        
    def setup_gui(self):
        """GUIコンポーネントの初期化"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # タブコントロール
        self.tab_control = ttk.Notebook(main_frame)
        self.tab_control.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # リモート記事タブ
        remote_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(remote_tab, text='リモート記事')
        
        # ローカル記事タブ
        local_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(local_tab, text='ローカル記事')
        
        # リモート記事用ツリービュー
        self.remote_posts_tree = ttk.Treeview(remote_tab, columns=('check', 'date', 'status', 'title', 'local_edit'),
                                            show='headings', height=20)
        self.remote_posts_tree.heading('check', text='✓')
        self.remote_posts_tree.heading('date', text='日付')
        self.remote_posts_tree.heading('status', text='状態')
        self.remote_posts_tree.heading('title', text='タイトル')
        self.remote_posts_tree.heading('local_edit', text='ローカル編集')
        
        self.remote_posts_tree.column('check', width=30, anchor='center')
        self.remote_posts_tree.column('date', width=100, anchor='w')
        self.remote_posts_tree.column('status', width=100, anchor='w')
        self.remote_posts_tree.column('title', width=400, anchor='w')
        self.remote_posts_tree.column('local_edit', width=100, anchor='center')
        
        self.remote_posts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.remote_posts_tree.bind('<Button-1>', self.on_remote_tree_click)
        
        # リモート記事用スクロールバー
        remote_scrollbar = ttk.Scrollbar(remote_tab, orient=tk.VERTICAL, command=self.remote_posts_tree.yview)
        remote_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.remote_posts_tree.configure(yscrollcommand=remote_scrollbar.set)
        
        # ローカル記事用ツリービュー
        self.local_posts_tree = ttk.Treeview(local_tab, columns=('check', 'date', 'status', 'title', 'remote_sync'),
                                     show='headings', height=20)
        self.local_posts_tree.heading('check', text='✓')
        self.local_posts_tree.heading('date', text='日付')
        self.local_posts_tree.heading('status', text='状態')
        self.local_posts_tree.heading('title', text='タイトル')
        self.local_posts_tree.heading('remote_sync', text='リモート連携')
        
        self.local_posts_tree.column('check', width=30, anchor='center')
        self.local_posts_tree.column('date', width=100, anchor='w')
        self.local_posts_tree.column('status', width=100, anchor='w')
        self.local_posts_tree.column('title', width=400, anchor='w')
        self.local_posts_tree.column('remote_sync', width=100, anchor='center')
        
        self.local_posts_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.local_posts_tree.bind('<Button-1>', self.on_local_tree_click)
        
        # ローカル記事用スクロールバー
        local_scrollbar = ttk.Scrollbar(local_tab, orient=tk.VERTICAL, command=self.local_posts_tree.yview)
        local_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.local_posts_tree.configure(yscrollcommand=local_scrollbar.set)
        
        # ボタンフレーム
        button_frame = ttk.Frame(main_frame, padding="5")
        button_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        
        # 各種ボタン
        ttk.Button(button_frame, text="全選択", command=self.select_all_posts).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="選択解除", command=self.deselect_all_posts).grid(row=0, column=1, padx=5)
        ttk.Button(button_frame, text="記事取得", command=self.fetch_posts_list_only).grid(row=0, column=2, padx=5)
        ttk.Button(button_frame, text="記事更新", command=self.update_posts).grid(row=0, column=3, padx=5)
        ttk.Button(button_frame, text="新規作成", command=self.create_new_post).grid(row=0, column=4, padx=5)
        ttk.Button(button_frame, text="記事編集", command=self.edit_selected_post).grid(row=0, column=5, padx=5)
        ttk.Button(button_frame, text="記事削除", command=self.delete_selected_posts).grid(row=0, column=6, padx=5)
        ttk.Button(button_frame, text="本文取得", command=self.fetch_selected_posts_content).grid(row=0, column=7, padx=5)
        
        # ログ表示エリア
        log_frame = ttk.LabelFrame(main_frame, text="ログ", padding="5")
        log_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        self.log_text = tk.Text(log_frame, height=10, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        # グリッドの設定
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        remote_tab.columnconfigure(0, weight=1)
        remote_tab.rowconfigure(0, weight=1)
        local_tab.columnconfigure(0, weight=1)
        local_tab.rowconfigure(0, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def setup_logging(self):
        """ログ設定"""
        class QueueHandler(logging.Handler):
            def __init__(self, queue):
                super().__init__()
                self.queue = queue
            
            def emit(self, record):
                self.queue.put(record)
        
        # ルートロガーにキューハンドラを追加
        queue_handler = QueueHandler(self.log_queue)
        queue_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        
    def check_log_queue(self):
        """ログキューをチェックして表示を更新"""
        while True:
            try:
                record = self.log_queue.get_nowait()
                msg = self.format_log_record(record)
                self.log_text.insert(tk.END, msg + '\n')
                self.log_text.see(tk.END)
            except queue.Empty:
                break
        self.root.after(100, self.check_log_queue)
        
    def format_log_record(self, record):
        """ログレコードをフォーマット"""
        if record.levelno >= logging.ERROR:
            return f"エラー: {record.getMessage()}"
        elif record.levelno >= logging.WARNING:
            return f"警告: {record.getMessage()}"
        else:
            return record.getMessage()
        
    def clear_log(self):
        """ログをクリア"""
        self.log_text.delete(1.0, tk.END)
        
    def update_progress(self, message):
        """進捗状況をログに表示"""
        # 最後の行が進捗表示だった場合は上書き
        last_line = self.log_text.get("end-2l", "end-1l")
        if last_line.startswith("取得中:") or "の記事を取得中:" in last_line:
            self.log_text.delete("end-2l", "end-1l")
        
        # 新しい進捗メッセージを表示
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def run_in_thread(self, func):
        """関数をバックグラウンドスレッドで実行"""
        def wrapper():
            try:
                func()
            except Exception as e:
                logging.error(str(e))
            finally:
                # 両方のリストを更新
                self.update_remote_list()
                self.update_local_list()
                
        thread = threading.Thread(target=wrapper)
        thread.daemon = True
        thread.start()
        
    def on_remote_tree_click(self, event):
        """リモート記事一覧のクリックイベント処理"""
        region = self.remote_posts_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.remote_posts_tree.identify_column(event.x)
            item = self.remote_posts_tree.identify_row(event.y)
            
            # チェックボックス列がクリックされた場合
            if column == "#1" and item:
                index = self.remote_posts_tree.index(item)
                post_id = self.get_remote_post_id_by_index(index)
                
                if post_id is not None:
                    # チェック状態を切り替え
                    current_check = self.selected_remote_posts.get(post_id, False)
                    self.selected_remote_posts[post_id] = not current_check
                    
                    # 表示を更新
                    check_mark = "✓" if self.selected_remote_posts[post_id] else ""
                    values = list(self.remote_posts_tree.item(item, "values"))
                    values[0] = check_mark
                    self.remote_posts_tree.item(item, values=values)
                    
                    # ログに表示
                    post_title = values[3]
                    action = "選択" if self.selected_remote_posts[post_id] else "選択解除"
                    self.log_text.insert(tk.END, f"記事を{action}: {post_title}\n")
                    self.log_text.see(tk.END)

    def on_local_tree_click(self, event):
        """ローカル記事一覧のクリックイベント処理"""
        region = self.local_posts_tree.identify("region", event.x, event.y)
        if region == "cell":
            column = self.local_posts_tree.identify_column(event.x)
            item = self.local_posts_tree.identify_row(event.y)
            
            # チェックボックス列がクリックされた場合
            if column == "#1" and item:
                index = self.local_posts_tree.index(item)
                post_id = self.get_local_post_id_by_index(index)
                
                if post_id is not None:
                    # チェック状態を切り替え
                    current_check = self.selected_local_posts.get(post_id, False)
                    self.selected_local_posts[post_id] = not current_check
                    
                    # 表示を更新
                    check_mark = "✓" if self.selected_local_posts[post_id] else ""
                    values = list(self.local_posts_tree.item(item, "values"))
                    values[0] = check_mark
                    self.local_posts_tree.item(item, values=values)
                    
                    # ログに表示
                    post_title = values[3]
                    action = "選択" if self.selected_local_posts[post_id] else "選択解除"
                    self.log_text.insert(tk.END, f"記事を{action}: {post_title}\n")
                    self.log_text.see(tk.END)

    def get_remote_post_id_by_index(self, index):
        """リモート記事の行インデックスから記事IDを取得"""
        try:
            posts = self.automation.db.get_post_list(include_content=True)
            if 0 <= index < len(posts):
                return posts[index]['id']
        except Exception as e:
            logging.error(f"記事ID取得中にエラー: {str(e)}")
        return None

    def get_local_post_id_by_index(self, index):
        """ローカル記事の行インデックスから記事IDを取得"""
        try:
            posts = self.automation.db.get_local_posts()
            if 0 <= index < len(posts):
                return posts[index]['id']
        except Exception as e:
            logging.error(f"記事ID取得中にエラー: {str(e)}")
        return None
        
    def select_all_posts(self):
        """全ての記事を選択"""
        # すべての行を選択状態にする
        for item in self.remote_posts_tree.get_children():
            index = self.remote_posts_tree.index(item)
            post_id = self.get_remote_post_id_by_index(index)
            
            if post_id is not None:
                self.selected_remote_posts[post_id] = True
                
                # 表示を更新
                values = list(self.remote_posts_tree.item(item, "values"))
                values[0] = "✓"  # チェックマーク
                self.remote_posts_tree.item(item, values=values)
        
        self.log_text.insert(tk.END, "全ての記事を選択しました\n")
        self.log_text.see(tk.END)
        
    def deselect_all_posts(self):
        """全ての記事の選択を解除"""
        # すべての行の選択を解除
        for item in self.remote_posts_tree.get_children():
            index = self.remote_posts_tree.index(item)
            post_id = self.get_remote_post_id_by_index(index)
            
            if post_id is not None:
                self.selected_remote_posts[post_id] = False
                
                # 表示を更新
                values = list(self.remote_posts_tree.item(item, "values"))
                values[0] = ""  # チェックマークを削除
                self.remote_posts_tree.item(item, values=values)
        
        self.log_text.insert(tk.END, "全ての記事の選択を解除しました\n")
        self.log_text.see(tk.END)
        
    def get_selected_post_ids(self):
        """選択されている記事IDのリストを取得"""
        return [post_id for post_id, selected in self.selected_remote_posts.items() if selected]
        
    def fetch_posts_list_only(self):
        """記事一覧のみを取得する（内容は取得しない）"""
        try:
            # 月数を設定（デフォルト12ヶ月）
            months = 12
            if hasattr(self, 'months_var'):
                try:
                    months = int(self.months_var.get())
                except:
                    pass
            
            # メッセージ
            self.log_text.insert(tk.END, f"過去{months}ヶ月分の記事一覧を取得します...\n")
            self.log_text.see(tk.END)
            
            # 進捗コールバック関数
            def progress_callback(current_month, total_posts, current_page=None, month_str=None):
                msg = f"記事一覧取得中: "
                if month_str:
                    msg += f"{month_str} "
                else:
                    msg += f"{current_month}ヶ月目 "
                    
                if current_page:
                    msg += f"ページ{current_page} "
                    
                msg += f"/ 取得済み: {total_posts}件"
                
                # GUIスレッドで実行
                self.root.after(0, lambda: self.update_progress(msg))
                return True
            
            # ログイン情報の取得
            load_dotenv()
            username = os.getenv("AMEBA_USERNAME")
            password = os.getenv("AMEBA_PASSWORD")
            
            if not username or not password:
                messagebox.showerror("エラー", "環境変数にAMEBA_USERNAMEとAMEBA_PASSWORDを設定してください。")
                return
            
            # 別スレッドで実行
            def fetch_task():
                try:
                    # 記事を取得
                    posts = self.automation.get_blog_posts(
                        max_months=months,
                        progress_callback=progress_callback
                    )
                    
                    # 完了メッセージ
                    if not posts:
                        self.root.after(0, lambda: self.log_text.insert(tk.END, f"記事一覧取得完了: 記事が見つかりませんでした。\n"))
                        self.root.after(0, lambda: messagebox.showinfo("情報", f"過去{months}ヶ月分の記事は見つかりませんでした。"))
                    else:
                        # データベースに保存
                        from .database import AmebaDatabase
                        db = AmebaDatabase()
                        db.add_posts_to_list(posts)
                        
                        self.root.after(0, lambda: self.log_text.insert(tk.END, f"記事一覧取得完了: {len(posts)}件の記事をデータベースに保存しました。\n"))
                    
                    # 記事一覧を更新
                    self.root.after(0, self.update_remote_list)
                    
                except Exception as e:
                    error_msg = str(e)
                    self.root.after(0, lambda: self.log_text.insert(tk.END, f"エラー: {error_msg}\n"))
                    self.root.after(0, lambda: messagebox.showerror("エラー", f"記事一覧取得中にエラーが発生しました: {error_msg}"))
            
            # 別スレッドで実行
            threading.Thread(target=fetch_task, daemon=True).start()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"エラー: {str(e)}\n")
            self.log_text.see(tk.END)
            messagebox.showerror("エラー", f"記事一覧取得中にエラーが発生しました: {str(e)}")
            
    def fetch_year_posts_list_only(self):
        """特定の年の記事一覧のみを取得する（内容は取得しない）"""
        try:
            # 年を取得
            year = int(self.year_var.get())
            
            # メッセージ
            self.log_text.insert(tk.END, f"{year}年の記事一覧を取得します...\n")
            self.log_text.see(tk.END)
            
            # 進捗コールバック関数
            def progress_callback(current_month, total_posts, current_page=None, month_str=None):
                msg = f"{year}年の記事一覧取得中: "
                if month_str:
                    msg += f"{month_str} "
                else:
                    msg += f"{current_month}ヶ月目 "
                    
                if current_page:
                    msg += f"ページ{current_page} "
                    
                msg += f"/ 取得済み: {total_posts}件"
                
                # GUIスレッドで実行
                self.root.after(0, lambda: self.update_progress(msg))
                return True
            
            # 記事を取得（内容は取得しない）
            remote_posts, _ = self.automation.fetch_blog_posts(
                max_months=12,
                progress_callback=progress_callback,
                target_year=year
            )
            
            # 完了メッセージ
            if len(remote_posts) == 0:
                self.log_text.insert(tk.END, f"記事一覧取得完了: {year}年の記事は見つかりませんでした。\n")
                messagebox.showinfo("情報", f"{year}年の記事は見つかりませんでした。")
            else:
                self.log_text.insert(tk.END, f"記事一覧取得完了: {len(remote_posts)}件\n")
            
            self.log_text.see(tk.END)
            
            # 記事一覧を更新
            self.update_remote_list()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"エラー: {str(e)}\n")
            self.log_text.see(tk.END)
            messagebox.showerror("エラー", f"記事一覧取得中にエラーが発生しました: {str(e)}")
            
    def fetch_selected_posts_content(self):
        """選択された記事の本文を取得する"""
        selected_ids = self.get_selected_post_ids()
        if not selected_ids:
            self.log_text.insert(tk.END, "記事が選択されていません\n")
            self.log_text.see(tk.END)
            return
            
        # 進捗ダイアログを表示
        progress_dialog = tk.Toplevel(self.root)
        progress_dialog.title("記事本文取得中")
        progress_dialog.geometry("400x150")
        progress_dialog.transient(self.root)
        progress_dialog.grab_set()
        
        # 進捗メッセージ
        message_label = ttk.Label(progress_dialog, text="選択された記事の本文を取得しています...")
        message_label.pack(pady=10)
        
        # 進捗バー
        progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(progress_dialog, variable=progress_var, maximum=len(selected_ids))
        progress_bar.pack(fill='x', padx=20, pady=10)
        
        # 現在処理中の記事タイトル
        current_title_var = tk.StringVar(value="準備中...")
        current_title_label = ttk.Label(progress_dialog, textvariable=current_title_var)
        current_title_label.pack(pady=5)
        
        # キャンセルボタン
        cancel_button = ttk.Button(progress_dialog, text="キャンセル", command=progress_dialog.destroy)
        cancel_button.pack(pady=10)
        
        # 別スレッドで記事取得を実行
        def fetch_content_task():
            try:
                total = len(selected_ids)
                success_count = 0
                error_count = 0
                
                for i, post_id in enumerate(selected_ids):
                    try:
                        # 記事情報を取得
                        post = self.automation.db.get_post_list_item(post_id)
                        if not post:
                            continue
                            
                        # 進捗更新
                        title = post.get('title', f'記事ID: {post_id}')
                        self.root.after(0, lambda: current_title_var.set(f"取得中: {title}"))
                        self.root.after(0, lambda i=i: progress_var.set(i+1))
                        
                        # 記事本文を取得
                        if post.get('edit_url'):
                            content_data = self.automation.get_post_content(post['edit_url'])
                            if content_data and isinstance(content_data, dict):
                                # データベースに保存
                                content = content_data.get('content', '')
                                if content:
                                    self.automation.db.add_post_content(post_id, post['title'], content)
                                    success_count += 1
                                    self.log_text.insert(tk.END, f"記事「{title}」の本文を取得しました\n")
                                else:
                                    error_count += 1
                                    self.log_text.insert(tk.END, f"記事「{title}」の本文が空でした\n")
                            else:
                                error_count += 1
                                self.log_text.insert(tk.END, f"記事「{title}」の本文取得に失敗しました\n")
                        else:
                            error_count += 1
                            self.log_text.insert(tk.END, f"記事「{title}」の編集URLがありません\n")
                    except Exception as e:
                        error_count += 1
                        self.log_text.insert(tk.END, f"エラー: {str(e)}\n")
                        self.log_text.see(tk.END)
                
                # 完了メッセージ
                self.root.after(0, lambda: current_title_var.set(f"完了: 成功={success_count}, 失敗={error_count}"))
                self.log_text.insert(tk.END, f"記事本文取得完了: 成功={success_count}, 失敗={error_count}\n")
                self.log_text.see(tk.END)
                
                # 記事一覧を更新
                self.root.after(1000, self.update_remote_list)
                
                # ダイアログを閉じる
                self.root.after(2000, progress_dialog.destroy)
                
            except Exception as e:
                self.log_text.insert(tk.END, f"予期せぬエラーが発生しました: {str(e)}\n")
                self.log_text.see(tk.END)
                progress_dialog.destroy()
        
        # 別スレッドで実行
        threading.Thread(target=fetch_content_task, daemon=True).start()
            
    def post_selected(self):
        """選択した記事を投稿"""
        selection = self.posts_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "記事が選択されていません")
            return
            
        post_id = self.posts_tree.index(selection[0])
        
        if not check_chrome_running():
            if not self.confirm_chrome_warning():
                return
                
        try:
            self.automation.post_to_ameba(post_id)
            messagebox.showinfo("完了", "記事を投稿しました")
        except Exception as e:
            messagebox.showerror("エラー", f"投稿に失敗しました: {str(e)}")
            
    def edit_selected(self):
        """選択した記事を編集"""
        selection = self.posts_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "記事が選択されていません")
            return
            
        post_id = self.posts_tree.index(selection[0])
        post = self.automation.db.get_local_post(post_id)
        
        # 編集ダイアログを表示
        dialog = tk.Toplevel(self.root)
        dialog.title("記事を編集")
        dialog.transient(self.root)
        
        # タイトル
        ttk.Label(dialog, text="タイトル:").grid(row=0, column=0, sticky=tk.W)
        title_var = tk.StringVar(value=post['title'])
        title_entry = ttk.Entry(dialog, textvariable=title_var, width=60)
        title_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # 本文
        ttk.Label(dialog, text="本文:").grid(row=1, column=0, sticky=tk.W)
        content_text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, 
                                               width=60, height=20)
        content_text.grid(row=1, column=1, padx=5, pady=5)
        content_text.insert(tk.END, post['content'])
        
        def save_changes():
            new_title = title_var.get()
            new_content = content_text.get(1.0, tk.END).strip()
            
            if not new_title:
                messagebox.showwarning("警告", "タイトルを入力してください")
                return
                
            if not new_content:
                messagebox.showwarning("警告", "本文を入力してください")
                return
                
            try:
                self.automation.edit_post(post_id, new_title, new_content)
                messagebox.showinfo("完了", "記事を更新しました")
                dialog.destroy()
                self.update_remote_list()
            except Exception as e:
                messagebox.showerror("エラー", f"更新に失敗しました: {str(e)}")
                
        # ボタン
        button_frame = ttk.Frame(dialog, padding="5")
        button_frame.grid(row=2, column=0, columnspan=2)
        
        ttk.Button(button_frame, text="保存",
                  command=save_changes).grid(row=0, column=0, padx=5)
        ttk.Button(button_frame, text="キャンセル",
                  command=dialog.destroy).grid(row=0, column=1, padx=5)
        
    def export_selected_post(self):
        """選択した記事をエクスポート"""
        selection = self.posts_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "記事が選択されていません")
            return
            
        # 選択した行のインデックスを取得
        index = self.posts_tree.index(selection[0])
        
        # 記事一覧から該当する記事を取得
        posts = self.automation.db.get_post_list(include_content=True)
        if index < len(posts):
            post = posts[index]
            
            # ローカル記事IDを取得
            post_id = post.get('local_post_id', post.get('id', -1))
            
            if post_id == -1:
                messagebox.showwarning("警告", "エクスポートできる記事ではありません")
                return
                
            # エクスポート処理
            filename = f"post_{post_id}.txt"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {post.get('title', '')}\n")
                    f.write(f"Date: {post.get('date', post.get('created_at', ''))}\n\n")
                    f.write(post.get('content', ''))
                messagebox.showinfo("完了", f"記事を {filename} にエクスポートしました")
            except Exception as e:
                messagebox.showerror("エラー", f"エクスポートに失敗しました: {str(e)}")
            
    def confirm_chrome_warning(self):
        """Chromeの警告を表示して確認"""
        message = """
        ⚠️ 警告: Chromeブラウザが見つかりません
        
        このツールを使用するには、Chromeブラウザを特定のモードで起動する必要があります。
        
        以下の手順でChromeを起動してください：
        1. すべてのChromeウィンドウを閉じる
        2. コマンドプロンプトを起動して以下のコマンドを実行：
           chrome.exe --remote-debugging-port=9222
           または
           "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
        
        ※ Chromeが起動したら、ブラウザウィンドウは閉じずに開いたままにしておいてください。
        ※ 最初のアクセス時には必要に応じて手動でログインしてください。
        
        続行しますか？
        """
        return messagebox.askyesno("警告", message, icon='warning')

    def create_content_view(self):
        """記事内容表示エリアを作成"""
        # このメソッドはsetup_guiメソッド内で直接実装しました
        pass

    def on_post_select(self, event):
        """記事が選択されたときの処理"""
        selection = self.posts_tree.selection()
        if not selection:
            return
        
        # 選択した行のインデックスを取得
        index = self.posts_tree.index(selection[0])
        
        # 記事一覧から該当する記事を取得
        posts = self.automation.db.get_post_list(include_content=True)
        if index < len(posts):
            post = posts[index]
            
            # タイトルと本文を設定
            self.title_var.set(post.get('title', ''))
            self.content_text.delete(1.0, tk.END)
            self.content_text.insert(tk.END, post.get('content', ''))
            
            # 現在選択中の記事IDを保存
            self.current_post_id = post.get('local_post_id', post.get('id', -1))
            self.current_is_remote = 'url' in post and post['url']
            
            # 状態を表示
            status = "投稿済" if post.get('posted') or post.get('status') == '投稿済' else "未投稿"
            self.log_text.insert(tk.END, f"記事を選択: [{status}] {post.get('title')}\n")
            self.log_text.see(tk.END)

    def update_remote_list(self):
        """リモート記事一覧を更新"""
        try:
            # リモート記事一覧をクリア
            for item in self.remote_posts_tree.get_children():
                self.remote_posts_tree.delete(item)
            
            # 記事一覧を取得
            posts = self.automation.db.get_post_list(include_content=True)
            
            if not posts:
                self.log_text.insert(tk.END, "リモート記事がありません。「記事取得」ボタンを押して記事を取得してください。\n")
                self.log_text.see(tk.END)
                return
            
            # 記事一覧を表示
            for post in posts:
                # 選択状態を取得
                check_mark = "✓" if self.selected_remote_posts.get(post['id'], False) else ""
                
                # ローカル編集の有無
                has_local = "あり" if self.automation.db.has_local_edit(post['id']) else ""
                
                # 記事の状態
                status = post.get('status', '未取得')
                
                # 日付フォーマットを整える
                date = post.get('date', '')
                if not date and 'created_at' in post:
                    date = post['created_at'].split()[0] if ' ' in post['created_at'] else post['created_at']
                
                # TreeViewに追加
                self.remote_posts_tree.insert("", tk.END, values=(
                    check_mark,
                    date,
                    status,
                    post['title'],
                    has_local
                ))
            
            self.log_text.insert(tk.END, f"リモート記事一覧を更新しました（{len(posts)}件）\n")
            self.log_text.see(tk.END)
            
        except Exception as e:
            self.log_text.insert(tk.END, f"リモート記事一覧の更新中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"リモート記事一覧の更新中にエラー: {str(e)}")

    def update_local_list(self):
        """ローカル記事一覧を更新"""
        try:
            # ローカル記事一覧をクリア
            for item in self.local_posts_tree.get_children():
                self.local_posts_tree.delete(item)
            
            # 記事一覧を取得
            posts = self.automation.db.get_local_posts()
            
            if not posts:
                self.log_text.insert(tk.END, "ローカル記事がありません。「新規作成」ボタンを押して記事を作成してください。\n")
                self.log_text.see(tk.END)
                return
            
            # 記事一覧を表示
            for post in posts:
                # 選択状態を取得
                check_mark = "✓" if self.selected_local_posts.get(post['id'], False) else ""
                
                # リモート連携状態
                remote_sync = "あり" if post.get('remote_id') else "なし"
                
                # 日付フォーマットを整える
                date = post.get('date', '')
                if not date and 'created_at' in post:
                    date = post['created_at'].split()[0] if ' ' in post['created_at'] else post['created_at']
                
                # TreeViewに追加
                self.local_posts_tree.insert("", tk.END, values=(
                    check_mark,
                    date,
                    post.get('status', '編集中'),
                    post['title'],
                    remote_sync
                ))
            
            self.log_text.insert(tk.END, f"ローカル記事一覧を更新しました（{len(posts)}件）\n")
            self.log_text.see(tk.END)
            
        except Exception as e:
            self.log_text.insert(tk.END, f"ローカル記事一覧の更新中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"ローカル記事一覧の更新中にエラー: {str(e)}")

    def fetch_posts(self):
        """選択された記事の内容を取得"""
        selected_ids = self.get_selected_post_ids()
        if not selected_ids:
            self.log_text.insert(tk.END, "記事が選択されていません\n")
            self.log_text.see(tk.END)
            return
        
        try:
            for post_id in selected_ids:
                self.automation.fetch_post_content(post_id)
                self.log_text.insert(tk.END, f"記事ID {post_id} の内容を取得しました\n")
                self.log_text.see(tk.END)
            
            # 記事一覧を更新
            self.update_remote_list()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"記事内容の取得中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"記事内容の取得中にエラー: {str(e)}")

    def create_new_post(self):
        """新規記事を作成"""
        try:
            # 新規記事をデータベースに追加
            post_id = self.automation.db.create_local_post()
            
            # エディタで開く
            self.automation.open_editor(post_id)
            
            # 記事一覧を更新
            self.update_local_list()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"新規記事の作成中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"新規記事の作成中にエラー: {str(e)}")

    def edit_selected_post(self):
        """選択された記事を編集"""
        # 現在のタブを確認
        current_tab = self.tab_control.select()
        tab_id = self.tab_control.index(current_tab)
        
        try:
            if tab_id == 0:  # リモートタブ
                selected_ids = self.get_selected_post_ids()
                if not selected_ids:
                    self.log_text.insert(tk.END, "記事が選択されていません\n")
                    self.log_text.see(tk.END)
                    return
                
                # 最初に選択された記事のみを編集
                post_id = selected_ids[0]
                
                # 記事内容を取得（まだ取得していない場合）
                if not self.automation.db.has_content(post_id):
                    self.automation.fetch_post_content(post_id)
                
                # エディタで開く
                self.automation.open_editor(post_id)
                
            else:  # ローカルタブ
                selected_ids = [post_id for post_id, selected in self.selected_local_posts.items() if selected]
                if not selected_ids:
                    self.log_text.insert(tk.END, "記事が選択されていません\n")
                    self.log_text.see(tk.END)
                    return
                
                # 最初に選択された記事のみを編集
                post_id = selected_ids[0]
                
                # エディタで開く
                self.automation.open_editor(post_id)
            
        except Exception as e:
            self.log_text.insert(tk.END, f"記事の編集中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"記事の編集中にエラー: {str(e)}")

    def delete_selected_posts(self):
        """選択された記事を削除"""
        # 現在のタブを確認
        current_tab = self.tab_control.select()
        tab_id = self.tab_control.index(current_tab)
        
        try:
            if tab_id == 0:  # リモートタブ
                selected_ids = self.get_selected_post_ids()
            else:  # ローカルタブ
                selected_ids = [post_id for post_id, selected in self.selected_local_posts.items() if selected]
            
            if not selected_ids:
                self.log_text.insert(tk.END, "記事が選択されていません\n")
                self.log_text.see(tk.END)
                return
            
            # 確認ダイアログを表示
            if not messagebox.askyesno("確認", "選択された記事を削除しますか？"):
                return
            
            # 記事を削除
            for post_id in selected_ids:
                if tab_id == 0:
                    self.automation.db.delete_post(post_id)
                else:
                    self.automation.db.delete_local_post(post_id)
                self.log_text.insert(tk.END, f"記事ID {post_id} を削除しました\n")
                self.log_text.see(tk.END)
            
            # 記事一覧を更新
            if tab_id == 0:
                self.update_remote_list()
            else:
                self.update_local_list()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"記事の削除中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"記事の削除中にエラー: {str(e)}")

    def update_posts(self):
        """記事一覧を更新"""
        try:
            # 現在のタブを確認
            current_tab = self.tab_control.select()
            tab_id = self.tab_control.index(current_tab)
            
            if tab_id == 0:  # リモートタブ
                self.update_remote_list()
            else:  # ローカルタブ
                self.update_local_list()
                
            self.log_text.insert(tk.END, "記事一覧を更新しました\n")
            self.log_text.see(tk.END)
            
        except Exception as e:
            self.log_text.insert(tk.END, f"記事一覧の更新中にエラー: {str(e)}\n")
            self.log_text.see(tk.END)
            logging.error(f"記事一覧の更新中にエラー: {str(e)}")

def main():
    """アプリケーションのエントリーポイント"""
    try:
        root = tk.Tk()
        app = AmebaGUI(root)
        root.mainloop()
    except Exception as e:
        logger.error(f"アプリケーションの起動に失敗: {str(e)}")
        messagebox.showerror("エラー", f"アプリケーションの起動に失敗しました\n\n{str(e)}")
        raise

if __name__ == "__main__":
    main() 