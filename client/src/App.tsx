import { useState, useEffect, useRef } from 'react'
import './App.css'

// -- Types matching the Python backend --
interface Stake {
  label: 'THREAT' | 'OPPORTUNITY' | 'UNKNOWN';
  text: string;
}

interface Choice {
  key: 'A' | 'B' | 'C' | 'D';
  text: string;
}

interface ResolvedThread {
  status: 'RESOLVED' | 'OPEN';
  thread: string;
  detail: string;
}

interface ChapterResponse {
  chapter_number: int;
  scene?: string;
  reveal?: string;
  stakes?: Stake[];
  choices?: Choice[];
  resolution?: string;
  threads?: ResolvedThread[];
  epitaph?: string;
  is_ending: boolean;
}

interface CatalogStory {
  id: number;
  title: string;
  genre: string;
  description: string;
}

// Reuse the StoryPanel but adapt it for prose
function StoryPanel({ chapter, genre }: { chapter: ChapterResponse, genre: string }) {
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [loadingImg, setLoadingImg] = useState<boolean>(true);
  const [errorImg, setErrorImg] = useState<boolean>(false);

  useEffect(() => {
    if (!chapter.scene) {
        setLoadingImg(false);
        return;
    }

    const fetchImage = async () => {
      try {
        // Compose a prompt using the scene, but summarize it for better results
        const promptSummary = chapter.reveal || chapter.scene?.split('.')[0] || "A mysterious scene";
        const imagePrompt = `A comic book panel illustration. Genre: ${genre}. Action: ${promptSummary}. High quality, detailed, graphic novel style.`;
        
        // Note: This endpoint will be added to the python backend
        const res = await fetch('/api/story/generate-image', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt: imagePrompt })
        });
        
        if (!res.ok) throw new Error("Image generation failed");
        
        const data = await res.json();
        if (data.imageBase64) {
          setImageSrc(`data:image/png;base64,${data.imageBase64}`);
        } else {
          setErrorImg(true);
        }
      } catch (err) {
        console.error("Error fetching image for chapter:", err);
        setErrorImg(true);
      } finally {
        setLoadingImg(false);
      }
    };

    fetchImage();
  }, [chapter.scene, chapter.reveal, genre]);

  return (
    <div className="panel">
      {chapter.scene && (
        <>
          {loadingImg ? (
            <div className="scene-placeholder loading-image">
              <div className="loading-content">
                <div className="spinner"></div>
                <span>Drawing scene...</span>
              </div>
            </div>
          ) : errorImg || !imageSrc ? (
            <div className="scene-placeholder">
                <div className="loading-content">
                  <span>No Image</span>
                </div>
            </div>
          ) : (
            <img src={imageSrc} alt={chapter.scene.substring(0, 50)} className="panel-image" />
          )}
          <div className="caption">
            {chapter.resolution && <div className="resolution"><strong>Resolution:</strong> {chapter.resolution}</div>}
            <div className="prose">{chapter.scene}</div>
            {chapter.reveal && <div className="reveal"><strong>REVEAL:</strong> {chapter.reveal}</div>}
            
            {chapter.stakes && chapter.stakes.length > 0 && (
              <div className="stakes">
                <strong>STAKES:</strong>
                <ul>
                  {chapter.stakes.map((s, i) => (
                    <li key={i}><span className={`label-${s.label.toLowerCase()}`}>{s.label}</span> — {s.text}</li>
                  ))}
                </ul>
              </div>
            )}

            {chapter.epitaph && <div className="epitaph">{chapter.epitaph}</div>}
          </div>
        </>
      )}
    </div>
  );
}

function App() {
  const [catalog, setCatalog] = useState<CatalogStory[]>([]);
  const [selectedStory, setSelectedStory] = useState<CatalogStory | null>(null);
  const [customStory, setCustomStory] = useState("");
  
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterResponse[]>([]);
  const [currentProse, setCurrentProse] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isStarted, setIsStarted] = useState(false);
  const [userInput, setUserInput] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);

  // Load catalog on mount
  useEffect(() => {
    fetch('/api/catalog')
      .then(res => res.json())
      .then(setCatalog)
      .catch(err => {
        console.error("Failed to load catalog:", err);
        setError("Failed to load story catalog.");
      });
  }, []);

  // Scroll to bottom
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chapters, currentProse]);

  const consumeStream = async (response: Response) => {
    const reader = response.body?.getReader();
    if (!reader) return;

    const decoder = new TextDecoder();
    let partial = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      const lines = (partial + chunk).split('\n\n');
      partial = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const content = line.slice(6).trim();
          
          if (content.startsWith('[SESSION_ID]')) {
            setSessionId(content.slice(12).trim());
          } else if (content.startsWith('[CHAPTER_JSON]')) {
            const chapterJson = JSON.parse(content.slice(14).trim());
            setChapters(prev => [...prev, chapterJson]);
            setCurrentProse("");
          } else if (content.startsWith('[ERROR]')) {
            setError(content.slice(7).trim());
          } else {
            // It's a prose chunk
            setCurrentProse(prev => prev + content);
          }
        }
      }
    }
  };

  const startStory = async (source_story?: string, catalog_id?: number) => {
    setLoading(true);
    setError("");
    setIsStarted(true);
    setChapters([]);
    setCurrentProse("");
    
    try {
      const res = await fetch('/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_story, catalog_id })
      });

      if (!res.ok) throw new Error("Failed to start story");
      
      await consumeStream(res);
    } catch (err: any) {
      setError(err.message || "Failed to start story.");
      setIsStarted(false);
    } finally {
      setLoading(false);
    }
  };

  const handleChoice = async (input: string) => {
    if (!sessionId) return;
    setLoading(true);
    setError("");
    setCurrentProse("");
    setUserInput("");
    
    try {
      const res = await fetch(`/api/stories/${sessionId}/chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input })
      });

      if (!res.ok) throw new Error("Failed to continue story");
      
      await consumeStream(res);
    } catch (err: any) {
      setError(err.message || "Failed to continue story.");
    } finally {
      setLoading(false);
    }
  };

  if (!isStarted) {
    return (
      <main className="app-container">
        <header className="header">
          <h1>Story Engine</h1>
          <p>Choose a classic story or enter your own to begin an interactive adventure.</p>
        </header>

        <div className="catalog-grid">
          {catalog.map(story => (
            <div key={story.id} className="catalog-card" onClick={() => startStory(undefined, story.id)}>
              <h3>{story.title}</h3>
              <span className="genre-tag">{story.genre}</span>
              <p>{story.description}</p>
            </div>
          ))}
        </div>

        <div className="custom-story">
          <h3>Or start a custom story:</h3>
          <div className="input-group">
            <input 
              type="text" 
              placeholder="e.g. A space marine stranded on a jungle planet" 
              value={customStory}
              onChange={(e) => setCustomStory(e.target.value)}
            />
            <button onClick={() => startStory(customStory)} disabled={!customStory.trim() || loading}>
              Start Adventure
            </button>
          </div>
        </div>
        {error && <div className="error-banner">{error}</div>}
      </main>
    );
  }

  const lastChapter = chapters[chapters.length - 1];

  return (
    <main className="app-container">
      <header className="header">
        <h1>{selectedStory?.title || "Custom Story"}</h1>
        <div className="status-bar">
          <span className="genre-tag">{selectedStory?.genre || "Action"}</span>
          <span className="session-id">Session: {sessionId?.slice(0,8)}</span>
        </div>
      </header>

      <div className="comic-strip">
        {chapters.map((chapter, idx) => (
          <StoryPanel key={idx} chapter={chapter} genre={selectedStory?.genre || "Action"} />
        ))}
        
        {currentProse && (
          <div className="panel streaming">
            <div className="caption">
              <div className="prose">{currentProse}</div>
              <div className="cursor"></div>
            </div>
          </div>
        )}
        
        <div ref={bottomRef} />
      </div>

      {loading && !currentProse && <div className="loading">Consulting the Oracle...</div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && lastChapter && !lastChapter.is_ending && (
        <div className="interaction-area">
          {lastChapter.choices && (
            <div className="checkpoint">
              <h3>What will you do?</h3>
              <div className="choices">
                {lastChapter.choices.map((choice) => (
                  <button key={choice.key} className="choice-btn" onClick={() => handleChoice(choice.key)}>
                    <span className="choice-text">{choice.key}. {choice.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="user-narration">
             <h3>Or write your own action:</h3>
             <form onSubmit={(e) => { e.preventDefault(); handleChoice(userInput); }}>
               <input 
                 type="text" 
                 value={userInput}
                 onChange={(e) => setUserInput(e.target.value)}
                 placeholder="Type your action..."
                 disabled={loading}
               />
               <button type="submit" disabled={loading || !userInput.trim()}>
                 Execute
               </button>
             </form>
          </div>
        </div>
      )}

      {lastChapter?.is_ending && (
        <div className="interaction-area">
          <h2 style={{ textAlign: 'center' }}>The End</h2>
          <button className="choice-btn" style={{ width: '100%' }} onClick={() => setIsStarted(false)}>
            Start a New Story
          </button>
        </div>
      )}
    </main>
  );
}

export default App
