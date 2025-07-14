import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import quote_plus
import time
import random

def extract_key_phrases(lyrics: str, max_phrases: int = 5):
    """
    Enhanced key phrase extraction focusing on distinctive lyrics
    """
    lines = [line.strip() for line in lyrics.split('\n') if line.strip()]
    
    # Score lines based on uniqueness indicators
    scored_lines = []
    
    for line in lines:
        if len(line) < 8:  # Skip very short lines
            continue
            
        score = len(line)  # Base score on length
        line_lower = line.lower()
        
        # Boost score for distinctive patterns
        uniqueness_indicators = [
            ('coming out', 15), ('started with', 12), ('how did it end up', 20),
            ('it was only', 10), ('stomach is sick', 15), ('all in my head', 10),
            ('calling a cab', 12), ('having a smoke', 12), ('going to bed', 8),
            ('touching his chest', 15), ('falling asleep', 10)
        ]
        
        for phrase, boost in uniqueness_indicators:
            if phrase in line_lower:
                score += boost
        
        # Boost for questions (often memorable)
        if '?' in line:
            score += 8
        
        # Boost for emotional content
        emotional_words = ['sick', 'head', 'heart', 'soul', 'feel', 'love', 'hate', 'want', 'need']
        for word in emotional_words:
            if word in line_lower:
                score += 3
        
        # Penalize very common phrases
        common_phrases = ['and i', 'but i', 'when i', 'that i', 'if i', 'so i']
        for phrase in common_phrases:
            if phrase in line_lower:
                score -= 2
        
        scored_lines.append((score, line))
    
    # Sort by score and return top phrases
    scored_lines.sort(reverse=True, key=lambda x: x[0])
    return [line for score, line in scored_lines[:max_phrases]]

def search_genius_by_lyrics_scrape(lyrics_snippet: str, max_results: int = 5):
    """
    Enhanced Google search scraping with better query strategies and error handling
    """
    # Create more targeted search variations
    search_queries = []
    
    # If snippet is long, try the most distinctive parts
    if len(lyrics_snippet) > 60:
        # Split into sentences and try each
        sentences = [s.strip() for s in re.split(r'[.!?]', lyrics_snippet) if len(s.strip()) > 10]
        for sentence in sentences[:3]:  # Try top 3 sentences
            search_queries.append(f'site:genius.com "{sentence}" lyrics')
    
    # Add the main queries
    search_queries.extend([
        f'site:genius.com "{lyrics_snippet}" lyrics',
        f'site:genius.com "{lyrics_snippet}"',
        f'"{lyrics_snippet}" lyrics site:genius.com'
    ])
    
    USER_AGENTS = [
        # Windows Chrome
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",

        # macOS Safari
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.1 Safari/605.1.15",

        # Linux Firefox
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:110.0) Gecko/20100101 Firefox/110.0",

        # Windows Edge
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",

        # Android Chrome
        "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/91.0.4472.77 Mobile Safari/537.36",

        # iPhone Safari
        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 "
        "(KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
    ]
    
    def get_random_headers():
        return {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
    
    all_links = []
    
    def is_google_captcha(response_text):
        return (
            "Our systems have detected unusual traffic" in response_text
            or "/sorry/index" in response_text
            or "detected unusual traffic" in response_text
            or "unusual traffic from your computer network" in response_text
            or "captcha" in response_text.lower()
        )
    
    def backoff_sleep(retry_count, base=3.0, jitter=2.0):
        delay = base * (2 ** retry_count) + random.uniform(0, jitter)
        print(f"🕒 Sleeping for {delay:.2f}s before retrying...")
        time.sleep(delay)
    
    MAX_RETRIES = 4

    for i, query in enumerate(search_queries):
        if len(all_links) >= max_results:
            break

        print(f"🔍 Trying query {i+1}/{len(search_queries)}: {query[:50]}...")
        
        for retry in range(MAX_RETRIES):
            try:
                search_url = f"https://www.google.com/search?q={quote_plus(query)}"
                headers = get_random_headers()
                
                # Add session for connection reuse
                session = requests.Session()
                session.headers.update(headers)
                
                response = session.get(search_url, timeout=15)

                # Detect CAPTCHA or 429
                if response.status_code == 429 or is_google_captcha(response.text):
                    print(f"⚠️ Rate limited or CAPTCHA detected (attempt {retry+1})")
                    if retry < MAX_RETRIES - 1:
                        backoff_sleep(retry)
                        continue
                    else:
                        print(f"❌ Max retries reached for query: {query[:50]}...")
                        break

                response.raise_for_status()

                # Parse the page normally if no CAPTCHA
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # More comprehensive link extraction
                link_selectors = [
                    'a[href*="genius.com"]',
                    'cite:contains("genius.com")',
                    'span:contains("genius.com")'
                ]
                
                found_links_this_query = 0
                
                for selector in link_selectors:
                    try:
                        elements = soup.select(selector)
                        for element in elements:
                            href = element.get('href') or element.get_text()
                            if not href:
                                continue
                                
                            # Extract Genius URLs
                            genius_urls = re.findall(r'https://genius\.com/[^"&\s]+', href)
                            for url in genius_urls:
                                if re.match(r"https://genius\.com/.+-lyrics/?$", url):
                                    # Extract better title info
                                    title_part = url.split("/")[-1].replace("-lyrics", "")
                                    
                                    # Try to separate artist and song
                                    parts = title_part.split('-')
                                    if len(parts) >= 2:
                                        # Last part is usually song, earlier parts are artist
                                        potential_artist = ' '.join(parts[:-1]).replace('-', ' ').title()
                                        potential_song = parts[-1].replace('-', ' ').title()
                                        title = f"{potential_song} by {potential_artist}"
                                    else:
                                        title = title_part.replace("-", " ").title()
                                    
                                    # Check for duplicates
                                    if not any(link['url'] == url for link in all_links):
                                        all_links.append({
                                            "title": title,
                                            "url": url,
                                            "search_query": query  # Track which query found this
                                        })
                                        found_links_this_query += 1
                    except Exception as e:
                        print(f"⚠️ Error parsing selector {selector}: {e}")
                        continue
                
                print(f"✅ Found {found_links_this_query} new links from this query")
                
                # Add random delay between successful requests
                if i < len(search_queries) - 1:  # Don't sleep after last query
                    time.sleep(random.uniform(3, 7))
                
                break  # Successful request, break retry loop

            except requests.exceptions.Timeout:
                print(f"⚠️ Timeout on query attempt {retry+1} for '{query[:50]}...'")
                if retry < MAX_RETRIES - 1:
                    backoff_sleep(retry)
                else:
                    print(f"❌ Max retries reached due to timeouts")
            except requests.exceptions.RequestException as e:
                print(f"⚠️ Request error on query attempt {retry+1} for '{query[:50]}...': {e}")
                if retry < MAX_RETRIES - 1:
                    backoff_sleep(retry)
                else:
                    print(f"❌ Max retries reached due to request errors")
            except Exception as e:
                print(f"⚠️ Unexpected error on query attempt {retry+1} for '{query[:50]}...': {e}")
                if retry < MAX_RETRIES - 1:
                    backoff_sleep(retry)
                else:
                    print(f"❌ Max retries reached due to unexpected errors")
    
    # Enhanced filtering
    filtered_links = []
    exclude_terms = [
        'script', 'annotated', 'trailer', 'scene', 'dialogue', 'monologue',
        'interview', 'explanation', 'meaning', 'analysis', 'review'
    ]
    
    for link in all_links:
        title_lower = link['title'].lower()
        url_lower = link['url'].lower()
        
        # Skip excluded content
        if any(term in title_lower or term in url_lower for term in exclude_terms):
            continue
            
        # Prefer actual song lyrics pages
        if '-lyrics' in url_lower:
            filtered_links.append(link)
        elif len(filtered_links) < max_results:  # Only add non-lyrics if we need more results
            filtered_links.append(link)
    
    print(f"🎵 Total unique results found: {len(filtered_links)}")
    return filtered_links[:max_results]

def search_multiple_strategies(lyrics_text: str, max_results_per_strategy: int = 3):
    """
    Use multiple search strategies and combine results
    """
    all_results = []
    
    # Strategy 1: Key phrases (most distinctive lines)
    print("🎯 Strategy 1: Key phrases")
    try:
        key_phrases = extract_key_phrases(lyrics_text, 3)
        for phrase in key_phrases:
            results = search_genius_by_lyrics_scrape(phrase, max_results_per_strategy)
            for result in results:
                result['search_strategy'] = f'key_phrase: {phrase[:30]}...'
                if not any(r['url'] == result['url'] for r in all_results):
                    all_results.append(result)
    except Exception as e:
        print(f"⚠️ Error in Strategy 1: {e}")
    
    # Strategy 2: First distinctive line
    print("🎯 Strategy 2: First distinctive line")
    try:
        lines = [line.strip() for line in lyrics_text.split('\n') if len(line.strip()) > 15]
        if lines:
            first_line = lines[0]
            results = search_genius_by_lyrics_scrape(first_line, max_results_per_strategy)
            for result in results:
                result['search_strategy'] = f'first_line: {first_line[:30]}...'
                if not any(r['url'] == result['url'] for r in all_results):
                    all_results.append(result)
    except Exception as e:
        print(f"⚠️ Error in Strategy 2: {e}")
    
    # Strategy 3: Questions (if any)
    print("🎯 Strategy 3: Questions and unique phrases")
    try:
        question_lines = [line.strip() for line in lyrics_text.split('\n') if '?' in line and len(line.strip()) > 10]
        for question in question_lines[:2]:  # Try top 2 questions
            results = search_genius_by_lyrics_scrape(question, max_results_per_strategy)
            for result in results:
                result['search_strategy'] = f'question: {question[:30]}...'
                if not any(r['url'] == result['url'] for r in all_results):
                    all_results.append(result)
    except Exception as e:
        print(f"⚠️ Error in Strategy 3: {e}")
    
    # Strategy 4: Combined distinctive phrases
    print("🎯 Strategy 4: Combined phrases")
    try:
        key_phrases = extract_key_phrases(lyrics_text, 3)  # Re-extract in case Strategy 1 failed
        if len(key_phrases) >= 2:
            combined = f"{key_phrases[0]} {key_phrases[1]}"[:100]  # Limit length
            results = search_genius_by_lyrics_scrape(combined, max_results_per_strategy)
            for result in results:
                result['search_strategy'] = f'combined: {combined[:30]}...'
                if not any(r['url'] == result['url'] for r in all_results):
                    all_results.append(result)
    except Exception as e:
        print(f"⚠️ Error in Strategy 4: {e}")
    
    print(f"✅ Found {len(all_results)} unique results across all strategies")
    return all_results