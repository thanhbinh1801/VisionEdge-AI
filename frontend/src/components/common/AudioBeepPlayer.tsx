import React, { useEffect } from 'react';
import { useAudioAlert } from '../../hooks/useAudioAlert';
import { EventRecord } from '../../types';

interface AudioBeepPlayerProps {
  lastEvent?: EventRecord | null;
  isMuted?: boolean;
}

export const AudioBeepPlayer: React.FC<AudioBeepPlayerProps> = ({ lastEvent, isMuted = false }) => {
  const { playBeep } = useAudioAlert();

  useEffect(() => {
    if (!isMuted && lastEvent && lastEvent.severity === 3) {
      playBeep(3);
    }
  }, [lastEvent, isMuted, playBeep]);

  return null;
};
