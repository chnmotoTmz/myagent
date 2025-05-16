import unittest
import networkx as nx
from network_manager import NetworkManager

class TestNetworkManager(unittest.TestCase):

    def setUp(self):
        self.network = NetworkManager(db_path='test_models.db')

    def test_add_and_connect_models(self):
        self.network.add_model('model1')
        self.network.add_model('model2')
        self.network.connect_models('model1', 'model2', 0.9)
        connections = self.network.get_connections('model1')
        self.assertIn('model2', connections)

    def test_load_network_from_db(self):
        # 最初にデータベースにいくつかのモデルを追加
        self.network.add_model('model3')
        self.network.add_model('model4')
        self.network.connect_models('model3', 'model4', 0.8)

        # 新しいNetworkManagerインスタンスを作成し、データベースから読み込む
        new_network = NetworkManager(db_path='test_models.db')
        new_network.load_network_from_db()

        # ネットワークが正しく読み込まれたか確認
        self.assertIn('model3', new_network.network.nodes())
        self.assertIn('model4', new_network.network.nodes())
        self.assertEqual(new_network.network['model3']['model4']['weight'], 0.8)

    def test_generate_single_model_network(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # テスト用のデータ
        documents = ["This is a test", "Another test document", "Yet another one"]
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)

        # 単一モデルのネットワークを生成
        G = self.network.generate_single_model_network(vectorizer, tfidf_matrix, "test_model", threshold=0.1)

        # ネットワークの構造を確認
        self.assertEqual(len(G.nodes()), 3)  # 3つのドキュメントに対応するノード
        self.assertGreater(len(G.edges()), 0)  # エッジが存在することを確認

    def test_calculate_pairwise_similarity(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        
        # テスト用のデータ
        documents1 = ["This is model1", "Another document for model1"]
        documents2 = ["This is model2", "Another document for model2"]

        vectorizer1 = TfidfVectorizer()
        tfidf_matrix1 = vectorizer1.fit_transform(documents1)
        vectorizer2 = TfidfVectorizer()
        tfidf_matrix2 = vectorizer2.fit_transform(documents2)

        models = {
            "model1": (vectorizer1, tfidf_matrix1),
            "model2": (vectorizer2, tfidf_matrix2)
        }

        similarities = self.network.calculate_pairwise_similarity(models, threshold=0.1)

        # 類似度が計算されていることを確認
        self.assertGreater(len(similarities), 0)

    def tearDown(self):
        # テスト用のデータベースをクリーンアップ
        import os
        if os.path.exists('test_models.db'):
            os.remove('test_models.db')

if __name__ == '__main__':
    unittest.main()