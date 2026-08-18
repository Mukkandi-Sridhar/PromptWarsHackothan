import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';
import type { Recommendation } from '../store';

export default function RecommendationCard() {
  const { recommendation, isStreaming, isOffline, fullTrace } = useStore();
  const [showTrace, setShowTrace] = useState(false);

  if (!recommendation && !isStreaming) {
    return (
      <div
        id="recommendation-panel"
        className="panel"
        style={{
          padding: '16px',
          background: 'var(--ink-raise)',
          border: '1px solid var(--grid)',
          borderRadius: 6,
        }}
      >
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--bone-dim)' }}>
          Watch a reel. The agent needs signal before it can say anything useful.
        </div>
      </div>
    );
  }

  if (isStreaming && !recommendation) {
    return (
      <div
        id="recommendation-panel"
        className="panel"
        style={{
          padding: '16px',
          background: 'var(--ink-raise)',
          border: '1px solid var(--grid)',
          borderRadius: 6,
        }}
      >
        <motion.div
          animate={{ opacity: [0.4, 1, 0.4] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--signal)' }}
        >
          Agent reasoning...
        </motion.div>
      </div>
    );
  }

  if (!recommendation) return null;

  const specPairs = parseFormattedBlock(recommendation.formatted_block, recommendation);

  return (
    <div
      id="recommendation-panel"
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
        opacity: isStreaming ? 0.6 : 1,
        transition: 'opacity 0.2s ease',
      }}
    >
      {/* Panel Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span className="panel-heading">
          Recommendation
        </span>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span className="tag-chip">
            {recommendation.confidence} Confidence
          </span>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--bone-dim)' }}>
            {isOffline ? 'offline' : 'gpt'}
          </span>
        </div>
      </div>

      {/* Title: 26px Space Grotesk Word-by-Word Reveal (Part 3 S7) */}
      <div>
        <AnimatedTitle title={recommendation.title} />
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 4 }}>
          <span className="tag-chip">
            {recommendation.category}
          </span>
          <span className="tag-chip">
            {recommendation.difficulty}
          </span>
          {recommendation.creator_handle && (
            <span style={{ fontFamily: 'var(--font-body)', fontSize: 12, color: 'var(--bone-dim)' }}>
              {recommendation.creator_handle}
            </span>
          )}
        </div>
      </div>

      {/* 2-Column Mono Grid Output Block with Character Typing (Part 3 S7) */}
      <dl className="spec-grid" id="recommendation-output-block">
        {specPairs.map(({ label, value }) => (
          <React.Fragment key={label}>
            <dt>{label}</dt>
            <dd>
              {label === 'WHY:' || label === 'WHY THIS RECOMMENDATION:' ? (
                <TypedWhyText text={value} />
              ) : (
                value
              )}
            </dd>
          </React.Fragment>
        ))}
      </dl>

      {/* Open Reasoning Trace Toggle */}
      <div>
        <button
          id="open-trace-btn"
          onClick={() => setShowTrace(!showTrace)}
          style={{
            background: 'none',
            border: 0,
            cursor: 'pointer',
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--bone-dim)',
            padding: 0,
            display: 'flex',
            alignItems: 'center',
            gap: 4,
          }}
        >
          {showTrace ? '▼ Hide reasoning trace' : '▶ Open reasoning trace'}
        </button>
      </div>

      <AnimatePresence>
        {Boolean(showTrace && fullTrace) && (
          <motion.pre
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            style={{
              fontFamily: 'var(--font-mono)',
              fontSize: 10,
              color: 'var(--bone-dim)',
              background: 'var(--ink)',
              padding: 10,
              borderRadius: 3,
              overflowX: 'auto',
              maxHeight: 200,
            }}
          >
            {String(JSON.stringify(fullTrace, null, 2))}
          </motion.pre>
        )}
      </AnimatePresence>
    </div>
  );
}

function AnimatedTitle({ title }: { title: string }) {
  const words = title.split(' ');
  return (
    <h2 className="title-rec" style={{ marginBottom: 6 }}>
      {words.map((word, i) => (
        <motion.span
          key={`${word}-${i}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.28, delay: i * 0.045, ease: [0.22, 1, 0.36, 1] }}
          style={{ display: 'inline-block', marginRight: '0.25em' }}
        >
          {word}
        </motion.span>
      ))}
    </h2>
  );
}

function TypedWhyText({ text }: { text: string }) {
  const [displayedText, setDisplayedText] = useState('');
  const [isTypingComplete, setIsTypingComplete] = useState(false);

  useEffect(() => {
    setDisplayedText('');
    setIsTypingComplete(false);
    let i = 0;
    const timer = setInterval(() => {
      if (i < text.length) {
        setDisplayedText(text.slice(0, i + 1));
        i++;
      } else {
        setIsTypingComplete(true);
        clearInterval(timer);
      }
    }, 24);

    return () => clearInterval(timer);
  }, [text]);

  return (
    <span>
      {displayedText}
      {!isTypingComplete && <span className="typing-caret" />}
    </span>
  );
}

function parseFormattedBlock(block: string, rec?: Recommendation): { label: string; value: string }[] {
  const labels = [
    'CURRENT REEL:',
    'INTEREST DETECTED:',
    'WHY:',
    'RECOMMENDED TECH REEL:',
    'CATEGORY:',
    'WHY THIS RECOMMENDATION:',
    'DIFFICULTY:',
    'CONFIDENCE:',
  ];

  const result: { label: string; value: string }[] = [];
  if (block) {
    const lines = block.split('\n');
    let currentLabel = '';
    let currentValue = '';

    for (const line of lines) {
      const matchedLabel = labels.find(l => line.startsWith(l));
      if (matchedLabel) {
        if (currentLabel) {
          result.push({ label: currentLabel, value: currentValue.trim() });
        }
        currentLabel = matchedLabel;
        currentValue = line.slice(matchedLabel.length).trim();
      } else if (currentLabel) {
        currentValue += ' ' + line.trim();
      }
    }
    if (currentLabel) {
      result.push({ label: currentLabel, value: currentValue.trim() });
    }
  }

  if (result.length < 8 && rec) {
    return [
      { label: 'CURRENT REEL:', value: rec.why_evidence ? rec.why_evidence.split(' ')[0] : 'watched content' },
      { label: 'INTEREST DETECTED:', value: rec.interest_detected || 'software engineering' },
      { label: 'WHY:', value: rec.why_evidence || 'converging identity signals' },
      { label: 'RECOMMENDED TECH REEL:', value: rec.title },
      { label: 'CATEGORY:', value: rec.category },
      { label: 'WHY THIS RECOMMENDATION:', value: rec.why_recommendation },
      { label: 'DIFFICULTY:', value: rec.difficulty },
      { label: 'CONFIDENCE:', value: rec.confidence },
    ];
  }

  return result;
}
