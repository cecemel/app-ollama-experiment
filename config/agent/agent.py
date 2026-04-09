import os
import ollama
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS


# --- TOOL 1: WEB SEARCH ---
def search_web(query: str):
    """Use this to find current information, news, or facts on any topic by searching the web via DuckDuckGo.
    Returns titles, snippets, and URLs for the top results. Use this first when you don't have a specific URL yet."""
    print(f"  [System: Searching for '{query}'...]", flush=True)
    results = DDGS().text(query, max_results=3)
    return "\n".join([f"{r['title']}: {r['body']} (URL: {r['href']})" for r in results])


# --- TOOL 2: URL SCRAPER ---
def get_url_content(url: str):
    """Use this to read the full text content of a specific webpage. Provide a complete URL including https://.
    Use this after search_web to read the actual article or page behind a search result, or when the user gives you a direct URL."""
    print(f"  [System: Reading content from {url}...]", flush=True)
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
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
    """Use this to fetch structured data from a JSON API endpoint. Provide a complete URL including https://.
    Use this when the target URL is a REST API or returns JSON rather than an HTML page."""
    print(f"  [System: Crawling API {endpoint_url}...]", flush=True)
    try:
        response = requests.get(endpoint_url)
        return str(response.json())[:2000]
    except Exception as e:
        return f"Error crawling API: {e}"


def run_agent():
    model = os.environ['MODEL']
    tools_list = [search_web, get_url_content, fetch_api_data]

    messages = [{"role": "system", "content": "You are here to help for more info. You have internet connectivity. Use tools to find info, read pages, or crawl APIs as needed."}]

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
