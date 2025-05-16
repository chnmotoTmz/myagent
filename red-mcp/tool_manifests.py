TOOL_MANIFESTS = [
    {
        "name": "create_issue",
        "description": "Creates a new issue in a specified Redmine project.",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_id": {
                    "type": "integer",
                    "description": "The numeric ID or string identifier of the Redmine project."
                },
                "subject": {
                    "type": "string",
                    "description": "The subject line of the new issue."
                },
                "description": {
                    "type": "string",
                    "description": "The detailed description of the new issue."
                },
                "tracker_id": {
                    "type": "integer",
                    "description": "The numeric ID of the tracker (e.g., 1 for Bug, 2 for Feature).",
                    "default": 1
                }
            },
            "required": ["project_id", "subject", "description"]
        }
    }
]
