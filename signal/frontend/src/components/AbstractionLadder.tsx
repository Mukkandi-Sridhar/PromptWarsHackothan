import { useEffect, useState } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { useStore } from '../store';

export default function AbstractionLadder() {
  const { graphNodes, topL2, recommendation, mode, isStreaming, stages, streamLog } = useStore();
  const prefersReducedMotion = useReducedMotion();
  const [climbProgress, setClimbProgress] = useState<'idle' | 'l1' | 'l2' | 'l3' | 'descend'>('idle');
  const [logExpanded, setLogExpanded] = useState(false);

  const l1Nodes = graphNodes.filter(n => n.layer === 'L1').slice(0, 6);
  const l2Nodes = graphNodes.filter(n => n.layer === 'L2').slice(0, 4);
  const l3Nodes = graphNodes.filter(n => n.layer === 'L3').slice(0, 1);

  const displayL3 = l3Nodes.length ? l3Nodes : [{ id: 'l3_default', label: 'Becoming a software engineer · placement anxiety', layer: 'L3' as const, convergence: 0, supporting_reels: [], weight: 0 }];
  const displayL2 = l2Nodes.length ? l2Nodes : [
    { id: 'l2_be', label: 'Backend Engineering', layer: 'L2' as const, convergence: 0, supporting_reels: [], weight: 0 },
    { id: 'l2_it', label: 'Interview Technique', layer: 'L2' as const, convergence: 0, supporting_reels: [], weight: 0 },
    { id: 'l2_dt', label: 'Developer Tooling', layer: 'L2' as const, convergence: 0, supporting_reels: [], weight: 0 },
  ];
  const displayL1 = l1Nodes.length ? l1Nodes : [
    { id: 'l1_java', label: 'Java', layer: 'L1' as const, convergence: 0, supporting_reels: [], weight: 0 },
    { id: 'l1_npe', label: 'NullPointerException', layer: 'L1' as const, convergence: 0, supporting_reels: [], weight: 0 },
    { id: 'l1_lc', label: 'LeetCode', layer: 'L1' as const, convergence: 0, supporting_reels: [], weight: 0 },
    { id: 'l1_mac', label: 'MacBook M4', layer: 'L1' as const, convergence: 0, supporting_reels: [], weight: 0 },
  ];

  const isShallow = mode === 'shallow';

  useEffect(() => {
    if (!graphNodes.length) { setClimbProgress('idle'); return; }
    if (isStreaming) { setClimbProgress('l1'); return; }
    if (l3Nodes.length > 0) {
      const t1 = setTimeout(() => setClimbProgress('l2'), prefersReducedMotion ? 0 : 300);
      const t2 = setTimeout(() => setClimbProgress('l3'), prefersReducedMotion ? 0 : 700);
      const t3 = setTimeout(() => {
        if (recommendation) setClimbProgress('descend');
      }, prefersReducedMotion ? 0 : 1200);
      return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); };
    }
  }, [graphNodes.length, l3Nodes.length, recommendation, isStreaming, prefersReducedMotion]);

  const isL3Active = (climbProgress === 'l3' || climbProgress === 'descend') && !isShallow;
  const isL2Active = (climbProgress === 'l2' || climbProgress === 'l3' || climbProgress === 'descend') && !isShallow;

  const currentStage = stages.find(s => s.status === 'running') || stages.filter(s => s.status === 'done').pop();

  return (
    <div
      id="abstraction-ladder"
      className="panel"
      style={{
        height: 300,
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
        background: 'var(--ink-raise)',
        border: '1px solid var(--grid)',
        borderRadius: 6,
        padding: 0,
        overflow: 'hidden',
      }}
    >
      {/* Upper Content Area (Padding 16px) */}
      <div style={{ flex: 1, padding: 16, display: 'flex', flexDirection: 'column', gap: 12, overflow: 'hidden' }}>
        {/* Panel Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
          <span className="panel-heading">
            Abstraction Ladder
          </span>
          {isShallow && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                color: 'var(--reject)',
                padding: '2px 6px',
                background: 'rgba(255,107,90,0.1)',
                borderRadius: 3,
              }}
            >
              L1 loop
            </span>
          )}
        </div>

        {/* 3 Tiers Layout (18px tier gap per Spec 3.4) */}
        <div
          style={{
            flex: 1,
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
            position: 'relative',
            paddingLeft: 32,
          }}
        >
          {/* Vertical Climb Rail */}
          <div
            style={{
              position: 'absolute',
              left: 12,
              top: 6,
              bottom: 6,
              width: 1,
              background: isL3Active ? 'var(--signal)' : 'var(--grid)',
              transition: 'background 0.3s ease',
            }}
          />

          {/* ── TIER 3: L3 IDENTITY (Top) ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              L3 · Identity & Goals
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              {displayL3.map((node) => (
                <div
                  key={node.id}
                  style={{
                    fontFamily: 'var(--font-display)',
                    fontWeight: 600,
                    fontSize: 18,
                    lineHeight: 1.25,
                    maxWidth: 380,
                    padding: '6px 12px',
                    borderRadius: 3,
                    background: isL3Active ? 'rgba(255,176,32,0.12)' : 'var(--chip)',
                    border: isL3Active ? '1px solid var(--signal)' : '0',
                    color: isL3Active ? 'var(--bone)' : 'var(--bone-dim)',
                    transition: 'all 0.25s ease',
                  }}
                >
                  {node.label}
                </div>
              ))}
            </div>
          </div>

          {/* ── TIER 2: L2 SKILLS (Middle) ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4, opacity: isShallow ? 0.25 : 1, transition: 'opacity var(--dur-slow) var(--ease-out)' }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              L2 · Skill Domains
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {displayL2.map((node, i) => {
                const isChosenL2 = (topL2[0]?.id === node.id) || (i === 0 && (isL2Active || Boolean(recommendation)));
                const isHot = isChosenL2 && (isL2Active || Boolean(recommendation)) && !isShallow;
                return (
                  <div
                    key={node.id}
                    className={isHot ? 'chip-hot' : 'chip'}
                  >
                    {node.label}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── TIER 1: L1 SURFACE TOKENS (Bottom) ── */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                L1 · Surface Tokens
              </div>
              {isShallow && (
                <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--reject)' }}>
                  ↩ shallow loop at L1
                </span>
              )}
            </div>
            {isShallow && <div className="shallow-loop-circuit" />}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {displayL1.map((node) => (
                <div
                  key={node.id}
                  style={{
                    background: 'var(--chip)',
                    borderRadius: 3,
                    padding: '4px 8px',
                    fontFamily: 'var(--font-body)',
                    fontSize: 11,
                    color: 'var(--bone-dim)',
                  }}
                >
                  {node.label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Single 34px-tall Agent Ticker Bar pinned to bottom (Spec 1.2) ── */}
      <div
        id="agent-ticker"
        style={{
          height: 34,
          background: 'var(--ink)',
          borderTop: '1px solid var(--grid)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          flexShrink: 0,
          position: 'relative',
          zIndex: 10,
        }}
      >
        {/* Stage Pills S1 ▸ S2 ▸ S3 ▸ S4 ▸ S5 ▸ S6 ▸ S7 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}>
          {stages.map((st, i) => {
            const color = st.status === 'done' ? 'var(--bone)' :
                          st.status === 'running' ? 'var(--signal)' : 'var(--bone-dim)';
            const opacity = st.status === 'pending' ? 0.4 : 1;
            return (
              <span key={st.stage} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <span style={{ color, opacity, fontWeight: st.status === 'running' ? 600 : 400 }}>
                  S{st.stage}
                </span>
                {i < stages.length - 1 && (
                  <span style={{ color: 'var(--bone-dim)', opacity: 0.3 }}>▸</span>
                )}
              </span>
            );
          })}
        </div>

        {/* Right Status + Drawer Toggle ⌃ */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
            {currentStage ? `${currentStage.status} S${currentStage.stage} · ${currentStage.label.toLowerCase()}` : 'idle'}
          </span>
          <button
            id="toggle-stream-drawer"
            onClick={() => setLogExpanded(!logExpanded)}
            style={{
              background: 'none',
              border: 0,
              color: 'var(--bone-dim)',
              fontFamily: 'var(--font-mono)',
              fontSize: 12,
              cursor: 'pointer',
              padding: '2px 4px',
            }}
            aria-label="Toggle agent log drawer"
          >
            {logExpanded ? '▾' : '⌃'}
          </button>
        </div>
      </div>

      {/* 240px Log Drawer Overlay */}
      <AnimatePresence>
        {logExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 240, opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{
              position: 'absolute',
              bottom: 34,
              left: 0,
              right: 0,
              background: 'var(--ink-raise)',
              borderTop: '1px solid var(--grid)',
              padding: 12,
              zIndex: 20,
              overflowY: 'auto',
            }}
            className="scroll"
          >
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)', marginBottom: 6 }}>
              AGENT EXECUTION LOG
            </div>
            {streamLog.map((log, idx) => (
              <div key={idx} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)', lineHeight: 1.5 }}>
                {log}
              </div>
            ))}
            {!streamLog.length && (
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)' }}>
                No execution logs recorded yet.
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
