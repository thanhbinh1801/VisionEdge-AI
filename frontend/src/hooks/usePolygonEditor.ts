import { useState, useRef, useCallback } from 'react';
import { ZoneConfig } from '../types';

interface DragState {
  mode: 'vertex' | 'move';
  id: string;
  idx?: number;
  p0?: { x: number; y: number };
  orig?: [number, number][];
}

interface DraftState {
  points: [number, number][];
  hover: [number, number] | null;
}

export function usePolygonEditor(
  zones: ZoneConfig[],
  onUpdateZone: (zoneId: string, patch: Partial<ZoneConfig>) => void,
  onAddZone: (newZone: ZoneConfig) => void
) {
  const [tool, setTool] = useState<'select' | 'draw'>('select');
  const [zoneSel, setZoneSel] = useState<string | null>(null);
  const [zDraft, setZDraft] = useState<DraftState | null>(null);

  const dragRef = useRef<DragState | null>(null);

  const getFeedRect = (e: React.MouseEvent) => {
    let el: HTMLElement | null = e.target as HTMLElement;
    while (el) {
      if (el.dataset && el.dataset.zfeed) {
        return el.getBoundingClientRect();
      }
      el = el.parentElement;
    }
    return null;
  };

  const getPct = useCallback((e: React.MouseEvent) => {
    const r = getFeedRect(e);
    if (!r || !r.width) return null;
    const clamp = (v: number) => Math.max(0, Math.min(100, v));
    return {
      x: clamp(((e.clientX - r.left) / r.width) * 100),
      y: clamp(((e.clientY - r.top) / r.height) * 100),
    };
  }, []);

  const finishDraw = useCallback(() => {
    if (!zDraft || zDraft.points.length < 3) return;
    const id = 'z' + Date.now();
    const colors = ['#2f9bff', '#ff9f0a', '#bf5af2', '#30d158'];
    const newZone: ZoneConfig = {
      id,
      name: 'Zone mới ' + (zones.length + 1),
      color: colors[zones.length % colors.length],
      points: zDraft.points.map((p) => [+p[0].toFixed(1), +p[1].toFixed(1)]),
      types: { 'Container': 1, 'Xe nâng': 1, 'Xe con': 0, 'Xe máy': 0 },
    };
    onAddZone(newZone);
    setZoneSel(id);
    setTool('select');
    setZDraft(null);
  }, [zDraft, zones, onAddZone]);

  const cancelDraw = useCallback(() => {
    setZDraft(null);
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (tool !== 'draw') {
        dragRef.current = null;
        setZoneSel(null);
        return;
      }
      const p = getPct(e);
      if (!p) return;

      if (zDraft && zDraft.points.length >= 3) {
        const f = zDraft.points[0];
        if (Math.abs(p.x - f[0]) < 3 && Math.abs(p.y - f[1]) < 3) {
          finishDraw();
          return;
        }
      }

      setZDraft((prev) => ({
        points: [...(prev?.points || []), [p.x, p.y]],
        hover: null,
      }));
    },
    [tool, zDraft, getPct, finishDraw]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      const p = getPct(e);
      if (!p) return;

      if (tool === 'draw') {
        if (zDraft && zDraft.points.length > 0) {
          setZDraft((prev) => (prev ? { ...prev, hover: [p.x, p.y] } : null));
        }
        return;
      }

      const d = dragRef.current;
      if (!d) return;

      const clampCoord = (v: number, min: number, max: number) => Math.max(min, Math.min(max, v));

      const selZone = zones.find((x) => x.id === d.id);
      if (!selZone) return;

      if (d.mode === 'vertex' && d.idx !== undefined) {
        const pts: [number, number][] = selZone.points.map((v) => [...v] as [number, number]);
        pts[d.idx] = [clampCoord(p.x, 1.5, 98.5), clampCoord(p.y, 2.5, 97)];
        onUpdateZone(d.id, { points: pts });
      } else if (d.mode === 'move' && d.p0 && d.orig) {
        let dx = p.x - d.p0.x;
        let dy = p.y - d.p0.y;
        const xs = d.orig.map((v) => v[0]);
        const ys = d.orig.map((v) => v[1]);
        dx = Math.max(1.5 - Math.min(...xs), Math.min(98.5 - Math.max(...xs), dx));
        dy = Math.max(2.5 - Math.min(...ys), Math.min(97 - Math.max(...ys), dy));
        onUpdateZone(d.id, {
          points: d.orig.map((v) => [v[0] + dx, v[1] + dy] as [number, number]),
        });
      }
    },
    [tool, zDraft, zones, getPct, onUpdateZone]
  );

  const handleMouseUp = useCallback(() => {
    dragRef.current = null;
  }, []);

  const handlePolygonMouseDown = useCallback(
    (e: React.MouseEvent, zoneId: string) => {
      if (e && e.stopPropagation) e.stopPropagation();
      if (tool !== 'select') return;
      const p = getPct(e);
      if (!p) return;
      const z = zones.find((x) => x.id === zoneId);
      if (!z) return;
      dragRef.current = {
        mode: 'move',
        id: zoneId,
        p0: p,
        orig: z.points.map((q) => [...q] as [number, number]),
      };
      setZoneSel(zoneId);
    },
    [tool, zones, getPct]
  );

  const handleVertexMouseDown = useCallback(
    (e: React.MouseEvent, zoneId: string, idx: number) => {
      if (e && e.stopPropagation) e.stopPropagation();
      dragRef.current = { mode: 'vertex', id: zoneId, idx };
    },
    []
  );

  const handleEdgeMouseDown = useCallback(
    (e: React.MouseEvent, zoneId: string, idx: number, mx: number, my: number) => {
      if (e && e.stopPropagation) e.stopPropagation();
      const z = zones.find((x) => x.id === zoneId);
      if (!z) return;
      const pts: [number, number][] = z.points.map((v) => [...v] as [number, number]);
      pts.splice(idx + 1, 0, [mx, my]);
      onUpdateZone(zoneId, { points: pts });
      dragRef.current = { mode: 'vertex', id: zoneId, idx: idx + 1 };
    },
    [zones, onUpdateZone]
  );

  return {
    tool,
    setTool,
    zoneSel,
    setZoneSel,
    zDraft,
    finishDraw,
    cancelDraw,
    handleMouseDown,
    handleMouseMove,
    handleMouseUp,
    handlePolygonMouseDown,
    handleVertexMouseDown,
    handleEdgeMouseDown,
  };
}
