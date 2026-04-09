import os
import ollama
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


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
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'nl-BE,nl;q=0.9,en-US;q=0.7,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
        }
        session = requests.Session()
        session.headers.update(headers)
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')

        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.extract()

        text = soup.get_text(separator="\n", strip=True)
        # Collapse excessive blank lines
        lines = [l for l in text.splitlines() if l.strip()]
        return "\n".join(lines)
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

        print("  [Thinking — waiting for model response...]", flush=True)
        response = ollama.chat(model=model, messages=messages, tools=tools_list)

        if response['message'].get('tool_calls'):
            function_map = {
                'search_web': search_web,
                'get_url_content': get_url_content,
                'fetch_api_data': fetch_api_data,
            }

            tool_calls = response['message']['tool_calls']
            print(f"  [Model wants to call {len(tool_calls)} tool(s)]", flush=True)

            for tool in tool_calls:
                name = tool['function']['name']
                args = tool['function']['arguments']
                print(f"  [Calling tool: {name} with args: {args}]", flush=True)
                result = function_map[name](**args)
                print(f"  [Tool returned {len(result)} chars]", flush=True)
                print(f"  --- raw output ---\n{result}\n  ---", flush=True)

                messages.append(response['message'])
                messages.append({'role': 'tool', 'content': result})

            print("  [All tools done — asking model to summarize...]", flush=True)
            final_res = ollama.chat(model=model, messages=messages)
            print(f"\nAI: {final_res['message']['content']}", flush=True)
            messages.append(final_res['message'])
        else:
            print("  [No tools needed — responding directly]", flush=True)
            print(f"\nAI: {response['message']['content']}", flush=True)
            messages.append(response['message'])


if __name__ == "__main__":
    run_agent()
