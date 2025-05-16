import gradio as gr
import pandas as pd
from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.charfilter import UnicodeNormalizeCharFilter
from janome.tokenfilter import POSKeepFilter, POSStopFilter, LowerCaseFilter
from core import keitaiso,load_data_from_file
# 必要な追加の関数や定義（load_stopwords, NumericFilter, LengthLimitFilter, StopWordFilter, preprocess, load_data_from_file）をここに配置してください



def analyze_text(file):
    # ファイルからデータを読み込む
    df = load_data_from_file(file.name)
    texts = df['Column1'].tolist()

    # 形態素解析
    analyzed_texts = keitaiso(texts)

    # 結果を整形
    result = "\n\n".join([f"Original: {orig}\nAnalyzed: {anal}" for orig, anal in zip(texts, analyzed_texts)])

    return result

iface = gr.Interface(
    fn=analyze_text,
    inputs=gr.File(label="Upload file (CSV, TXT, or XLSX)"),
    outputs=gr.Textbox(label="Analysis Result", lines=20),
    title="Text Analysis Visualization",
    description="Upload a file to see the results of morphological analysis."
)

if __name__ == "__main__":
    iface.launch(share=False, server_name="0.0.0.0",server_port=7862,show_api=False)

