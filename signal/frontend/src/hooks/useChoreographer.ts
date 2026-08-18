import { useState, useCallback } from 'react';

export type SpeedMode = '1x' | '2x' | 'instant';

export interface ChoreographerState {
  speed: SpeedMode;
  setSpeed: (s: SpeedMode) => void;
  activeStage: number | null;
  setActiveStage: (s: number | null) => void;
  pulseSignalDot: boolean;
  triggerSignalDotPulse: () => void;
}

export function useChoreographer() {
  const [speed, setSpeedState] = useState<SpeedMode>('1x');
  const [activeStage, setActiveStage] = useState<number | null>(null);
  const [pulseSignalDot, setPulseSignalDot] = useState(false);

  const setSpeed = useCallback((s: SpeedMode) => {
    setSpeedState(s);
  }, []);

  const triggerSignalDotPulse = useCallback(() => {
    setPulseSignalDot(true);
    setTimeout(() => setPulseSignalDot(false), 300);
  }, []);

  return {
    speed,
    setSpeed,
    activeStage,
    setActiveStage,
    pulseSignalDot,
    triggerSignalDotPulse,
  };
}
