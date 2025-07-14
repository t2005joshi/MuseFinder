import React, { useState, useRef } from 'react';

function App() {
  const [file, setFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [activeTab, setActiveTab] = useState('cleaned');
  const [processingStage, setProcessingStage] = useState(null);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef(null);

  const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  const handleFileSelect = (selectedFile) => {
    // Validate file type
    const validTypes = ['audio/mpeg', 'audio/wav', 'audio/mp4', 'audio/flac', 'audio/x-m4a'];
    const validExtensions = ['.mp3', '.wav', '.m4a', '.flac'];
    
    const fileExtension = selectedFile.name.toLowerCase().substring(selectedFile.name.lastIndexOf('.'));
    
    if (!validTypes.includes(selectedFile.type) && !validExtensions.includes(fileExtension)) {
      setError('Please select a valid audio file (MP3, WAV, M4A, or FLAC)');
      return;
    }

    // Validate file size (50MB max)
    const maxSize = 50 * 1024 * 1024;
    if (selectedFile.size > maxSize) {
      setError('File size must be less than 50MB');
      return;
    }

    setFile(selectedFile);
    setError(null);
    setResults(null);
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragOver(false);

    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const handleFileInputChange = (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const processAudio = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setResults(null);
    setProgress(0);
    setProcessingStage('upload');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/identify-lyrics`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to process audio');
      }

      if (data.success) {
        setResults(data);
        setProgress(100);
        setProcessingStage('completed');
      } else {
        setError('No matches found for this audio');
        setResults(data);
      }
    } catch (err) {
      setError(err.message || 'An error occurred while processing the audio');
      console.error('Processing error:', err);
    } finally {
      setLoading(false);
    }
  };

  const removeFile = () => {
    setFile(null);
    setResults(null);
    setError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const resetApp = () => {
    setFile(null);
    setResults(null);
    setError(null);
    setLoading(false);
    setProgress(0);
    setProcessingStage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const getConfidenceClass = (confidenceText) => {
    if (confidenceText.includes('High confidence')) return 'confidence-high';
    if (confidenceText.includes('Good match')) return 'confidence-good';
    if (confidenceText.includes('Possible match') || confidenceText.includes('Low confidence')) return 'confidence-low';
    return 'confidence-none';
  };

  const getProcessingStages = () => {
    const stages = [
      { key: 'upload', label: 'Upload' },
      { key: 'vocal_isolation', label: 'Vocals' },
      { key: 'speech_to_text', label: 'Text' },
      { key: 'lyrics_cleaning', label: 'Clean' },
      { key: 'searching', label: 'Search' },
      { key: 'ranking', label: 'Rank' },
      { key: 'completed', label: 'Done' }
    ];

    return stages.map(stage => ({
      ...stage,
      completed: processingStage === 'completed' || (processingStage && stages.findIndex(s => s.key === processingStage) > stages.findIndex(s => s.key === stage.key)),
      active: processingStage === stage.key
    }));
  };

  return (
    <div style={{
      margin: 0,
      padding: 0,
      boxSizing: 'border-box',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Oxygen", "Ubuntu", "Cantarell", "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
      WebkitFontSmoothing: 'antialiased',
      MozOsxFontSmoothing: 'grayscale',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      minHeight: '100vh',
      color: '#333',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '20px'
    }}>
      <div style={{
        background: 'rgba(255, 255, 255, 0.95)',
        backdropFilter: 'blur(10px)',
        borderRadius: '20px',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
        padding: '40px',
        maxWidth: '800px',
        width: '100%',
        margin: '20px'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '40px' }}>
          <h1 style={{
            fontSize: '2.5rem',
            fontWeight: '700',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            marginBottom: '10px'
          }}>
            🎵 MuseFinder
          </h1>
          <p style={{
            fontSize: '1.1rem',
            color: '#666',
            marginBottom: '30px'
          }}>
            Upload an audio file and let AI identify the song by analyzing its lyrics
          </p>
        </div>

        {!loading && !results && (
          <div style={{ marginBottom: '30px' }}>
            <div 
              style={{
                border: `3px dashed ${dragOver ? '#764ba2' : '#667eea'}`,
                borderRadius: '15px',
                padding: '40px',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                background: dragOver ? 'rgba(102, 126, 234, 0.15)' : 'rgba(102, 126, 234, 0.05)',
                position: 'relative',
                overflow: 'hidden',
                transform: dragOver ? 'scale(1.02)' : 'none'
              }}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div style={{ fontSize: '3rem', marginBottom: '20px', opacity: '0.7' }}>
                🎧
              </div>
              <div style={{
                fontSize: '1.2rem',
                fontWeight: '600',
                color: '#667eea',
                marginBottom: '10px'
              }}>
                {file ? 'Change Audio File' : 'Drop your audio file here'}
              </div>
              <div style={{
                fontSize: '0.9rem',
                color: '#888',
                marginBottom: '20px'
              }}>
                Supports MP3, WAV, M4A, and FLAC files up to 50MB
              </div>
              <button 
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  padding: '12px 30px',
                  borderRadius: '25px',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: 'pointer',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)'
                }}
                type="button"
              >
                {file ? 'Choose Different File' : 'Choose File'}
              </button>
              <input
                ref={fileInputRef}
                type="file"
                style={{ display: 'none' }}
                accept=".mp3,.wav,.m4a,.flac,audio/*"
                onChange={handleFileInputChange}
              />
            </div>

            {file && (
              <div style={{
                marginTop: '20px',
                padding: '15px',
                background: 'rgba(102, 126, 234, 0.1)',
                borderRadius: '10px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <span style={{ fontWeight: '600', color: '#667eea' }}>{file.name}</span>
                  <span style={{ fontSize: '0.9rem', color: '#888' }}>
                    ({formatFileSize(file.size)})
                  </span>
                </div>
                <button 
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#e74c3c',
                    cursor: 'pointer',
                    fontSize: '1.2rem',
                    padding: '5px',
                    borderRadius: '50%',
                    transition: 'all 0.3s ease'
                  }}
                  onClick={removeFile}
                >
                  ✕
                </button>
              </div>
            )}

            {file && (
              <button 
                style={{
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  padding: '15px 40px',
                  borderRadius: '25px',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  transition: 'all 0.3s ease',
                  boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)',
                  width: '100%',
                  marginTop: '20px',
                  opacity: loading ? '0.6' : '1'
                }}
                onClick={processAudio}
                disabled={loading}
              >
                🎵 Identify Song
              </button>
            )}
          </div>
        )}

        {loading && (
          <div style={{ textAlign: 'center', padding: '40px' }}>
            <div style={{
              width: '60px',
              height: '60px',
              border: '4px solid rgba(102, 126, 234, 0.3)',
              borderTop: '4px solid #667eea',
              borderRadius: '50%',
              animation: 'spin 1s linear infinite',
              margin: '0 auto 20px'
            }}></div>
            <div style={{
              fontSize: '1.2rem',
              fontWeight: '600',
              color: '#667eea',
              marginBottom: '10px'
            }}>
              Processing Audio...
            </div>
            <div style={{
              fontSize: '0.9rem',
              color: '#888',
              marginBottom: '20px'
            }}>
              This may take 2-5 minutes depending on file size
            </div>
            
            <div style={{
              width: '100%',
              height: '8px',
              background: 'rgba(102, 126, 234, 0.2)',
              borderRadius: '4px',
              overflow: 'hidden',
              marginBottom: '20px'
            }}>
              <div style={{
                height: '100%',
                background: 'linear-gradient(90deg, #667eea 0%, #764ba2 100%)',
                borderRadius: '4px',
                transition: 'width 0.3s ease',
                width: `${progress}%`
              }}></div>
            </div>
            
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              marginTop: '20px',
              fontSize: '0.8rem',
              flexWrap: 'wrap',
              gap: '10px'
            }}>
              {getProcessingStages().map((stage) => (
                <div 
                  key={stage.key}
                  style={{
                    padding: '5px 10px',
                    borderRadius: '15px',
                    background: stage.completed ? 'rgba(46, 204, 113, 0.2)' : 
                               stage.active ? 'rgba(102, 126, 234, 0.2)' : 'rgba(102, 126, 234, 0.1)',
                    color: stage.completed ? '#27ae60' : 
                           stage.active ? '#667eea' : '#667eea',
                    fontWeight: stage.active ? '600' : 'normal',
                    transition: 'all 0.3s ease'
                  }}
                >
                  {stage.label}
                </div>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div style={{
            background: 'rgba(231, 76, 60, 0.1)',
            color: '#e74c3c',
            padding: '20px',
            borderRadius: '10px',
            borderLeft: '4px solid #e74c3c',
            marginTop: '20px',
            textAlign: 'center'
          }}>
            <div style={{
              fontSize: '1.2rem',
              fontWeight: '600',
              marginBottom: '10px'
            }}>
              ❌ Error
            </div>
            <div style={{
              fontSize: '1rem',
              lineHeight: '1.5'
            }}>
              {error}
            </div>
            <button 
              style={{
                background: 'rgba(102, 126, 234, 0.1)',
                color: '#667eea',
                border: '2px solid rgba(102, 126, 234, 0.3)',
                padding: '10px 20px',
                borderRadius: '20px',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                marginTop: '20px'
              }}
              onClick={resetApp}
            >
              Try Again
            </button>
          </div>
        )}

        {results && (
          <div style={{ marginTop: '40px' }}>
            <div style={{ textAlign: 'center', marginBottom: '30px' }}>
              <h2 style={{
                fontSize: '2rem',
                fontWeight: '700',
                color: '#333',
                marginBottom: '10px'
              }}>
                🎯 Results
              </h2>
              <div style={{
                display: 'inline-block',
                padding: '8px 16px',
                borderRadius: '20px',
                fontSize: '0.9rem',
                fontWeight: '600',
                marginBottom: '20px',
                background: results.confidence_level.includes('High confidence') ? 'rgba(46, 204, 113, 0.2)' :
                           results.confidence_level.includes('Good match') ? 'rgba(52, 152, 219, 0.2)' :
                           results.confidence_level.includes('Possible match') ? 'rgba(241, 196, 15, 0.2)' :
                           'rgba(231, 76, 60, 0.2)',
                color: results.confidence_level.includes('High confidence') ? '#27ae60' :
                       results.confidence_level.includes('Good match') ? '#3498db' :
                       results.confidence_level.includes('Possible match') ? '#f39c12' :
                       '#e74c3c'
              }}>
                {results.confidence_level}
              </div>
            </div>

            <div style={{ marginBottom: '30px' }}>
              <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
                <button 
                  style={{
                    padding: '10px 20px',
                    border: '2px solid rgba(102, 126, 234, 0.3)',
                    borderRadius: '20px',
                    background: activeTab === 'cleaned' ? '#667eea' : 'transparent',
                    color: activeTab === 'cleaned' ? 'white' : '#667eea',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    fontWeight: '600'
                  }}
                  onClick={() => setActiveTab('cleaned')}
                >
                  Cleaned Lyrics
                </button>
                <button 
                  style={{
                    padding: '10px 20px',
                    border: '2px solid rgba(102, 126, 234, 0.3)',
                    borderRadius: '20px',
                    background: activeTab === 'raw' ? '#667eea' : 'transparent',
                    color: activeTab === 'raw' ? 'white' : '#667eea',
                    cursor: 'pointer',
                    transition: 'all 0.3s ease',
                    fontWeight: '600'
                  }}
                  onClick={() => setActiveTab('raw')}
                >
                  Raw Transcription
                </button>
              </div>
              
              <div style={{
                background: '#f8f9fa',
                padding: '20px',
                borderRadius: '10px',
                borderLeft: '4px solid #667eea',
                fontFamily: 'monospace',
                lineHeight: '1.6',
                whiteSpace: 'pre-wrap',
                maxHeight: '200px',
                overflowY: 'auto'
              }}>
                {activeTab === 'cleaned' ? results.cleaned_lyrics : results.raw_transcription}
              </div>
            </div>

            {results.matches && results.matches.length > 0 ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {results.matches.map((match, index) => (
                  <div key={index} style={{
                    background: 'white',
                    borderRadius: '15px',
                    padding: '25px',
                    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.1)',
                    transition: 'all 0.3s ease',
                    borderLeft: '4px solid #667eea'
                  }}>
                    <div style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      marginBottom: '15px'
                    }}>
                      <div style={{ flex: 1 }}>
                        <div style={{
                          fontSize: '1.3rem',
                          fontWeight: '700',
                          color: '#333',
                          marginBottom: '5px'
                        }}>
                          {match.title}
                        </div>
                        {match.artist && match.artist !== 'Unknown' && (
                          <div style={{
                            fontSize: '1rem',
                            color: '#666',
                            marginBottom: '10px'
                          }}>
                            by {match.artist}
                          </div>
                        )}
                        <div style={{
                          display: 'flex',
                          gap: '15px',
                          fontSize: '0.9rem',
                          color: '#888'
                        }}>
                          <span>Method: {match.search_method}</span>
                        </div>
                      </div>
                      <div style={{
                        fontSize: '1.2rem',
                        fontWeight: '700',
                        padding: '10px 15px',
                        borderRadius: '20px',
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        color: 'white',
                        minWidth: '80px',
                        textAlign: 'center'
                      }}>
                        {match.similarity > 0 ? `${match.similarity.toFixed(1)}%` : 'N/A'}
                      </div>
                    </div>
                    
                    <div style={{
                      display: 'flex',
                      gap: '10px',
                      marginTop: '15px',
                      flexWrap: 'wrap'
                    }}>
                      {match.genius_url && (
                        <a 
                          href={match.genius_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{
                            textDecoration: 'none',
                            padding: '8px 16px',
                            borderRadius: '20px',
                            fontSize: '0.9rem',
                            fontWeight: '600',
                            transition: 'all 0.3s ease',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            background: 'rgba(255, 255, 112, 0.2)',
                            color: '#f39c12',
                            border: '2px solid rgba(255, 255, 112, 0.3)'
                          }}
                        >
                          🎤 Genius
                        </a>
                      )}
                      {match.youtube_url && (
                        <a 
                          href={match.youtube_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{
                            textDecoration: 'none',
                            padding: '8px 16px',
                            borderRadius: '20px',
                            fontSize: '0.9rem',
                            fontWeight: '600',
                            transition: 'all 0.3s ease',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            background: 'rgba(255, 0, 0, 0.1)',
                            color: '#e74c3c',
                            border: '2px solid rgba(255, 0, 0, 0.2)'
                          }}
                        >
                          ▶️ YouTube
                        </a>
                      )}
                      {match.spotify_url && (
                        <a 
                          href={match.spotify_url} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          style={{
                            textDecoration: 'none',
                            padding: '8px 16px',
                            borderRadius: '20px',
                            fontSize: '0.9rem',
                            fontWeight: '600',
                            transition: 'all 0.3s ease',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            background: 'rgba(30, 215, 96, 0.1)',
                            color: '#1db954',
                            border: '2px solid rgba(30, 215, 96, 0.2)'
                          }}
                        >
                          🎶 Spotify
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                <div style={{
                  fontSize: '1.5rem',
                  fontWeight: '600',
                  marginBottom: '15px'
                }}>
                  🤔 No Matches Found
                </div>
                <div style={{
                  fontSize: '1rem',
                  lineHeight: '1.6',
                  marginBottom: '20px'
                }}>
                  The AI couldn't find any matching songs. Try these manual search options:
                </div>
                <div style={{
                  display: 'flex',
                  gap: '10px',
                  justifyContent: 'center',
                  flexWrap: 'wrap'
                }}>
                  <a 
                    href={`https://www.google.com/search?q=${encodeURIComponent('site:genius.com ' + (results.cleaned_lyrics ? results.cleaned_lyrics.split('\n')[0] : ''))}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      textDecoration: 'none',
                      padding: '10px 20px',
                      borderRadius: '20px',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      transition: 'all 0.3s ease',
                      color: '#667eea',
                      border: '2px solid #667eea'
                    }}
                  >
                    🔍 Search Google
                  </a>
                  <a 
                    href={`https://genius.com/search?q=${encodeURIComponent(results.cleaned_lyrics ? results.cleaned_lyrics.split('\n')[0] : '')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      textDecoration: 'none',
                      padding: '10px 20px',
                      borderRadius: '20px',
                      fontSize: '0.9rem',
                      fontWeight: '600',
                      transition: 'all 0.3s ease',
                      color: '#667eea',
                      border: '2px solid #667eea'
                    }}
                  >
                    🎤 Search Genius
                  </a>
                </div>
              </div>
            )}

            <button 
              style={{
                background: 'rgba(102, 126, 234, 0.1)',
                color: '#667eea',
                border: '2px solid rgba(102, 126, 234, 0.3)',
                padding: '10px 20px',
                borderRadius: '20px',
                fontSize: '0.9rem',
                fontWeight: '600',
                cursor: 'pointer',
                transition: 'all 0.3s ease',
                marginTop: '20px',
                width: '100%'
              }}
              onClick={resetApp}
            >
              🔄 Process Another File
            </button>
          </div>
        )}
      </div>
      
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
}

export default App;