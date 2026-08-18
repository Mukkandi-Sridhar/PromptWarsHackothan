import { useEffect, useCallback, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import './index.css';
import './theme.css';
import { useStore } from './store';
import { startSession, fetchReels, recordInteraction, createSSEStream } from './api';

import PhoneFeed from './components/PhoneFeed';
import AbstractionLadder from './components/AbstractionLadder';
import HypeShield from './components/HypeShield';
import RecommendationCard from './components/RecommendationCard';
import ModeToggle from './components/ModeToggle';
import MetricsStrip from './components/MetricsStrip';
import CandidateStreamOverlay from './components/CandidateStreamOverlay';

export type SpeedMode = '1x' | '2x' | 'instant';

export default function App() {
  const {
    sessionId, setSessionId,
    reels, setReels,
    currentReelIdx,
    mode,
    isStreaming, setIsStreaming,
    stages, updateStage, resetStages,
    setGraph,
    setSubstance,
    setRecommendation,
    addStreamLog, clearStreamLog,
    setIsOffline,
    setFullTrace,
    serverError, setServerError,
  } = useStore();

  const [speed, setSpeed] = useState<SpeedMode>('1x');
  const cleanupRef = useRef<(() => void) | null>(null);

  // Health check on mount (Part 2.3)
  useEffect(() => {
    (async () => {
      try {
        const res = await fetch('http://localhost:8000/health');
        if (!res.ok) throw new Error('Health check non-ok');
      } catch {
        setServerError('backend not reachable on :8000');
      }
    })();
  }, [setServerError]);

  // Initialize session and load reels
  useEffect(() => {
    (async () => {
      try {
        const [sid, reelData] = await Promise.all([startSession(), fetchReels()]);
        setSessionId(sid);
        setReels(reelData);
      } catch (err: any) {
        console.error('Failed to initialize SIGNAL:', err);
        setServerError(err.message || 'initialization failed');
      }
    })();
  }, []);

  // Compute dwell time based on pacing speed control (Part 2)
  const getDwellMs = useCallback(() => {
    if (speed === 'instant') return 0;
    if (speed === '2x') return 150;
    return 300; // 1x default
  }, [speed]);

  // Run agent pipeline with abort controller cleanup & choreographed pacing (Part 2)
  const runAgent = useCallback(async () => {
    if (!sessionId) return;

    if (cleanupRef.current) {
      cleanupRef.current();
      cleanupRef.current = null;
    }

    setIsStreaming(true);
    clearStreamLog();
    resetStages();

    const dwellMs = getDwellMs();

    const cleanup = createSSEStream(
      sessionId,
      mode,
      (event, data: any) => {
        switch (event) {
          case 'stage_start':
            updateStage(data.stage, 'running');
            addStreamLog(`[probe] S${data.stage} — ${data.label}`);
            break;

          case 'decomposition':
            addStreamLog(`  · ${data.reel_id}: ${data.intent_signal} (${data.sophistication_level})`);
            break;

          case 'interest_graph':
            setTimeout(() => {
              updateStage(2, 'done', data);
              setGraph(
                data.nodes || [],
                data.edges || [],
                data.latent_need || '',
                data.top_l3 || null,
                data.top_l2 || []
              );
              addStreamLog(`[signal] L3 identity ignited: ${data.top_l3?.label || 'building...'}`);
            }, dwellMs);
            break;

          case 'retrieval':
            setTimeout(() => {
              updateStage(3, 'done', data);
              addStreamLog(`  · ${data.candidate_count} candidates retrieved via composed query`);
            }, dwellMs * 2);
            break;

          case 'substance':
            setTimeout(() => {
              updateStage(4, 'done', data);
              const rejected = data.rejected || [];
              const passed = data.passed || [];
              setSubstance(rejected, passed.length);
              addStreamLog(`[signal] ${passed.length} passed substance gate`);
            }, dwellMs * 3);
            break;

          case 'ranking':
            setTimeout(() => {
              updateStage(5, 'done', data);
              updateStage(6, 'done');
              if (data.shallow_moves_blocked?.length) {
                useStore.setState({ shallowMovesBlocked: data.shallow_moves_blocked });
              }
              addStreamLog(`[signal] Top fit ranked: ${data.scored?.[0]?.title?.slice(0, 36)}`);
            }, dwellMs * 4);
            break;

          case 'recommendation':
            setTimeout(() => {
              updateStage(7, 'done', data);
              setRecommendation(
                data.recommendation,
                data.alternates || [],
                data.serendipity,
                data.confidence || data.recommendation?.confidence || 'High',
                data.confidence_reason || '',
              );
              setIsOffline(!data.llm_used);
              addStreamLog(`[signal] Recommendation ready — ${data.confidence || 'High'} confidence`);
            }, dwellMs * 5);
            break;

          case 'trace':
            setFullTrace(data);
            break;
        }
      },
      () => {
        setTimeout(() => {
          setIsStreaming(false);
          [1, 2, 3, 4, 5, 6, 7].forEach(i => updateStage(i, 'done'));
          cleanupRef.current = null;
        }, dwellMs * 5 + 100);
      },
      (err) => {
        setIsStreaming(false);
        addStreamLog(`[reject] Error: ${err}`);
        setServerError(err);
        cleanupRef.current = null;
      },
    );

    cleanupRef.current = cleanup;
  }, [sessionId, mode, getDwellMs]);

  // Pre-seed and sync interactions up to currentReelIdx and run pipeline automatically
  useEffect(() => {
    if (!sessionId || !reels.length) return;
    (async () => {
      const maxIdx = Math.max(currentReelIdx, 3);
      for (let i = 0; i <= maxIdx && i < reels.length; i++) {
        const reel = reels[i];
        const eng = reel.engagement;
        await recordInteraction({
          session_id: sessionId,
          reel_id: reel.id,
          watch_completion: eng?.watch_completion ?? 0.9,
          rewatched: eng?.rewatched ?? false,
          liked: eng?.liked ?? false,
          saved: eng?.saved ?? false,
          shared: eng?.shared ?? false,
          commented: eng?.commented ?? false,
          skipped_at_sec: eng?.skipped_at_sec,
        }).catch((err: any) => {
          console.error('Interaction POST error:', err);
          setServerError(err.message || 'interaction error');
        });
      }
      runAgent();
    })();
  }, [currentReelIdx, sessionId, reels]);

  // Active Stage Attention Highlight (Part 4)
  const currentRunningStage = stages.find((s) => s.status === 'running')?.stage || null;
  const isLadderActive = currentRunningStage === 1 || currentRunningStage === 2;
  const isHypeActive = currentRunningStage === 3 || currentRunningStage === 4;
  const isRecActive = currentRunningStage !== null && currentRunningStage >= 5;

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateRows: '52px 1fr 56px',
        height: '100dvh',
        width: '100vw',
        background: 'var(--ink)',
        overflow: 'hidden',
        position: 'relative',
      }}
    >
      {/* Candidate Dot Stream Overlay (Part 3 S3/S4) */}
      <CandidateStreamOverlay active={isHypeActive} />

      {/* ── HEADER 52px (Part 7 entrance) ── */}
      <motion.header
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
        style={{
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          borderBottom: '1px solid var(--grid)',
          background: 'var(--ink-raise)',
          gap: 16,
          flexShrink: 0,
        }}
      >
        {/* Logo */}
        <div
          style={{
            fontFamily: 'var(--font-display)',
            fontWeight: 600,
            fontSize: 18,
            color: 'var(--bone)',
            letterSpacing: '-0.02em',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
          }}
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="var(--bone)" strokeWidth="1.5" />
            <path d="M8 12l3 3 5-5" stroke="var(--bone)" strokeWidth="1.5" strokeLinecap="round" />
          </svg>
          SIGNAL
        </div>

        <div style={{ width: 1, height: 20, background: 'var(--grid)' }} />

        {/* Mode Toggle */}
        <ModeToggle />

        {/* Speed Selector (Part 2) */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, background: 'var(--chip)', padding: '3px 6px', borderRadius: 3 }}>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)', marginRight: 4 }}>Pacing:</span>
          {(['1x', '2x', 'instant'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              style={{
                background: speed === s ? 'var(--chip-hot)' : 'transparent',
                border: 0,
                borderRadius: 2,
                color: speed === s ? 'var(--bone)' : 'var(--bone-dim)',
                fontFamily: 'var(--font-mono)',
                fontSize: 10,
                padding: '2px 6px',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {s}
            </button>
          ))}
        </div>

        {/* Action Button & Session ID */}
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 14 }}>
          <button
            id="analyze-btn"
            onClick={runAgent}
            disabled={isStreaming || !sessionId}
            style={{
              padding: '6px 14px',
              background: isStreaming ? 'var(--chip)' : 'var(--grid)',
              border: 0,
              borderRadius: 3,
              color: 'var(--bone)',
              fontFamily: 'var(--font-body)',
              fontSize: 12,
              fontWeight: 500,
              cursor: isStreaming || !sessionId ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.15s ease',
            }}
          >
            {isStreaming ? 'Analyzing session...' : '▶ Analyze session'}
          </button>

          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
            {sessionId ? `${sessionId.slice(0, 8)}...` : 'connecting...'}
          </span>
        </div>
      </motion.header>

      {/* ── MIDDLE APP SHELL ── */}
      <main
        style={{
          display: 'grid',
          gridTemplateColumns: '340px 1fr',
          height: '100%',
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {/* Left Column: Phone Feed (Part 7 entrance delay 80ms) */}
        <motion.section
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.32, delay: 0.08, ease: [0.22, 1, 0.36, 1] }}
          style={{
            borderRight: '1px solid var(--grid)',
            height: '100%',
            minHeight: 0,
            overflow: 'hidden',
            background: 'var(--ink)',
          }}
        >
          <PhoneFeed />
        </motion.section>

        {/* Right Column (.right) */}
        <section
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            padding: 10,
            minHeight: 0,
            height: '100%',
            overflow: 'hidden',
          }}
        >
          {/* Server Error Bar */}
          {serverError && (
            <div
              style={{
                background: 'var(--reject)',
                color: '#fff',
                padding: '6px 12px',
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                borderRadius: 3,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                flexShrink: 0,
              }}
            >
              <span>backend error · {serverError} · check console</span>
              <button
                onClick={() => setServerError(null)}
                style={{ background: 'none', border: 0, color: '#fff', cursor: 'pointer', fontFamily: 'var(--font-mono)' }}
              >
                ✕
              </button>
            </div>
          )}

          {/* Top: Abstraction Ladder Panel with Stage Attention Highlight (Part 4) */}
          <div
            style={{ minHeight: 0, height: 300, flexShrink: 0 }}
            className={isLadderActive ? 'panel-active-attention' : ''}
          >
            <AbstractionLadder />
          </div>

          {/* Bottom (.lower): Recommendation + Hype Shield */}
          <div
            className="lower"
            style={{
              display: 'grid',
              gridTemplateColumns: '1.6fr 1fr',
              gap: 10,
              minHeight: 0,
              height: '100%',
              overflow: 'hidden',
            }}
          >
            {/* Left: Recommendation Card */}
            <div
              style={{ minHeight: 0, height: '100%', overflow: 'hidden' }}
              className={isRecActive ? 'panel-active-attention' : ''}
            >
              <RecommendationCard />
            </div>

            {/* Right: Hype Shield */}
            <div
              style={{ minHeight: 0, height: '100%', overflow: 'hidden' }}
              className={isHypeActive ? 'panel-active-attention' : ''}
            >
              <HypeShield />
            </div>
          </div>
        </section>
      </main>

      {/* ── BOTTOM METRICS STRIP 56px (Part 7 entrance delay 600ms) ── */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.32, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
        style={{ flexShrink: 0 }}
      >
        <MetricsStrip />
      </motion.div>
    </div>
  );
}
