import os

# Prefer environment variables if available, otherwise use defaults
REDMINE_API_KEY = os.getenv("REDMINE_API_KEY", "YOUR_REDMINE_API_KEY_HERE")
REDMINE_URL = os.getenv("REDMINE_URL", "https://YOUR_REDMINE_URL_HERE")
