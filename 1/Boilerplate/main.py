import requests
import json

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers={"Authorization": "Bearer YOUR_API_KEY"},
    json={
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello!"}]
    }
)
print(response.json())