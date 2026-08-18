import { motion } from 'framer-motion';
import { useStore } from '../store';
import { recordInteraction } from '../api';
import ReelCard from './ReelCard';

export default function PhoneFeed() {
  const { reels, currentReelIdx, setCurrentReelIdx, sessionId, setInteraction } = useStore();
  const interactions = useStore((s) => s.interactions);

  if (!reels.length) {
    return (
      <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--bone-dim)' }}>
        Loading feed...
      </div>
    );
  }

  const currentReel = reels[currentReelIdx];
  const myInteraction = (currentReel && interactions[currentReel.id]) || { liked: false, saved: false, shared: false };

  const handleAction = async (key: 'liked' | 'saved' | 'shared') => {
    if (!currentReel || !sessionId) return;
    const newVal = !myInteraction[key];
    setInteraction(currentReel.id, key, newVal);

    try {
      await recordInteraction({
        session_id: sessionId,
        reel_id: currentReel.id,
        watch_completion: currentReel.engagement?.watch_completion ?? 0.9,
        liked: key === 'liked' ? newVal : myInteraction.liked,
        saved: key === 'saved' ? newVal : myInteraction.saved,
        shared: key === 'shared' ? newVal : myInteraction.shared,
        skipped_at_sec: currentReel.engagement?.skipped_at_sec,
      });
    } catch (err) {
      console.error('Interaction save error:', err);
    }
  };

  const goTo = (delta: number) => {
    const nextIdx = Math.max(0, Math.min(reels.length - 1, currentReelIdx + delta));
    if (nextIdx !== currentReelIdx) {
      setCurrentReelIdx(nextIdx);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        height: '100%',
        gap: 12,
        padding: '12px 0',
      }}
    >
      {/* 310x600 Centered Phone Frame */}
      <div
        style={{
          width: 310,
          height: 560,
          background: 'var(--ink-raise)',
          border: '1px solid var(--grid)',
          borderRadius: 20,
          overflow: 'hidden',
          position: 'relative',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
        }}
      >
        {/* Notch */}
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            width: 100,
            height: 18,
            background: 'var(--ink)',
            borderBottomLeftRadius: 10,
            borderBottomRightRadius: 10,
            zIndex: 30,
          }}
        />

        {/* Current Reel View */}
        <div style={{ flex: 1, position: 'relative' }}>
          {currentReel && <ReelCard reel={currentReel} />}
        </div>

        {/* Counter Badge */}
        <div
          style={{
            position: 'absolute',
            bottom: 12,
            left: 12,
            fontFamily: 'var(--font-mono)',
            fontSize: 10,
            color: 'var(--bone-dim)',
            background: 'rgba(7,19,25,0.7)',
            padding: '2px 6px',
            borderRadius: 3,
          }}
        >
          {currentReelIdx + 1} / {reels.length}
        </div>
      </div>

      {/* Action Row Under Phone Frame with Framer Motion Spring Animations (Part 5) */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 12,
          width: 320,
        }}
      >
        <motion.button
          id={`like-btn`}
          onClick={() => handleAction('liked')}
          whileTap={{ scale: 0.92 }}
          whileHover={{ scale: 1.04 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          style={{
            height: 44,
            minWidth: 64,
            padding: '0 12px',
            background: myInteraction.liked ? 'rgba(255,107,90,0.15)' : 'var(--chip)',
            border: 0,
            borderRadius: 3,
            color: myInteraction.liked ? 'var(--reject)' : 'var(--bone-dim)',
            fontFamily: 'var(--font-body)',
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
          aria-label="Like reel"
        >
          <motion.span animate={{ scale: myInteraction.liked ? [1, 1.3, 1] : 1 }}>♥</motion.span> Like
        </motion.button>

        <motion.button
          id={`save-btn`}
          onClick={() => handleAction('saved')}
          whileTap={{ scale: 0.92 }}
          whileHover={{ scale: 1.04 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          style={{
            height: 44,
            minWidth: 64,
            padding: '0 12px',
            background: myInteraction.saved ? 'rgba(255,176,32,0.15)' : 'var(--chip)',
            border: 0,
            borderRadius: 3,
            color: myInteraction.saved ? 'var(--signal)' : 'var(--bone-dim)',
            fontFamily: 'var(--font-body)',
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
          aria-label="Save reel"
        >
          <motion.span animate={{ scale: myInteraction.saved ? [1, 1.3, 1] : 1 }}>🔖</motion.span> Save
        </motion.button>

        <motion.button
          id={`share-btn`}
          onClick={() => handleAction('shared')}
          whileTap={{ scale: 0.92 }}
          whileHover={{ scale: 1.04 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          style={{
            height: 44,
            minWidth: 64,
            padding: '0 12px',
            background: myInteraction.shared ? 'rgba(79,209,217,0.15)' : 'var(--chip)',
            border: 0,
            borderRadius: 3,
            color: myInteraction.shared ? 'var(--bone)' : 'var(--bone-dim)',
            fontFamily: 'var(--font-body)',
            fontSize: 12,
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
          aria-label="Share reel"
        >
          <motion.span animate={{ scale: myInteraction.shared ? [1, 1.3, 1] : 1 }}>⤻</motion.span> Share
        </motion.button>

        <motion.button
          id="next-reel"
          onClick={() => goTo(1)}
          disabled={currentReelIdx >= reels.length - 1}
          whileTap={{ scale: 0.92 }}
          whileHover={{ scale: 1.04 }}
          transition={{ type: 'spring', stiffness: 320, damping: 26 }}
          style={{
            height: 44,
            padding: '0 16px',
            background: 'var(--chip)',
            border: 0,
            borderRadius: 3,
            color: 'var(--bone)',
            fontFamily: 'var(--font-body)',
            fontSize: 12,
            cursor: currentReelIdx >= reels.length - 1 ? 'not-allowed' : 'pointer',
            opacity: currentReelIdx >= reels.length - 1 ? 0.4 : 1,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
          aria-label="Next reel"
        >
          Next ↓
        </motion.button>
      </div>
    </div>
  );
}
