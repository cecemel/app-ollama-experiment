import os
import re
import subprocess
import tempfile
import ollama
import requests
from bs4 import BeautifulSoup, NavigableString
from ddgs import DDGS


BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'nl-BE,nl;q=0.9,en-US;q=0.7,en;q=0.5',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'DNT': '1',
}

NOISE_TAGS = ["script", "style", "noscript", "iframe", "nav", "footer", "aside", "form"]


def _make_session():
    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)
    return session


def _strip_noise(soup):
    for tag in soup.find_all(NOISE_TAGS):
        tag.decompose()


def _smart_truncate(text: str, budget: int = 4000) -> str:
    """Truncate at a paragraph boundary within budget, keeping content from the top."""
    if len(text) <= budget:
        return text
    truncated = text[:budget]
    # Walk back to the last double newline (paragraph boundary)
    boundary = truncated.rfind('\n\n')
    if boundary > budget // 2:  # only use boundary if it's not too far back
        truncated = truncated[:boundary]
    total = len(text)
    kept = len(truncated)
    return truncated + f"\n\n[... {total - kept} chars truncated ...]"


def _html_to_markdown(root):
    """Convert a BeautifulSoup element tree to markdown, preserving meaningful structure."""
    lines = []

    def walk(el):
        if isinstance(el, NavigableString):
            text = str(el).strip()
            if len(text) > 3:
                lines.append(text)
            return

        name = el.name
        text = el.get_text(separator=' ', strip=True)
        if not text:
            return

        if name == 'h1':
            lines.append(f"\n# {text}\n")
        elif name == 'h2':
            lines.append(f"\n## {text}\n")
        elif name == 'h3':
            lines.append(f"\n### {text}\n")
        elif name in ('h4', 'h5', 'h6'):
            lines.append(f"\n#### {text}\n")
        elif name == 'p':
            if len(text) > 20:
                lines.append(f"\n{text}\n")
        elif name == 'blockquote':
            lines.append(f"\n> {text}\n")
        elif name in ('ul', 'ol'):
            for li in el.find_all('li', recursive=False):
                li_text = li.get_text(separator=' ', strip=True)
                if li_text:
                    lines.append(f"- {li_text}")
            lines.append("")
        elif name == 'table':
            for row in el.find_all('tr'):
                cells = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                if any(cells):
                    lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
        elif name == 'time':
            lines.append(f"*{el.get('datetime', text)}*")
        elif name in ('strong', 'b'):
            lines.append(f"**{text}**")
        elif name in ('em', 'i'):
            lines.append(f"_{text}_")
        elif name == 'a':
            href = el.get('href', '')
            if href and not href.startswith('#'):
                lines.append(f"[{text}]({href})")
            else:
                lines.append(text)
        else:
            for child in el.children:
                walk(child)

    walk(root)

    result = "\n".join(lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


# --- TOOL 1: WEB SEARCH ---
def search_web(query: str):
    """Search the web for current information, news, or facts using DuckDuckGo.
    Returns titles, snippets, and URLs for the top results.
    Use this first when you don't have a specific URL yet. The results will contain URLs
    you can then pass to peek_url to decide how to fetch them."""
    print(f"  [System: Searching for '{query}'...]", flush=True)
    results = DDGS().text(query, max_results=3)
    return "\n".join([f"{r['title']}: {r['body']} (URL: {r['href']})" for r in results])


# --- TOOL 2: URL PEEK ---
def peek_url(url: str):
    """Quickly preview a URL to understand what type of content it contains, before fetching it fully.
    Returns the page title, meta description, og:type, and content-type header.
    Use this when you have a URL but are unsure whether it's a news article, a generic webpage, or a JSON API.
    Based on the result, immediately call fetch_news_article, fetch_page, or fetch_api_data — do not wait."""
    print(f"  [System: Peeking at {url}...]", flush=True)
    try:
        session = _make_session()
        response = session.get(url, timeout=10)
        content_type = response.headers.get('Content-Type', '')

        if 'json' in content_type:
            return f"Content-Type: {content_type}\nSuggested tool: fetch_api_data — call it now."

        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.find('title')
        title = title.get_text(strip=True) if title else 'unknown'

        description = (
            soup.find('meta', attrs={'name': 'description'}) or
            soup.find('meta', attrs={'property': 'og:description'})
        )
        description = description.get('content', '') if description else ''

        og_type = soup.find('meta', attrs={'property': 'og:type'})
        og_type = og_type.get('content', '') if og_type else ''

        is_news = bool(
            soup.find('article') or
            og_type in ('article', 'news') or
            soup.find('meta', attrs={'property': 'article:published_time'})
        )

        suggestion = 'fetch_news_article' if is_news else 'fetch_page'

        return (
            f"Title: {title}\n"
            f"Description: {description}\n"
            f"OG type: {og_type}\n"
            f"Content-Type: {content_type}\n"
            f"Suggested tool: {suggestion} — call it now without waiting."
        )
    except Exception as e:
        return f"Error peeking at URL: {e}"


# --- TOOL 3: GENERIC PAGE FETCHER ---
def fetch_page(url: str):
    """Fetch the full content of a generic webpage as structured markdown.
    Good for documentation, blogs, product pages, or any non-news URL.
    Preserves headings, lists, tables, and links. Use peek_url first if unsure what type the URL is."""
    print(f"  [System: Fetching page {url}...]", flush=True)
    try:
        session = _make_session()
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        _strip_noise(soup)
        articles = soup.find_all('article')
        if articles:
            return "\n\n---\n\n".join(_html_to_markdown(a) for a in articles)
        root = soup.find('main') or soup.body or soup
        return _html_to_markdown(root)
    except Exception as e:
        return f"Error fetching page: {e}"


# --- TOOL 4: NEWS ARTICLE FETCHER ---
def fetch_news_article(url: str):
    """Fetch a news article and extract its content as structured markdown.
    Focuses on the article body, headline, author, and publication date.
    Strips ads, navigation, and related article links.
    Use peek_url first if unsure, or call this directly for known news/media URLs."""
    print(f"  [System: Fetching news article {url}...]", flush=True)
    try:
        session = _make_session()
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        _strip_noise(soup)
        articles = soup.find_all('article')
        if articles:
            combined = "\n\n---\n\n".join(_html_to_markdown(a) for a in articles)
        else:
            root = soup.find('main') or soup.body or soup
            combined = _html_to_markdown(root)
        return _smart_truncate(combined)
    except Exception as e:
        return f"Error fetching news article: {e}"


# --- TOOL 5: JSON API FETCHER ---
def fetch_api_data(endpoint_url: str, headers: dict = {}):
    """Fetch structured data from a JSON API endpoint.
    Use when the URL returns JSON rather than an HTML page.
    Use peek_url first if unsure whether the URL is an API or a webpage.
    Pass any required headers (e.g. Authorization, Accept, API keys) via the headers dict."""
    print(f"  [System: Fetching API {endpoint_url} headers={headers}...]", flush=True)
    try:
        response = requests.get(endpoint_url, headers=headers)
        return str(response.json())[:2000]
    except Exception as e:
        return f"Error fetching API: {e}"


# --- TOOL 6: PYTHON EXECUTION ---
def run_python(code: str):
    """Write and execute arbitrary Python code. Use this to compute things, parse data,
    process text, call APIs, or do anything easier expressed as code.
    Basic stdlib is available, plus requests and beautifulsoup4.
    Returns stdout + stderr. Define helper functions inline if needed."""
    print(f"  [System: Running Python ({len(code)} chars)...]", flush=True)
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            tmp = f.name
        result = subprocess.run(
            ['python', tmp], capture_output=True, text=True, timeout=30
        )
        os.unlink(tmp)
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return _smart_truncate(output.strip() or "(no output)", budget=3000)
    except subprocess.TimeoutExpired:
        return "Error: script timed out after 30 seconds"
    except Exception as e:
        return f"Error running Python: {e}"


# --- TOOL 7: SHELL EXECUTION ---
def run_shell(command: str):
    """Run a shell command via bash. Use this for curl requests, file operations,
    or any shell one-liner. curl, python, and standard Unix tools are available.
    Returns stdout + stderr combined."""
    print(f"  [System: Running shell: {command}]", flush=True)
    try:
        result = subprocess.run(
            command, shell=True, executable='/bin/bash',
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[stderr]\n{result.stderr}"
        return _smart_truncate(output.strip() or "(no output)", budget=3000)
    except subprocess.TimeoutExpired:
        return "Error: command timed out after 30 seconds"
    except Exception as e:
        return f"Error running shell command: {e}"


TOOLS = [search_web, peek_url, fetch_page, fetch_news_article, fetch_api_data, run_python, run_shell]
FUNCTION_MAP = {fn.__name__: fn for fn in TOOLS}


def run_agent():
    model = os.environ['MODEL']

    messages = [{"role": "system", "content": (
        "You are a helpful assistant with internet access. "
        "When given a URL, use peek_url first, then immediately call the suggested fetch tool — do not stop between steps to report back. "
        "When you need to find something online, use search_web, then peek and fetch the most relevant result. "
        "Chain tool calls automatically until you have enough information to answer. "
        "Not every question needs a tool — use your own knowledge when that's enough. "
        "Mention explicitly when you used your own knowledge."
    )}]

    print(f"--- Connected Agent Active (model: {model}) ---", flush=True)
    print("Type your message, then // on its own line to send. Type 'exit' or 'quit' to stop.\n", flush=True)

    while True:
        print("\nYour message (type // on its own line to send):", flush=True)
        lines = []
        while True:
            try:
                line = input()
            except EOFError:
                break
            if line == "//":
                break
            lines.append(line)
        user_input = "\n".join(lines).strip()
        if not user_input:
            continue
        if user_input.lower() in ['exit', 'quit']:
            break
        messages.append({'role': 'user', 'content': user_input})

        # Agentic loop: keep calling tools until the model gives a final answer
        while True:
            print("  [Thinking...]", flush=True)
            response = ollama.chat(model=model, messages=messages, tools=TOOLS)

            if not response['message'].get('tool_calls'):
                print("  [No more tools needed — responding]", flush=True)
                print(f"\nAI: {response['message']['content']}", flush=True)
                messages.append(response['message'])
                break

            tool_calls = response['message']['tool_calls']
            print(f"  [Model wants to call {len(tool_calls)} tool(s)]", flush=True)
            messages.append(response['message'])

            for tool in tool_calls:
                name = tool['function']['name']
                args = tool['function']['arguments']
                print(f"  [Calling: {name} {args}]", flush=True)
                result = FUNCTION_MAP[name](**args)
                print(f"  [Got {len(result)} chars]", flush=True)
                print(f"  --- raw output ---\n{result}\n  ---", flush=True)
                messages.append({'role': 'tool', 'content': result})


if __name__ == "__main__":
    run_agent()
