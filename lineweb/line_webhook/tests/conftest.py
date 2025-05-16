import pytest
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# プロジェクトルートをパスに追加してインポートできるようにする
sys.path.append(str(Path(__file__).parent.parent.parent))
from line_webhook.app.main import app

@pytest.fixture
def client():
    app.port = 8083
    return TestClient(app, base_url="http://localhost:8083")

@pytest.fixture(autouse=True)
def setup_test_env():
    # Setup any test environment variables here
    import os
    # Use a temporary directory for tests ideally, but for now change the default
    os.environ["STORAGE_PATH"] = r"C:\Users\Public\Documents\test_storage" # Use a dedicated test path
    yield
