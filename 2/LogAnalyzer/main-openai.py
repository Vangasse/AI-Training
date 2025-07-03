# main.py
from openai import OpenAI
from dotenv import load_dotenv
import os
from prompt import PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 1. Defina os logs a serem analisados como uma string multi-linha
log_input = """
2025-07-03 09:15:11 INFO: User 'admin' successfully logged in.
2025-07-03 09:15:14 ERROR: Traceback (most recent call last):
  File "/app/jobs.py", line 42, in process_invoices
    user_profile.update_last_seen()
AttributeError: 'NoneType' object has no attribute 'update_last_seen'
2025-07-03 09:17:05 ERROR: Failed to connect to database: pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on 'db-primary' (111)")
"""

# 2. Formate o prompt com os logs. O nome 'log_data' corresponde ao placeholder.
final_prompt = PROMPT.format(log_data=log_input)

# 3. Envie para a API
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": final_prompt}],
    stream=True,
)

# 4. Imprima a resposta
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")