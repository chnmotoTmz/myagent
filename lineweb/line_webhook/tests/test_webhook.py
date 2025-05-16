import pytest
import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8083"  # Adjust port according to your server

def test_webhook_success():
    payload = {
        "message": "Test webhook message",
        "timestamp": datetime.now().isoformat()
    }
    
    response = requests.post(f"{BASE_URL}/webhook", json=payload)
    
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/json")
    
    data = response.json()
    assert data["success"] is True
    assert "message" in data

def test_webhook_invalid_payload():
    invalid_payload = {}
    
    response = requests.post(f"{BASE_URL}/webhook", json=invalid_payload)
    
    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/json")
    
    data = response.json()
    assert "error" in data
