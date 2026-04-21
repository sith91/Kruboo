import trafilatura
from bs4 import BeautifulSoup
import requests
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import json
import time

class WebResearcher:
    """
    The Exploration Layer: Website-agnostic parsing with BeautifulSoup for surgical precision.
    """
    
    @staticmethod
    def extract_with_bs4(html_content):
        """
        Surgical fallback for Trafilatura using BS4 for specific patterns.
        """
        soup = BeautifulSoup(html_content, 'lxml')
        
        # 1. Basic cleaning - remove scripts/styles
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        # 2. Extract Title and Meta
        title = soup.title.string if soup.title else "No Title"
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        desc = meta_desc['content'] if meta_desc else ""

        # 3. Smart Listing Detection (Common patterns for prices, locations)
        # Look for headers and paragraphs
        paragraphs = [p.get_text() for p in soup.find_all('p')[:10]]
        headers = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])[:5]]
        
        full_text = "\n".join(headers + paragraphs)
        return f"{title}\n{desc}\n{full_text}"[:3000]

    @staticmethod
    def search_and_extract(query: str, max_results: int = 5):
        """
        Performs a web search, identifies top URLs, and extracts clean content.
        Uses Trafilatura for speed and BeautifulSoup as a high-precision fallback.
        """
        results = []
        headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }

        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=max_results))
                
                for idx, r in enumerate(search_results):
                    url = r.get("href")
                    title = r.get("title")
                    
                    try:
                        print(f"Researcher visiting: {url}")
                        # First try Trafilatura (Built-in patterns)
                        downloaded = trafilatura.fetch_url(url)
                        text = trafilatura.extract(downloaded, include_links=False)
                        
                        if not text or len(text) < 100:
                            # Fallback to BeautifulSoup for deeper scraping
                            response = requests.get(url, headers=headers, timeout=10)
                            if response.status_code == 200:
                                text = WebResearcher.extract_with_bs4(response.text)
                        
                        results.append({
                            "id": idx + 1,
                            "title": title,
                            "url": url,
                            "content": text[:2500] if text else r.get("body")
                        })
                    except Exception as e:
                        print(f"Deep Search Issue with {url}: {e}")
                        results.append({
                            "id": idx + 1, "title": title, "url": url, "content": r.get("body")
                        })
            
            return results
        except Exception as e:
            return [{"error": f"Search failed: {e}"}]

    @staticmethod
    def search_specific_site(site: str, product_query: str):
        """
        Routes the search to a specific domain (e.g. ikman.lk, booking.com)
        """
        full_query = f"site:{site} {product_query}"
        return WebResearcher.search_and_extract(full_query, max_results=3)

def universal_research(query: str):
    """
    The Synthesis Layer: Aggregates raw extracted data into a structured report.
    """
    print(f"Starting Universal Web Research for: {query}")
    
    # 1. Determine Strategy (Simplified Intent Detection)
    target_site = None
    if "on " in query.lower() or "check " in query.lower():
        # Heuristic for specific site search (e.g., "check ikman.lk for tv")
        words = query.lower().split()
        for i, word in enumerate(words):
            if "." in word and (word.endswith(".lk") or word.endswith(".com") or word.endswith(".net")):
                target_site = word
                break
    
    if target_site:
        raw_results = WebResearcher.search_specific_site(target_site, query)
    else:
        raw_results = WebResearcher.search_and_extract(query)
    
    # 2. Format for LLM Synthesis
    report = []
    for r in raw_results:
        if "error" in r:
            continue
        report.append(f"Source [{r['id']}]: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n---")
    
    return "\n".join(report) if report else "No information found on the web."
