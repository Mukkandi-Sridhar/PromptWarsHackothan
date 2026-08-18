const API = 'http://localhost:8000/api';

export async function startSession(): Promise<string> {
  const res = await fetch(`${API}/session/start`, { method: 'POST' });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`startSession ${res.status}: ${text}`);
  }
  const data = await res.json();
  return data.session_id;
}

export async function fetchReels() {
  const res = await fetch(`${API}/reels/feed`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`fetchReels ${res.status}: ${text}`);
  }
  return res.json();
}

export async function recordInteraction(payload: {
  session_id: string;
  reel_id: string;
  watch_completion: number;
  rewatched?: boolean;
  liked?: boolean;
  saved?: boolean;
  shared?: boolean;
  commented?: boolean;
  skipped_at_sec?: number | null;
}) {
  const res = await fetch(`${API}/session/interaction`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`interaction ${res.status}: ${body}`);
  }
  return res.json();
}

export function createSSEStream(
  sessionId: string,
  mode: 'agent' | 'shallow',
  onEvent: (event: string, data: unknown) => void,
  onDone: () => void,
  onError: (err: string) => void,
  currentReelId?: string,
): () => void {
  let url = `${API}/recommend/stream?session_id=${sessionId}&mode=${mode}`;
  if (currentReelId) {
    url += `&current_reel_id=${encodeURIComponent(currentReelId)}`;
  }
  const es = new EventSource(url);

  const events = [
    'stage_start', 'decomposition', 'interest_graph', 'retrieval',
    'substance', 'ranking', 'recommendation', 'trace', 'done', 'error'
  ];

  events.forEach((evt) => {
    es.addEventListener(evt, (e: MessageEvent) => {
      try {
        const data = JSON.parse(e.data);
        if (evt === 'done') {
          onDone();
          es.close();
        } else if (evt === 'error') {
          onError(data.message || 'Stream error');
          es.close();
        } else {
          onEvent(evt, data);
        }
      } catch {
        onEvent(evt, e.data);
      }
    });
  });

  es.onerror = () => {
    onError('SSE connection failed');
    es.close();
  };

  return () => {
    es.close();
  };
}
