import pandas as pd
import numpy as np
import re
from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.charfilter import UnicodeNormalizeCharFilter
from janome.tokenfilter import POSKeepFilter, POSStopFilter, LowerCaseFilter
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import pickle
import pdb
import chardet
from model import save_model_to_file,save_model_to_db,get_model_list,get_default_model_name,get_default_description,load_model
import matplotlib.pyplot as plt
from PIL import Image
import io
import re
from janome.tokenizer import Tokenizer
from janome.analyzer import Analyzer
from janome.charfilter import UnicodeNormalizeCharFilter
from janome.tokenfilter import POSKeepFilter, POSStopFilter, LowerCaseFilter, CompoundNounFilter
from PIL import Image
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

import re

import pandas as pd
import pdb


def show_image(img):
    # Convert To PIL Image
    image = Image.open(img)
    print(type(image))

    # Convert the image to a NumPy array
    image_array = np.array(image)
    print(type(image_array))

    return image_array, image


# カスタム辞書を使用してTokenizerを初期化
UDIC = r"user_simpledic.csv"
tokenizer = Tokenizer(UDIC, udic_type="simpledic", udic_enc="utf8")

# 前処理用の正規表現
preprocessing_regex = re.compile(r'[^a-zA-Z0-9ぁ-んァ-ヶヷ-ヺー一-龥、。！？\s.,!?]')

def preprocess(text):
    text = preprocessing_regex.sub('', text)
    return text


from janome.tokenfilter import TokenFilter

class NumericFilter(TokenFilter):
    def apply(self, tokens):
        for token in tokens:
            if not token.part_of_speech.startswith('名詞,数'):  # 数詞を除外
                yield token

class LengthLimitFilter(TokenFilter):
    def __init__(self, max_length=10):
        self.max_length = max_length

    def apply(self, tokens):
        for token in tokens:
            if len(token.surface) <= self.max_length:
                yield token

class StopWordFilter(TokenFilter):
    def __init__(self, stop_words):
        self.stop_words = set(stop_words)

    def apply(self, tokens):
        for token in tokens:
            if token.surface not in self.stop_words:
                yield token

def load_stopwords(file_path='stop_word.txt'):
    with open(file_path, 'r', encoding='utf8') as f:
        stop_words = [line.strip() for line in f]
    return stop_words

# Token filtersのリストに追加
#token_filters = [
    #CompoundNounFilter(),  # 複合語の分割
    POSKeepFilter(['名詞', '動詞', '形容詞']),  # 名詞、動詞、形容詞のみ残す
    POSStopFilter(['助詞', '助動詞']),  # 助詞と助動詞を除去
    LowerCaseFilter(),  # 小文字化
    NumericFilter(),  # 数字を除去
    LengthLimitFilter(max_length=4)  # 10文字以上の複合語を除去]

def preprocess(text):
    text = preprocessing_regex.sub('', text)
    return text

def split_camel_case(s):
    return re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', s)

def keitaiso(texts):
    char_filters = [UnicodeNormalizeCharFilter()]
    
    # ストップワードのロード 
    stop_words = load_stopwords()

    # Token filtersのリストに追加 
    token_filters = [
        POSKeepFilter(['名詞', '動詞', '形容詞']),  # 名詞、動詞、形容詞のみ残す 
        POSStopFilter(['助詞', '助動詞']),  # 助詞と助動詞を除去 
        LowerCaseFilter(),  # 小文字化 
        #NumericFilter(),  # 数字を除去 
        #LengthLimitFilter(max_length=4),  # 指定長度以下のトークンのみ残す 
        StopWordFilter(stop_words)   # ストップワードフィルタを追加 
    ]

    analyzer = Analyzer(char_filters=char_filters, tokenizer=tokenizer, token_filters=token_filters)

    words = []
    for text in texts:
        # テキストを "_" で分割
        split_text = text.split('_')
        
        # 各部分を個別に処理
        processed_parts = []
        for part in split_text:
            tokens = [token.surface for token in analyzer.analyze(part)]
            processed_parts.append(' '.join(tokens))
        
        # 処理された部分を "_" で再結合
        words.append(' '.join(processed_parts))

    return words


def tokenize(text):
    tokenizer = Tokenizer()
    return [token.surface for token in tokenizer.tokenize(text)]

def load_data_from_excel(file_path):
    df = pd.read_excel(file_path)
    df['Column1'] = df.apply(lambda row: ' '.join(row.dropna().astype(str)), axis=1)
    df = df[['Column1']]
    return df

def load_data_from_file(file_path):

    file_parts = file_path.rsplit('.', 1)
    if len(file_parts) == 2:
        file_extension = file_parts[1].lower()
    else:
        file_extension = ''

    if file_extension == 'csv' or file_extension == 'txt':
        with open(file_path, "rb") as f:
            result = chardet.detect(f.read())
        encoding = result['encoding']

        # ファイルを読み込み、改行ごとに分割してDataFrameに変換
        with open(file_path, 'r', encoding=encoding) as file:
            lines = file.readlines()
        
        # 改行ごとにDataFrameの行として追加
        df = pd.DataFrame({'Column1': [line.strip() for line in lines]})
        
    elif file_extension == 'xlsx':
        df = pd.read_excel(file_path)
    
    df['Column1'] = df.apply(lambda row: ' '.join(row.dropna().astype(str)), axis=1)
    df = df[['Column1']]
    return df

import networkx as nx
from sklearn.metrics.pairwise import cosine_similarity

def generate_complete_network(models, threshold=0.3):
    G = nx.Graph()
    
    # 各モデルの単一グラフを生成
    for model_name, (vectorizer, tfidf_matrix) in models.items():
        single_model_graph = generate_single_model_network(vectorizer, tfidf_matrix, model_name, threshold)
        G = nx.compose(G, single_model_graph)
    
    # モデル間のグラフを生成
    inter_model_graph = generate_inter_model_network(models, threshold)
    G = nx.compose(G, inter_model_graph)
    
    return G

def generate_single_model_network(vectorizer, tfidf_matrix, model_name, threshold=0.3):
    cosine_similarities = cosine_similarity(tfidf_matrix)
    G = nx.Graph()
    num_documents = tfidf_matrix.shape[0]
    
    for i in range(num_documents):
        for j in range(i + 1, num_documents):
            similarity_score = cosine_similarities[i][j]
            if similarity_score > threshold:
                node1 = f"{model_name}_{i}"
                node2 = f"{model_name}_{j}"
                G.add_edge(node1, node2, weight=similarity_score)
    
    return G

def generate_inter_model_network(models, threshold=0.3):
    G = nx.Graph()
    
    for (model1_name, (vectorizer1, tfidf_matrix1)) in models.items():
        for (model2_name, (vectorizer2, tfidf_matrix2)) in models.items():
            if model1_name < model2_name:  # 重複比較を避ける
                # 一時的な結合ベクトライザーを作成
                combined_vectorizer = TfidfVectorizer()
                combined_tfidf = combined_vectorizer.fit_transform(
                    vectorizer1.get_feature_names_out().tolist() + 
                    vectorizer2.get_feature_names_out().tolist()
                )
                
                similarity = cosine_similarity(
                    combined_tfidf[:len(vectorizer1.get_feature_names_out())],
                    combined_tfidf[len(vectorizer1.get_feature_names_out()):]
                )
                
                if similarity[0][0] > threshold:
                    G.add_edge(model1_name, model2_name, weight=similarity[0][0])
    
    return G

def vectorize_texts(texts):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    return tfidf_matrix, vectorizer

def train_and_save_model(texts_to_analyze, model_name, description, model):
    analyzed_texts = keitaiso(texts_to_analyze)   
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(analyzed_texts)

    model_data = (vectorizer, tfidf_matrix, model)

    file_path = save_model_to_file(model_data, model_name)
    save_model_to_db(model_name, file_path, description)
    return f"Model {model_name} trained and saved successfully."



def predict_with_model(query_text, vectorizer, tfidf_matrix, df, top_n=1):
    query_analyzed_text = keitaiso([query_text])[0]
    closest_entries, valid_words = find_closest_entries(query_analyzed_text, tfidf_matrix, vectorizer, df, top_n=top_n)
    
    if valid_words:
        print(f"Valid words in query: {', '.join(valid_words)}")
    
    return closest_entries

def find_closest_entries(query, tfidf_matrix, vectorizer, df, top_n=1, top_words=10):
    query_vec = vectorizer.transform([query])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_n_indices = np.argsort(-cosine_similarities)[:top_n]
    top_n_similarities = cosine_similarities[top_n_indices]
    closest_entries = df.iloc[top_n_indices]

    # 関連する単語の抽出
    feature_names = vectorizer.get_feature_names_out()
    related_words = []
    for idx in top_n_indices:
        entry_vec = tfidf_matrix[idx].toarray().flatten()
        top_word_indices = np.argsort(-entry_vec)[:top_words]
        top_words_list = [feature_names[i] for i in top_word_indices]
        related_words.append(top_words_list)

    # 有効な単語の抽出
    query_words = query.split()
    valid_words = [word for word in query_words if word in feature_names]

    results = [(entry.Column1, similarity, words)
               for entry, similarity, words in zip(closest_entries.itertuples(index=False), top_n_similarities, related_words)]

    return results, valid_words


def initialize():
    file_path = 'files_info2.xlsx'
    df = load_data_from_excel(file_path)
    texts_to_analyze = df['Column1'].tolist()
    train_and_save_model(texts_to_analyze, model=df)
    vectorizer, tfidf_matrix, df = load_model()
    return vectorizer, tfidf_matrix, df


def load_csv_file(file_path, encoding):
    # Determine the maximum number of columns
    with open(file_path, 'r', encoding=encoding) as f:
        max_columns = max(len(line.split(',')) for line in f)

    # Read the CSV file
    df = pd.read_csv(file_path, header=None, names=range(max_columns), sep=None, engine='python', encoding=encoding)

    # Combine all columns into one
    df['Column1'] = df.apply(lambda row: ' '.join(row.dropna().astype(str)), axis=1)
    return df[['Column1']]

def load_txt_file(file_path, encoding):
    with open(file_path, 'r', encoding=encoding) as file:
        content = file.read()
    return pd.DataFrame({'Column1': [line for line in content.split('\n') if line.strip()]})

def load_xlsx_file(file_path):
    df = pd.read_excel(file_path)
    df['Column1'] = df.apply(lambda row: ','.join(row.dropna().astype(str)), axis=1)
    return df[['Column1']]

def load_data_from_file(file_path):
    encodings_to_try = ['utf-8', 'cp932', 'shift_jis', 'euc-jp']
    
    for encoding in encodings_to_try:
        try:
            if file_path.lower().endswith('.csv'):
                return load_csv_file(file_path, encoding)
            elif file_path.lower().endswith('.txt'):
                return load_txt_file(file_path, encoding)
            elif file_path.lower().endswith('.xlsx'):
                return load_xlsx_file(file_path)
        except UnicodeDecodeError:
            continue
        except pd.errors.ParserError:
            print(f"Warning: Some lines in the CSV file could not be parsed with encoding {encoding}. Skipping those lines.")
            continue
    
    raise ValueError(f"Unable to read the file with any of the attempted encodings: {encodings_to_try}")

def upload_and_train(file, model_name, description):
    if file is None:
        return "No file uploaded", [], [], []

    file_path = file.name
    df = load_data_from_file(file_path)

    if 'Column1' not in df.columns:
        return "The expected column 'Column1' is not present in the DataFrame.", [], [], []

    texts_to_analyze = df['Column1'].tolist()

    result = train_and_save_model(texts_to_analyze, model_name, description, df)
    updated_model_list = get_model_list()
    return result, updated_model_list, updated_model_list, updated_model_list

def upload_file(file):
    if file is None:
        return None, "", ""
    
    file_path = file.name
    df = load_data_from_file(file_path)
    
    default_model_name = get_default_model_name(file_path)
    default_description = get_default_description(df)
    
    return df, default_model_name, default_description


def make_prediction(query_text, top_n):
    vectorizer, tfidf_matrix, df = load_model('model.pkl')
    closest_entries = predict_with_model(query_text, vectorizer, tfidf_matrix, df, top_n=top_n)
    return closest_entries

def get_top_words(node, top_n=10):
    model_name, node_index = node.split(':')
    
    model_data = load_model(model_name)
    
    if model_data is None:
        return [f"Model '{model_name}' not found"]
    
    vectorizer, tfidf_matrix, _ = model_data  # モデルは使用しないので無視
    
    feature_names = vectorizer.get_feature_names_out()
    node_vector = tfidf_matrix[int(node_index)]
    
    # スパース行列を密な配列に変換
    dense_vector = node_vector.toarray()[0]
    
    # 重要度順にソート
    sorted_indices = dense_vector.argsort()[::-1]
    
    # 上位N個の単語を取得
    top_words = [(feature_names[i], dense_vector[i]) for i in sorted_indices[:top_n]]
    
    return top_words


def extract_top_words(tfidf_matrix, feature_names, top_n=10):
    top_words = []
    for row in tfidf_matrix:
        top_indices = np.argsort(row.toarray()[0])[-top_n:]
        top_words.append([feature_names[i] for i in top_indices])
    return top_words

def predict_with_model(query_text, vectorizer, tfidf_matrix, top_n=1):
    query_vec = vectorizer.transform([query_text])
    cosine_similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
    top_n_indices = np.argsort(-cosine_similarities)[:top_n]
    top_n_similarities = cosine_similarities[top_n_indices]
    return list(zip(top_n_indices, top_n_similarities))