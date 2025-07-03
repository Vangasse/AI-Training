# main.py (versão que visita apenas os submódulos da primeira página)
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from openai import OpenAI
from dotenv import load_dotenv
from prompt import PROMPT
import time

# --- CONFIGURAÇÃO INICIAL ---
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- FUNÇÕES DE SCRAPING E CONVERSÃO (sem alterações) ---

def scrape_page(url: str) -> BeautifulSoup | None:
    """Busca o conteúdo de uma URL e retorna um objeto BeautifulSoup para análise."""
    print(f"Buscando: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.RequestException as e:
        print(f"  -> Erro ao buscar a URL {url}: {e}")
        return None

def get_main_content_html(soup: BeautifulSoup, url: str) -> str | None:
    """Extrai o HTML da área de conteúdo principal do objeto Soup."""
    main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.find('div', class_='document')
    if not main_content:
        print(f"  -> Aviso: Não foi possível encontrar a área de conteúdo principal em {url}")
        return None
    return str(main_content)

def convert_html_to_md(html_content: str) -> str:
    """Envia o HTML para o LLM e retorna o Markdown convertido."""
    print("  -> Convertendo HTML para Markdown com LLM...")
    final_prompt = PROMPT.format(html_content=html_content)
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": final_prompt}]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  -> Erro na API da OpenAI: {e}")
        return ""

def process_and_save_page(url: str, output_dir: str):
    """Função reutilizável para raspar, converter e salvar uma única página."""
    soup = scrape_page(url)
    if not soup:
        return

    html_content = get_main_content_html(soup, url)
    if not html_content:
        return

    markdown_content = convert_html_to_md(html_content)
    if not markdown_content:
        return

    path = urlparse(url).path
    file_name = (path.strip('/').replace('/', '_') or "index") + ".md"
    file_path = os.path.join(output_dir, file_name)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    print(f"  -> Salvo em: {file_path}")


# --- EXECUÇÃO PRINCIPAL EM DUAS FASES ---

if __name__ == "__main__":
    start_url = 'https://requests.readthedocs.io/en/latest/'
    output_dir = 'output_markdown'
    base_domain = urlparse(start_url).netloc

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Diretório '{output_dir}' criado.")

    sub_pages_to_visit = []
    
    # --- FASE 1: Processar a página inicial e COLETAR os links ---
    print("--- FASE 1: Processando a página inicial ---")
    soup_inicial = scrape_page(start_url)
    if soup_inicial:
        # Primeiro, processa e salva a própria página inicial
        html_content = get_main_content_html(soup_inicial, start_url)
        if html_content:
            markdown_content = convert_html_to_md(html_content)
            if markdown_content:
                 path = urlparse(start_url).path
                 file_name = (path.strip('/').replace('/', '_') or "index") + ".md"
                 file_path = os.path.join(output_dir, file_name)
                 with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                 print(f"  -> Salvo em: {file_path}")

        # Agora, encontra e coleta os links dos submódulos
        print("\n  -> Coletando links dos submódulos...")
        for link in soup_inicial.find_all('a', href=True):
            absolute_link = urljoin(start_url, link['href']).split('#')[0]
            if urlparse(absolute_link).netloc == base_domain and absolute_link != start_url:
                if absolute_link not in sub_pages_to_visit:
                    sub_pages_to_visit.append(absolute_link)
        print(f"  -> {len(sub_pages_to_visit)} submódulos encontrados para visitar.")

    # --- FASE 2: Processar CADA UM dos submódulos encontrados na página inicial ---
    print("\n--- FASE 2: Processando os submódulos ---")
    if not sub_pages_to_visit:
        print("Nenhum submódulo para processar.")
    else:
        for page_url in sub_pages_to_visit[0:1]:
            process_and_save_page(page_url, output_dir)
            time.sleep(1) # Pausa para não sobrecarregar o servidor

    print("\nProcesso concluído!")