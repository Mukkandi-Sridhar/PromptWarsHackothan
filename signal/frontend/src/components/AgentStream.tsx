import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';

export default function AgentStream() {
  const { stages, streamLog, isStreaming, isOffline } = useStore();

  return (
    <div
      id="agent-stream-panel"
      className="panel"
      role="region"
      aria-labelledby="agent-stream-heading"
      aria-live="polite"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        height: '100%',
        minHeight: 220,
        background: 'var(--ink-raise)',
        border: '1px solid var(--grid)',
        borderRadius: 4,
        padding: 16,
      }}
    >
      {/* Panel Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span id="agent-stream-heading" className="panel-heading">
          Agent Stream
        </span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          {isOffline && (
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
              offline model
            </span>
          )}
          {isStreaming && (
            <motion.div
              animate={{ opacity: [1, 0.3, 1] }}
              transition={{ repeat: Infinity, duration: 1.2 }}
              style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--signal)' }}
            />
          )}
        </div>
      </div>

      {/* Pipeline Stage Badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, flexShrink: 0 }}>
        {stages.map((st) => (
          <div
            key={st.stage}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              padding: '2px 6px',
              borderRadius: 2,
              border: `1px solid ${st.status === 'done' ? 'var(--probe)' : st.status === 'running' ? 'var(--signal)' : 'var(--grid)'}`,
              color: st.status === 'done' ? 'var(--probe)' : st.status === 'running' ? 'var(--signal)' : 'var(--bone-dim)',
              background: st.status === 'running' ? 'rgba(255,176,32,0.08)' : 'transparent',
            }}
          >
            S{st.stage} {st.label.split(' ')[0]}
          </div>
        ))}
      </div>

      <div style={{ height: 1, background: 'var(--grid)', flexShrink: 0 }} />

      {/* Internal Scroll Log */}
      <div className="scroll" style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 4, minHeight: 0 }}>
        <AnimatePresence initial={false}>
          {streamLog.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: msg.includes('[reject]') ? 'var(--reject)' :
                       msg.includes('[signal]') ? 'var(--probe)' :
                       msg.includes('[probe]') ? 'var(--probe)' :
                       'var(--bone-dim)',
                lineHeight: 1.4,
                wordBreak: 'break-word',
              }}
            >
              {msg}
            </motion.div>
          ))}
        </AnimatePresence>
        {!streamLog.length && !isStreaming && (
          <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)', lineHeight: 1.6 }}>
            Waiting for reels to analyze...
          </div>
        )}
      </div>
    </div>
  );
}
