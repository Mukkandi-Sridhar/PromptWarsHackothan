import { useStore } from '../store';
import type { Reel } from '../store';

interface Props {
  reel: Reel;
  isActive?: boolean;
}

const CATEGORY_PALETTES: Record<string, { c0: string; c1: string; c2: string; c3: string; glyph: string; hook: string; hookSub?: string }> = {
  reel_001: { c0: '#1A0D14', c1: '#5C1F33', c2: '#FF6B3D', c3: '#2A1420', glyph: '☕', hook: '"me at 2am: it worked yesterday"' },
  reel_002: { c0: '#1C1109', c1: '#4A2A12', c2: '#F0A43A', c3: '#2B1A12', glyph: '▲', hook: '"6:40am. bengaluru. again."' },
  reel_003: { c0: '#0D0F26', c1: '#2B2F6B', c2: '#6C63FF', c3: '#14183A', glyph: '⟨⟩', hook: '"so, reverse a linked list"', hookSub: 'and my brain: 🧍' },
  reel_004: { c0: '#0B1016', c1: '#2A3A48', c2: '#8FA6B8', c3: '#101820', glyph: '▭', hook: '"8GB is fine bro"' },
  reel_005: { c0: '#12101A', c1: '#332C48', c2: '#A78BFA', c3: '#1A1626', glyph: '●', hook: '"₹40 and it changed me"' },
  reel_006: { c0: '#12101A', c1: '#332C48', c2: '#A78BFA', c3: '#1A1626', glyph: '●', hook: '"1 HP. one bullet left."' },
  reel_007: { c0: '#04211F', c1: '#0D4A42', c2: '#35E0A1', c3: '#062A2E', glyph: '◈', hook: '"3nm. 2x cache. same price."' },
  reel_008: { c0: '#1C1109', c1: '#4A2A12', c2: '#F0A43A', c3: '#2B1A12', glyph: '▲', hook: '"while you scroll, someone\'s building"' },
};

export default function ReelCard({ reel }: Props) {
  const { currentReelIdx, reels } = useStore();
  const meta = CATEGORY_PALETTES[reel.id] || {
    c0: '#0D0F26', c1: '#2B2F6B', c2: '#6C63FF', c3: '#14183A', glyph: '◈', hook: `"${reel.title}"`
  };

  const meshGradient = `
    radial-gradient(circle at 20% 30%, ${meta.c2}33 0%, transparent 60%),
    radial-gradient(circle at 80% 70%, ${meta.c1}66 0%, transparent 70%),
    radial-gradient(circle at 50% 50%, ${meta.c0} 0%, ${meta.c3} 100%)
  `;

  return (
    <div
      id={`reel-${reel.id}`}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: meshGradient,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
      {/* z1: Category Glyph (340px, 6% opacity) */}
      <div
        style={{
          position: 'absolute',
          top: -30,
          right: -40,
          fontSize: 260,
          lineHeight: 1,
          opacity: 0.06,
          color: '#fff',
          fontFamily: 'var(--font-display)',
          pointerEvents: 'none',
          zIndex: 1,
        }}
      >
        {meta.glyph}
      </div>

      {/* z2: SVG Grain Noise Overlay (Block 7.1) */}
      <svg
        style={{
          position: 'absolute',
          inset: 0,
          width: '100%',
          height: '100%',
          opacity: 0.04,
          mixBlendMode: 'overlay',
          pointerEvents: 'none',
          zIndex: 2,
        }}
      >
        <filter id={`grain-${reel.id}`}>
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3" />
        </filter>
        <rect width="100%" height="100%" filter={`url(#grain-${reel.id})`} />
      </svg>

      {/* z3: Top Inset Segmented Progress Bar (Block 7.4) */}
      <div
        style={{
          position: 'relative',
          zIndex: 10,
          padding: '24px 12px 0 12px',
          display: 'flex',
          gap: 3,
        }}
      >
        {Array.from({ length: Math.min(reels.length, 8) }).map((_, idx) => {
          let bg = 'rgba(255,255,255,0.12)';
          if (idx < currentReelIdx) bg = 'var(--bone)';
          else if (idx === currentReelIdx) bg = 'var(--signal)';
          return (
            <div
              key={idx}
              style={{
                flex: 1,
                height: 2,
                borderRadius: 1,
                background: bg,
                transition: 'background 0.2s ease',
              }}
            />
          );
        })}
      </div>

      {/* z3: Burned-in Hook Text in upper-middle of frame (Block 7.3) */}
      <div
        style={{
          position: 'relative',
          zIndex: 10,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '0 20px',
          marginTop: 20,
          textAlign: 'center',
        }}
      >
        <div className="hook" style={{ color: '#ffffff', textShadow: '0 2px 20px rgba(0,0,0,0.65)' }}>
          {meta.hook}
        </div>
        {meta.hookSub && (
          <div style={{ fontFamily: 'var(--font-body)', fontSize: 13, color: 'var(--bone-dim)', marginTop: 6 }}>
            {meta.hookSub}
          </div>
        )}
      </div>

      {/* z3: Scrim & Caption Stack at bottom (Block 7.4) */}
      <div style={{ position: 'relative', zIndex: 10, padding: '0 16px 44px 16px' }}>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(to top, rgba(7,19,25,0.92) 0%, rgba(7,19,25,0.6) 60%, transparent 100%)',
            pointerEvents: 'none',
          }}
        />

        <div style={{ position: 'relative', zIndex: 11 }}>
          <div style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--bone-dim)', marginBottom: 4 }}>
            {reel.creator_handle} · {reel.duration_sec}s
          </div>

          <h3 style={{ fontFamily: 'var(--font-body)', fontWeight: 600, fontSize: 15, color: '#ffffff', lineHeight: 1.25, marginBottom: 4 }}>
            {reel.title}
          </h3>

          <p style={{ fontSize: 12, color: 'var(--bone-dim)', marginBottom: 8, lineHeight: 1.35, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {reel.caption}
          </p>

          {/* Plain Inline Tags (no boxes, no cyan) */}
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'rgba(255,255,255,0.45)', display: 'flex', gap: 8 }}>
            {reel.tags.slice(0, 3).map((t) => (
              <span key={t}>#{t}</span>
            ))}
          </div>
        </div>
      </div>

      {/* Waveform Playback Strip at bottom (Block 7.4) */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 32,
          zIndex: 12,
          background: 'rgba(7,19,25,0.85)',
          borderTop: '1px solid var(--grid)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
        }}
      >
        <svg width="100%" height="20" viewBox="0 0 280 20" fill="none">
          {Array.from({ length: 40 }).map((_, i) => {
            const h = Math.max(3, Math.abs(Math.sin(i * 0.7 + 1)) * 16);
            return (
              <rect
                key={i}
                x={i * 7}
                y={10 - h / 2}
                width="3"
                height={h}
                rx="1"
                fill={i / 40 <= (reel.engagement?.watch_completion ?? 0.8) ? 'rgba(255,255,255,0.35)' : 'var(--grid)'}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}
