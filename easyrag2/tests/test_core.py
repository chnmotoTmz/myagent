import unittest
from core import preprocess_text, tokenize, calculate_similarity

class TestCoreFunctions(unittest.TestCase):
    def test_preprocess_text(self):
        self.assertEqual(preprocess_text('Hello, World!'), 'hello world')

    def test_tokenize(self):
        self.assertEqual(tokenize('hello world'), ['hello', 'world'])

    def test_calculate_similarity(self):
        self.assertAlmostEqual(calculate_similarity('hello world', 'hello'),0.5797386715376658, places=3)

if __name__ == '__main__':
    unittest.main()
    