import requests
import json
from dotenv import load_dotenv
import os
import pdb 


# Load environment variables
load_dotenv()

def generate_content(prompt):
    """
    Sends a request to the Gemini API to generate content based on the provided prompt.

    Args:
        prompt (str): The text prompt to generate content from.

    Returns:
        str: The generated content if successful, otherwise an error message.
    """
    url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent'

    headers = {
        'Content-Type': 'application/json'
    }

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }

    params = {
        'key': os.getenv('GAI')  # Ensure your API key is stored in the environment variables
    }


    response = requests.post(url, headers=headers, params=params, data=json.dumps(data))

    if response.status_code == 200:
        # Extract and return the answer text
        try:
            answer = response.json()['candidates'][0]['content']['parts'][0]['text']
            return answer
        except (KeyError, IndexError) as e:
            return f"Error extracting content: {e}"
    else:
        return f"Error {response.status_code}: {response.text}"

# Example usage
# prompt = "Explain how AI works"
# result = generate_content(prompt)
# print(result)


