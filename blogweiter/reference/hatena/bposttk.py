import tkinter as tk
from tkinter import filedialog
import csv
import re
from gapi import generate_content
import pdb
from imagec import generate_and_save_image

class BlogPostApp:
    def __init__(self, master):
        self.master = master
        master.title('画像付きブログ投稿システム')

        # CSV file selection button
        self.csv_button = tk.Button(master, text='CSVファイルを選択', command=self.select_csv_file)
        self.csv_button.pack(pady=10)

        # Content generation button
        self.generate_button = tk.Button(master, text='コンテンツ生成', command=self.process_csv)
        self.generate_button.pack(pady=10)

        # Define the common instruction prompt
        self.common_instruction = (
            "ブログ記事を2000字で書きたい、口調を合わせて。実際に機能するように過去記事の関連リンクURLもつけて、"
            "タイトルと、画像生成ＡＩ用Imagecreator用のプロンプトも書いて（最後に、minitureをつけること）。"
            "適当な商品アフェリエイトを探して、名前で挿入すること（書式は【品名】）。"
            "最後に懇願するような、リンク登録とyoutubeチャンネルへの登録要請も書いて。"
            "イベント参加はリンク先のfacebookからメッセージください。"
            "```Imagecreator用プロンプト：   ここに書くこと```"
        )

    def select_csv_file(self):
        self.csv_file_path = filedialog.askopenfilename(filetypes=[('CSV files', '*.csv')])
        print(f'Selected CSV file: {self.csv_file_path}')

    def process_csv(self):
        if not hasattr(self, 'csv_file_path'):
            print('CSVファイルが選択されていません。')
            return

        try:
            with open(self.csv_file_path, newline='', encoding='shift_jis') as csvfile:
                csvreader = csv.reader(csvfile)
                for row in csvreader:
                    prompt = row[0]  # Assuming the prompt is in the first column
                    full_prompt = self.common_instruction + "#以下がブログのテーマ\n " + prompt
                    self.generate_content(full_prompt)
        except UnicodeDecodeError as e:
            print(f'Encoding error: {e}')

    def generate_content(self, prompt):
        markdown_content = self.generate_content_from_gpt(prompt)
        if markdown_content is None:
            print(f'Failed to generate content for prompt: {prompt}')
            return
        pdb.set_trace()
        
        image_prompts = self.extract_image_prompts(markdown_content)
        image_urls = [self.upload_image(self.generate_and_save_image(p)) for p in image_prompts]
        final_markdown = self.embed_images(markdown_content, image_urls)
        self.save_markdown(final_markdown, prompt)

    def generate_content_from_gpt(self, prompt):
        return generate_content(prompt)

    def extract_image_prompts(self, markdown):
        # Use regex to extract image prompts
        pattern = rpattern = r'Imagecreator.*?\n(.*)'
        matches = re.findall(pattern, markdown, re.DOTALL)
        return matches

    def generate_and_save_image(self, prompt):
        return generate_and_save_image(prompt)
        # Generate and save image, return file path

    def upload_image(self, image_path):
        # Upload image to Google Cloud and return URL
        pass

    def embed_images(self, markdown, image_urls):
        # Embed image URLs in the Markdown content
        pass

    def save_markdown(self, markdown):
        # Save the final Markdown content to a file
        pass

root = tk.Tk()
app = BlogPostApp(root)
root.mainloop()