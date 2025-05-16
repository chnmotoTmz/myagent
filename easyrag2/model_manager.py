import os
import pickle
import sqlite3
import networkx as nx
import matplotlib.pyplot as plt

class ModelManager:
    def __init__(self, db_path='models.db', model_dir='models'):
        self.db_path = db_path
        self.model_dir = model_dir
        if not os.path.exists(model_dir):
            os.makedirs(model_dir)
        self._create_database()

    def _create_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS models
            (id INTEGER PRIMARY KEY, name TEXT UNIQUE, file_path TEXT, description TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        c.execute('''CREATE TABLE IF NOT EXISTS network
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            model1 TEXT,
            model2 TEXT,
            similarity REAL,
            relationship_type TEXT,
            UNIQUE(model1, model2))''')
        conn.commit()
        conn.close()

    def save_model(self, model, model_name, description=''):
        file_path = os.path.join(self.model_dir, f"{model_name}.pkl")
        with open(file_path, 'wb') as file:
            pickle.dump(model, file)
        self._save_model_to_db(model_name, file_path, description)

    def _save_model_to_db(self, model_name, file_path, description):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO models (name, file_path, description) VALUES (?, ?, ?)",
                  (model_name, file_path, description))
        conn.commit()
        conn.close()

    def load_model(self, model_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT file_path FROM models WHERE name = ?", (model_name,))
        result = c.fetchone()
        conn.close()
        if result:
            file_path = result[0]
            with open(file_path, 'rb') as file:
                return pickle.load(file)
        else:
            raise FileNotFoundError(f"No model found with name {model_name}")

    def delete_model(self, model_name):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT file_path FROM models WHERE name = ?", (model_name,))
        result = c.fetchone()
        if result:
            file_path = result[0]
            if os.path.exists(file_path):
                os.remove(file_path)
            c.execute("DELETE FROM models WHERE name = ?", (model_name,))
            conn.commit()
        conn.close()

    def get_model_list(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT name FROM models")
        models = [row[0] for row in c.fetchall()]
        conn.close()
        return models

    def get_node_relations(self, node, min_weight=0.0):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT model1, model2, similarity
            FROM network
            WHERE (model1 = ? OR model2 = ?) AND similarity >= ?
        """, (node, node, min_weight))
        relations = c.fetchall()
        conn.close()
        return relations

    def get_network_nodes(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
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

    def save_network_and_similarities(self, G, similarities, clear_existing=True):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        try:
            if clear_existing:
                c.execute('DELETE FROM network')
            for (node1, node2), similarity in similarities.items():
                if node1 == node2:
                    continue
                model1, num1 = node1.split(':')
                model2, num2 = node2.split(':')
                relationship_type = 'self_similarity' if model1 == model2 else 'network'
                c.execute("""
                    INSERT OR REPLACE INTO network (model1, model2, similarity, relationship_type)
                    VALUES (?, ?, ?, ?)
                """, (node1, node2, similarity, relationship_type))
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            print(f"An error occurred: {e}")
        finally:
            conn.close()

    def load_network_from_database(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT model1, model2, similarity FROM network")
        data = c.fetchall()
        conn.close()
        G = nx.Graph()
        similarities = {}
        for model1, model2, similarity in data:
            G.add_edge(model1, model2, weight=similarity)
            if similarity is not None:
                similarities[(model1, model2)] = similarity
        return G, similarities

    def clear_network_data(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM network')
        conn.commit()
        conn.close()

    @staticmethod
    def save_network_to_file(G, file_path):
        nx.write_gpickle(G, file_path)

    @staticmethod
    def load_network_from_file(file_path):
        return nx.read_gpickle(file_path)