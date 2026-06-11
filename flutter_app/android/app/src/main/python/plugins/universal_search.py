import trafilatura
from bs4 import BeautifulSoup
import requests
try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        paragraphs = [p.get_text() for p in soup.find_all('p')[:10]]
        headers = [h.get_text() for h in soup.find_all(['h1', 'h2', 'h3'])[:5]]
        
        full_text = "\n".join(headers + paragraphs)
        return f"{title}\n{desc}\n{full_text}"[:3000]

    @staticmethod
    def fetch_and_extract_url(url, title, idx, body_fallback):
        """
        Worker function to fetch and extract content from a single URL.
        """
        headers = { 'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36' }
        try:
            print(f"Researcher visiting: {url}")
            # Try Trafilatura first (faster)
            downloaded = trafilatura.fetch_url(url)
            text = trafilatura.extract(downloaded, include_links=False) if downloaded else None
            
            if not text or len(text) < 100:
                # Fallback to BeautifulSoup with a strict timeout
                response = requests.get(url, headers=headers, timeout=5)
                if response.status_code == 200:
                    text = WebResearcher.extract_with_bs4(response.text)
            
            return {
                "id": idx + 1,
                "title": title,
                "url": url,
                "content": text[:2500] if text else body_fallback
            }
        except Exception as e:
            print(f"Deep Search Issue with {url}: {e}")
            return {
                "id": idx + 1, "title": title, "url": url, "content": body_fallback
            }

    @staticmethod
    def search_and_extract(query: str, max_results: int = 3):
        """
        Performs a web search and extracts content in parallel.
        """
        results = []
        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(query, max_results=max_results))
                
                # Use ThreadPoolExecutor for parallel extraction
                with ThreadPoolExecutor(max_workers=max_results) as executor:
                    futures = [
                        executor.submit(
                            WebResearcher.fetch_and_extract_url, 
                            r.get("href"), 
                            r.get("title"), 
                            idx, 
                            r.get("body")
                        ) 
                        for idx, r in enumerate(search_results)
                    ]
                    
                    for future in as_completed(futures):
                        results.append(future.result())
            
            # Sort back by original index to maintain relevance ranking
            results.sort(key=lambda x: x["id"])
            return results
        except Exception as e:
            return [{"error": f"Search failed: {e}"}]

    @staticmethod
    def search_specific_site(site: str, product_query: str):
        """
        Routes the search to a specific domain.
        """
        full_query = f"site:{site} {product_query}"
        return WebResearcher.search_and_extract(full_query, max_results=3)

def universal_research(query: str):
    """
    The Synthesis Layer: Aggregates raw extracted data into a structured report.
    """
    print(f"Starting Universal Web Research for: {query}")
    
    target_site = None
    if "on " in query.lower() or "check " in query.lower():
        words = query.lower().split()
        for word in words:
            if "." in word and (word.endswith(".lk") or word.endswith(".com") or word.endswith(".net")):
                target_site = word
                break
    
    if target_site:
        raw_results = WebResearcher.search_specific_site(target_site, query)
    else:
        raw_results = WebResearcher.search_and_extract(query)
    
    report = []
    for r in raw_results:
        if "error" in r:
            continue
        report.append(f"Source [{r['id']}]: {r['title']}\nURL: {r['url']}\nContent: {r['content']}\n---")
    
    return "\n".join(report) if report else "No information found on the web."
