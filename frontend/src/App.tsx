import { useState, useEffect, useRef, useCallback } from 'react'
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
  initial_plot?: string;
  environment?: string;
  text_style?: string;
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
  initial_plot: undefined,
  environment: undefined,
  text_style: undefined,
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
  const [generating, setGenerating] = useState(false);
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
          <label>Initial Plot</label>
          <textarea
            rows={3}
            value={form.initial_plot ?? ''}
            onChange={e => setForm(p => ({ ...p, initial_plot: e.target.value || undefined }))}
            placeholder="e.g. The story begins with Hamlet returning from university to find his father dead and mother remarried — leave blank to let the AI decide"
          />
        </div>

        <div className="form-field">
          <label>Environment</label>
          <textarea
            rows={2}
            value={form.environment ?? ''}
            onChange={e => setForm(p => ({ ...p, environment: e.target.value || undefined }))}
            placeholder="e.g. Elsinore Castle, medieval Denmark, cold and politically tense — leave blank to let the AI decide"
          />
        </div>

        <div className="form-field">
          <label>Writing Style</label>
          <textarea
            rows={2}
            value={form.text_style ?? ''}
            onChange={e => setForm(p => ({ ...p, text_style: e.target.value || undefined }))}
            placeholder="e.g. Terse Hemingway prose, short punchy sentences — or: florid Victorian gothic, rich with metaphor — leave blank for default"
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
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem', flexWrap: 'wrap' }}>
            <button
              className="btn-generate-thumb"
              disabled={generating || saving}
              onClick={async () => {
                if (!form.title.trim() || !form.source_story.trim()) {
                  setError('Title and Source Story are required to generate a thumbnail.');
                  return;
                }
                setGenerating(true);
                setError('');
                try {
                  const res = await fetch('/api/catalog/thumbnail', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                      title: form.title,
                      genre: form.genre,
                      description: form.description,
                      source_story: form.source_story,
                      image_generated_style: form.image_generated_style,
                    }),
                  });
                  if (!res.ok) throw new Error(await res.text());
                  const { image_base64, image_mime_type } = await res.json();
                  setForm(p => ({ ...p, image_base64, image_mime_type }));
                } catch (err: unknown) {
                  setError(err instanceof Error ? err.message : 'Thumbnail generation failed.');
                } finally {
                  setGenerating(false);
                }
              }}
            >
              {generating ? 'Generating…' : '✨ Generate Thumbnail'}
            </button>
            {form.image_base64 && (
              <button
                className="btn-cancel"
                style={{ fontSize: '0.8rem' }}
                onClick={() => setForm(p => ({ ...p, image_base64: undefined, image_mime_type: undefined }))}
              >
                Remove image
              </button>
            )}
          </div>
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

// ── Narration helpers (Vertex AI TTS + STT via backend) ───────────────────────

const NARRATION_LANGUAGES: { code: string; label: string }[] = [
  { code: 'en-US', label: 'English (US)' },
  { code: 'en-GB', label: 'English (UK)' },
  { code: 'es-ES', label: 'Spanish' },
  { code: 'fr-FR', label: 'French' },
  { code: 'de-DE', label: 'German' },
  { code: 'it-IT', label: 'Italian' },
  { code: 'pt-BR', label: 'Portuguese (BR)' },
  { code: 'ja-JP', label: 'Japanese' },
  { code: 'ko-KR', label: 'Korean' },
  { code: 'zh-CN', label: 'Chinese (Mandarin)' },
  { code: 'hi-IN', label: 'Hindi' },
  { code: 'ar-SA', label: 'Arabic' },
  { code: 'ru-RU', label: 'Russian' },
  { code: 'nl-NL', label: 'Dutch' },
  { code: 'pl-PL', label: 'Polish' },
  { code: 'sv-SE', label: 'Swedish' },
  { code: 'tr-TR', label: 'Turkish' },
  { code: 'id-ID', label: 'Indonesian' },
  { code: 'vi-VN', label: 'Vietnamese' },
  { code: 'th-TH', label: 'Thai' },
];

const NARRATION_VOICES = ['Aoede', 'Charon', 'Fenrir', 'Kore', 'Leda', 'Orus', 'Puck', 'Zephyr'];

// ── TTS streaming helpers ─────────────────────────────────────────────────────

interface StreamBuffer {
  chunks: string[];   // base64 PCM chunks received so far
  done: boolean;
  notify: (() => void) | null;  // called when a new chunk arrives or stream ends
}

/** Start fetching TTS audio as a stream of PCM chunks. Returns immediately;
 *  chunks accumulate in the buffer as they arrive from the server. */
function startTTSStream(
  text: string,
  voice: string,
  signal: AbortSignal,
  cacheKeys?: { sessionId: string; choiceKey: string },
): StreamBuffer {
  const buf: StreamBuffer = { chunks: [], done: false, notify: null };

  (async () => {
    try {
      const form = new FormData();
      form.append('text', text);
      form.append('voice', voice);
      if (cacheKeys) {
        form.append('session_id', cacheKeys.sessionId);
        form.append('choice_key', cacheKeys.choiceKey);
      }
      const res = await fetch('/api/narrate/tts/stream', { method: 'POST', body: form, signal });
      if (!res.ok || !res.body) return;

      const reader = res.body.getReader();
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
          if (content !== '[DONE]') buf.chunks.push(content);
          buf.notify?.();
        }
      }
    } catch {
      // aborted or network error — treat as done
    } finally {
      buf.done = true;
      buf.notify?.();
    }
  })();

  return buf;
}

/** Play a StreamBuffer through the Web Audio API, scheduling chunks as they
 *  arrive so the first words play immediately without waiting for the full audio.
 *  `onSkipReady` is called with a function the caller can invoke to stop playback
 *  early and resolve immediately (used for the Skip button). */
async function ttsStreamPlay(
  buf: StreamBuffer,
  audioCtx: AudioContext,
  activeSources: Set<AudioBufferSourceNode>,
  signal: AbortSignal,
  onSkipReady: (skip: () => void) => void,
): Promise<void> {
  let nextIdx = 0;
  let nextPlayTime = audioCtx.currentTime + 0.05;

  // Skip promise — resolved externally when the user clicks Skip
  let resolveSkip!: () => void;
  const skipPromise = new Promise<void>(r => { resolveSkip = r; });
  onSkipReady(resolveSkip);

  const scheduleChunk = (b64: string) => {
    const raw = atob(b64);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);

    const samples = bytes.length / 2;
    const float32 = new Float32Array(samples);
    const view = new DataView(bytes.buffer);
    for (let i = 0; i < samples; i++) {
      float32[i] = view.getInt16(i * 2, true) / 32768;
    }

    const buffer = audioCtx.createBuffer(1, samples, 24000);
    buffer.copyToChannel(float32, 0);
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);
    const startAt = Math.max(nextPlayTime, audioCtx.currentTime + 0.02);
    source.start(startAt);
    activeSources.add(source);
    source.onended = () => activeSources.delete(source);
    nextPlayTime = startAt + buffer.duration;
  };

  while (true) {
    if (signal.aborted) throw new DOMException('Aborted', 'AbortError');

    while (nextIdx < buf.chunks.length) {
      scheduleChunk(buf.chunks[nextIdx++]);
    }

    if (buf.done) break;

    // Wait for the next chunk, done signal, or a skip request
    await Promise.race([
      new Promise<void>(resolve => { buf.notify = resolve; }),
      skipPromise,
    ]);
    buf.notify = null;
    if (signal.aborted) throw new DOMException('Aborted', 'AbortError');
  }

  // Wait for audio to finish — or skip if the user requests it early
  const remaining = nextPlayTime - audioCtx.currentTime;
  if (remaining > 0) {
    await Promise.race([
      new Promise<void>(resolve => setTimeout(resolve, remaining * 1000 + 200)),
      skipPromise,
    ]);
  }
}

async function sttTranscribe(blob: Blob, language: string): Promise<string> {
  const form = new FormData();
  form.append('audio', blob, 'recording.webm');
  form.append('language', language);
  const res = await fetch('/api/narrate/stt', { method: 'POST', body: form });
  if (!res.ok) throw new Error('STT request failed');
  const { transcript } = await res.json();
  return (transcript as string) || '';
}

// ── useNarration ──────────────────────────────────────────────────────────────

type NarrationPhase = 'idle' | 'speaking' | 'listening' | 'processing';
const LISTEN_SECONDS = 5;

function useNarration(
  chapters: ChapterResponse[],
  loading: boolean,
  onChoice: (key: string) => void,
  voice: string,
  language: string,
  sessionId: string | null,
) {
  const [active, setActive] = useState(false);
  const [phase, setPhase] = useState<NarrationPhase>('idle');
  const [countdown, setCountdown] = useState(0);

  // Refs so async callbacks always see fresh values
  const activeRef = useRef(false);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const lastNarratedRef = useRef<number>(-1);
  const pendingStreamRef = useRef<StreamBuffer | null>(null);       // first paragraph
  const pendingRemainStreamRef = useRef<StreamBuffer | null>(null); // remaining paragraphs
  const pendingChoicesStreamRef = useRef<StreamBuffer | null>(null); // choices prompt
  const audioCtxRef = useRef<AudioContext | null>(null);
  const activeSourcesRef = useRef<Set<AudioBufferSourceNode>>(new Set());
  const abortControllerRef = useRef<AbortController | null>(null);
  const skipAudioRef = useRef<(() => void) | null>(null);
  const stopListenRef = useRef<(() => void) | null>(null);
  const lastChoiceKeyRef = useRef<string | null>(null);
  const onChoiceRef = useRef(onChoice);
  onChoiceRef.current = onChoice;
  const voiceRef = useRef(voice);
  voiceRef.current = voice;
  const langRef = useRef(language);
  langRef.current = language;
  const sessionIdRef = useRef(sessionId);
  sessionIdRef.current = sessionId;

  const stop = useCallback(() => {
    activeRef.current = false;
    // Abort all in-flight TTS fetches and wake any waiting stream consumer
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
    // Stop all scheduled Web Audio sources immediately
    activeSourcesRef.current.forEach(s => { try { s.stop(0); } catch { /* already stopped */ } });
    activeSourcesRef.current.clear();
    // Suspend the audio context to release hardware resources
    audioCtxRef.current?.suspend();
    pendingStreamRef.current = null;
    pendingRemainStreamRef.current = null;
    pendingChoicesStreamRef.current = null;
    skipAudioRef.current?.();   // unblock ttsStreamPlay's final wait
    skipAudioRef.current = null;
    stopListenRef.current?.();  // unblock listenForChoice's listen timeout
    stopListenRef.current = null;
    recorderRef.current?.stop();
    recorderRef.current = null;
    setActive(false);
    setPhase('idle');
    setCountdown(0);
    lastNarratedRef.current = -1;
  }, []);

  const listenForChoice = useCallback(async (choices: Choice[]) => {
    if (!activeRef.current) return;

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setPhase('idle');
      return;
    }

    // Prefer audio/webm;codecs=opus — Chrome sometimes defaults to video/webm
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
    const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
    recorderRef.current = recorder;
    const chunks: Blob[] = [];
    recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };

    // Set onstop BEFORE calling stop() to avoid the race where the event fires first
    const stoppedPromise = new Promise<void>(resolve => { recorder.onstop = () => resolve(); });

    setPhase('listening');
    setCountdown(LISTEN_SECONDS);
    recorder.start(200); // 200 ms timeslice ensures ondataavailable fires during recording

    // Countdown tick — race against stopListenRef so stop() can cancel immediately
    const stopPromise = new Promise<void>(resolve => { stopListenRef.current = resolve; });
    const tick = setInterval(() => setCountdown(prev => (prev > 1 ? prev - 1 : 0)), 1000);
    await Promise.race([
      new Promise<void>(resolve => setTimeout(resolve, LISTEN_SECONDS * 1000)),
      stopPromise,
    ]);
    clearInterval(tick);
    stopListenRef.current = null;

    if (!activeRef.current) { recorder.stop(); stream.getTracks().forEach(t => t.stop()); return; }

    recorder.stop();
    stream.getTracks().forEach(t => t.stop());
    await stoppedPromise;
    recorderRef.current = null;

    if (!activeRef.current) return;

    setPhase('processing');
    const blob = new Blob(chunks, { type: recorder.mimeType || mimeType || 'audio/webm' });

    try {
      const transcript = await sttTranscribe(blob, langRef.current);
      const upper = transcript.toUpperCase();
      const key = (['A', 'B', 'C', 'D'] as const).find(k => new RegExp(`\\b${k}\\b`).test(upper));
      if (key && choices.some(c => c.key === key)) {
        setPhase('idle');
        onChoiceRef.current(key);
      } else {
        // Unrecognized — fall back to idle so user can click manually
        setPhase('idle');
      }
    } catch {
      setPhase('idle');
    }
  }, []);

  /** Split a chapter into the three TTS parts we stream in parallel. */
  const buildNarrationParts = (chapter: ChapterResponse) => {
    const paragraphs = (chapter.scene ?? '').split('\n\n').filter(Boolean);
    const firstPara = paragraphs[0] ?? chapter.epitaph ?? '';
    const remaining = paragraphs.length > 1
      ? paragraphs.slice(1).join('\n\n') + (chapter.epitaph ? '\n\n' + chapter.epitaph : '')
      : '';
    const choices = chapter.choices?.length && !chapter.is_ending
      ? 'Your choices are: ' +
        chapter.choices.map(c => `${c.key}: ${c.text}`).join('. ') +
        '. Please say A, B, C, or D.'
      : '';
    return { firstPara, remaining, choices };
  };

  const narrateChapter = useCallback(async (chapter: ChapterResponse) => {
    if (!activeRef.current) return;
    const audioCtx = audioCtxRef.current;
    const signal = abortControllerRef.current?.signal;
    if (!audioCtx || !signal) return;

    const { firstPara, remaining, choices } = buildNarrationParts(chapter);

    // Use pre-fetched streams where available; fall back to starting fresh
    const firstStream = pendingStreamRef.current
      ?? (firstPara ? startTTSStream(firstPara, voiceRef.current, signal) : null);
    const remainStream = pendingRemainStreamRef.current
      ?? (remaining ? startTTSStream(remaining, voiceRef.current, signal) : null);
    const choicesStream = pendingChoicesStreamRef.current
      ?? (choices ? startTTSStream(choices, voiceRef.current, signal) : null);
    pendingStreamRef.current = null;
    pendingRemainStreamRef.current = null;
    pendingChoicesStreamRef.current = null;

    const playStream = async (stream: StreamBuffer | null) => {
      if (!stream || !activeRef.current) return;
      await ttsStreamPlay(stream, audioCtx, activeSourcesRef.current, signal, (skip) => {
        skipAudioRef.current = skip;
      });
      skipAudioRef.current = null;
    };

    setPhase('speaking');
    try {
      await playStream(firstStream);
      await playStream(remainStream);
      await playStream(choicesStream);
    } catch {
      if (activeRef.current) setPhase('idle');
      return;
    }

    if (!activeRef.current) return;

    if (chapter.choices?.length && !chapter.is_ending) {
      await listenForChoice(chapter.choices);
    } else {
      setPhase('idle');
    }
  }, [listenForChoice]);

  // Fire all three TTS requests in parallel as soon as a chapter arrives —
  // even while loading is still true — so they're buffering before playback starts.
  useEffect(() => {
    if (!active || !abortControllerRef.current) return;
    const chapter = chapters[chapters.length - 1];
    if (!chapter || chapter.chapter_number === lastNarratedRef.current) return;
    const signal = abortControllerRef.current.signal;
    const { firstPara, remaining, choices } = buildNarrationParts(chapter);

    // Use the prefetch cache for the first paragraph if this chapter came from a known choice
    const choiceKey = lastChoiceKeyRef.current;
    const sid = sessionIdRef.current;
    const cacheKeys = choiceKey && sid ? { sessionId: sid, choiceKey } : undefined;
    lastChoiceKeyRef.current = null; // consume it

    if (firstPara) pendingStreamRef.current = startTTSStream(firstPara, voiceRef.current, signal, cacheKeys);
    if (remaining) pendingRemainStreamRef.current = startTTSStream(remaining, voiceRef.current, signal);
    if (choices) pendingChoicesStreamRef.current = startTTSStream(choices, voiceRef.current, signal);
  }, [active, chapters]);

  // Play once loading is done — stream is already running, first chunks likely ready
  useEffect(() => {
    if (!active || loading) return;
    const chapter = chapters[chapters.length - 1];
    if (!chapter || chapter.chapter_number === lastNarratedRef.current) return;
    lastNarratedRef.current = chapter.chapter_number;
    narrateChapter(chapter);
  }, [active, loading, chapters, narrateChapter]);

  const start = useCallback(() => {
    // AudioContext must be created/resumed synchronously inside a user-gesture handler
    // so Chrome doesn't block audio playback.
    if (!audioCtxRef.current || audioCtxRef.current.state === 'closed') {
      audioCtxRef.current = new AudioContext();
    } else if (audioCtxRef.current.state === 'suspended') {
      audioCtxRef.current.resume();
    }
    abortControllerRef.current = new AbortController();
    lastNarratedRef.current = -1;
    activeRef.current = true;
    setActive(true);
  }, []);

  const skip = useCallback(() => {
    if (phase !== 'speaking') return;
    activeSourcesRef.current.forEach(s => { try { s.stop(0); } catch { /* already stopped */ } });
    activeSourcesRef.current.clear();
    skipAudioRef.current?.();
    skipAudioRef.current = null;
  }, [phase]);

  const notifyChoice = useCallback((key: string) => {
    lastChoiceKeyRef.current = ['A', 'B', 'C', 'D'].includes(key) ? key : null;
  }, []);

  return { active, phase, countdown, start, stop, skip, notifyChoice };
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

  // Narration — handleChoiceRef breaks the forward-reference cycle
  const handleChoiceRef = useRef<(input: string) => void>(() => {});
  const [narrationVoice, setNarrationVoice] = useState('Kore');
  const [narrationLang, setNarrationLang] = useState('en-US');
  const narration = useNarration(
    chapters, loading,
    (input) => handleChoiceRef.current(input),
    narrationVoice, narrationLang,
    sessionId,
  );

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
    narration.stop();
    if (!sessionId) { resetToStart(); return; }
    await fetch(`/api/stories/${sessionId}/end`, { method: 'POST' }).catch(() => {});
    resetToStart();
  };

  const handleChoice = async (input: string) => {
    if (!sessionId) return;
    narration.notifyChoice(input);
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
  // Keep ref in sync so narration callbacks always invoke the latest handleChoice
  handleChoiceRef.current = handleChoice;

  const resetToStart = () => {
    narration.stop();
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
        <header className="header catalog-hero">
          <div className="hero-logo">GODMODE</div>
          <p className="hero-tagline">Unlimited stories. Choose your destiny.</p>
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
              <div className="card-gradient" />
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
          <div className="narration-controls">
            <select
              className="narration-select"
              value={narrationVoice}
              onChange={e => setNarrationVoice(e.target.value)}
              disabled={narration.active}
              title="Voice"
            >
              {NARRATION_VOICES.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
            <select
              className="narration-select"
              value={narrationLang}
              onChange={e => setNarrationLang(e.target.value)}
              disabled={narration.active}
              title="Language"
            >
              {NARRATION_LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
            {narration.active ? (
              <button className="btn-narrate btn-narrate-stop" onClick={narration.stop}>⏹ Stop</button>
            ) : (
              <button className="btn-narrate" onClick={narration.start} disabled={loading}>🔊 Narrate</button>
            )}
            {narration.active && (
              <span className="narration-phase">
                {narration.phase === 'speaking' && (
                  <>
                    🔊 Speaking…
                    {lastChapter?.choices && !lastChapter.is_ending && (
                      <button className="btn-skip-narration" onClick={narration.skip}>
                        Skip ▶
                      </button>
                    )}
                  </>
                )}
                {narration.phase === 'listening' && `🎙 Listening… ${narration.countdown}s`}
                {narration.phase === 'processing' && '⏳ Processing…'}
              </span>
            )}
          </div>
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
                    <span className="choice-key">{choice.key}</span>
                    <span className="choice-text">{choice.text}</span>
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
