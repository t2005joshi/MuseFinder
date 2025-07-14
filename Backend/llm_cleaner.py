import ollama

def clean_lyrics_with_llama3(raw_lyrics: str) -> str:
    prompt = (
        "The following text is a noisy, possibly hallucinated transcription of a song's lyrics. "
        "Please clean it up to make it look like real English song lyrics, removing repetitions, "
        "hallucinations, and non-lyric content. Only output the cleaned lyrics.\n\n"
        f"Raw lyrics:\n{raw_lyrics}\n\nCleaned lyrics:"
    )

    try:
        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": prompt}],
        )
        return response['message']['content'].strip()
    except TypeError as e:
        if "proxies" in str(e):
            raise RuntimeError("⚠️ Ollama appears to be using a patched or misconfigured requests.post() call. "
                               "Check for global proxy settings or monkey patches.")
        raise
    except Exception as e:
        raise RuntimeError(f"⚠️ Failed to clean lyrics with Llama 3: {e}")
