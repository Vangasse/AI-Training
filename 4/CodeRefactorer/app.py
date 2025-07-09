from flask import Flask, render_template, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
import os
import json
from prompt import PROMPT

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Inicializa a aplicação Flask
app = Flask(__name__)

# Inicializa o cliente da OpenAI com a chave da API a partir das variáveis de ambiente
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("A variável OPENAI_API_KEY não foi encontrada no arquivo .env ou nas variáveis de ambiente.")
    client = OpenAI(api_key=api_key)
    print("Cliente OpenAI inicializado com sucesso.")
except ValueError as e:
    print(f"Erro: {e}")
    client = None

@app.route('/')
def index():
    """
    Renderiza a página principal da aplicação a partir do template.
    """
    return render_template('index.html')

@app.route('/refactor', methods=['POST'])
def refactor_code():
    """
    Recebe o código do usuário, envia para a API da OpenAI para refatoração,
    e retorna o resultado.
    """
    if not client:
        return jsonify({'error': 'O cliente da OpenAI não foi inicializado. Por favor, verifique a configuração da sua chave de API.'}), 500

    # Obtém o código original do corpo da requisição JSON
    data = request.get_json()
    original_code = data.get('code', '')

    if not original_code:
        return jsonify({'error': 'Nenhum código foi fornecido'}), 400

    try:
        # Formata o prompt principal com o código do usuário
        final_prompt = PROMPT.format(user_request=original_code)

        # Envia o prompt finalizado para a API da OpenAI
        print("Enviando requisição para a API da OpenAI...")
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": final_prompt}],
            response_format={"type": "json_object"} # Garante que a resposta seja um objeto JSON
        )
        print("Resposta recebida da API da OpenAI.")

        # Extrai o conteúdo JSON da resposta
        response_content = completion.choices[0].message.content
        
        # A API deve retornar uma string JSON. Nós a convertemos para enviar como uma resposta JSON.
        response_data = json.loads(response_content)

        # O frontend espera as chaves 'refactoredCode' e 'explanation'.
        return jsonify({
            'refactoredCode': response_data.get('refactoredCode', ''),
            'explanation': response_data.get('explanation', '')
        })

    except json.JSONDecodeError:
        print(f"Erro ao decodificar o JSON da resposta da OpenAI: {response_content}")
        return jsonify({'error': 'Falha ao processar a resposta do modelo de IA.'}), 500
    except Exception as e:
        print(f"Ocorreu um erro inesperado: {e}")
        return jsonify({'error': 'Ocorreu um erro inesperado ao comunicar com a API da OpenAI.'}), 500

if __name__ == '__main__':
    # Executa a aplicação em modo de depuração para desenvolvimento
    app.run(debug=True)
