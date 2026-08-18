import { useStore } from '../store';

export default function ModeToggle() {
  const { mode, setMode, isStreaming } = useStore();

  return (
    <div className="flex items-center gap-3">
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          color: mode === 'shallow' ? 'var(--bone)' : 'var(--bone-dim)',
          cursor: 'pointer',
          transition: 'color 0.2s ease',
        }}
        onClick={() => !isStreaming && setMode('shallow')}
      >
        Shallow
      </span>

      <button
        id="mode-toggle"
        disabled={isStreaming}
        onClick={() => setMode(mode === 'agent' ? 'shallow' : 'agent')}
        style={{
          opacity: isStreaming ? 0.5 : 1,
          background: 'none',
          border: 'none',
          padding: 0,
          cursor: isStreaming ? 'not-allowed' : 'pointer',
        }}
        aria-label={`Switch to ${mode === 'agent' ? 'shallow' : 'agent'} mode`}
      >
        <div
          style={{
            width: 48,
            height: 24,
            borderRadius: 12,
            background: 'var(--grid)',
            border: '1px solid var(--grid)',
            position: 'relative',
            transition: 'background 0.3s ease',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 2,
              left: mode === 'agent' ? 26 : 2,
              width: 18,
              height: 18,
              borderRadius: '50%',
              background: 'var(--bone)',
              transition: 'left 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          />
        </div>
      </button>

      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          fontWeight: mode === 'agent' ? 500 : 400,
          color: mode === 'agent' ? 'var(--signal)' : 'var(--bone-dim)',
          cursor: 'pointer',
          transition: 'color 0.2s ease',
        }}
        onClick={() => !isStreaming && setMode('agent')}
      >
        Agent
      </span>

      {mode === 'shallow' && (
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            padding: '2px 6px',
            background: 'rgba(255,107,90,0.1)',
            border: '1px solid rgba(255,107,90,0.3)',
            color: 'var(--reject)',
            borderRadius: 2,
          }}
        >
          keyword match only
        </span>
      )}
    </div>
  );
}
