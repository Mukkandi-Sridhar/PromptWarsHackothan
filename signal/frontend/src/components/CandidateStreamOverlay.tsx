import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../store';

interface CandidateDot {
  id: number;
  yOffset: number;
  delay: number;
  isReject: boolean;
}

export default function CandidateStreamOverlay({ active }: { active: boolean }) {
  const rejectedCandidates = useStore((s) => s.rejectedCandidates);
  const [dots, setDots] = useState<CandidateDot[]>([]);

  useEffect(() => {
    if (!active) {
      setDots([]);
      return;
    }

    const newDots: CandidateDot[] = Array.from({ length: 30 }, (_, i) => ({
      id: i,
      yOffset: (Math.random() - 0.5) * 120,
      delay: i * 0.012,
      isReject: i % 3 === 0 || i < rejectedCandidates.length,
    }));
    setDots(newDots);
  }, [active, rejectedCandidates]);

  if (!active || !dots.length) return null;

  return (
    <div
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        pointerEvents: 'none',
        zIndex: 50,
        overflow: 'hidden',
      }}
    >
      <AnimatePresence>
        {dots.map((dot) => (
          <motion.div
            key={dot.id}
            initial={{ x: '20%', y: `calc(50% + ${dot.yOffset}px)`, opacity: 0, scale: 1 }}
            animate={
              dot.isReject
                ? {
                    x: ['20%', '70%', '75%'],
                    y: [`calc(50% + ${dot.yOffset}px)`, `calc(50% + ${dot.yOffset}px)`, `calc(50% + ${dot.yOffset + 24}px)`],
                    opacity: [0, 0.8, 1, 0],
                    scale: [1, 1.2, 2, 0],
                    backgroundColor: ['#7C959C', '#FF6B5A', '#FF6B5A'],
                  }
                : {
                    x: ['20%', '95%'],
                    y: `calc(50% + ${dot.yOffset}px)`,
                    opacity: [0, 0.7, 0.9, 0],
                    scale: [1, 1, 1],
                    backgroundColor: ['#7C959C', '#4FD1D9', '#4FD1D9'],
                  }
            }
            transition={{
              duration: dot.isReject ? 0.75 : 0.6,
              delay: dot.delay,
              ease: 'easeOut',
            }}
            style={{
              position: 'absolute',
              width: 4,
              height: 4,
              borderRadius: '50%',
              willChange: 'transform, opacity',
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
