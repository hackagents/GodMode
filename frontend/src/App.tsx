import { useState, useEffect, useRef } from 'react'
import './App.css'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Stake {
  label: 'THREAT' | 'OPPORTUNITY' | 'UNKNOWN';
  text: string;
}

interface Choice {
  key: 'A' | 'B' | 'C' | 'D';
  text: string;
}

interface ChapterResponse {
  chapter_number: number;
  scene?: string;
  reveal?: string;
  stakes?: Stake[];
  choices?: Choice[];
  resolution?: string;
  epitaph?: string;
  is_ending: boolean;
  image_base64?: string;
  image_mime_type?: string;
}

interface CatalogStory {
  id: number;
  title: string;
  genre: string;
  description: string;
  source_story: string;
  image_base64?: string;
  image_mime_type?: string;
  image_generated_style?: string;
}

type CatalogFormData = Omit<CatalogStory, 'id'>;

// ── StoryPanel ────────────────────────────────────────────────────────────────

function StoryPanel({ chapter }: { chapter: ChapterResponse }) {
  const imageSrc = chapter.image_base64
    ? `data:${chapter.image_mime_type ?? 'image/png'};base64,${chapter.image_base64}`
    : null;

  return (
    <div className="panel">
      {imageSrc
        ? <img src={imageSrc} alt={`Chapter ${chapter.chapter_number}`} className="panel-image" />
        : <div className="scene-placeholder">No image</div>
      }
      <div className="caption">
        {chapter.resolution && (
          <div className="resolution"><strong>Resolution:</strong> {chapter.resolution}</div>
        )}
        {chapter.scene && <div className="prose">{chapter.scene}</div>}
        {chapter.reveal && (
          <div className="reveal"><strong>REVEAL:</strong> {chapter.reveal}</div>
        )}
        {chapter.stakes && chapter.stakes.length > 0 && (
          <div className="stakes">
            <strong>STAKES:</strong>
            <ul>
              {chapter.stakes.map((s, i) => (
                <li key={i}>
                  <span className={`label-${s.label.toLowerCase()}`}>{s.label}</span> — {s.text}
                </li>
              ))}
            </ul>
          </div>
        )}
        {chapter.epitaph && <div className="epitaph">{chapter.epitaph}</div>}
      </div>
    </div>
  );
}

// ── CatalogModal ──────────────────────────────────────────────────────────────

const EMPTY_FORM: CatalogFormData = {
  title: '',
  genre: '',
  description: '',
  source_story: '',
  image_base64: undefined,
  image_mime_type: undefined,
  image_generated_style: undefined,
};

interface CatalogModalProps {
  mode: 'add' | 'edit';
  initial: CatalogStory | null;
  onSave: (story: CatalogStory) => void;
  onClose: () => void;
}

function CatalogModal({ mode, initial, onSave, onClose }: CatalogModalProps) {
  const [form, setForm] = useState<CatalogFormData>(() =>
    initial ? { ...initial } : { ...EMPTY_FORM }
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const imagePreview = form.image_base64
    ? `data:${form.image_mime_type ?? 'image/png'};base64,${form.image_base64}`
    : null;

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result as string;
      const mime = result.match(/data:([^;]+)/)?.[1] ?? 'image/jpeg';
      const b64 = result.split(',')[1];
      setForm(prev => ({ ...prev, image_base64: b64, image_mime_type: mime }));
    };
    reader.readAsDataURL(file);
  };

  const handleSave = async () => {
    if (!form.title.trim() || !form.source_story.trim()) {
      setError('Title and Source Story are required.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const url = mode === 'add' ? '/api/catalog' : `/api/catalog/${initial!.id}`;
      const method = mode === 'add' ? 'POST' : 'PUT';
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(await res.text());
      const saved: CatalogStory = await res.json();
      onSave(saved);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save.');
    } finally {
      setSaving(false);
    }
  };

  // Close on backdrop click
  const handleBackdrop = (e: React.MouseEvent<HTMLDivElement>) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="modal-backdrop" onClick={handleBackdrop}>
      <div className="modal">
        <h2>{mode === 'add' ? 'Add Story' : 'Edit Story'}</h2>

        <div className="form-field">
          <label>Title *</label>
          <input
            value={form.title}
            onChange={e => setForm(p => ({ ...p, title: e.target.value }))}
            placeholder="e.g. Hamlet"
          />
        </div>

        <div className="form-field">
          <label>Genre</label>
          <input
            value={form.genre}
            onChange={e => setForm(p => ({ ...p, genre: e.target.value }))}
            placeholder="e.g. tragedy, adventure, romance"
          />
        </div>

        <div className="form-field">
          <label>Description</label>
          <textarea
            rows={3}
            value={form.description}
            onChange={e => setForm(p => ({ ...p, description: e.target.value }))}
            placeholder="Short blurb shown on the catalog card"
          />
        </div>

        <div className="form-field">
          <label>Source Story *</label>
          <textarea
            rows={2}
            value={form.source_story}
            onChange={e => setForm(p => ({ ...p, source_story: e.target.value }))}
            placeholder="Passed verbatim to the AI — e.g. 'Hamlet by Shakespeare'"
          />
        </div>

        <div className="form-field">
          <label>Image Generation Style</label>
          <textarea
            rows={2}
            value={form.image_generated_style ?? ''}
            onChange={e => setForm(p => ({ ...p, image_generated_style: e.target.value || undefined }))}
            placeholder="e.g. oil painting, dark and moody, Renaissance style — leave blank for default"
          />
        </div>

        <div className="form-field">
          <label>Cover Image</label>
          <div className="image-upload-area">
            <input type="file" accept="image/*" onChange={handleImageChange} />
            {imagePreview
              ? <img src={imagePreview} className="image-preview" alt="Cover preview" />
              : (
                <div className="image-upload-hint">
                  Click or drag an image here
                  <span>Recommended: 16:9, any format</span>
                </div>
              )
            }
          </div>
          {form.image_base64 && (
            <button
              className="btn-cancel"
              style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}
              onClick={() => setForm(p => ({ ...p, image_base64: undefined, image_mime_type: undefined }))}
            >
              Remove image
            </button>
          )}
        </div>

        {error && <div className="error-banner">{error}</div>}

        <div className="modal-actions">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button className="btn-save" onClick={handleSave} disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── App ───────────────────────────────────────────────────────────────────────

function App() {
  const [catalog, setCatalog] = useState<CatalogStory[]>([]);
  const [selectedStory, setSelectedStory] = useState<CatalogStory | null>(null);
  const [customStory, setCustomStory] = useState('');

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [chapters, setChapters] = useState<ChapterResponse[]>([]);
  const [currentProse, setCurrentProse] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isStarted, setIsStarted] = useState(false);
  const [userInput, setUserInput] = useState('');

  // Catalog management
  const [modalMode, setModalMode] = useState<'add' | 'edit'>('add');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingStory, setEditingStory] = useState<CatalogStory | null>(null);

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetch('/api/catalog')
      .then(res => res.json())
      .then(setCatalog)
      .catch(() => setError('Failed to load story catalog.'));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chapters, currentProse]);

  // ── Catalog management handlers ──────────────────────────────────────────

  const openAdd = () => {
    setEditingStory(null);
    setModalMode('add');
    setModalOpen(true);
  };

  const openEdit = (e: React.MouseEvent, story: CatalogStory) => {
    e.stopPropagation(); // don't trigger card click
    setEditingStory(story);
    setModalMode('edit');
    setModalOpen(true);
  };

  const handleModalSave = (saved: CatalogStory) => {
    setCatalog(prev =>
      modalMode === 'add'
        ? [...prev, saved]
        : prev.map(s => s.id === saved.id ? saved : s)
    );
    setModalOpen(false);
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    if (!confirm('Remove this story from the catalog?')) return;
    await fetch(`/api/catalog/${id}`, { method: 'DELETE' });
    setCatalog(prev => prev.filter(s => s.id !== id));
  };

  // ── Story streaming ───────────────────────────────────────────────────────

  const consumeStream = async (response: Response) => {
    const reader = response.body?.getReader();
    if (!reader) return;
    const decoder = new TextDecoder();
    let partial = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const lines = (partial + decoder.decode(value, { stream: true })).split('\n\n');
      partial = lines.pop() ?? '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const content = line.slice(6).trim();

        if (content.startsWith('[SESSION_ID]')) {
          setSessionId(content.slice(12).trim());
        } else if (content.startsWith('[CHAPTER_JSON]')) {
          const chapter: ChapterResponse = JSON.parse(content.slice(14).trim());
          setChapters(prev => [...prev, chapter]);
          setCurrentProse('');
        } else if (content.startsWith('[ERROR]')) {
          setError(content.slice(7).trim());
        } else {
          setCurrentProse(prev => prev + content);
        }
      }
    }
  };

  const startStory = async (catalogStory?: CatalogStory, customText?: string) => {
    setLoading(true);
    setError('');
    setIsStarted(true);
    setChapters([]);
    setCurrentProse('');
    setSelectedStory(catalogStory ?? null);

    const body = catalogStory
      ? { catalog_id: catalogStory.id }
      : { source_story: customText };

    try {
      const res = await fetch('/api/stories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error('Failed to start story');
      await consumeStream(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start story.');
      setIsStarted(false);
    } finally {
      setLoading(false);
    }
  };

  const endStory = async () => {
    if (!sessionId) { resetToStart(); return; }
    await fetch(`/api/stories/${sessionId}/end`, { method: 'POST' }).catch(() => {});
    resetToStart();
  };

  const handleChoice = async (input: string) => {
    if (!sessionId) return;
    setLoading(true);
    setError('');
    setCurrentProse('');
    setUserInput('');

    try {
      const res = await fetch(`/api/stories/${sessionId}/chapters`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ input }),
      });
      if (!res.ok) throw new Error('Failed to continue story');
      await consumeStream(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to continue story.');
    } finally {
      setLoading(false);
    }
  };

  const resetToStart = () => {
    setIsStarted(false);
    setSessionId(null);
    setChapters([]);
    setCurrentProse('');
    setError('');
    setSelectedStory(null);
    setCustomStory('');
  };

  // ── Catalog view ──────────────────────────────────────────────────────────

  if (!isStarted) {
    return (
      <main className="app-container">
        <header className="header">
          <h1>Story Engine</h1>
          <p>Choose a classic story or enter your own to begin an interactive adventure.</p>
        </header>

        <div className="catalog-header">
          <h2>Stories</h2>
          <button className="btn-add" onClick={openAdd}>+ Add Story</button>
        </div>

        <div className="catalog-grid">
          {catalog.map(story => (
            <div key={story.id} className="catalog-card" onClick={() => startStory(story)}>
              {story.image_base64
                ? (
                  <img
                    className="card-cover"
                    src={`data:${story.image_mime_type ?? 'image/png'};base64,${story.image_base64}`}
                    alt={story.title}
                  />
                )
                : <div className="card-cover-placeholder">📖</div>
              }
              <div className="card-body">
                <h3>{story.title}</h3>
                <span className="genre-tag">{story.genre}</span>
                <p>{story.description}</p>
              </div>
              <div className="card-actions">
                <button className="card-action-btn" onClick={e => openEdit(e, story)}>Edit</button>
                <button className="card-action-btn delete" onClick={e => handleDelete(e, story.id)}>Delete</button>
              </div>
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
              onChange={e => setCustomStory(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && customStory.trim() && !loading && startStory(undefined, customStory)}
            />
            <button onClick={() => startStory(undefined, customStory)} disabled={!customStory.trim() || loading}>
              Begin
            </button>
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}

        {modalOpen && (
          <CatalogModal
            mode={modalMode}
            initial={editingStory}
            onSave={handleModalSave}
            onClose={() => setModalOpen(false)}
          />
        )}
      </main>
    );
  }

  // ── Story view ────────────────────────────────────────────────────────────

  const lastChapter = chapters[chapters.length - 1];

  return (
    <main className="app-container">
      <header className="header">
        <div className="header-top">
          <button className="btn-back" onClick={resetToStart}>← Back to catalog</button>
        </div>
        <h1>{selectedStory?.title ?? 'Custom Story'}</h1>
        <div className="status-bar">
          <span className="genre-tag">{selectedStory?.genre ?? 'Adventure'}</span>
          {sessionId && <span>Session: {sessionId.slice(0, 8)}</span>}
        </div>
      </header>

      <div className="comic-strip">
        {chapters.map((chapter, idx) => (
          <StoryPanel key={idx} chapter={chapter} />
        ))}

        {currentProse && (
          <div className="panel streaming">
            <div className="caption">
              <div className="prose">{currentProse}</div>
              <span className="cursor" />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {loading && !currentProse && <div className="loading">Consulting the Oracle…</div>}
      {error && <div className="error-banner">{error}</div>}

      {!loading && lastChapter && !lastChapter.is_ending && (
        <div className="interaction-area">
          {lastChapter.choices && (
            <div className="checkpoint">
              <h3>What will you do?</h3>
              <div className="choices">
                {lastChapter.choices.map(choice => (
                  <button
                    key={choice.key}
                    className="choice-btn"
                    onClick={() => handleChoice(choice.key)}
                    disabled={loading}
                  >
                    <span className="choice-text">{choice.key}. {choice.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="user-narration">
            <h3>Or write your own action:</h3>
            <form onSubmit={e => { e.preventDefault(); if (userInput.trim()) handleChoice(userInput); }}>
              <input
                type="text"
                value={userInput}
                onChange={e => setUserInput(e.target.value)}
                placeholder="Type your action…"
                disabled={loading}
              />
              <button type="submit" disabled={loading || !userInput.trim()}>Execute</button>
            </form>
          </div>
        </div>
      )}

      {!loading && lastChapter && !lastChapter.is_ending && (
        <div className="end-story-row">
          <button className="btn-end-story" onClick={endStory}>End story</button>
        </div>
      )}

      {lastChapter?.is_ending && (
        <div className="interaction-area">
          <h2 style={{ textAlign: 'center', margin: '0 0 1.5rem 0' }}>The End</h2>
          <button className="choice-btn" onClick={resetToStart}>Start a New Story</button>
        </div>
      )}
    </main>
  );
}

export default App
