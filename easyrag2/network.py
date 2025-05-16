from core import load_model
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
import networkx as nx
from joblib import Parallel, delayed
import pdb
import matplotlib.pyplot as plt
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from model import save_similarities_to_database,save_network_and_similarities_to_database,load_model_pickel

def generate_single_model_network(vectorizer, tfidf_matrix, model_name, threshold=0.3):
    cosine_similarities = cosine_similarity(tfidf_matrix)
    G = nx.Graph()
    num_documents = tfidf_matrix.shape[0]
    for i in range(num_documents):
        for j in range(i + 1, num_documents):
            similarity_score = cosine_similarities[i][j]
            if similarity_score > threshold:
                # Change this line
                node1 = f"{model_name}:{i}"  # Use colon instead of underscore
                node2 = f"{model_name}:{j}"  # Use colon instead of underscore
                G.add_edge(node1, node2, weight=similarity_score)
    return G

def process_model_pair(model1_name, model2_name, models, threshold=0.1):
    try:
        vectorizer1, tfidf_matrix1 = models[model1_name]
        vectorizer2, tfidf_matrix2 = models[model2_name]
        
        if tfidf_matrix1.shape[0] == 0 or tfidf_matrix2.shape[0] == 0:
            print(f"Warning: Empty TF-IDF matrix for {model1_name} or {model2_name}")
            return None

        # Create a temporary combined vectorizer
        combined_features = np.concatenate([
            vectorizer1.get_feature_names_out(),
            vectorizer2.get_feature_names_out()
        ])
        
        # Combine TF-IDF matrices
        combined_tfidf = np.concatenate([tfidf_matrix1.toarray(), tfidf_matrix2.toarray()], axis=1)
        
        # Calculate similarity
        similarity = cosine_similarity(
            combined_tfidf[:len(vectorizer1.get_feature_names_out())],
            combined_tfidf[len(vectorizer1.get_feature_names_out()):]
        )
        
        if similarity[0][0] > threshold:
            return (model1_name, model2_name, {"weight": similarity[0][0]})
        return None
    except Exception as e:
        print(f"Error processing model pair {model1_name} and {model2_name}: {str(e)}")
        return None



def calculate_pairwise_similarity(models, threshold=0.1):
    # 1. 共通語彙の抽出
    common_vocabulary = set()
    for model_name, (vectorizer, _) in models.items():
        common_vocabulary.update(vectorizer.get_feature_names_out())
    
    # 2. TF-IDFベクトルの再計算
    combined_vectorizer = TfidfVectorizer(vocabulary=list(common_vocabulary))
    model_vectors = {}
    for model_name, (vectorizer, tfidf_matrix) in models.items():
        docs = vectorizer.inverse_transform(tfidf_matrix)
        docs = [' '.join(doc) for doc in docs]
        model_vectors[model_name] = combined_vectorizer.fit_transform(docs)
    
    # 3. 閾値を超える異なるモデル間のコサイン類似度の計算
    similarities = {}
    model_names = list(model_vectors.keys())
    for i, model1_name in enumerate(model_names):
        for j, model2_name in enumerate(model_names[i+1:], start=i+1):
            sim = cosine_similarity(model_vectors[model1_name], model_vectors[model2_name])
            for row in range(sim.shape[0]):
                for col in range(sim.shape[1]):
                    if sim[row, col] > threshold:
                        key = (f"{model1_name}:{row}", f"{model2_name}:{col}")
                        similarities[key] = sim[row, col]
    
    return similarities

def generate_network(model_names):
    models = {}
    for model_name in model_names:
        vectorizer, tfidf_matrix, df = load_model(model_name)
        if vectorizer is not None and tfidf_matrix is not None:
            models[model_name] = (vectorizer, tfidf_matrix)
        else:
            print(f"Warning: Could not load model {model_name}")

    if not models:
        return "No valid models could be loaded."

    G, similarities = generate_complete_network(models)
    save_network_and_similarities_to_database(G, similarities, clear_existing=True)
    return "Network generated and saved successfully."


def generate_complete_network(models, threshold=-0.1):
    G = nx.Graph()
    all_similarities = {}

    # 単一モデルのネットワーク生成と同じモデル内の類似度計算
    for model_name, (vectorizer, tfidf_matrix) in models.items():
        single_model_graph = generate_single_model_network(vectorizer, tfidf_matrix, model_name, threshold)
        G = nx.compose(G, single_model_graph)
        
        # 同じモデル内の類似度を all_similarities に追加
        all_similarities.update(nx.get_edge_attributes(single_model_graph, 'weight'))

    # 異なるモデル間のペアワイズの類似度を計算
    inter_model_similarities = calculate_pairwise_similarity(models, threshold=threshold)
    
    # 異なるモデル間の類似度を all_similarities に追加
    all_similarities.update(inter_model_similarities)

    # しきい値を超える類似度のエッジを追加（異なるモデル間のみ）
    for (element1, element2), similarity in inter_model_similarities.items():
        if similarity > threshold:
            G.add_edge(element1, element2, weight=similarity)

    return G, all_similarities

def get_related_nodes(G, start_node, top_n):
    related_nodes = sorted(G[start_node].items(), key=lambda x: x[1]['weight'], reverse=True)[:top_n]
    return [(node, data['weight']) for node, data in related_nodes]