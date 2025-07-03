from openai import OpenAI
from key import API_KEY

client = OpenAI(api_key=API_KEY)

stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Say this is a test"}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")