from vocal_isolation import isolate_vocals
from speech_to_text import extract_text
from search_songs import search_genius_by_lyrics_scrape, extract_key_phrases, search_multiple_strategies
from rag_retrieval import rag_search_with_similarity
from llm_cleaner import clean_lyrics_with_llama3
from lyrics_search import search_by_lyrics

import os
import string
import requests
import re
import gc

# Optional: Reduce TensorFlow logging noise
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'


def normalize_path(path: str) -> str:
    path = path.strip().strip('"').strip("'")
    if path.startswith('\\\\wsl.localhost\\'):
        path = path.replace('\\\\wsl.localhost\\Ubuntu-22.04\\', '/')
        path = path.replace('\\', '/')
    return path


def remove_llm_headers(text: str) -> str:
    """Remove LLM-added phrases like 'Here are the cleaned-up lyrics:'"""
    lines = text.strip().splitlines()
    return '\n'.join(
        line for line in lines
        if not re.match(r'^\s*(here\s+(are|is)|these|the following)\b.*?:?', line.strip(), re.IGNORECASE)
    ).strip()


def comprehensive_search_strategy(raw_lyrics, cleaned_lyrics):
    """
    Enhanced search strategy that tries multiple approaches systematically
    """
    print("🔍 Starting comprehensive search strategy...")
    
    all_candidates = []
    search_attempts = []
    
    # Parse lines for different strategies
    raw_lines = [line.strip() for line in raw_lyrics.split('\n') if line.strip() and len(line.strip()) > 10]
    cleaned_lines = [line.strip() for line in cleaned_lyrics.split('\n') if line.strip() and len(line.strip()) > 10]
    
    # Strategy 1: Key phrases from cleaned lyrics (most distinctive)
    print("🎯 Strategy 1: Key phrases from cleaned lyrics")
    key_phrases = extract_key_phrases(cleaned_lyrics, 5)
    
    for i, phrase in enumerate(key_phrases):
        if len(phrase.strip()) < 15:
            continue
            
        print(f"   [{i+1}] Trying phrase: '{phrase[:60]}{'...' if len(phrase) > 60 else ''}'")
        search_attempts.append(f"Key phrase: {phrase}")
        
        results = search_by_lyrics(phrase, max_results=8)
        if results:
            print(f"       ✅ Found {len(results)} matches")
            all_candidates.extend(results)
        else:
            print(f"       ❌ No matches")
    
    # Strategy 2: Multi-strategy search (uses multiple search patterns)
    print("\n🎯 Strategy 2: Multi-strategy search patterns")
    multi_results = search_multiple_strategies(cleaned_lyrics, max_results_per_strategy=3)
    if multi_results:
        print(f"   ✅ Multi-strategy found {len(multi_results)} additional matches")
        # Convert format to match other results
        for result in multi_results:
            formatted_result = {
                'title': result.get('title', 'Unknown'),
                'artist': 'Unknown',
                'genius_url': result.get('url', ''),
                'search_method': 'multi_strategy'
            }
            all_candidates.append(formatted_result)
    
    # Strategy 3: Best individual lines from cleaned lyrics
    print("\n🎯 Strategy 3: Best individual cleaned lines")
    # Score lines by length and uniqueness
    scored_lines = []
    for line in cleaned_lines:
        score = len(line)
        # Boost lines with distinctive words
        distinctive_words = ['sick', 'stomach', 'calling', 'cab', 'touching', 'chest', 'destiny']
        for word in distinctive_words:
            if word.lower() in line.lower():
                score += 15
        
        # Boost questions and emotional content
        if '?' in line:
            score += 10
        if any(word in line.lower() for word in ['how', 'why', 'what', 'feel', 'heart']):
            score += 8
            
        scored_lines.append((score, line))
    
    scored_lines.sort(reverse=True, key=lambda x: x[0])
    
    for i, (score, line) in enumerate(scored_lines[:3]):
        print(f"   [{i+1}] Trying line (score: {score}): '{line[:50]}{'...' if len(line) > 50 else ''}'")
        search_attempts.append(f"Cleaned line: {line}")
        
        results = search_by_lyrics(line, max_results=5)
        if results:
            print(f"       ✅ Found {len(results)} matches")
            all_candidates.extend(results)
        else:
            print(f"       ❌ No matches")
    
    # Strategy 4: Best raw transcription lines (in case cleaning removed important info)
    if len(all_candidates) < 5:
        print("\n🎯 Strategy 4: Raw transcription lines")
        for i, line in enumerate(raw_lines[:3]):
            line_clean = line.translate(str.maketrans('', '', string.punctuation))
            print(f"   [{i+1}] Trying raw line: '{line[:50]}{'...' if len(line) > 50 else ''}'")
            search_attempts.append(f"Raw line: {line}")
            
            results = search_by_lyrics(line_clean, max_results=5)
            if results:
                print(f"       ✅ Found {len(results)} matches")
                all_candidates.extend(results)
    
    # Strategy 5: Combined phrases for better context
    if len(all_candidates) < 5 and len(cleaned_lines) >= 2:
        print("\n🎯 Strategy 5: Combined phrases")
        for i in range(min(3, len(cleaned_lines) - 1)):
            combined = f"{cleaned_lines[i].strip()} {cleaned_lines[i+1].strip()}"
            if len(combined) > 120:  # Keep reasonable length
                combined = combined[:120]
                
            print(f"   [{i+1}] Trying combined: '{combined[:50]}{'...' if len(combined) > 50 else ''}'")
            search_attempts.append(f"Combined: {combined}")
            
            results = search_by_lyrics(combined, max_results=3)
            if results:
                print(f"       ✅ Found {len(results)} matches")
                all_candidates.extend(results)
    
    # Strategy 6: Fallback web scraping if still not enough results
    if len(all_candidates) < 3:
        print("\n🎯 Strategy 6: Fallback web scraping")
        fallback_terms = (key_phrases[:2] + cleaned_lines[:2])
        
        for term in fallback_terms:
            if len(term.strip()) < 15:
                continue
                
            print(f"   🕷️ Scraping with: '{term[:50]}{'...' if len(term) > 50 else ''}'")
            search_attempts.append(f"Web scraping: {term}")
            
            scrape_results = search_genius_by_lyrics_scrape(term, max_results=3)
            if scrape_results:
                print(f"       ✅ Scraping found {len(scrape_results)} matches")
                for result in scrape_results:
                    formatted_result = {
                        'title': result.get('title', 'Unknown'),
                        'artist': 'Unknown',
                        'genius_url': result.get('url', ''),
                        'search_method': 'web_scraping'
                    }
                    all_candidates.append(formatted_result)
    
    # Remove duplicates while preserving order
    seen_urls = set()
    unique_candidates = []
    for candidate in all_candidates:
        url = candidate.get('genius_url') or candidate.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_candidates.append(candidate)
    
    print(f"\n📊 Search Summary:")
    print(f"   • Total searches attempted: {len(search_attempts)}")
    print(f"   • Total candidates found: {len(all_candidates)}")
    print(f"   • Unique candidates: {len(unique_candidates)}")
    
    if not unique_candidates:
        print("\n🔍 Search attempts made:")
        for attempt in search_attempts[-5:]:  # Show last 5 attempts
            print(f"   • {attempt[:80]}{'...' if len(attempt) > 80 else ''}")
    
    return unique_candidates


def main():
    print("🎵 Enter the path to your audio file (MP3/WAV):")
    audio_path = input("→ ").strip()
    audio_path = normalize_path(audio_path)

    if not os.path.isfile(audio_path):
        print(f"❌ File not found at: {audio_path}")
        return

    try:
        print("🎤 Isolating vocals...")
        vocal_path = isolate_vocals(audio_path)
    except Exception as e:
        print(f"❌ Failed to isolate vocals: {e}")
        return

    try:
        print("\n🗣️ Extracting lyrics (speech-to-text)...")
        raw_transcription = extract_text(vocal_path).strip()
        if not raw_transcription:
            raise ValueError("No lyrics were transcribed.")
        print("📝 Raw Transcription:\n", raw_transcription)

        print("\n🤖 Cleaning lyrics with Llama 3...")
        cleaned_lyrics = clean_lyrics_with_llama3(raw_transcription)
        cleaned_lyrics = remove_llm_headers(cleaned_lyrics)
        if not cleaned_lyrics.strip():
            print("⚠️ Lyrics cleaning returned empty output, using raw transcription")
            cleaned_lyrics = raw_transcription
        
        print("📝 Cleaned Lyrics:\n", cleaned_lyrics)

        # Use comprehensive search strategy
        candidates = comprehensive_search_strategy(raw_transcription, cleaned_lyrics)

        if not candidates:
            print("❌ No matches found with any search strategy.")
            
            # Create fallback search URLs
            lines = [line.strip() for line in cleaned_lyrics.split('\n') if len(line.strip()) > 15]
            if lines:
                fallback_line = lines[0]
                google_url = f"https://www.google.com/search?q={requests.utils.quote('site:genius.com ' + fallback_line)}"
                genius_url = f"https://genius.com/search?q={requests.utils.quote(fallback_line)}"
                
                print(f"\n🔗 Manual search suggestions:")
                print(f"   Google: {google_url}")
                print(f"   Genius: {genius_url}")
            return

        print(f"\n🤖 Ranking {len(candidates)} candidates using full transcription similarity...")
        
        # Use FULL transcription for similarity matching
        full_transcription = f"{raw_transcription}\n\n{cleaned_lyrics}".strip()
        
    except Exception as e:
        print(f"❌ Speech-to-text or lyric cleaning failed: {e}")
        return

    try:
        # Enhanced RAG search with full transcription
        final_results = rag_search_with_similarity(
            query=full_transcription,  # Use complete transcription for better matching
            search_results=candidates,
            use_full_lyrics_comparison=True  # Enable enhanced comparison
        )
        
        print(f"✅ Successfully ranked and enriched results")
        
    except Exception as e:
        print(f"❌ Failed to rank results: {e}")
        print("📋 Showing unranked results...")
        final_results = candidates

    # Display results
    if not final_results:
        print("❌ No results after processing.")
        return

    print(f"\n🎧 Top {min(5, len(final_results))} Matches (sorted by similarity):\n")
    
    for i, song in enumerate(final_results[:5], 1):
        title = song.get('title', 'Unknown')
        artist = song.get('artist', 'Unknown')
        similarity = song.get('similarity', 0.0)
        genius_url = song.get('genius_url') or song.get('url', 'N/A')
        youtube_url = song.get('youtube_url', 'N/A')
        spotify_url = song.get('spotify_url', 'N/A')
        search_method = song.get('search_method', 'API')
        
        print(f"[{i}] {title}")
        if artist and artist != 'Unknown':
            print(f"    Artist: {artist}")
        
        if isinstance(similarity, (int, float)) and similarity > 0:
            print(f"    📊 Similarity: {similarity:.1f}%")
        
        print(f"    🔍 Found via: {search_method}")
        print(f"    🔗 Genius: {genius_url}")
        
        if youtube_url and youtube_url != 'N/A':
            print(f"    ▶️ YouTube: {youtube_url}")
        if spotify_url and spotify_url != 'N/A':
            print(f"    🎶 Spotify: {spotify_url}")
        print()

    # Show confidence indicator
    if final_results and isinstance(final_results[0].get('similarity'), (int, float)):
        top_similarity = final_results[0].get('similarity', 0)
        if top_similarity > 80:
            print("🎯 High confidence match!")
        elif top_similarity > 60:
            print("👍 Good match found")
        elif top_similarity > 40:
            print("🤔 Possible match - verify manually")
        else:
            print("⚠️ Low confidence - consider manual verification")

    gc.collect()


if __name__ == "__main__":
    main()
