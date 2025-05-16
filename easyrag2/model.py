import sqlite3
import os
import chardet
import pickle
import networkx as nx
import matplotlib.pyplot as plt
import networkx as nx

# グローバル変数としてモデル保存用フォルダパスを宣言
MODELS_FOLDER = 'models'

def get_node_relations(node, min_weight=0.0):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("""
    SELECT model1, model2, similarity
    FROM network
    WHERE (model1 = ? OR model2 = ?) AND similarity >= ?
    """, (node, node, min_weight))
    relations = c.fetchall()
    conn.close()
    return relations

def get_network_nodes():
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    
    # networkテーブルから一意のノードを取得
    c.execute("""
    SELECT DISTINCT node FROM (
        SELECT model1 AS node FROM network
        UNION
        SELECT model2 AS node FROM network
    )
    """)
    
    nodes = [row[0] for row in c.fetchall()]
    
    conn.close()
    
    return nodes


def load_model_pickel(file_path):
    with open(file_path, 'rb') as file:
        model_data = pickle.load(file)
    return model_data
    
def create_database():
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS models
                 (id INTEGER PRIMARY KEY, name TEXT UNIQUE, file_path TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 統合されたnetworkテーブル
    c.execute('''
        CREATE TABLE IF NOT EXISTS network (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model1 TEXT,
            model2 TEXT,
            similarity REAL,
            relationship_type TEXT,
            UNIQUE(model1, model2)
        )
    ''')
    conn.commit()
    conn.close()

def get_default_model_name(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def get_default_description(df):
    return f"Dataset with {len(df)} rows and {len(df.columns)} columns"

def save_model_to_db(model_name, file_path, description):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    try:
        c.execute("INSERT OR REPLACE INTO models (name, file_path, description) VALUES (?, ?, ?)", 
                  (model_name, file_path, description))
        conn.commit()
    except sqlite3.Error as e:
        return "Database Error", str(e)
    finally:
        conn.close()

def save_model_to_file(model_data, model_name):
    if not os.path.exists(MODELS_FOLDER):
        os.makedirs(MODELS_FOLDER)
    file_path = os.path.join(MODELS_FOLDER, f"{model_name}.pkl")
    with open(file_path, 'wb') as f:
        pickle.dump(model_data, f)
    return file_path
  
def get_network_relations(node, min_weight=0.0):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("""
    SELECT model1, model2, similarity
    FROM network
    WHERE (model1 LIKE ? OR model2 LIKE ?) AND similarity >= ?
    """, (f"{node}%", f"{node}%", min_weight))
    relations = c.fetchall()
    conn.close()
    return relations


def get_model_list():
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("SELECT name FROM models")
    models = [row[0] for row in c.fetchall()]
    conn.close()
    print("Models in database:", models)  # デバッグ用出力
    return models

def delete_model(model_name):
    if isinstance(model_name, list) and len(model_name) > 0:
        model_name = model_name[0]
    
    if not isinstance(model_name, str):
        return "Invalid model name provided.", [], [], []

    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    try:
        c.execute("SELECT file_path FROM models WHERE name = ?", (model_name,))
        result = c.fetchone()
        if result:
            model_path = result[0]
            if os.path.exists(model_path):
                os.remove(model_path)
            c.execute("DELETE FROM models WHERE name = ?", (model_name,))
            conn.commit()
            updated_model_list = get_model_list()
            return f"Model '{model_name}' has been deleted.", updated_model_list, updated_model_list, updated_model_list
        else:
            return f"Model '{model_name}' not found.", get_model_list(), get_model_list(), get_model_list()
    except sqlite3.Error as e:
        return f"Database error: {str(e)}", get_model_list(), get_model_list(), get_model_list()
    finally:
        conn.close()

def save_similarities_to_database(similarities):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    
    # similaritiesテーブルの作成（存在しない場合）
    c.execute('''CREATE TABLE IF NOT EXISTS similarities
                 (element1 TEXT, element2 TEXT, similarity REAL,
                 PRIMARY KEY (element1, element2))''')
    
    # データの挿入
    for (element1, element2), similarity in similarities.items():
        c.execute("INSERT OR REPLACE INTO similarities VALUES (?, ?, ?)", 
                  (element1, element2, similarity))
    
    conn.commit()
    conn.close()



def clear_network_data():
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute('DELETE FROM network')
    conn.commit()
    conn.close()
    print('Network data cleared successfully')

def save_network_to_file(G, file_path):
    nx.write_gpickle(G, file_path)

def load_network_from_file(file_path):
    return nx.read_gpickle(file_path)

def load_network_from_database():
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("SELECT model1, model2, similarity FROM network")
    data = c.fetchall()
    conn.close()
    
    G = nx.Graph()
    similarities = {}
    for model1, model2, similarity in data:
        G.add_edge(model1, model2, weight=similarity)  # 修正箇所
        if similarity is not None:
            similarities[(model1, model2)] = similarity
    return G, similarities

def model_exists(model_name):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM models WHERE name = ?", (model_name,))
    count = c.fetchone()[0]
    conn.close()
    return count > 0
    
def save_network_and_similarities_to_database(G, similarities, clear_existing=True):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    try:
        if clear_existing:
            c.execute('DELETE FROM network')
            print('Existing network data cleared')

        for (node1, node2), similarity in similarities.items():
            if node1 == node2:
                continue
            # Change these lines
            model1, num1 = node1.split(':')  # Split on colon
            model2, num2 = node2.split(':')  # Split on colon
            relationship_type = 'self_similarity' if model1 == model2 else 'network'
            
            c.execute("""
            INSERT OR REPLACE INTO network (model1, model2, similarity, relationship_type)
            VALUES (?, ?, ?, ?)
            """, (node1, node2, similarity, relationship_type))
        
        conn.commit()
        print('Network and similarity data saved to database successfully')
    except sqlite3.Error as e:
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def save_model_to_file(model_data, model_name):
    if not os.path.exists(MODELS_FOLDER):
        os.makedirs(MODELS_FOLDER)
    file_path = os.path.join(MODELS_FOLDER, f"{model_name}.pkl")
    with open(file_path, 'wb') as f:
        pickle.dump(model_data, f)
    return file_path

def load_model(model_name):
    conn = sqlite3.connect('models.db')
    c = conn.cursor()
    c.execute("SELECT file_path FROM models WHERE name = ?", (model_name,))
    result = c.fetchone()
    conn.close()

    if result:
        file_path = result[0]
        with open(file_path, 'rb') as f:
            model_data = pickle.load(f)
            if isinstance(model_data, tuple):
                vectorizer = model_data[0] if len(model_data) > 0 else None
                tfidf_matrix = model_data[1] if len(model_data) > 1 else None
                df = model_data[2] if len(model_data) > 2 else None
                return vectorizer, tfidf_matrix, df
            else:
                return model_data, None, None
    return None, None, None
