from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from scipy.spatial.distance import cosine
import urllib.parse
import re
import requests
from bs4 import BeautifulSoup
import time
import numpy as np

# Load embedding model once
try:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("✅ Sentence transformer model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load sentence transformer: {e}")
    model = None

# Try importing YouTube search with fallback
try:
    from youtubesearchpython import VideosSearch
    YOUTUBE_AVAILABLE = True
except ImportError:
    print("⚠️ youtubesearchpython not available. YouTube links will be generated as search URLs.")
    YOUTUBE_AVAILABLE = False


def encode(text: str):
    """Encodes a string into a dense vector using SentenceTransformer."""
    if model is None:
        return None
    try:
        return model.encode(text, convert_to_numpy=True)
    except Exception as e:
        print(f"⚠️ Encoding error: {e}")
        return None


def parse_genius_url(url: str) -> tuple:
    """
    Enhanced Genius URL parser that handles various URL formats.
    Returns: (title, artist) tuple
    """
    if not url:
        return None, None
        
    try:
        # Clean up the URL first
        url = url.strip().split('?')[0]  # Remove query parameters
        
        # Handle different Genius URL patterns
        patterns = [
            r'genius\.com/([^/]+)-([^/]+?)-lyrics/?$',  # artist-song-lyrics
            r'genius\.com/([^/]+)-([^/]+?)/?$',         # artist-song
            r'genius\.com/(.+?)-lyrics/?$',             # combined-name-lyrics
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:
                    artist_raw, title_raw = match.groups()
                else:
                    # For single group, try to split on common patterns
                    combined = match.group(1)
                    # Look for artist indicators
                    if ' by ' in combined:
                        parts = combined.split(' by ')
                        title_raw, artist_raw = parts[0], parts[1] if len(parts) > 1 else 'Unknown'
                    else:
                        # Try to split on the last dash (often separates title from artist)
                        parts = combined.rsplit('-', 1)
                        if len(parts) == 2:
                            title_raw, artist_raw = parts
                        else:
                            title_raw, artist_raw = combined, 'Unknown'
                
                # Clean up the extracted parts
                def clean_part(part):
                    if not part:
                        return 'Unknown'
                    # Replace hyphens with spaces, remove special chars, title case
                    cleaned = re.sub(r'[^a-zA-Z0-9\s]', ' ', part.replace('-', ' '))
                    cleaned = ' '.join(cleaned.split())
                    return cleaned.title() if cleaned else 'Unknown'
                
                title = clean_part(title_raw)
                artist = clean_part(artist_raw)
                
                return title, artist
                
    except Exception as e:
        print(f"⚠️ Failed to parse Genius URL '{url}': {e}")
    
    return None, None


def get_lyrics_from_genius(url: str, max_retries: int = 2) -> str:
    """
    Enhanced lyrics scraping with better error handling and retry logic.
    """
    if not url:
        return ""
        
    for attempt in range(max_retries):
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Enhanced selectors for lyrics (Genius updates their CSS frequently)
            lyrics_selectors = [
                '[data-lyrics-container="true"]',
                '.lyrics',
                '.Lyrics__Container-sc-1ynbvzw-6',
                '.LyricsBody__Container-sc-1ynbvzw-6',
                '[class*="lyrics"]',
                '[class*="Lyrics"]',
                '[class*="LyricsBody"]',
                '.song_body-lyrics p',
                '.verse, .chorus, .bridge'
            ]
            
            lyrics_text = ""
            for selector in lyrics_selectors:
                lyrics_elements = soup.select(selector)
                if lyrics_elements:
                    for element in lyrics_elements:
                        # Better text extraction preserving structure
                        text = element.get_text(separator='\n', strip=True)
                        if text and len(text) > 50:
                            lyrics_text += text + "\n"
                    if lyrics_text:
                        break
            
            if lyrics_text:
                # Clean up the lyrics text
                lyrics_text = re.sub(r'\n+', '\n', lyrics_text)
                lyrics_text = re.sub(r'\[.*?\]', '', lyrics_text)
                lyrics_text = re.sub(r'\s+', ' ', lyrics_text.strip())
                return lyrics_text[:1500]
                
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout getting lyrics from {url} (attempt {attempt + 1})")
            time.sleep(1)
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Request error getting lyrics from {url}: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Unexpected error getting lyrics from {url}: {e}")
            break
    
    return ""


def calculate_enhanced_similarity(query_lyrics: str, candidate_text: str, 
                                lyrics_content: str = "", title: str = "", 
                                artist: str = "") -> float:
    """
    Enhanced similarity calculation using multiple comparison strategies.
    """
    if model is None:
        return 0.0
    
    try:
        query_vector = encode(query_lyrics)
        if query_vector is None:
            return 0.0
        
        similarities = []
        
        # 1. Direct candidate text similarity
        if candidate_text.strip():
            candidate_vector = encode(candidate_text)
            if candidate_vector is not None:
                sim = 1 - cosine(query_vector, candidate_vector)
                similarities.append(('direct', sim, 1.0))
        
        # 2. Lyrics content similarity (highest weight if available)
        if lyrics_content.strip():
            lyrics_vector = encode(lyrics_content)
            if lyrics_vector is not None:
                sim = 1 - cosine(query_vector, lyrics_vector)
                similarities.append(('lyrics', sim, 2.0))  # Higher weight for actual lyrics
        
        # 3. Individual line matching (check if any query lines match well)
        query_lines = [line.strip() for line in query_lyrics.split('\n') 
                      if line.strip() and len(line.strip()) > 10]
        
        if lyrics_content and query_lines:
            lyrics_lines = [line.strip() for line in lyrics_content.split('\n')
                           if line.strip() and len(line.strip()) > 10]
            
            best_line_similarity = 0.0
            for q_line in query_lines[:5]:  # Check top 5 query lines
                q_vector = encode(q_line)
                if q_vector is None:
                    continue
                    
                for l_line in lyrics_lines[:10]:  # Against top 10 lyrics lines
                    l_vector = encode(l_line)
                    if l_vector is not None:
                        line_sim = 1 - cosine(q_vector, l_vector)
                        best_line_similarity = max(best_line_similarity, line_sim)
            
            if best_line_similarity > 0:
                similarities.append(('best_line', best_line_similarity, 1.5))
        
        # 4. Metadata similarity (title + artist)
        if title.strip() and artist.strip():
            metadata_text = f"{title} {artist}"
            meta_vector = encode(metadata_text)
            if meta_vector is not None:
                sim = 1 - cosine(query_vector, meta_vector)
                similarities.append(('metadata', sim, 0.5))  # Lower weight
        
        # Calculate weighted average
        if similarities:
            total_weight = sum(weight for _, _, weight in similarities)
            weighted_sum = sum(sim * weight for _, sim, weight in similarities)
            final_similarity = weighted_sum / total_weight
            
            # Boost for multiple positive signals
            if len([s for _, s, _ in similarities if s > 0.3]) >= 2:
                final_similarity *= 1.1  # 10% boost
            
            return max(0.0, min(1.0, final_similarity))  # Clamp to [0, 1]
        
        return 0.0
        
    except Exception as e:
        print(f"⚠️ Error calculating similarity: {e}")
        return 0.0


def rank_by_similarity(query_lyrics: str, candidates: List[Dict], 
                      use_full_lyrics_comparison: bool = True) -> List[Dict]:
    """
    Enhanced ranking with full lyrics comparison and better similarity calculation.
    """
    if model is None:
        print("⚠️ Similarity ranking unavailable - returning original order")
        return candidates
    
    print(f"🔄 Ranking {len(candidates)} candidates with enhanced similarity matching...")
    
    for i, song in enumerate(candidates):
        try:
            # Extract basic info
            title = song.get('title', '')
            artist = song.get('artist', '')
            genius_url = song.get('genius_url') or song.get('url')
            
            # Fill missing title/artist from URL if needed
            if (not title or title.lower() in ['unknown', 'unknown title']) and genius_url:
                parsed_title, parsed_artist = parse_genius_url(genius_url)
                if parsed_title:
                    title = parsed_title
                    song['title'] = title
                if parsed_artist and (not artist or artist.lower() in ['unknown', 'unknown artist']):
                    artist = parsed_artist
                    song['artist'] = artist
            
            # Get lyrics content if enabled and URL available
            lyrics_content = ""
            if use_full_lyrics_comparison and genius_url:
                print(f"   📖 Fetching lyrics for candidate {i+1}: {title}")
                lyrics_content = get_lyrics_from_genius(genius_url)
                if lyrics_content:
                    song['fetched_lyrics'] = lyrics_content[:200] + "..." if len(lyrics_content) > 200 else lyrics_content
                else:
                    print(f"   ⚠️ Could not fetch lyrics for {title}")
            
            # Build candidate text for comparison
            candidate_text_parts = []
            
            if title and title.lower() != 'unknown':
                candidate_text_parts.append(title)
            if artist and artist.lower() != 'unknown':
                candidate_text_parts.append(artist)
            if song.get('lyrics'):  # Existing lyrics field
                candidate_text_parts.append(song['lyrics'])
            
            candidate_text = ' '.join(candidate_text_parts)
            if not candidate_text.strip():
                candidate_text = genius_url or "unknown song"
            
            # Calculate enhanced similarity
            similarity = calculate_enhanced_similarity(
                query_lyrics=query_lyrics,
                candidate_text=candidate_text,
                lyrics_content=lyrics_content,
                title=title,
                artist=artist
            )
            
            song['similarity'] = round(similarity * 100, 2)
            song['ranking_method'] = 'enhanced_full_lyrics' if use_full_lyrics_comparison else 'basic'
            
            print(f"   ✅ Candidate {i+1}: {title} - Similarity: {song['similarity']:.1f}%")
            
        except Exception as e:
            print(f"⚠️ Error processing candidate {i+1} ({song.get('title', 'Unknown')}): {e}")
            song['similarity'] = 0.0
            song['ranking_method'] = 'error'

    # Sort by similarity
    ranked = sorted(candidates, key=lambda x: x.get('similarity', 0), reverse=True)
    
    print(f"🎯 Top candidate: {ranked[0].get('title', 'Unknown')} ({ranked[0].get('similarity', 0):.1f}%)")
    return ranked


def find_youtube_link(query: str) -> str:
    """
    Enhanced YouTube search with better query formatting.
    """
    if not YOUTUBE_AVAILABLE:
        encoded_query = urllib.parse.quote_plus(f"{query} official music video")
        return f"https://www.youtube.com/results?search_query={encoded_query}"
    
    try:
        # Try multiple search variations
        search_terms = [
            f"{query} official music video",
            f"{query} official video",
            f"{query} music video",
            query
        ]
        
        for term in search_terms:
            try:
                search = VideosSearch(term, limit=1)
                results = search.result().get("result", [])
                if results:
                    return results[0].get("link")
            except:
                continue
                
    except Exception as e:
        print(f"⚠️ YouTube search error: {e}")
    
    # Fallback to search URL
    encoded_query = urllib.parse.quote_plus(f"{query} official music video")
    return f"https://www.youtube.com/results?search_query={encoded_query}"


def find_spotify_link(query: str) -> str:
    """Enhanced Spotify search URL generation."""
    # Clean query for better search results
    clean_query = re.sub(r'[^\w\s]', ' ', query)
    clean_query = ' '.join(clean_query.split())
    
    encoded_query = urllib.parse.quote_plus(clean_query)
    return f"https://open.spotify.com/search/{encoded_query}"


def enrich_with_links(songs: List[Dict]) -> List[Dict]:
    """
    Enhanced link enrichment with better error handling.
    """
    for i, song in enumerate(songs[:5]):  # Only enrich top 5
        title = song.get('title') or 'Unknown Title'
        artist = song.get('artist') or 'Unknown Artist'
        
        # Skip if both are unknown or invalid
        if (title.lower() in ['unknown title', 'unknown'] and 
            artist.lower() in ['unknown artist', 'unknown']):
            continue
            
        # Create search query
        if artist.lower() not in ['unknown artist', 'unknown']:
            query = f"{title} {artist}".strip()
        else:
            query = title.strip()
        
        print(f"   🔗 Enriching [{i+1}] {title} by {artist}")
        
        try:
            # Add YouTube link
            if not song.get('youtube_url'):
                song['youtube_url'] = find_youtube_link(query)
                time.sleep(0.3)  # Rate limiting
            
            # Add Spotify link
            if not song.get('spotify_url'):
                song['spotify_url'] = find_spotify_link(query)
                
        except Exception as e:
            print(f"   ⚠️ Error enriching {title}: {e}")

    return songs


def rag_search_with_similarity(query: str, search_results: List[Dict], 
                              use_full_lyrics_comparison: bool = False) -> List[Dict]:
    """
    Main entry point with enhanced processing and the option for full lyrics comparison.
    
    Args:
        query: The full transcribed lyrics to compare against
        search_results: List of candidate songs from search
        use_full_lyrics_comparison: Whether to fetch and compare actual lyrics (slower but more accurate)
    """
    if not search_results:
        print("⚠️ No search results to process")
        return []
    
    print(f"🔄 Processing {len(search_results)} search results...")
    print(f"🎯 Full lyrics comparison: {'ENABLED' if use_full_lyrics_comparison else 'DISABLED'}")
    
    # Rank by similarity
    try:
        ranked = rank_by_similarity(query, search_results, use_full_lyrics_comparison)
        print(f"✅ Ranked {len(ranked)} results by similarity")
    except Exception as e:
        print(f"⚠️ Similarity ranking failed: {e}")
        ranked = search_results
    
    # Enrich with links
    try:
        enriched = enrich_with_links(ranked)
        print(f"✅ Enriched top results with streaming links")
        return enriched
    except Exception as e:
        print(f"⚠️ Link enrichment failed: {e}")
        return ranked


# Utility functions for testing and debugging
def test_similarity_matching():
    """Test similarity matching with sample data"""
    sample_query = "started out with a kiss how did it end up like this stomach is sick"
    sample_candidates = [
        {
            'title': 'Mr Brightside',
            'artist': 'The Killers',
            'genius_url': 'https://genius.com/the-killers-mr-brightside-lyrics'
        },
        {
            'title': 'Some Other Song',
            'artist': 'Different Artist',
            'genius_url': 'https://genius.com/different-artist-some-other-song-lyrics'
        }
    ]
    
    results = rag_search_with_similarity(sample_query, sample_candidates, use_full_lyrics_comparison=True)
    
    print("Test Results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.get('title')} - {result.get('similarity', 0):.1f}%")


if __name__ == "__main__":
    test_similarity_matching()