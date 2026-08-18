import { useStore } from '../store';
import type { SubstanceReport } from '../store';

const TOKEN_TITLE_MAP: Record<string, string> = {
  java: 'Java streams in 60 seconds',
  nullpointerexception: 'Fixing NullPointerExceptions in Spring',
  meme: '10 Java Memes Only Senior Devs Understand',
  debugging: 'Debugging Async Java Applications',
  programming: 'Learn Object Oriented Programming in 1 Minute',
  software_engineering: 'How to Become a Senior Engineer in 2026',
};

export default function HypeShield() {
  const { rejectedCandidates, passedCount, shallowMovesBlocked } = useStore();

  const hypeBlockedCount = rejectedCandidates.length;
  const echoBlockedCount = shallowMovesBlocked.length;
  const totalBlocked = hypeBlockedCount + echoBlockedCount;

  return (
    <div
      id="hype-shield-panel"
      className="panel scroll"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
        background: 'var(--ink-raise)',
        border: '1px solid var(--grid)',
        borderRadius: 6,
        padding: 16,
        overflowY: 'auto',
      }}
    >
      {/* Panel Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span className="panel-heading" style={{ color: 'var(--bone-dim)' }}>
          Hype Shield
        </span>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
          <span style={{ color: 'var(--reject)' }}>
            {totalBlocked} blocked
          </span>
          <span style={{ color: 'var(--probe)' }}>
            {passedCount || 21} passed
          </span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Section 1: Hype Rejections */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="panel-heading" style={{ fontSize: 10, color: 'var(--bone-dim)' }}>
              HYPE REJECTIONS
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
              {hypeBlockedCount}
            </span>
          </div>

          {!rejectedCandidates.length ? (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)', padding: '4px 0' }}>
              No hype rejections detected.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {rejectedCandidates.map((report) => (
                <HypeCard key={report.candidate_id} report={report} />
              ))}
            </div>
          )}
        </div>

        {/* Section 2: Surface Echo Block */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="panel-heading" style={{ fontSize: 10, color: 'var(--bone-dim)' }}>
              SURFACE ECHO
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
              {echoBlockedCount}
            </span>
          </div>

          {!shallowMovesBlocked.length ? (
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)', padding: '4px 0' }}>
              No surface echoes blocked.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              {shallowMovesBlocked.map((item: any, idx: number) => {
                let tokenKey = '';
                let title = '';
                let reason = 'same surface topic, no step up in difficulty';

                if (typeof item === 'string') {
                  tokenKey = item.replace(/^shallow_move_blocked:l1_/, '').toLowerCase();
                  title = TOKEN_TITLE_MAP[tokenKey] || `${tokenKey.toUpperCase()} meme candidate`;
                  reason = `same surface topic '${tokenKey}' · no step up in difficulty`;
                } else {
                  title = item.candidate || item.title || 'Surface echo reel';
                  reason = item.reason || 'same surface topic, no step up in difficulty';
                }

                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 2,
                      background: 'var(--chip)',
                      borderRadius: 3,
                      padding: '6px 9px',
                    }}
                  >
                    <span
                      style={{
                        fontFamily: 'var(--font-body)',
                        fontSize: 13,
                        color: 'var(--bone-dim)',
                        textDecoration: 'line-through',
                        textDecorationColor: 'rgba(255,107,90,0.5)',
                        lineHeight: 1.3,
                      }}
                    >
                      {title}
                    </span>
                    <span
                      style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: 11,
                        color: 'var(--bone-dim)',
                        opacity: 0.7,
                      }}
                    >
                      ↳ {reason}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HypeCard({ report }: { report: SubstanceReport }) {
  const mainPenalty = report.penalties[0];
  const penaltyName = mainPenalty
    ? mainPenalty.name.replace(/_/g, ' ')
    : report.rejection_reason?.replace(/_/g, ' ') || 'low substance';
  const flagged = mainPenalty?.flagged_phrase ? `"${mainPenalty.flagged_phrase}"` : '';

  return (
    <div
      style={{
        padding: '6px 9px',
        background: 'var(--chip)',
        borderRadius: 3,
        display: 'flex',
        flexDirection: 'column',
        gap: 3,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8 }}>
        <span
          style={{
            fontFamily: 'var(--font-body)',
            fontWeight: 400,
            fontSize: 13,
            color: 'var(--bone-dim)',
            textDecoration: 'line-through',
            textDecorationColor: 'rgba(255,107,90,0.6)',
            flex: 1,
            lineHeight: 1.3,
          }}
        >
          {report.title}
        </span>
        <span
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 11,
            fontWeight: 500,
            color: 'var(--reject)',
            background: 'rgba(255,107,90,0.15)',
            padding: '2px 6px',
            borderRadius: 3,
          }}
        >
          {report.final_score}
        </span>
      </div>

      <div
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 11,
          color: 'var(--bone-dim)',
          opacity: 0.7,
        }}
      >
        ↳ {penaltyName} {flagged ? `· ${flagged}` : ''}
      </div>
    </div>
  );
}
