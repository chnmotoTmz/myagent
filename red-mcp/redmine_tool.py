import requests
from typing import Dict, Any, Union
from config import REDMINE_API_KEY, REDMINE_URL

class RedmineError(Exception):
    def __init__(self, message: str, status_code: int = None, response_data: Dict[str, Any] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

def create_issue(project_id: Union[int, str], subject: str, description: str, tracker_id: int = 1) -> Dict[str, Any]:
    url = f"{REDMINE_URL}/issues.json"
    headers = {"X-Redmine-API-Key": REDMINE_API_KEY, "Content-Type": "application/json"}
    data = {
        "issue": {
            "project_id": project_id,
            "subject": subject,
            "description": description,
            "tracker_id": tracker_id
        }
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        raise RedmineError(f"Redmine API error: {http_err}", 
                          status_code=response.status_code, 
                          response_data=response.text)
    except requests.exceptions.RequestException as req_err:
        raise RedmineError(f"Network error connecting to Redmine: {req_err}")
