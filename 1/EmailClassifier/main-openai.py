from openai import OpenAI
from dotenv import load_dotenv
import os
from prompt import PROMPT

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa o cliente da OpenAI com a chave da API
api_key = os.getenv(key="OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 1. Defina a sua requisição (o que você quer que a IA gere)
mail_content = "Hi there, I just saw my latest invoice and it looks like I was charged twice for this month's subscription. Can you please look into this and issue a refund for the extra charge? Thanks."

# 2. Formate o prompt principal com a sua requisição
final_prompt = PROMPT.format(mail_content=mail_content)

# 3. Envie o prompt finalizado para a API
stream = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": final_prompt}],
    stream=True,
)

# Imprime a resposta da API
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="")