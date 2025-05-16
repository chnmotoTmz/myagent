import PySimpleGUI as sg
from logger import log_debug
import os
from dotenv import load_dotenv
from datetime import datetime
import json
from rss_reader import RSSReader

class BlogManagerGUI:
    def __init__(self):
        # テーマの設定
        sg.theme('LightBlue2')
        
        # 環境変数の読み込み
        load_dotenv()
        
        # 設定の初期化
        self.config = {
            'hatena_id': os.getenv('HATENA_ID', ''),
            'blog_domain': os.getenv('BLOG_DOMAIN', ''),
            'api_key': os.getenv('HATENA_BLOG_ATOMPUB_KEY', '')
        }
        
        # インポート済み記事の保存用
        self.imported_entries = []
        
        self.rss_reader = RSSReader()
        
    def create_settings_layout(self):
        return [
            [sg.Text('RSSフィード設定', font=('Helvetica', 16))],
            [sg.Text('フィード一覧：')],
            [sg.Multiline(''.join(f"- {url}\n" for urls in self.rss_reader.feeds.values() for url in urls),
                         size=(50, 5), disabled=True)],
            [sg.Button('フィード更新', key='-UPDATE_FEEDS-')]
        ]

    def create_import_layout(self):
        return [
            [sg.Text('記事インポート', font=('Helvetica', 16))],
            [sg.Button('記事を取得', key='-IMPORT-'), 
             sg.Button('選択した記事を保存', key='-SAVE_SELECTED-')],
            [sg.Table(
                values=[],
                headings=['タイトル', '作成日時', 'カテゴリー', 'タグ', 'プラットフォーム'],
                auto_size_columns=True,
                display_row_numbers=True,
                justification='left',
                num_rows=15,
                key='-TABLE-',
                enable_events=True,
                select_mode=sg.TABLE_SELECT_MODE_EXTENDED
            )]
        ]

    def create_filter_layout(self):
        return [
            [sg.Text('フィルター', font=('Helvetica', 16))],
            [sg.Text('キーワード:', size=(10, 1)), 
             sg.Input(key='-FILTER_KEYWORD-', size=(30, 1)), 
             sg.Button('検索', key='-SEARCH-')],
            [sg.Text('カテゴリー:', size=(10, 1)), 
             sg.Combo([], key='-FILTER_CATEGORY-', size=(30, 1), enable_events=True)],
            [sg.Text('タグ:', size=(10, 1)), 
             sg.Combo([], key='-FILTER_TAG-', size=(30, 1), enable_events=True)],
            [sg.Text('プラットフォーム:', size=(10, 1)),
             sg.Combo(['全て', 'hatena', 'ameblo'], default_value='全て',
                     key='-FILTER_PLATFORM-', size=(30, 1), enable_events=True)]
        ]

    def create_layout(self):
        return [
            [sg.TabGroup([[
                sg.Tab('設定', self.create_settings_layout()),
                sg.Tab('インポート', self.create_import_layout()),
                sg.Tab('フィルター', self.create_filter_layout())
            ]])],
            [sg.Text('', key='-STATUS-', size=(60, 1))]
        ]

    def import_entries(self, window):
        try:
            entries = self.rss_reader.get_entries()
            self.imported_entries = entries
            
            table_data = [
                [
                    entry['title'],
                    entry['created_at'].strftime('%Y-%m-%d %H:%M'),
                    entry['category'],
                    ', '.join(entry['tags']),
                    entry['platform']
                ]
                for entry in entries
            ]
            
            window['-TABLE-'].update(values=table_data)
            
            # カテゴリーとタグの更新
            categories = sorted(list(set(entry['category'] for entry in entries)))
            tags = sorted(list(set(tag for entry in entries for tag in entry['tags'])))
            
            window['-FILTER_CATEGORY-'].update(values=['全て'] + categories)
            window['-FILTER_TAG-'].update(values=['全て'] + tags)
            
            stats = self.rss_reader.get_feed_stats()
            window['-STATUS-'].update(
                f"合計: {stats['total_entries']}記事 "
                f"(はてな: {stats['hatena_entries']}, "
                f"アメブロ: {stats['ameblo_entries']})"
            )
            
        except Exception as e:
            sg.popup_error(f'エラーが発生しました: {str(e)}')

    def save_selected_entries(self, window, selected_rows):
        if not selected_rows:
            sg.popup_warning('記事が選択されていません')
            return
            
        save_path = sg.popup_get_folder('保存先フォルダを選択してください')
        if not save_path:
            return
            
        try:
            selected_entries = [self.imported_entries[row] for row in selected_rows]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            for entry in selected_entries:
                filename = f"{entry['title'].replace('/', '_')}_{timestamp}.json"
                filepath = os.path.join(save_path, filename)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(entry, f, ensure_ascii=False, indent=2, default=str)
            
            window['-STATUS-'].update(f'{len(selected_entries)}件の記事を保存しました')
            
        except Exception as e:
            sg.popup_error(f'保存中にエラーが発生しました: {str(e)}')

    def filter_entries(self, window, values):
        if not self.imported_entries:
            return
            
        keyword = values['-FILTER_KEYWORD-'].lower()
        category = values['-FILTER_CATEGORY-']
        tag = values['-FILTER_TAG-']
        platform = values['-FILTER_PLATFORM-']
        
        filtered_entries = self.imported_entries
        
        if keyword:
            filtered_entries = [
                entry for entry in filtered_entries
                if keyword in entry['title'].lower() or
                   keyword in entry['content'].lower()
            ]
            
        if category and category != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if entry['category'] == category
            ]
            
        if tag and tag != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if tag in entry['tags']
            ]
            
        if platform and platform != '全て':
            filtered_entries = [
                entry for entry in filtered_entries
                if entry['platform'] == platform
            ]
            
        table_data = [
            [
                entry['title'],
                entry['created_at'].strftime('%Y-%m-%d %H:%M'),
                entry['category'],
                ', '.join(entry['tags']),
                entry['platform']
            ]
            for entry in filtered_entries
        ]
        
        window['-TABLE-'].update(values=table_data)
        window['-STATUS-'].update(f'{len(filtered_entries)}件の記事が見つかりました')

    def run(self):
        window = sg.Window('ブログコンテンツ管理システム', self.create_layout(), resizable=True)
        
        while True:
            event, values = window.read()
            
            if event == sg.WIN_CLOSED:
                break
                
            elif event == '-IMPORT-':
                self.import_entries(window)
                
            elif event == '-SAVE_SELECTED-':
                selected_rows = [row for row in values['-TABLE-']]
                self.save_selected_entries(window, selected_rows)
                
            elif event in ['-SEARCH-', '-FILTER_CATEGORY-', '-FILTER_TAG-', '-FILTER_PLATFORM-']:
                self.filter_entries(window, values)
        
        window.close()

if __name__ == '__main__':
    app = BlogManagerGUI()
    app.run()
