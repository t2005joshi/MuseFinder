import lyricsgenius
import os
from typing import List, Dict
from search_songs import search_genius_by_lyrics_scrape, extract_key_phrases, search_multiple_strategies

# Use environment variable for API token
GENIUS_TOKEN = os.getenv('GENIUS_TOKEN', "")

# Initialize Genius client with better settings
genius = lyricsgenius.Genius(
    GENIUS_TOKEN, 
    skip_non_songs=True, 
    excluded_terms=["(Remix)", "(Live)", "(Acoustic)", "(Demo)", "Script", "Annotated", "Interview"],
    remove_section_headers=True,
    timeout=15
)

def search_by_lyrics_api_enhanced(lyrics_snippet: str, max_results: int = 8) -> List[Dict]:
    """
    Enhanced API search with better term selection and error handling
    """
    results = []
    
    try:
        # Create diverse search terms
        search_terms = []
        
        # Add the original snippet (truncated if too long)
        if len(lyrics_snippet) <= 100:
            search_terms.append(lyrics_snippet)
        
        # Add key phrases
        key_phrases = extract_key_phrases(lyrics_snippet, 4)
        search_terms.extend(key_phrases)
        
        # Add individual meaningful lines
        lines = [line.strip() for line in lyrics_snippet.split('\n') if len(line.strip()) > 12]
        search_terms.extend(lines[:3])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_terms = []
        for term in search_terms:
            if term not in seen and len(term.strip()) > 8:
                seen.add(term)
                unique_terms.append(term)
        
        print(f"   🔍 Trying {len(unique_terms)} different search terms via API")
        
        for i, term in enumerate(unique_terms[:6]):  # Limit to prevent too many API calls
            try:
                print(f"   📡 API search {i+1}: '{term[:40]}{'...' if len(term) > 40 else ''}'")
                
                search_result = genius.search_songs(term, per_page=min(max_results, 10))
                
                if search_result and 'hits' in search_result:
                    for hit in search_result['hits']:
                        result = hit['result']
                        
                        # Skip non-song results
                        if result.get('_type') != 'song':
                            continue
                        
                        # Skip certain types of content
                        title = result.get('title', '').lower()
                        if any(skip_word in title for skip_word in ['interview', 'script', 'skit', 'interlude']):
                            continue
                            
                        song_info = {
                            "title": result['title'],
                            "artist": result['primary_artist']['name'],
                            "genius_url": result['url'],
                            "search_term": term,
                            "api_confidence": hit.get('highlights', []) != []  # Has highlights = better match
                        }
                        
                        # Avoid duplicates
                        if not any(r['genius_url'] == song_info['genius_url'] for r in results):
                            results.append(song_info)
                
                # If we got some good results early, we can be less aggressive
                if len(results) >= max_results:
                    break
                    
            except Exception as e:
                print(f"   ⚠️ API error with term '{term[:30]}...': {e}")
                continue
                
    except Exception as e:
        print(f"⚠️ Genius API search error: {e}")
    
    print(f"   ✅ API found {len(results)} results")
    return results

def search_by_lyrics_scrape_enhanced(lyrics_snippet: str, max_results: int = 8) -> List[Dict]:
    """
    Enhanced scraping search using multiple strategies
    """
    print("   🕷️ Using enhanced web scraping...")
    
    try:
        # Use the multi-strategy search from search_songs.py
        results = search_multiple_strategies(lyrics_snippet, max_results_per_strategy=3)
        
        # Convert to consistent format
        formatted_results = []
        for result in results:
            # Try to extract artist from title or URL
            title = result.get('title', 'Unknown')
            artist = 'Unknown'
            
            # If title contains "by", split it
            if ' by ' in title:
                parts = title.split(' by ')
                if len(parts) == 2:
                    title, artist = parts[0].strip(), parts[1].strip()
            
            song_info = {
                "title": title,
                "artist": artist,
                "genius_url": result['url'],
                "search_term": result.get('search_strategy', 'scraping'),
                "scrape_method": result.get('search_strategy', 'unknown')
            }
            
            formatted_results.append(song_info)
        
        print(f"   ✅ Scraping found {len(formatted_results)} results")
        return formatted_results[:max_results]
        
    except Exception as e:
        print(f"⚠️ Enhanced scraping error: {e}")
        return []

def search_by_lyrics(lyrics_snippet: str, max_results: int = 10) -> List[Dict]:
    """
    Enhanced combined search function with better strategy coordination
    """
    print(f"🔍 Enhanced search for: '{lyrics_snippet[:60]}{'...' if len(lyrics_snippet) > 60 else ''}'")
    
    all_results = []
    
    # Strategy 1: Try API first (faster, more reliable when it works)
    print("📡 Trying Genius API...")
    api_results = search_by_lyrics_api_enhanced(lyrics_snippet, max_results // 2)
    all_results.extend(api_results)
    
    # Strategy 2: Enhanced scraping (more comprehensive)
    if len(api_results) < max_results // 2:
        print("🕷️ Complementing with enhanced web scraping...")
        scrape_results = search_by_lyrics_scrape_enhanced(lyrics_snippet, max_results - len(api_results))
        
        # Merge results, avoiding duplicates
        for result in scrape_results:
            if not any(r['genius_url'] == result['genius_url'] for r in all_results):
                all_results.append(result)
    
    # Strategy 3: If still not enough results, try fallback methods
    if len(all_results) < 3:
        print("🔄 Trying fallback search methods...")
        
        # Try with individual distinctive lines
        lines = [line.strip() for line in lyrics_snippet.split('\n') if len(line.strip()) > 15]
        for line in lines[:2]:
            fallback_results = search_genius_by_lyrics_scrape(line, 2)
            for result in fallback_results:
                formatted_result = {
                    "title": result.get('title', 'Unknown'),
                    "artist": 'Unknown',
                    "genius_url": result['url'],
                    "search_term": f"fallback: {line[:30]}...",
                    "fallback_method": True
                }
                
                if not any(r['genius_url'] == formatted_result['genius_url'] for r in all_results):
                    all_results.append(formatted_result)
    
    print(f"✅ Total unique results found: {len(all_results)}")
    
    # Sort results by confidence indicators
    def sort_key(result):
        score = 0
        
        # Prefer API results
        if result.get('api_confidence'):
            score += 20
        elif 'search_term' in result and 'API' in str(result['search_term']):
            score += 10
            
        # Prefer results from key phrases
        if 'key_phrase' in str(result.get('search_term', '')):
            score += 15
            
        # Prefer results from questions
        if 'question' in str(result.get('search_term', '')):
            score += 12
            
        # Prefer results with proper titles
        if result.get('title', '').lower() not in ['unknown', '']:
            score += 5
            
        return score
    
    all_results.sort(key=sort_key, reverse=True)
    
    return all_results[:max_results]

def get_song_lyrics(song_url: str) -> str:
    """
    Get full lyrics from a Genius URL with better error handling
    """
    try:
        # Extract song ID from URL
        song_id = song_url.split('/')[-1].replace('-lyrics', '')
        song = genius.song(song_id)
        return song.lyrics if song else ""
    except Exception as e:
        print(f"⚠️ Error getting lyrics from {song_url}: {e}")
        return ""