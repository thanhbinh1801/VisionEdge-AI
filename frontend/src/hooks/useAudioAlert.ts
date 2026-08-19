import { useCallback, useRef } from 'react';
import { SeverityLevel } from '../types';

export function useAudioAlert() {
  const audioCtxRef = useRef<AudioContext | null>(null);

  const playBeep = useCallback((severity: SeverityLevel) => {
    if (severity < 3) return; // Beep audio alert only for level 3 critical alerts (ADR-001)

    try {
      if (!audioCtxRef.current) {
        const AudioContextClass = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
        audioCtxRef.current = new AudioContextClass();
      }

      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume();
      }

      const osc = ctx.createOscillator();
      const gain = ctx.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(880, ctx.currentTime); // High pitch alarm sound
      gain.gain.setValueAtTime(0.3, ctx.currentTime);

      osc.connect(gain);
      gain.connect(ctx.destination);

      osc.start();
      osc.stop(ctx.currentTime + 0.5); // 500ms beep duration
    } catch {
      // Ignore audio synthesis errors on autoplay restrictions
    }
  }, []);

  return { playBeep };
}
