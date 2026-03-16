import { useState, useEffect, useRef } from 'react'
import './App.css'

// -- Types matching the backend/prompts --
interface Panel {
  caption: string;
  scene: string;
}

interface Choice {
  text: string;
  genre: string;
  hint: string;
}

interface Checkpoint {
  moment: string;
  choices: Choice[];
}

interface Ending {
  final_panel: Panel;
  rest: string;
}

interface SessionState {
  STORY_TITLE: string;
  DIVERGENCE: string;
  GENRE: string;
  MAX_PANELS: number;
  PANELS_USED: number;
  PANELS_REMAINING: number;
  STORY_SO_FAR: string;
  LAST_PANEL_CAPTION: string;
  ENDING_TRIGGERED: boolean;
  ENDING_TRIGGER_REASON: string;
}

function App() {
  const [session, setSession] = useState<SessionState>({
    STORY_TITLE: "The Midnight Heist",
    DIVERGENCE: "They forgot the blueprint.",
    GENRE: "Dark",
    MAX_PANELS: 10,
    PANELS_USED: 0,
    PANELS_REMAINING: 10,
    STORY_SO_FAR: "",
    LAST_PANEL_CAPTION: "",
    ENDING_TRIGGERED: false,
    ENDING_TRIGGER_REASON: ""
  });

  const [panels, setPanels] = useState<Panel[]>([]);
  const [checkpoint, setCheckpoint] = useState<Checkpoint | null>(null);
  const [ending, setEnding] = useState<Ending | null>(null);
  const [userInput, setUserInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [absorbedMessage, setAbsorbedMessage] = useState("");

  const bottomRef = useRef<HTMLDivElement>(null);

  // Start the story on mount
  useEffect(() => {
    bootstrapStory();
  }, []);

  // Scroll to bottom when panels change
  useEffect(() => {
    if (panels.length > 0) {
      setTimeout(() => {
        bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  }, [panels, ending]);

  const bootstrapStory = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/story/bootstrap', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          storyTitle: session.STORY_TITLE, 
          divergence: session.DIVERGENCE, 
          genre: session.GENRE 
        })
      });
      const data = await res.json();
      
      setPanels(data.panels);
      setCheckpoint(data.checkpoint);
      
      const newPanelsUsed = data.panels.length;
      updateSessionAfterPanels(newPanelsUsed, data.panels[data.panels.length - 1].caption);
      
    } catch (err) {
      console.error(err);
      setError("Failed to start story.");
    } finally {
      setLoading(false);
    }
  };

  const updateSessionAfterPanels = (panelsAdded: number, lastCaption: string) => {
    setSession(prev => {
      const newUsed = prev.PANELS_USED + panelsAdded;
      return {
        ...prev,
        PANELS_USED: newUsed,
        PANELS_REMAINING: prev.MAX_PANELS - newUsed,
        LAST_PANEL_CAPTION: lastCaption
      }
    });
    // Note: In a real app, you'd also call /api/story/summary here
  };

  const handleChoice = async (choice: Choice) => {
    setLoading(true);
    setAbsorbedMessage("");
    try {
      const res = await fetch('/api/story/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          storySoFar: session.STORY_SO_FAR,
          choiceText: choice.text,
          choiceGenre: choice.genre,
          panelsRemaining: session.PANELS_REMAINING
        })
      });
      const data = await res.json();
      
      setPanels(prev => [...prev, ...data.panels]);
      setCheckpoint(data.checkpoint);
      updateSessionAfterPanels(data.panels.length, data.panels[data.panels.length - 1].caption);

      if (session.PANELS_REMAINING - data.panels.length <= 0) {
          triggerEnding("panel_limit");
      }
      
    } catch (err) {
      console.error(err);
      setError("Failed to continue story.");
    } finally {
      setLoading(false);
    }
  };

  const handleUserNarration = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim()) return;

    setLoading(true);
    setError("");
    setAbsorbedMessage("");

    try {
      // 1. Validate
      const valRes = await fetch('/api/story/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ userInput, storyContext: session.LAST_PANEL_CAPTION })
      });
      const valData = await valRes.json();

      if (!valData.usable) {
        setError(valData.reason || "That direction doesn't fit this story. Try something else.");
        setLoading(false);
        return;
      }

      // 2. Inject
      const res = await fetch('/api/story/narration', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          storySoFar: session.STORY_SO_FAR,
          userInput: valData.sanitised,
          panelsRemaining: session.PANELS_REMAINING
        })
      });
      const data = await res.json();

      setPanels(prev => [...prev, ...data.panels]);
      setCheckpoint(data.checkpoint);
      setAbsorbedMessage(data.absorbed);
      setUserInput("");
      
      updateSessionAfterPanels(data.panels.length, data.panels[data.panels.length - 1].caption);

      if (session.PANELS_REMAINING - data.panels.length <= 0) {
        triggerEnding("panel_limit");
      }

    } catch (err) {
      console.error(err);
      setError("Failed to process your idea.");
    } finally {
      setLoading(false);
    }
  };

  const triggerEnding = async (reason: string, customEndingText?: string) => {
    setLoading(true);
    setCheckpoint(null);
    try {
      const res = await fetch('/api/story/ending', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          triggerType: reason,
          storySoFar: session.STORY_SO_FAR,
          lastPanelCaption: session.LAST_PANEL_CAPTION,
          genre: session.GENRE,
          userEndingInput: customEndingText
        })
      });
      const data = await res.json();
      setEnding(data);
      setSession(prev => ({
        ...prev,
        ENDING_TRIGGERED: true,
        ENDING_TRIGGER_REASON: reason
      }));
    } catch (err) {
      console.error(err);
      setError("Failed to generate ending.");
    } finally {
      setLoading(false);
    }
  };

  const handleCustomEnding = (e: React.FormEvent) => {
    e.preventDefault();
    if (!userInput.trim()) return;
    triggerEnding("user_ending", userInput);
    setUserInput("");
  };


  return (
    <main className="app-container">
      <header className="header">
        <h1>{session.STORY_TITLE}</h1>
        <div className="status-bar">
          <span className="genre-tag">{session.GENRE}</span>
          <span className="panel-counter">Panels: {session.PANELS_USED} / {session.MAX_PANELS}</span>
        </div>
      </header>

      <div className="comic-strip">
        {panels.map((panel, idx) => (
          <div key={idx} className="panel">
            <div className={`scene-placeholder scene-${panel.scene}`}>
               [{panel.scene.toUpperCase()}]
            </div>
            <div className="caption">{panel.caption}</div>
          </div>
        ))}
        
        {absorbedMessage && (
           <div className="absorbed-banner">{absorbedMessage}</div>
        )}

        {ending && (
          <div className="ending-section">
             <div className="panel final-panel">
               <div className={`scene-placeholder scene-${ending.final_panel.scene}`}>
                 [{ending.final_panel.scene.toUpperCase()}]
               </div>
               <div className="caption">{ending.final_panel.caption}</div>
             </div>
             <p className="rest-line">{ending.rest}</p>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {loading && <div className="loading">Drawing next panels...</div>}
      {error && <div className="error-banner">{error}</div>}

      {!session.ENDING_TRIGGERED && !loading && (
        <div className="interaction-area">
          {checkpoint && (
            <div className="checkpoint">
              <h3>{checkpoint.moment}</h3>
              <div className="choices">
                {checkpoint.choices.map((choice, idx) => (
                  <button key={idx} className="choice-btn" onClick={() => handleChoice(choice)}>
                    <span className="choice-text">{choice.text}</span>
                    <span className="choice-meta">
                      <span className="choice-genre">{choice.genre}</span>
                      <span className="choice-hint">{choice.hint}</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="user-narration">
             <h3>Or write your own {checkpoint ? "direction" : "ending"}:</h3>
             <form onSubmit={checkpoint ? handleUserNarration : handleCustomEnding}>
               <input 
                 type="text" 
                 value={userInput}
                 onChange={(e) => setUserInput(e.target.value)}
                 placeholder={checkpoint ? "What happens next?" : "How does it end?"}
                 disabled={loading}
               />
               <button type="submit" disabled={loading || !userInput.trim()}>
                 {checkpoint ? "Weave Idea" : "End Story"}
               </button>
             </form>
          </div>

          <div className="ending-controls">
            <button className="end-story-btn" onClick={() => triggerEnding("user_choice")}>
              End story here
            </button>
          </div>
        </div>
      )}
    </main>
  )
}

export default App
