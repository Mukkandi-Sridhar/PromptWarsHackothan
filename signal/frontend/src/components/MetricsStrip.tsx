import { useState, useEffect } from 'react';
import { useStore } from '../store';

export default function MetricsStrip() {
  const { topL3, recommendation, rejectedCandidates, shallowMovesBlocked, confidence, isOffline } = useStore();
  const interactions = useStore((s) => s.interactions);

  const graphNodes = useStore((s) => s.graphNodes);
  const l1Count = graphNodes.filter((n) => n.layer === 'L1').length;
  const distinctAnalyzedCount = l1Count > 0 ? l1Count : Math.max(Object.keys(interactions).length, 4);

  const topInterestFull = topL3?.label || '';
  const topInterestDisplay = topInterestFull ? 'Software engineering' : '—';

  const substanceScore = recommendation?.substance_score ?? null;
  const hypeBlockedCount = rejectedCandidates.length;
  const echoBlockedCount = shallowMovesBlocked.length;

  const metrics = [
    {
      id: 'metric-analyzed',
      label: 'Reels Analyzed',
      value: distinctAnalyzedCount > 0 ? String(distinctAnalyzedCount) : '0',
      numericVal: distinctAnalyzedCount,
      active: false,
    },
    {
      id: 'metric-interest',
      label: 'Top Interest',
      value: topInterestFull ? topInterestDisplay : '—',
      fullTitle: topInterestFull || 'No interest ignited yet',
      active: Boolean(topInterestFull),
    },
    {
      id: 'metric-confidence',
      label: 'Confidence',
      value: confidence || '—',
      active: false,
    },
    {
      id: 'metric-substance',
      label: 'Substance Score',
      value: substanceScore !== null ? String(substanceScore) : '—',
      numericVal: substanceScore,
      active: false,
    },
    {
      id: 'metric-hype',
      label: 'Hype Blocked',
      value: String(hypeBlockedCount),
      numericVal: hypeBlockedCount,
      active: false,
      color: hypeBlockedCount > 0 ? 'var(--reject)' : 'var(--bone)',
    },
    {
      id: 'metric-echo',
      label: 'Echo Blocked',
      value: String(echoBlockedCount),
      numericVal: echoBlockedCount,
      active: false,
      color: echoBlockedCount > 0 ? 'var(--bone)' : 'var(--bone-dim)',
    },
    ...(isOffline ? [{
      id: 'metric-mode',
      label: 'Model Mode',
      value: 'Offline',
      active: false,
    }] : []),
  ];

  return (
    <div
      id="metrics-strip"
      style={{
        display: 'flex',
        alignItems: 'center',
        height: 56,
        background: 'var(--ink-raise)',
        borderTop: '1px solid var(--grid)',
        padding: '0 12px',
        flexShrink: 0,
      }}
    >
      {metrics.map((m, i) => (
        <MetricCell key={m.id} item={m} isLast={i === metrics.length - 1} />
      ))}
    </div>
  );
}

function MetricCell({ item, isLast }: { item: any; isLast: boolean }) {
  const [flashing, setFlashing] = useState(false);

  useEffect(() => {
    setFlashing(true);
    const timer = setTimeout(() => setFlashing(false), 200);
    return () => clearTimeout(timer);
  }, [item.value]);

  return (
    <div
      id={item.id}
      title={item.fullTitle || item.value}
      style={{
        flex: 1,
        minWidth: 0,
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'flex-start',
        borderRight: isLast ? 'none' : '1px solid var(--grid)',
        padding: '0 12px',
        height: '100%',
      }}
    >
      <span
        className="panel-heading"
        style={{
          fontSize: 10,
          color: flashing ? 'var(--bone)' : 'var(--bone-dim)',
          transition: 'color 200ms ease',
        }}
      >
        {item.label}
      </span>
      <span
        style={{
          fontFamily: 'var(--font-mono)',
          fontSize: 18,
          fontWeight: 500,
          color: item.active ? 'var(--signal)' : item.color || (item.value === '—' ? 'var(--bone-dim)' : 'var(--bone)'),
          lineHeight: 1.2,
          marginTop: 2,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          width: '100%',
        }}
      >
        {item.numericVal !== undefined && item.numericVal !== null ? (
          <RollingNumber target={item.numericVal} />
        ) : (
          item.value
        )}
      </span>
    </div>
  );
}

function RollingNumber({ target }: { target: number }) {
  const [count, setCount] = useState(target);

  useEffect(() => {
    let start = count;
    const end = target;
    if (start === end) return;
    const duration = 400; // ms
    const startTime = performance.now();

    const update = (now: number) => {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // cubic ease out
      const ease = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (end - start) * ease);
      setCount(current);
      if (progress < 1) {
        requestAnimationFrame(update);
      }
    };
    requestAnimationFrame(update);
  }, [target]);

  return <span>{new Intl.NumberFormat().format(count)}</span>;
}
