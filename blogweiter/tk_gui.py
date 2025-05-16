import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from tkinter import filedialog
from datetime import datetime
import json
import os
from rss_reader import RSSReader

class BlogManagerTk:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('ブログコンテンツ管理システム')
        self.root.geometry('1200x800')
        
        self.rss_reader = RSSReader()
        self.imported_entries = []
        
        self._create_widgets()
        
    def _create_widgets(self):
        # タブコントロール
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # 設定タブ
        self.settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_frame, text='設定')
        
        # フィード一覧
        ttk.Label(self.settings_frame, text='RSSフィード設定', font=('Helvetica', 16)).pack(pady=5)
        ttk.Label(self.settings_frame, text='フィード一覧：').pack(pady=5)
        
        self.feed_text = tk.Text(self.settings_frame, height=10, width=60)
        self.feed_text.pack(pady=5)
        self.feed_text.insert('1.0', ''.join(f"- {url}\n" for urls in self.rss_reader.feeds.values() for url in urls))
        self.feed_text.configure(state='disabled')
        
        ttk.Button(self.settings_frame, text='フィード更新', command=self._update_feeds).pack(pady=5)
        
        # インポートタブ
        self.import_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.import_frame, text='インポート')
        
        # ボタンフレーム
        button_frame = ttk.Frame(self.import_frame)
        button_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(button_frame, text='記事を取得', command=self._import_entries).pack(side='left', padx=5)
        ttk.Button(button_frame, text='選択した記事を保存', command=self._save_selected_entries).pack(side='left', padx=5)
        
        # テーブル
        columns = ('post_id', 'title', 'created_at', 'category', 'tags', 'platform', 'status')
        self.tree = ttk.Treeview(self.import_frame, columns=columns, show='headings')
        
        # 列の設定
        self.tree.heading('post_id', text='記事ID')
        self.tree.heading('title', text='タイトル')
        self.tree.heading('created_at', text='作成日時')
        self.tree.heading('category', text='カテゴリー')
        self.tree.heading('tags', text='タグ')
        self.tree.heading('platform', text='プラットフォーム')
        self.tree.heading('status', text='状態')
        
        # 列幅の設定
        self.tree.column('post_id', width=150)
        self.tree.column('title', width=300)
        self.tree.column('created_at', width=150)
        self.tree.column('category', width=100)
        self.tree.column('tags', width=200)
        self.tree.column('platform', width=100)
        self.tree.column('status', width=80)
        
        # スクロールバー
        scrollbar = ttk.Scrollbar(self.import_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # フィルタータブ
        self.filter_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.filter_frame, text='フィルター')
        
        # キーワード検索
        keyword_frame = ttk.Frame(self.filter_frame)
        keyword_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(keyword_frame, text='キーワード:').pack(side='left', padx=5)
        self.keyword_var = tk.StringVar()
        self.keyword_entry = ttk.Entry(keyword_frame, textvariable=self.keyword_var)
        self.keyword_entry.pack(side='left', padx=5)
        ttk.Button(keyword_frame, text='検索', command=self._filter_entries).pack(side='left', padx=5)
        
        # カテゴリー
        category_frame = ttk.Frame(self.filter_frame)
        category_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(category_frame, text='カテゴリー:').pack(side='left', padx=5)
        self.category_var = tk.StringVar()
        self.category_combo = ttk.Combobox(category_frame, textvariable=self.category_var)
        self.category_combo.pack(side='left', padx=5)
        self.category_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_entries())
        
        # タグ
        tag_frame = ttk.Frame(self.filter_frame)
        tag_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(tag_frame, text='タグ:').pack(side='left', padx=5)
        self.tag_var = tk.StringVar()
        self.tag_combo = ttk.Combobox(tag_frame, textvariable=self.tag_var)
        self.tag_combo.pack(side='left', padx=5)
        self.tag_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_entries())
        
        # プラットフォーム
        platform_frame = ttk.Frame(self.filter_frame)
        platform_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(platform_frame, text='プラットフォーム:').pack(side='left', padx=5)
        self.platform_var = tk.StringVar(value='全て')
        self.platform_combo = ttk.Combobox(platform_frame, textvariable=self.platform_var, 
                                         values=['全て', 'hatena', 'ameblo'])
        self.platform_combo.pack(side='left', padx=5)
        self.platform_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_entries())
        
        # 状態
        status_frame = ttk.Frame(self.filter_frame)
        status_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(status_frame, text='状態:').pack(side='left', padx=5)
        self.status_var = tk.StringVar(value='全て')
        self.status_combo = ttk.Combobox(status_frame, textvariable=self.status_var,
                                       values=['全て', 'published', 'draft', 'private'])
        self.status_combo.pack(side='left', padx=5)
        self.status_combo.bind('<<ComboboxSelected>>', lambda e: self._filter_entries())
        
        # ステータスバー
        self.status_var = tk.StringVar()
        self.status_label = ttk.Label(self.root, textvariable=self.status_var)
        self.status_label.pack(side='bottom', fill='x', padx=5, pady=5)
        
    def _update_feeds(self):
        try:
            entries = self.rss_reader.get_entries()
            self._update_table(entries)
            messagebox.showinfo('成功', 'フィードを更新しました')
        except Exception as e:
            messagebox.showerror('エラー', f'フィードの更新に失敗しました: {str(e)}')
    
    def _import_entries(self):
        try:
            entries = self.rss_reader.get_entries()
            self.imported_entries = entries
            self._update_table(entries)
            
            # カテゴリーとタグの更新
            categories = sorted(list(set(entry['meta']['category'] for entry in entries)))
            tags = sorted(list(set(tag for entry in entries for tag in entry['meta']['tags'])))
            
            self.category_combo['values'] = ['全て'] + categories
            self.tag_combo['values'] = ['全て'] + tags
            
            stats = self.rss_reader.get_feed_stats()
            self.status_var.set(
                f"合計: {stats['total_entries']}記事 "
                f"(はてな: {stats['hatena_entries']}, "
                f"アメブロ: {stats['ameblo_entries']})"
            )
            
        except Exception as e:
            messagebox.showerror('エラー', f'記事の取得に失敗しました: {str(e)}')
    
    def _update_table(self, entries):
        # テーブルをクリア
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # 新しいデータを追加
        for entry in entries:
            self.tree.insert('', 'end', values=(
                entry['post_id'],
                entry['meta']['title'],
                entry['created_at'],
                entry['meta']['category'],
                ', '.join(entry['meta']['tags']),
                entry['platform'],
                entry['status']
            ))
    
    def _save_selected_entries(self):
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning('警告', '記事が選択されていません')
            return
        
        save_path = filedialog.askdirectory(title='保存先フォルダを選択してください')
        if not save_path:
            return
        
        try:
            selected_entries = []
            for item in selected_items:
                values = self.tree.item(item)['values']
                for entry in self.imported_entries:
                    if entry['post_id'] == values[0]:
                        selected_entries.append(entry)
                        break
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            for entry in selected_entries:
                filename = f"{entry['post_id']}_{timestamp}.json"
                filepath = os.path.join(save_path, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, ensure_ascii=False, indent=2, default=str)
            
            self.status_var.set(f'{len(selected_entries)}件の記事を保存しました')
            
        except Exception as e:
            messagebox.showerror('エラー', f'保存中にエラーが発生しました: {str(e)}')
    
    def _filter_entries(self):
        if not self.imported_entries:
            return
        
        keyword = self.keyword_var.get().lower()
        category = self.category_var.get()
        tag = self.tag_var.get()
        platform = self.platform_var.get()
        status = self.status_var.get()
        
        filtered_entries = self.imported_entries
        
        if keyword:
            filtered_entries = [
                entry for entry in filtered_entries
                if keyword in entry['meta']['title'].lower() or
                   keyword in entry['content']['body'].lower()
            ]
        
        if category and category != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if entry['meta']['category'] == category
            ]
        
        if tag and tag != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if tag in entry['meta']['tags']
            ]
        
        if platform and platform != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if entry['platform'] == platform
            ]
            
        if status and status != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if entry['status'] == status
            ]
        
        self._update_table(filtered_entries)
        self.status_var.set(f'{len(filtered_entries)}件の記事が見つかりました')
    
    def run(self):
        self.root.mainloop()

if __name__ == '__main__':
    app = BlogManagerTk()
    app.run() 