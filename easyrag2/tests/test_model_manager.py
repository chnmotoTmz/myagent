import unittest
import os
import sqlite3
import networkx as nx
from model_manager import ModelManager

class TestModelManager(unittest.TestCase):

    def setUp(self):
        self.manager = ModelManager(db_path='test_models.db', model_dir='test_models')
        self.model = {'key': 'value'}

    def tearDown(self):
        # テスト後にデータベースとモデルディレクトリをクリーンアップ
        if os.path.exists('test_models.db'):
            os.remove('test_models.db')
        if os.path.exists('test_models'):
            for file in os.listdir('test_models'):
                os.remove(os.path.join('test_models', file))
            os.rmdir('test_models')

    def test_save_and_load_model(self):
        self.manager.save_model(self.model, 'test_model')
        loaded_model = self.manager.load_model('test_model')
        self.assertEqual(self.model, loaded_model)

    def test_delete_model(self):
        self.manager.save_model(self.model, 'test_model')
        self.manager.delete_model('test_model')
        with self.assertRaises(FileNotFoundError):
            self.manager.load_model('test_model')

    def test_get_model_list(self):
        self.manager.save_model(self.model, 'test_model1')
        self.manager.save_model(self.model, 'test_model2')
        model_list = self.manager.get_model_list()
        self.assertIn('test_model1', model_list)
        self.assertIn('test_model2', model_list)

    def test_save_and_load_network(self):
        G = nx.Graph()
        G.add_edge('model1:1', 'model2:1', weight=0.5)
        similarities = {('model1:1', 'model2:1'): 0.5}
        self.manager.save_network_and_similarities(G, similarities)
        loaded_G, loaded_similarities = self.manager.load_network_from_database()
        self.assertEqual(list(G.edges(data=True)), list(loaded_G.edges(data=True)))
        self.assertEqual(similarities, loaded_similarities)

    def test_get_node_relations(self):
        G = nx.Graph()
        G.add_edge('model1:1', 'model2:1', weight=0.5)
        G.add_edge('model1:1', 'model3:1', weight=0.3)
        similarities = {('model1:1', 'model2:1'): 0.5, ('model1:1', 'model3:1'): 0.3}
        self.manager.save_network_and_similarities(G, similarities)
        relations = self.manager.get_node_relations('model1:1', min_weight=0.4)
        self.assertEqual(len(relations), 1)
        self.assertEqual(relations[0], ('model1:1', 'model2:1', 0.5))

    def test_clear_network_data(self):
        G = nx.Graph()
        G.add_edge('model1:1', 'model2:1', weight=0.5)
        similarities = {('model1:1', 'model2:1'): 0.5}
        self.manager.save_network_and_similarities(G, similarities)
        self.manager.clear_network_data()
        loaded_G, loaded_similarities = self.manager.load_network_from_database()
        self.assertEqual(len(loaded_G.edges()), 0)
        self.assertEqual(len(loaded_similarities), 0)

if __name__ == '__main__':
    unittest.main()