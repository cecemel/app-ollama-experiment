import os
import ollama
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS


# --- TOOL 1: WEB SEARCH ---
def search_web(query: str):
    """Search the web for current information and return top results."""
    print(f"  [System: Searching for '{query}'...]", flush=True)
    results = DDGS().text(query, max_results=3)
    return "\n".join([f"{r['title']}: {r['body']} (URL: {r['href']})" for r in results])


# --- TOOL 2: URL SCRAPER ---
def get_url_content(url: str):
    """Scrape the text content from a specific website URL."""
    print(f"  [System: Reading content from {url}...]", flush=True)
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0'}
        response = requests.get(url, timeout=10, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        for script in soup(["script", "style"]):
            script.extract()
        return soup.get_text()[:2000]
    except Exception as e:
        return f"Error reading URL: {e}"


# --- TOOL 3: API FETCHER ---
def fetch_api_data(endpoint_url: str):
    """Fetch raw data from a JSON API endpoint."""
    print(f"  [System: Crawling API {endpoint_url}...]", flush=True)
    try:
        response = requests.get(endpoint_url)
        return str(response.json())[:2000]
    except Exception as e:
        return f"Error crawling API: {e}"


def run_agent():
    model = os.environ['MODEL']
    tools_list = [search_web, get_url_content, fetch_api_data]

    messages = [{"role": "system", "content": "You are an advanced researcher. Use tools to find info, read pages, or crawl APIs as needed."}]

    print(f"--- Agent Active (model: {model}) ---", flush=True)
    print(f"Type 'exit' or 'quit' to stop.\n", flush=True)

    while True:
        print("\nType your question:", flush=True)
        user_input = input("> ")
        if user_input.lower() in ['exit', 'quit']:
            break
        messages.append({'role': 'user', 'content': user_input})

        print("  [Thinking...]", flush=True)
        response = ollama.chat(model=model, messages=messages, tools=tools_list)

        if response['message'].get('tool_calls'):
            function_map = {
                'search_web': search_web,
                'get_url_content': get_url_content,
                'fetch_api_data': fetch_api_data,
            }

            for tool in response['message']['tool_calls']:
                name = tool['function']['name']
                args = tool['function']['arguments']
                result = function_map[name](**args)
                print(f"  [Got {len(result)} chars of data]", flush=True)

                messages.append(response['message'])
                messages.append({'role': 'tool', 'content': result})

            print("  [Summarizing...]", flush=True)
            final_res = ollama.chat(model=model, messages=messages)
            print(f"\nAI: {final_res['message']['content']}", flush=True)
            messages.append(final_res['message'])
        else:
            print(f"\nAI: {response['message']['content']}", flush=True)
            messages.append(response['message'])


if __name__ == "__main__":
    run_agent()
