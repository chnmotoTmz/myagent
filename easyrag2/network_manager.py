import networkx as nx
import sqlite3
from core import load_model
import numpy as np
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from joblib import Parallel, delayed
import pdb
import matplotlib.pyplot as plt
import io
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from model import save_similarities_to_database, save_network_and_similarities_to_database

class NetworkManager:
    def __init__(self, db_path='models.db'):
        self.db_path = db_path
        self.network = nx.Graph()
        self._create_network_table()

    def _create_network_table(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS network (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model1 TEXT,
            model2 TEXT,
            similarity REAL,
            relationship_type TEXT,
            UNIQUE(model1, model2))''')
        conn.commit()
        conn.close()

    def add_model(self, model_name):
        self.network.add_node(model_name)

    def connect_models(self, model_name1, model_name2, similarity):
        self.network.add_edge(model_name1, model_name2, weight=similarity)
        self._save_network_to_db(model_name1, model_name2, similarity)

    def _save_network_to_db(self, model_name1, model_name2, similarity):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO network (model1, model2, similarity) VALUES (?, ?, ?)",
                  (model_name1, model_name2, similarity))
        conn.commit()
        conn.close()

    def get_connections(self, model_name):
        return list(self.network.neighbors(model_name))

    def load_network_from_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT model1, model2, similarity FROM network")
        data = c.fetchall()
        conn.close()
        for model1, model2, similarity in data:
            self.network.add_edge(model1, model2, weight=similarity)

    def generate_single_model_network(self, vectorizer, tfidf_matrix, model_name, threshold=0.3):
        cosine_similarities = cosine_similarity(tfidf_matrix)
        G = nx.Graph()
        num_documents = tfidf_matrix.shape[0]
        for i in range(num_documents):
            for j in range(i + 1, num_documents):
                similarity_score = cosine_similarities[i][j]
                if similarity_score > threshold:
                    node1 = f"{model_name}:{i}"  # Use colon instead of underscore
                    node2 = f"{model_name}:{j}"  # Use colon instead of underscore
                    G.add_edge(node1, node2, weight=similarity_score)
        return G

    def process_model_pair(self, model1_name, model2_name, models, threshold=0.3):
        try:
            vectorizer1, tfidf_matrix1 = models[model1_name]
            vectorizer2, tfidf_matrix2 = models[model2_name]
            if tfidf_matrix1.shape[0] == 0 or tfidf_matrix2.shape[0] == 0:
                print(f"Warning: Empty TF-IDF matrix for {model1_name} or {model2_name}")
                return None
            combined_features = np.concatenate([
                vectorizer1.get_feature_names_out(),
                vectorizer2.get_feature_names_out()
            ])
            combined_tfidf = np.concatenate([tfidf_matrix1.toarray(), tfidf_matrix2.toarray()], axis=1)
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

    def calculate_pairwise_similarity(self, models, threshold=0.3):
        common_vocabulary = set()
        for model_name, (vectorizer, _) in models.items():
            common_vocabulary.update(vectorizer.get_feature_names_out())
        combined_vectorizer = TfidfVectorizer(vocabulary=list(common_vocabulary))
        model_vectors = {}
        for model_name, (vectorizer, tfidf_matrix) in models.items():
            docs = vectorizer.inverse_transform(tfidf_matrix)
            docs = [' '.join(doc) for doc in docs]
            model_vectors[model_name] = combined_vectorizer.fit_transform(docs)
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

    def generate_network(self, model_names):
        pdb.set_trace()
        models = {name: load_model(f"{name}.pkl") for name in model_names}
        G, similarities = self.generate_complete_network(models)
        save_network_and_similarities_to_database(G, similarities, clear_existing=True)
        return "Network generated and saved successfully."

    def generate_complete_network(self, models, threshold=0.2):
        G = nx.Graph()
        all_similarities = {}
        for model_name, model_data in models.items():
            if isinstance(model_data, tuple) and len(model_data) == 2:
                vectorizer, tfidf_matrix = model_data
                single_model_graph = self.generate_single_model_network(vectorizer, tfidf_matrix, model_name, threshold)
                G = nx.compose(G, single_model_graph)
                all_similarities.update(nx.get_edge_attributes(single_model_graph, 'weight'))
            else:
                print(f"Skipping model {model_name} due to unexpected data format")
        inter_model_similarities = self.calculate_pairwise_similarity(models, threshold=threshold)
        all_similarities.update(inter_model_similarities)
        for (element1, element2), similarity in inter_model_similarities.items():
            if similarity > threshold:
                G.add_edge(element1, element2, weight=similarity)
        return G, all_similarities

    def get_related_nodes(self, G, start_node, top_n):
        pdb.set_trace()
        related_nodes = sorted(G[start_node].items(), key=lambda x: x[1]['weight'], reverse=True)[:top_n]
        return [(node, data['weight']) for node, data in related_nodes]