import { useState, useCallback } from 'react';

export function usePolygonEditor(initialPoints: [number, number][] = []) {
  const [points, setPoints] = useState<[number, number][]>(initialPoints);
  const [isDrawing, setIsDrawing] = useState(false);

  const addPoint = useCallback((x: number, y: number) => {
    setPoints((prev) => [...prev, [x, y]]);
  }, []);

  const clearPoints = useCallback(() => {
    setPoints([]);
    setIsDrawing(false);
  }, []);

  const updatePoint = useCallback((index: number, x: number, y: number) => {
    setPoints((prev) => {
      const next = [...prev];
      next[index] = [x, y];
      return next;
    });
  }, []);

  return {
    points,
    setPoints,
    isDrawing,
    setIsDrawing,
    addPoint,
    clearPoints,
    updatePoint,
  };
}
