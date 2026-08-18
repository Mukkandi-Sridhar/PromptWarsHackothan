import type { Reel } from '../store';

interface Props {
  reel: Reel;
  isActive?: boolean;
}

export default function ReelCard({ reel }: Props) {
  const gradient = reel.thumbnail_gradient?.length >= 2
    ? `linear-gradient(160deg, ${reel.thumbnail_gradient[0]} 0%, ${reel.thumbnail_gradient[1]} 100%)`
    : 'linear-gradient(160deg, #123039 0%, #0A181E 100%)';

  return (
    <div
      id={`reel-${reel.id}`}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        background: gradient,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'flex-end',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
      {/* Dark gradient scrim at bottom third */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: 'linear-gradient(to top, rgba(10,24,30,0.95) 0%, rgba(10,24,30,0.7) 45%, transparent 80%)',
          pointerEvents: 'none',
        }}
      />

      {/* Reel Content Overlay at Bottom Third */}
      <div style={{ position: 'relative', zIndex: 2, padding: '16px 16px 44px 16px' }}>
        <div
          style={{
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            color: 'var(--bone-dim)',
            marginBottom: 4,
          }}
        >
          {reel.creator_handle} · {reel.duration_sec}s
        </div>

        <h3
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: 16,
            color: 'var(--bone)',
            lineHeight: 1.25,
            marginBottom: 6,
          }}
        >
          {reel.title}
        </h3>

        <p
          style={{
            fontSize: 12,
            color: 'var(--bone-dim)',
            marginBottom: 10,
            lineHeight: 1.4,
          }}
        >
          {reel.caption}
        </p>

        {/* Tags */}
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {reel.tags.slice(0, 4).map((tag) => (
            <span key={tag} className="tag-chip">
              #{tag}
            </span>
          ))}
        </div>
      </div>

      {/* Waveform 32px Playback Strip at bottom of frame */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: 32,
          zIndex: 3,
          background: 'rgba(10,24,30,0.85)',
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
                fill={i / 40 <= (reel.engagement?.watch_completion ?? 0.8) ? 'var(--probe)' : 'var(--grid)'}
              />
            );
          })}
        </svg>
      </div>
    </div>
  );
}
