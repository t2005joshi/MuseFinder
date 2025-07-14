# uvicorn api:app --reload --host 0.0.0.0 --port 8000 --reload

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import os
import tempfile
import shutil
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Import your existing modules
from vocal_isolation import isolate_vocals
from speech_to_text import extract_text
from search_songs import search_genius_by_lyrics_scrape, extract_key_phrases, search_multiple_strategies
from rag_retrieval import rag_search_with_similarity
from llm_cleaner import clean_lyrics_with_llama3
from lyrics_search import search_by_lyrics
import string
import requests
import re
import gc

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

load_dotenv()  # Load .env file

allowed_origins = os.getenv("ALLOWED_ORIGINS", "")
origins = [origin.strip() for origin in allowed_origins.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional: Reduce TensorFlow logging noise
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Define response models
class ProcessingStatus(BaseModel):
    stage: str
    message: str
    progress: int  # 0-100

class SongMatch(BaseModel):
    title: str
    artist: str
    similarity: float
    genius_url: str
    youtube_url: Optional[str] = None
    spotify_url: Optional[str] = None
    search_method: str

class LyricsIdentificationResponse(BaseModel):
    success: bool
    raw_transcription: str
    cleaned_lyrics: str
    matches: List[SongMatch]
    processing_stages: List[ProcessingStatus]
    confidence_level: str

class ErrorResponse(BaseModel):
    error: str
    details: Optional[str] = None

# Utility functions from main.py
def remove_llm_headers(text: str) -> str:
    """Remove LLM-added phrases like 'Here are the cleaned-up lyrics:'"""
    lines = text.strip().splitlines()
    return '\n'.join(
        line for line in lines
        if not re.match(r'^\s*(here\s+(are|is)|these|the following)\b.*?:?', line.strip(), re.IGNORECASE)
    ).strip()

def comprehensive_search_strategy(raw_lyrics, cleaned_lyrics):
    """Enhanced search strategy that tries multiple approaches systematically"""
    all_candidates = []
    search_attempts = []
    
    # Parse lines for different strategies
    raw_lines = [line.strip() for line in raw_lyrics.split('\n') if line.strip() and len(line.strip()) > 10]
    cleaned_lines = [line.strip() for line in cleaned_lyrics.split('\n') if line.strip() and len(line.strip()) > 10]
    
    # Strategy 1: Key phrases from cleaned lyrics
    key_phrases = extract_key_phrases(cleaned_lyrics, 5)
    
    for phrase in key_phrases:
        if len(phrase.strip()) < 15:
            continue
            
        search_attempts.append(f"Key phrase: {phrase}")
        results = search_by_lyrics(phrase, max_results=8)
        if results:
            all_candidates.extend(results)
    
    # Strategy 2: Multi-strategy search
    multi_results = search_multiple_strategies(cleaned_lyrics, max_results_per_strategy=3)
    if multi_results:
        for result in multi_results:
            formatted_result = {
                'title': result.get('title', 'Unknown'),
                'artist': 'Unknown',
                'genius_url': result.get('url', ''),
                'search_method': 'multi_strategy'
            }
            all_candidates.append(formatted_result)
    
    # Strategy 3: Best individual lines from cleaned lyrics
    scored_lines = []
    for line in cleaned_lines:
        score = len(line)
        distinctive_words = ['sick', 'stomach', 'calling', 'cab', 'touching', 'chest', 'destiny']
        for word in distinctive_words:
            if word.lower() in line.lower():
                score += 15
        
        if '?' in line:
            score += 10
        if any(word in line.lower() for word in ['how', 'why', 'what', 'feel', 'heart']):
            score += 8
            
        scored_lines.append((score, line))
    
    scored_lines.sort(reverse=True, key=lambda x: x[0])
    
    for score, line in scored_lines[:3]:
        search_attempts.append(f"Cleaned line: {line}")
        results = search_by_lyrics(line, max_results=5)
        if results:
            all_candidates.extend(results)
    
    # Strategy 4: Raw transcription lines
    if len(all_candidates) < 5:
        for line in raw_lines[:3]:
            line_clean = line.translate(str.maketrans('', '', string.punctuation))
            search_attempts.append(f"Raw line: {line}")
            results = search_by_lyrics(line_clean, max_results=5)
            if results:
                all_candidates.extend(results)
    
    # Remove duplicates
    seen_urls = set()
    unique_candidates = []
    for candidate in all_candidates:
        url = candidate.get('genius_url') or candidate.get('url', '')
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_candidates.append(candidate)
    
    return unique_candidates

def determine_confidence_level(similarity_score):
    """Determine confidence level based on similarity score"""
    if similarity_score > 80:
        return "High confidence match!"
    elif similarity_score > 60:
        return "Good match found"
    elif similarity_score > 40:
        return "Possible match - verify manually"
    else:
        return "Low confidence - consider manual verification"

@app.post("/identify-lyrics", response_model=LyricsIdentificationResponse)
async def identify_lyrics(file: UploadFile = File(...)):
    """
    Main endpoint to identify lyrics from audio file
    """
    processing_stages = []
    
    # Validate file type
    if not file.filename.lower().endswith(('.mp3', '.wav', '.m4a', '.flac')):
        raise HTTPException(status_code=400, detail="Unsupported audio format. Use MP3, WAV, M4A, or FLAC")
    
    # Create temporary directory for processing
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded file
        processing_stages.append(ProcessingStatus(
            stage="upload",
            message="File uploaded successfully",
            progress=10
        ))
        
        audio_path = os.path.join(temp_dir, file.filename)
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Step 1: Isolate vocals
        processing_stages.append(ProcessingStatus(
            stage="vocal_isolation",
            message="Isolating vocals from audio...",
            progress=20
        ))
        
        try:
            vocal_path = isolate_vocals(audio_path)
        except Exception as e:
            logger.error(f"Failed to isolate vocals: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to isolate vocals: {str(e)}")
        
        # Step 2: Extract text
        processing_stages.append(ProcessingStatus(
            stage="speech_to_text",
            message="Extracting lyrics using speech-to-text...",
            progress=40
        ))
        
        try:
            raw_transcription = extract_text(vocal_path).strip()
            if not raw_transcription:
                raise ValueError("No lyrics were transcribed.")
        except Exception as e:
            logger.error(f"Speech-to-text failed: {e}")
            raise HTTPException(status_code=500, detail=f"Speech-to-text failed: {str(e)}")
        
        # Step 3: Clean lyrics
        processing_stages.append(ProcessingStatus(
            stage="lyrics_cleaning",
            message="Cleaning lyrics with AI...",
            progress=50
        ))
        
        try:
            cleaned_lyrics = clean_lyrics_with_llama3(raw_transcription)
            cleaned_lyrics = remove_llm_headers(cleaned_lyrics)
            if not cleaned_lyrics.strip():
                logger.warning("Lyrics cleaning returned empty output, using raw transcription")
                cleaned_lyrics = raw_transcription
        except Exception as e:
            logger.error(f"Lyrics cleaning failed: {e}")
            cleaned_lyrics = raw_transcription
        
        # Step 4: Search for matches
        processing_stages.append(ProcessingStatus(
            stage="searching",
            message="Searching for song matches...",
            progress=70
        ))
        
        candidates = comprehensive_search_strategy(raw_transcription, cleaned_lyrics)
        
        if not candidates:
            return LyricsIdentificationResponse(
                success=False,
                raw_transcription=raw_transcription,
                cleaned_lyrics=cleaned_lyrics,
                matches=[],
                processing_stages=processing_stages,
                confidence_level="No matches found"
            )
        
        # Step 5: Rank results
        processing_stages.append(ProcessingStatus(
            stage="ranking",
            message="Ranking matches using similarity analysis...",
            progress=85
        ))
        
        try:
            full_transcription = f"{raw_transcription}\n\n{cleaned_lyrics}".strip()
            final_results = rag_search_with_similarity(
                query=full_transcription,
                search_results=candidates,
                use_full_lyrics_comparison=True
            )
        except Exception as e:
            logger.error(f"Failed to rank results: {e}")
            final_results = candidates
        
        # Step 6: Format results
        processing_stages.append(ProcessingStatus(
            stage="completed",
            message="Processing completed successfully",
            progress=100
        ))
        
        # Convert to response format
        song_matches = []
        for song in final_results[:5]:  # Top 5 matches
            match = SongMatch(
                title=song.get('title', 'Unknown'),
                artist=song.get('artist', 'Unknown'),
                similarity=float(song.get('similarity', 0.0)),
                genius_url=song.get('genius_url') or song.get('url', ''),
                youtube_url=song.get('youtube_url'),
                spotify_url=song.get('spotify_url'),
                search_method=song.get('search_method', 'API')
            )
            song_matches.append(match)
        
        # Determine confidence
        confidence_level = "No matches found"
        if song_matches:
            top_similarity = song_matches[0].similarity
            confidence_level = determine_confidence_level(top_similarity)
        
        # Cleanup
        gc.collect()
        
        return LyricsIdentificationResponse(
            success=True,
            raw_transcription=raw_transcription,
            cleaned_lyrics=cleaned_lyrics,
            matches=song_matches,
            processing_stages=processing_stages,
            confidence_level=confidence_level
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    
    finally:
        # Cleanup temporary files
        try:
            shutil.rmtree(temp_dir)
        except:
            pass

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Audio Lyrics Identification API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2025-07-07"}

@app.get("/supported-formats")
async def get_supported_formats():
    """Get supported audio formats"""
    return {
        "supported_formats": [".mp3", ".wav", ".m4a", ".flac"],
        "max_file_size": "50MB",
        "processing_time": "2-5 minutes depending on file size"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)