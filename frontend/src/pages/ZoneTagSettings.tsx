import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '../context/AppContext';
import { usePolygonEditor } from '../hooks/usePolygonEditor';
import { fetchZoneFrame, VideoFrameMetadata } from '../services/api';

const formatTimestamp = (seconds: number) => {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
};

export const ZoneTagSettings: React.FC = () => {
  const {
    subTab,
    setSubTab,
    vehicles,
    toggleVehicleTag,
    zonesByCam,
    updateZone,
    addZone,
    deleteZone,
    toggleZoneType,
    objLabels,
    addObjLabel,
    renameObjLabel,
    deleteObjLabel,
    annSources,
    annSamples,
    addAnnSource,
    addAnnSample,
    updateAnnSampleLabel,
    deleteAnnSample,
    saveAnnSamples,
    clock,
  } = useApp();

  // Sub-tab 2 (Zone Editor) State
  const [camSel, setCamSel] = useState<string>('BAI-KIEM');
  const [editingZoneCardId, setEditingZoneCardId] = useState<string | null>(null);
  const [editingZoneCardText, setEditingZoneCardText] = useState<string>('');
  const [zoneFrameError, setZoneFrameError] = useState<string>('');
  const [zoneFrameSrc, setZoneFrameSrc] = useState<string>('');
  const [zoneFrameStatus, setZoneFrameStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [zoneFrameIndex, setZoneFrameIndex] = useState(0);
  const [zoneFrameDraft, setZoneFrameDraft] = useState(0);
  const [zoneFrameMeta, setZoneFrameMeta] = useState<VideoFrameMetadata | null>(null);
  const [zoneFrameRetry, setZoneFrameRetry] = useState(0);


  const curCamZones = zonesByCam[camSel] || [];

  useEffect(() => {
    let active = true;
    let objectUrl = '';
    setZoneFrameError('');
    setZoneFrameStatus('loading');
    fetchZoneFrame(camSel, { frameIndex: zoneFrameIndex })
      .then(({ blob, metadata }) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setZoneFrameSrc(objectUrl);
        setZoneFrameMeta(metadata);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setZoneFrameStatus('error');
        setZoneFrameError(error instanceof Error ? error.message : 'Không tải được frame video nền.');
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [camSel, zoneFrameIndex, zoneFrameRetry]);

  useEffect(() => {
    setZoneFrameIndex(0);
    setZoneFrameDraft(0);
    setZoneFrameMeta(null);
  }, [camSel]);

  const retryZoneFrame = () => {
    setZoneFrameError('');
    setZoneFrameStatus('loading');
    setZoneFrameRetry((value) => value + 1);
  };
  const {
    tool,
    setTool,
    zoneSel,
    setZoneSel,
    zDraft,
    finishDraw,
    cancelDraw,
    handleMouseDown: handleZoneMouseDown,
    handleMouseMove: handleZoneMouseMove,
    handleMouseUp: handleZoneMouseUp,
    handlePolygonMouseDown,
    handleVertexMouseDown,
    handleEdgeMouseDown,
  } = usePolygonEditor(
    curCamZones,
    (zId, patch) => updateZone(camSel, zId, patch),
    (newZ) => addZone(camSel, newZ)
  );

  // Sub-tab 3 (Object Labeler) State
  const [nlName, setNlName] = useState<string>('');
  const [nlKind, setNlKind] = useState<'nguoi' | 'xe'>('xe');
  const [annSel, setAnnSel] = useState<string | null>('l8'); // Selected label ID for drawing
  const [annSrc, setAnnSrc] = useState<string>('src1'); // Selected annotation source ID
  const [vidFrame, setVidFrame] = useState<number>(1);
  const [savedMsg, setSavedMsg] = useState<string>('');
  const [annPick, setAnnPick] = useState<string | null>(null); // Selected sample ID on canvas
  const [annDraft, setAnnDraft] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const [annFrameDraft, setAnnFrameDraft] = useState(1);
  const [annFrameSrc, setAnnFrameSrc] = useState('');
  const [annFrameMeta, setAnnFrameMeta] = useState<VideoFrameMetadata | null>(null);
  const [annFrameStatus, setAnnFrameStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [annFrameError, setAnnFrameError] = useState('');
  const [annFrameRetry, setAnnFrameRetry] = useState(0);

  const annDragRef = useRef<{ x0: number; y0: number } | null>(null);

  // Helper for annotation canvas percent coords
  const getAnnPct = (e: React.MouseEvent) => {
    let el: HTMLElement | null = e.target as HTMLElement;
    while (el) {
      if (el.dataset && el.dataset.annfeed) {
        const r = el.getBoundingClientRect();
        if (!r.width) return null;
        const clamp = (v: number) => Math.max(0, Math.min(100, v));
        return {
          x: clamp(((e.clientX - r.left) / r.width) * 100),
          y: clamp(((e.clientY - r.top) / r.height) * 100),
        };
      }
      el = el.parentElement;
    }
    return null;
  };

  const handleAnnMouseDown = (e: React.MouseEvent) => {
    if (!annSel) return;
    const p = getAnnPct(e);
    if (!p) return;
    annDragRef.current = { x0: p.x, y0: p.y };
    setAnnDraft({ x: p.x, y: p.y, w: 0, h: 0 });
  };

  const handleAnnMouseMove = (e: React.MouseEvent) => {
    const d = annDragRef.current;
    if (!d) return;
    const p = getAnnPct(e);
    if (!p) return;
    setAnnDraft({
      x: Math.min(d.x0, p.x),
      y: Math.min(d.y0, p.y),
      w: Math.abs(p.x - d.x0),
      h: Math.abs(p.y - d.y0),
    });
  };

  const handleAnnMouseUp = () => {
    const d = annDragRef.current;
    annDragRef.current = null;
    if (!d) return;
    const dft = annDraft;
    setAnnDraft(null);
    if (!dft || dft.w < 2 || dft.h < 2 || !annSel) return;

    const curSource = annSources.find((s) => s.id === annSrc) || annSources[0];
    const newSampleId = addAnnSample({
      labelId: annSel,
      srcId: curSource.id,
      frame: curSource.kind === 'video' ? vidFrame : null,
      x: +dft.x.toFixed(1),
      y: +dft.y.toFixed(1),
      w: +dft.w.toFixed(1),
      h: +dft.h.toFixed(1),
    });
    setSavedMsg('');
    setAnnPick(newSampleId);
  };

  const handleSaveSamples = () => {
    const count = saveAnnSamples();
    if (count > 0) {
      setSavedMsg(`✓ Đã lưu ${count} mẫu`);
    }
  };

  const handleSaveNewLabel = () => {
    const trimmed = nlName.trim();
    if (!trimmed) return;
    addObjLabel(trimmed, nlKind);
    setNlName('');
  };

  const handleImportImage = () => {
    const imgCount = annSources.filter((s) => s.kind === 'img').length + 1;
    const tints = ['#2a3f55', '#3d4a3a', '#4a3d5a', '#5a4a3d'];
    const id = 'src' + Date.now();
    addAnnSource({
      id,
      name: `import-hinh-${String(imgCount).padStart(2, '0')}.jpg`,
      kind: 'img',
      tint: tints[imgCount % tints.length],
    });
    setAnnSrc(id);
    setAnnDraft(null);
    setSavedMsg('');
    setAnnPick(null);
  };

  const handleImportVideo = () => {
    const vidCount = annSources.filter((s) => s.kind === 'video').length + 1;
    const id = 'src' + Date.now();
    addAnnSource({
      id,
      name: `import-video-${String(vidCount).padStart(2, '0')}.mp4`,
      kind: 'video',
      tint: '#3a4450',
    });
    setAnnSrc(id);
    setVidFrame(0);
    setAnnDraft(null);
    setSavedMsg('');
    setAnnPick(null);
  };

  const currentAnnSource = annSources.find((s) => s.id === annSrc) || annSources[0];
  const annCameraId = currentAnnSource.name.toLowerCase().includes('gate') ? 'GATE-01' : 'BAI-KIEM';

  useEffect(() => {
    if (currentAnnSource.kind !== 'video') {
      setAnnFrameSrc('');
      setAnnFrameMeta(null);
      setAnnFrameError('');
      return;
    }
    let active = true;
    let objectUrl = '';
    setAnnFrameStatus('loading');
    setAnnFrameError('');
    fetchZoneFrame(annCameraId, { frameIndex: vidFrame })
      .then(({ blob, metadata }) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setAnnFrameSrc(objectUrl);
        setAnnFrameMeta(metadata);
      })
      .catch((error: unknown) => {
        if (!active) return;
        setAnnFrameStatus('error');
        setAnnFrameError(error instanceof Error ? error.message : 'Không tải được frame dataset.');
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [annCameraId, currentAnnSource.kind, vidFrame, annFrameRetry]);

  useEffect(() => {
    setAnnFrameDraft(vidFrame);
  }, [vidFrame]);

  const frameKey = currentAnnSource.id + (currentAnnSource.kind === 'video' ? ':' + vidFrame : '');
  const activeAnnBoxes = annSamples.filter(
    (s) =>
      (s.srcId || 'src1') + (s.frame !== undefined && s.frame !== null ? ':' + s.frame : '') === frameKey ||
      ((s.srcId || 'src1') === currentAnnSource.id && currentAnnSource.kind !== 'video' && s.frame === null)
  );

  const pendingCount = annSamples.filter((s) => s.session).length;
  const pickedSample = annSamples.find((s) => s.id === annPick) || null;
  const activeLabelObj = objLabels.find((o) => o.id === annSel) || null;

  const labelColors: Record<string, string> = {
    l1: '#39e0d0',
    l2: '#30d158',
    l3: '#ff9f0a',
    l4: '#bf5af2',
    l5: '#5fb3ff',
    l6: '#ff453a',
    l7: '#a1a1ab',
    l8: '#2f9bff',
  };
  const getLabelColor = (id: string) => labelColors[id] || '#2f9bff';

  const iconsSvg: Record<string, string> = {
    nguoi: 'M12 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM5 21c0-4 3-6 7-6s7 2 7 6',
    xe: 'M3 16V9h11v7M14 11h4l3 3v2M6 19a1.5 1.5 0 1 0 0-3M17 19a1.5 1.5 0 1 0 0-3',
  };

  return (
    <div style={{ padding: '20px', maxWidth: '1360px', margin: '0 auto' }}>
      {/* Sub-tab Switcher Pills */}
      <div
        style={{
          display: 'flex',
          gap: '5px',
          background: 'var(--card)',
          border: '1px solid var(--line)',
          borderRadius: '11px',
          padding: '4px',
          marginBottom: '18px',
          width: 'fit-content',
        }}
      >
        <button
          onClick={() => setSubTab('label')}
          style={{
            fontSize: '12.5px',
            fontWeight: 600,
            padding: '7px 15px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap',
            background: subTab === 'label' ? 'var(--acc)' : 'transparent',
            color: subTab === 'label' ? '#fff' : 'var(--ink2)',
          }}
        >
          Gắn nhãn xe
        </button>
        <button
          onClick={() => setSubTab('zone')}
          style={{
            fontSize: '12.5px',
            fontWeight: 600,
            padding: '7px 15px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap',
            background: subTab === 'zone' ? 'var(--acc)' : 'transparent',
            color: subTab === 'zone' ? '#fff' : 'var(--ink2)',
          }}
        >
          Vẽ zone
        </button>
        <button
          onClick={() => setSubTab('obj')}
          style={{
            fontSize: '12.5px',
            fontWeight: 600,
            padding: '7px 15px',
            borderRadius: '8px',
            border: 'none',
            cursor: 'pointer',
            fontFamily: 'inherit',
            whiteSpace: 'nowrap',
            background: subTab === 'obj' ? 'var(--acc)' : 'transparent',
            color: subTab === 'obj' ? '#fff' : 'var(--ink2)',
          }}
        >
          Nhãn đối tượng
        </button>
      </div>

      {/* ==================== SUB-TAB 1: GẮN NHÃN XE ==================== */}
      {subTab === 'label' && (
        <div
          style={{
            background: 'var(--card)',
            border: '1px solid var(--line)',
            borderRadius: '14px',
            overflow: 'hidden',
          }}
        >
          <div style={{ padding: '13px 16px', borderBottom: '1px solid var(--line)' }}>
            <div style={{ fontSize: '13.5px', fontWeight: 600 }}>Gắn nhãn phương tiện đã thu thập</div>
            <div style={{ fontSize: '11.5px', color: 'var(--ink3)', marginTop: '2px' }}>
              Đánh dấu xe quen (được phép) / xe lạ — hệ thống dùng nhãn này để cảnh báo khi xe vào zone
            </div>
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '70px 1.1fr 1fr 0.8fr 0.9fr 130px',
              padding: '9px 16px',
              borderBottom: '1px solid var(--line)',
              fontSize: '11px',
              color: 'var(--ink3)',
              fontWeight: 600,
            }}
          >
            <div>Ảnh</div>
            <div>Biển số</div>
            <div>Loại xe</div>
            <div>Lượt vào</div>
            <div>Lần cuối</div>
            <div>Nhãn</div>
          </div>

          {vehicles.map((v) => {
            const isLa = v.tag === 'la';
            const tagFg = isLa ? 'var(--p0)' : 'var(--ok)';
            const tagBg = isLa ? 'var(--p0q)' : 'var(--okq)';
            const tagBorder = isLa ? 'var(--p0)' : 'var(--ok)';
            const tagLabel = isLa ? 'Xe lạ' : 'Xe quen';

            return (
              <div
                key={v.plate}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '70px 1.1fr 1fr 0.8fr 0.9fr 130px',
                  padding: '11px 16px',
                  borderBottom: '1px solid var(--line)',
                  alignItems: 'center',
                  fontSize: '12.5px',
                }}
              >
                <div>
                  <div
                    style={{
                      width: '52px',
                      height: '34px',
                      borderRadius: '6px',
                      background: `linear-gradient(150deg, ${v.tint || '#1a2129'}, #11161c)`,
                      border: '1px solid var(--line2)',
                    }}
                  />
                </div>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", fontWeight: 600 }}>{v.plate}</div>
                <div style={{ color: 'var(--ink2)' }}>{v.type}</div>
                <div style={{ fontFamily: "'IBM Plex Mono', monospace", color: 'var(--ink2)' }}>
                  {v.visits}
                </div>
                <div
                  style={{
                    color: 'var(--ink3)',
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: '11.5px',
                  }}
                >
                  {v.last}
                </div>
                <div>
                  <button
                    onClick={() => toggleVehicleTag(v.plate)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '7px',
                      fontSize: '11.5px',
                      fontWeight: 700,
                      padding: '5px 12px',
                      borderRadius: '20px',
                      border: `1px solid ${tagBorder}`,
                      background: tagBg,
                      color: tagFg,
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: tagFg }} />
                    {tagLabel}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ==================== SUB-TAB 2: VẼ ZONE ==================== */}
      {subTab === 'zone' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '16px' }}>
          {/* Left Column: Interactive Canvas */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
              <div
                style={{
                  display: 'flex',
                  gap: '4px',
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: '10px',
                  padding: '4px',
                }}
              >
                {[
                  { id: 'BAI-KIEM', label: 'Bãi Kiểm' },
                  { id: 'GATE-01', label: 'Cổng vào' },
                ].map((c) => {
                  const on = camSel === c.id;
                  return (
                    <button
                      key={c.id}
                      onClick={() => {
                        setCamSel(c.id);
                        setZoneSel(null);
                        setZoneFrameError('');
                      }}
                      style={{
                        fontSize: '12px',
                        fontWeight: 600,
                        padding: '6px 12px',
                        borderRadius: '7px',
                        border: 'none',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                        whiteSpace: 'nowrap',
                        background: on ? 'var(--acc)' : 'transparent',
                        color: on ? '#fff' : 'var(--ink2)',
                      }}
                    >
                      {c.label}
                    </button>
                  );
                })}
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '6px 12px',
                  borderRadius: '10px',
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--ink2)',
                  whiteSpace: 'nowrap',
                }}
              >
                Camera kiểm thử · {camSel === 'GATE-01' ? 'Cổng vào' : 'Bãi Kiểm'}
              </div>

              {/* Tool Pills */}
              <div
                style={{
                  display: 'flex',
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: '10px',
                  padding: '4px',
                  gap: '2px',
                }}
              >
                <button
                  onClick={() => setTool('select')}
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '6px 12px',
                    borderRadius: '7px',
                    border: 'none',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    whiteSpace: 'nowrap',
                    background: tool === 'select' ? 'var(--acc)' : 'transparent',
                    color: tool === 'select' ? '#fff' : 'var(--ink2)',
                  }}
                >
                  Chọn
                </button>
                <button
                  onClick={() => setTool('draw')}
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '6px 12px',
                    borderRadius: '7px',
                    border: 'none',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    whiteSpace: 'nowrap',
                    background: tool === 'draw' ? 'var(--acc)' : 'transparent',
                    color: tool === 'draw' ? '#fff' : 'var(--ink2)',
                  }}
                >
                  Vẽ zone
                </button>
              </div>

              {zDraft && zDraft.points.length >= 3 && (
                <button
                  onClick={finishDraw}
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '7px 14px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--ok)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  ✓ Hoàn tất zone
                </button>
              )}

              {zDraft && (
                <button
                  onClick={cancelDraw}
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '7px 14px',
                    borderRadius: '8px',
                    border: '1px solid var(--line2)',
                    background: 'transparent',
                    color: 'var(--ink2)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Hủy
                </button>
              )}

              <span style={{ fontSize: '11.5px', color: 'var(--ink3)' }}>
                {tool === 'draw'
                  ? 'Bấm lần lượt trên khung hình để thêm góc; bấm gần điểm đầu hoặc “Hoàn tất” để đóng zone.'
                  : 'Bấm chọn zone: kéo đỉnh để sửa hình dạng, kéo điểm giữa cạnh để thêm góc, kéo thân để di chuyển.'}
              </span>
            </div>

            {/* SVG Polygon Canvas Container */}
            <div
              data-zfeed="1"
              onMouseDown={handleZoneMouseDown}
              onMouseMove={handleZoneMouseMove}
              onMouseUp={handleZoneMouseUp}
              onMouseLeave={handleZoneMouseUp}
              style={{
                position: 'relative',
                width: '100%',
                aspectRatio: '16/9',
                background: '#0c0f13',
                border: '1px solid var(--line)',
                borderRadius: '12px',
                overflow: 'hidden',
                cursor: tool === 'draw' ? 'crosshair' : 'default',
                userSelect: 'none',
              }}
            >
              {/* Real Overhead Camera Background Image from backend-extracted video frame */}
              <img
                src={zoneFrameSrc}
                alt={`${camSel} Camera View`}
                onLoad={() => setZoneFrameStatus('success')}
                onError={() => {
                  setZoneFrameStatus('error');
                  setZoneFrameError('Không tải được frame video nền từ backend.');
                }}
                style={{
                  position: 'absolute',
                  inset: 0,
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                  opacity: 1,
                  pointerEvents: 'none',
                }}
              />
              {zoneFrameStatus !== 'success' && (
                <div
                  role={zoneFrameStatus === 'error' ? 'alert' : 'status'}
                  aria-live="polite"
                  style={{
                    position: 'absolute',
                    inset: 0,
                    display: 'grid',
                    placeItems: 'center',
                    textAlign: 'center',
                    background: 'rgba(0,0,0,.72)',
                    color: '#fff',
                    fontSize: '12px',
                    zIndex: 4,
                  }}
                >
                  <div>
                    <div>{zoneFrameStatus === 'error' ? zoneFrameError : 'Đang trích xuất frame thật…'}</div>
                    {zoneFrameStatus === 'error' && (
                      <button
                        type="button"
                        onClick={(event) => {
                          event.stopPropagation();
                          retryZoneFrame();
                        }}
                        style={{ marginTop: '9px', padding: '5px 10px', cursor: 'pointer' }}
                      >
                        Thử lại
                      </button>
                    )}
                  </div>
                </div>
              )}


              {/* Camera Badges */}
              <div
                style={{
                  position: 'absolute',
                  left: '10px',
                  top: '9px',
                  background: 'rgba(0,0,0,.55)',
                  color: '#e3e7ea',
                  fontSize: '10px',
                  padding: '3px 7px',
                  borderRadius: '5px',
                  fontFamily: "'IBM Plex Mono', monospace",
                  pointerEvents: 'none',
                }}
              >
                {zoneFrameMeta?.sourceName || camSel} · frame {zoneFrameMeta?.frameIndex ?? zoneFrameIndex}
              </div>
              <div
                style={{
                  position: 'absolute',
                  right: '10px',
                  bottom: '9px',
                  background: 'rgba(0,0,0,.55)',
                  color: '#e3e7ea',
                  fontSize: '10px',
                  padding: '3px 7px',
                  borderRadius: '5px',
                  fontFamily: "'IBM Plex Mono', monospace",
                  pointerEvents: 'none',
                }}
              >
                {zoneFrameMeta
                  ? `${formatTimestamp(zoneFrameMeta.timestampSeconds)} · ${zoneFrameMeta.fps?.toFixed(1) ?? '?'} FPS`
                  : `${clock} · góc trên cao`}
              </div>

              {/* SVG Polygons */}
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }}>
                {curCamZones.map((z) => {
                  const sel = zoneSel === z.id;
                  const ptsStr = z.points.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
                  return (
                    <polygon
                      key={z.id}
                      onMouseDown={(e) => handlePolygonMouseDown(e, z.id)}
                      points={ptsStr}
                      fill={z.color + (sel ? '33' : '1a')}
                      stroke={z.color}
                      strokeWidth={sel ? '2' : '1.5'}
                      strokeDasharray={sel ? '0' : '5 4'}
                      vectorEffect="non-scaling-stroke"
                      style={{ cursor: tool === 'select' ? (sel ? 'move' : 'pointer') : 'crosshair', pointerEvents: 'auto' }}
                    />
                  );
                })}

                {/* Draft Polygon Preview */}
                {zDraft && zDraft.points.length > 0 && (
                  <polygon
                    points={(zDraft.hover ? [...zDraft.points, zDraft.hover] : zDraft.points)
                      .map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`)
                      .join(' ')}
                    fill="rgba(47,155,255,.16)"
                    stroke="#2f9bff"
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                    vectorEffect="non-scaling-stroke"
                    style={{ pointerEvents: 'none' }}
                  />
                )}
              </svg>

              {/* Zone Label Tags */}
              {curCamZones.map((z) => {
                let topPoint = z.points[0];
                for (const p of z.points) {
                  if (p[1] < topPoint[1]) topPoint = p;
                }
                return (
                  <span
                    key={z.id}
                    style={{
                      position: 'absolute',
                      left: `${topPoint[0]}%`,
                      top: `${topPoint[1]}%`,
                      transform: 'translateY(-115%)',
                      background: z.color,
                      color: '#06080a',
                      fontSize: '9.5px',
                      fontWeight: 700,
                      padding: '1px 7px',
                      borderRadius: '3px',
                      whiteSpace: 'nowrap',
                      pointerEvents: 'none',
                    }}
                  >
                    {z.name}
                  </span>
                );
              })}

              {/* Vertex Handles (Square white dots with zone color border) */}
              {tool === 'select' &&
                (() => {
                  const selZoneObj = curCamZones.find((z) => z.id === zoneSel);
                  if (!selZoneObj) return null;
                  return selZoneObj.points.map((p, i) => (
                    <span
                      key={i}
                      onMouseDown={(e) => handleVertexMouseDown(e, selZoneObj.id, i)}
                      style={{
                        position: 'absolute',
                        left: `${p[0]}%`,
                        top: `${p[1]}%`,
                        width: '11px',
                        height: '11px',
                        margin: '-5.5px 0 0 -5.5px',
                        background: '#fff',
                        border: `1.5px solid ${selZoneObj.color}`,
                        borderRadius: '2px',
                        cursor: 'grab',
                      }}
                    />
                  ));
                })()}

              {/* Edge Handles (Round dashed dots at midpoints) */}
              {tool === 'select' &&
                (() => {
                  const selZoneObj = curCamZones.find((z) => z.id === zoneSel);
                  if (!selZoneObj) return null;
                  return selZoneObj.points.map((p, i) => {
                    const q = selZoneObj.points[(i + 1) % selZoneObj.points.length];
                    const mx = (p[0] + q[0]) / 2;
                    const my = (p[1] + q[1]) / 2;
                    return (
                      <span
                        key={i}
                        onMouseDown={(e) => handleEdgeMouseDown(e, selZoneObj.id, i, mx, my)}
                        title="Kéo để thêm góc"
                        style={{
                          position: 'absolute',
                          left: `${mx}%`,
                          top: `${my}%`,
                          width: '9px',
                          height: '9px',
                          margin: '-4.5px 0 0 -4.5px',
                          background: 'rgba(255,255,255,.25)',
                          border: `1.5px dashed ${selZoneObj.color}`,
                          borderRadius: '50%',
                          cursor: 'copy',
                        }}
                      />
                    );
                  });
                })()}

              {/* Draft Vertex Dots */}
              {zDraft &&
                zDraft.points.map((p, idx) => (
                  <span
                    key={idx}
                    style={{
                      position: 'absolute',
                      left: `${p[0]}%`,
                      top: `${p[1]}%`,
                      width: '9px',
                      height: '9px',
                      margin: '-4.5px 0 0 -4.5px',
                      background: '#2f9bff',
                      border: '1.5px solid #fff',
                      borderRadius: '50%',
                      pointerEvents: 'none',
                    }}
                  />
                ))}
            </div>

            <div style={{ marginTop: '9px', padding: '9px 12px', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: '10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '6px', fontSize: '11px', color: 'var(--ink3)' }}>
                <span>Frame preview: {zoneFrameDraft}</span>
                <span>{zoneFrameMeta ? `${zoneFrameMeta.sourceName} · ${formatTimestamp(zoneFrameMeta.timestampSeconds)}` : 'Đang đọc metadata…'}</span>
              </div>
              <input
                type="range"
                min={0}
                max={Math.max(0, (zoneFrameMeta?.totalFrames ?? 301) - 1)}
                value={Math.min(zoneFrameDraft, Math.max(0, (zoneFrameMeta?.totalFrames ?? 301) - 1))}
                onChange={(event) => setZoneFrameDraft(Number(event.target.value))}
                onPointerUp={(event) => setZoneFrameIndex(Number(event.currentTarget.value))}
                onKeyUp={(event) => setZoneFrameIndex(Number(event.currentTarget.value))}
                aria-label="Chọn frame nền cho Zone Editor"
                style={{ width: '100%' }}
              />
            </div>
          </div>

          {/* Right Column: Zone Cards List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {curCamZones.map((z) => {
              const isSelected = zoneSel === z.id;
              return (
                <div
                  key={z.id}
                  onClick={() => setZoneSel(z.id)}
                  style={{
                    background: 'var(--card)',
                    border: `1px solid ${isSelected ? z.color : 'var(--line)'}`,
                    borderRadius: '13px',
                    padding: '14px',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '9px', marginBottom: '10px' }}>
                    <span style={{ width: '10px', height: '10px', borderRadius: '3px', background: z.color }} />
                    {editingZoneCardId === z.id ? (
                      <input
                        type="text"
                        value={editingZoneCardText}
                        onChange={(e) => setEditingZoneCardText(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const trimmed = editingZoneCardText.trim();
                            if (trimmed) updateZone(camSel, z.id, { name: trimmed });
                            setEditingZoneCardId(null);
                          }
                          if (e.key === 'Escape') setEditingZoneCardId(null);
                        }}
                        onBlur={() => {
                          const trimmed = editingZoneCardText.trim();
                          if (trimmed) updateZone(camSel, z.id, { name: trimmed });
                          setEditingZoneCardId(null);
                        }}
                        onClick={(e) => e.stopPropagation()}
                        autoFocus
                        style={{
                          fontSize: '12.5px',
                          fontWeight: 600,
                          flex: 1,
                          background: 'var(--bg)',
                          border: `1px solid ${z.color}`,
                          borderRadius: '4px',
                          color: 'var(--ink)',
                          padding: '2px 6px',
                        }}
                      />
                    ) : (
                      <span
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingZoneCardId(z.id);
                          setEditingZoneCardText(z.name);
                        }}
                        title="Bấm để chỉnh sửa tên zone"
                        style={{ fontSize: '13px', fontWeight: 600, flex: 1, cursor: 'pointer' }}
                      >
                        {z.name} <span style={{ fontSize: '11px', color: 'var(--ink3)', fontWeight: 400 }}>✎</span>
                      </span>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteZone(camSel, z.id);
                        if (zoneSel === z.id) setZoneSel(null);
                      }}
                      style={{
                        fontSize: '11px',
                        fontWeight: 600,
                        padding: '4px 10px',
                        borderRadius: '7px',
                        border: '1px solid var(--p0)',
                        background: 'transparent',
                        color: 'var(--p0)',
                        cursor: 'pointer',
                        fontFamily: 'inherit',
                      }}
                    >
                      Xóa
                    </button>
                  </div>


                  <div style={{ fontSize: '10.5px', color: 'var(--ink3)', marginBottom: '8px' }}>
                    Chọn loại xe được phép vào zone (bấm để đổi ✓ được phép / ✕ cấm)
                  </div>

                  <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                    {objLabels.map((o) => {
                      const isAllowed = !!z.types[o.name];
                      const btnBg = isAllowed ? 'var(--okq)' : 'var(--p0q)';
                      const btnFg = isAllowed ? 'var(--ok)' : 'var(--p0)';
                      const btnBorder = isAllowed ? 'var(--ok)' : 'rgba(255,69,58,.4)';
                      return (
                        <button
                          key={o.id}
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleZoneType(camSel, z.id, o.name);
                          }}
                          style={{
                            fontSize: '11px',
                            fontWeight: 600,
                            padding: '4px 11px',
                            borderRadius: '20px',
                            border: `1px solid ${btnBorder}`,
                            background: btnBg,
                            color: btnFg,
                            cursor: 'pointer',
                            fontFamily: 'inherit',
                          }}
                        >
                          {isAllowed ? '✓ ' : '✕ '}
                          {o.name}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}

            <div style={{ fontSize: '11px', color: 'var(--ink3)', lineHeight: '1.55', padding: '0 3px' }}>
              Xe mang nhãn <b style={{ color: 'var(--p0)' }}>Xe lạ</b> hoặc sai loại xe cho phép sẽ sinh cảnh báo khi đi vào zone. Zone là đa giác: kéo đỉnh (ô vuông) để sửa hình dạng, kéo điểm tròn giữa cạnh để thêm góc mới, kéo thân để di chuyển.
            </div>
          </div>
        </div>
      )}

      {/* ==================== SUB-TAB 3: NHÃN ĐỐI TƯỢNG ==================== */}
      {subTab === 'obj' && (
        <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '16px', marginBottom: '16px' }}>
          {/* Left Column: Bounding Box Dataset Collector */}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
              <span style={{ fontSize: '12.5px', fontWeight: 600 }}>Gắn mẫu từ hình / video</span>
              <span style={{ fontSize: '11.5px', color: 'var(--ink3)' }}>
                {activeLabelObj ? `Kéo khoanh khung quanh "${activeLabelObj.name}" trên khung hình.` : 'Chọn một nhãn ở bảng bên phải trước.'}
              </span>
              <div style={{ flex: 1 }} />
              <button
                onClick={handleImportImage}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  padding: '6px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--line2)',
                  background: 'var(--card)',
                  color: 'var(--ink)',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                + Import hình
              </button>
              <button
                onClick={handleImportVideo}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  padding: '6px 12px',
                  borderRadius: '8px',
                  border: '1px solid var(--line2)',
                  background: 'var(--card)',
                  color: 'var(--ink)',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                + Import video
              </button>
            </div>

            {/* Thumbnail Sources Bar */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', overflowX: 'auto', paddingBottom: '2px' }}>
              {annSources.map((s) => {
                const isSelected = s.id === annSrc;
                return (
                  <button
                    key={s.id}
                    onClick={() => {
                      setAnnSrc(s.id);
                      setVidFrame(0);
                      setAnnFrameDraft(0);
                      setAnnDraft(null);
                      setAnnPick(null);
                    }}
                    style={{
                      position: 'relative',
                      flex: 'none',
                      width: '96px',
                      height: '58px',
                      borderRadius: '9px',
                      border: `2px solid ${isSelected ? 'var(--acc)' : 'var(--line)'}`,
                      background: '#0c0f13',
                      cursor: 'pointer',
                      overflow: 'hidden',
                      padding: 0,
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        inset: 0,
                        background: `linear-gradient(150deg, ${s.tint || '#1a2129'}, #0c0f13)`,
                      }}
                    />
                    {s.kind === 'video' && (
                      <span
                        style={{
                          position: 'absolute',
                          left: '4px',
                          top: '4px',
                          background: 'rgba(0,0,0,.6)',
                          borderRadius: '4px',
                          padding: '1px 5px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '3px',
                        }}
                      >
                        <span style={{ fontSize: '8px', fontWeight: 700, color: '#fff' }}>VIDEO</span>
                      </span>
                    )}
                    <span
                      style={{
                        position: 'absolute',
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'rgba(0,0,0,.62)',
                        color: '#e3e7ea',
                        fontSize: '8.5px',
                        fontWeight: 600,
                        padding: '2px 5px',
                        textAlign: 'left',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {s.name}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Interactive Annotation Canvas Viewport */}
            <div
              data-annfeed="1"
              onMouseDown={handleAnnMouseDown}
              onMouseMove={handleAnnMouseMove}
              onMouseUp={handleAnnMouseUp}
              onMouseLeave={handleAnnMouseUp}
              style={{
                position: 'relative',
                width: '100%',
                aspectRatio: '16/9',
                background: '#0c0f13',
                border: '1px solid var(--line)',
                borderRadius: '12px',
                overflow: 'hidden',
                cursor: annSel ? 'crosshair' : 'default',
                userSelect: 'none',
              }}
            >
              {currentAnnSource.kind === 'video' ? (
                <img
                  src={annFrameSrc}
                  alt={`Dataset frame ${vidFrame}`}
                  onLoad={() => setAnnFrameStatus('success')}
                  onError={() => {
                    setAnnFrameStatus('error');
                    setAnnFrameError('Không hiển thị được frame dataset đã tải.');
                  }}
                  style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', pointerEvents: 'none' }}
                />
              ) : (
                <div
                  style={{
                    position: 'absolute',
                    inset: 0,
                    pointerEvents: 'none',
                    background: `linear-gradient(150deg, ${currentAnnSource.tint || '#1a2129'}, #0c0f13)`,
                  }}
                />
              )}

              {currentAnnSource.kind === 'video' && annFrameStatus !== 'success' && (
                <div
                  role={annFrameStatus === 'error' ? 'alert' : 'status'}
                  aria-live="polite"
                  style={{ position: 'absolute', inset: 0, zIndex: 5, display: 'grid', placeItems: 'center', background: 'rgba(0,0,0,.72)', color: '#fff', textAlign: 'center', fontSize: '12px' }}
                >
                  <div>
                    <div>{annFrameStatus === 'error' ? annFrameError : 'Đang tải frame dataset…'}</div>
                    {annFrameStatus === 'error' && (
                      <button
                        type="button"
                        onMouseDown={(event) => event.stopPropagation()}
                        onClick={(event) => {
                          event.stopPropagation();
                          setAnnFrameStatus('loading');
                          setAnnFrameRetry((value) => value + 1);
                        }}
                        style={{ marginTop: '9px', padding: '5px 10px', cursor: 'pointer' }}
                      >
                        Thử lại
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* Source Name Badge */}
              <div
                style={{
                  position: 'absolute',
                  left: '10px',
                  top: '9px',
                  background: 'rgba(0,0,0,.55)',
                  color: '#e3e7ea',
                  fontSize: '10px',
                  padding: '3px 7px',
                  borderRadius: '5px',
                  fontFamily: "'IBM Plex Mono', monospace",
                  pointerEvents: 'none',
                }}
              >
                {currentAnnSource.name}
                {currentAnnSource.kind === 'video'
                  ? ` · ${annFrameMeta?.sourceName || annCameraId} · frame ${annFrameMeta?.frameIndex ?? vidFrame} · ${formatTimestamp(annFrameMeta?.timestampSeconds ?? 0)}`
                  : ''}
              </div>

              {/* Render Existing Bounding Boxes */}
              {activeAnnBoxes.map((s) => {
                const lb = objLabels.find((o) => o.id === s.labelId);
                if (!lb) return null;
                const color = getLabelColor(s.labelId);
                const isSelected = annPick === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={(e) => {
                      e.stopPropagation();
                      setAnnPick(s.id);
                    }}
                    style={{
                      position: 'absolute',
                      left: `${s.x}%`,
                      top: `${s.y}%`,
                      width: `${s.w}%`,
                      height: `${s.h}%`,
                      border: `${isSelected ? '2.5px' : '1.5px'} solid ${color}`,
                      background: color + (isSelected ? '2e' : '14'),
                      boxSizing: 'border-box',
                      cursor: 'pointer',
                    }}
                  >
                    <span
                      style={{
                        position: 'absolute',
                        left: '-1px',
                        top: '-18px',
                        background: color,
                        color: '#06080a',
                        fontSize: '9.5px',
                        fontWeight: 700,
                        padding: '1px 7px',
                        borderRadius: '3px',
                        whiteSpace: 'nowrap',
                        pointerEvents: 'none',
                      }}
                    >
                      {lb.name.toUpperCase()}
                    </span>
                  </div>
                );
              })}

              {/* Draft Box Preview during dragging */}
              {annDraft && (
                <div
                  style={{
                    position: 'absolute',
                    left: `${annDraft.x}%`,
                    top: `${annDraft.y}%`,
                    width: `${annDraft.w}%`,
                    height: `${annDraft.h}%`,
                    border: '1.5px dashed #fff',
                    background: 'rgba(255,255,255,.12)',
                    pointerEvents: 'none',
                  }}
                />
              )}
            </div>

            {/* Video Frame Timeline Scrubber (when source is video) */}
            {currentAnnSource.kind === 'video' && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginTop: '9px',
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  borderRadius: '10px',
                  padding: '8px 13px',
                }}
              >
                <span style={{ fontSize: '10.5px', color: 'var(--ink3)', fontFamily: "'IBM Plex Mono', monospace" }}>
                  00:00
                </span>
                <input
                  type="range"
                  min={0}
                  max={Math.max(0, (annFrameMeta?.totalFrames ?? 301) - 1)}
                  value={Math.min(annFrameDraft, Math.max(0, (annFrameMeta?.totalFrames ?? 301) - 1))}
                  onChange={(event) => setAnnFrameDraft(Number(event.target.value))}
                  onPointerUp={(event) => {
                    setVidFrame(Number(event.currentTarget.value));
                    setAnnDraft(null);
                    setAnnPick(null);
                  }}
                  onKeyUp={(event) => {
                    setVidFrame(Number(event.currentTarget.value));
                    setAnnDraft(null);
                    setAnnPick(null);
                  }}
                  aria-label="Chọn frame cho Dataset BBox Tool"
                  style={{ flex: 1 }}
                />
                <span style={{ fontSize: '10.5px', color: 'var(--ink3)', fontFamily: "'IBM Plex Mono', monospace" }}>
                  {formatTimestamp(
                    ((annFrameMeta?.totalFrames ?? 301) - 1) / (annFrameMeta?.fps ?? 30),
                  )}
                </span>
                <span style={{ fontSize: '10.5px', color: 'var(--ink2)' }}>
                  frame {annFrameDraft} · {formatTimestamp(annFrameDraft / (annFrameMeta?.fps ?? 30))}
                </span>
              </div>
            )}

            {/* Controls Bar for Picked Sample */}
            {pickedSample && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginTop: '10px',
                  background: 'var(--card)',
                  border: '1px solid var(--acc)',
                  borderRadius: '10px',
                  padding: '9px 13px',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 600 }}>Mẫu đang chọn:</span>
                <select
                  value={pickedSample.labelId}
                  onChange={(e) => updateAnnSampleLabel(pickedSample.id, e.target.value)}
                  style={{
                    border: '1px solid var(--line2)',
                    borderRadius: '8px',
                    padding: '6px 9px',
                    background: 'var(--bg)',
                    color: 'var(--ink)',
                    fontSize: '12px',
                    fontWeight: 600,
                    fontFamily: 'inherit',
                    outline: 'none',
                    cursor: 'pointer',
                  }}
                >
                  {objLabels.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => {
                    deleteAnnSample(pickedSample.id);
                    setAnnPick(null);
                  }}
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--p0)',
                    background: 'transparent',
                    color: 'var(--p0)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Xóa mẫu
                </button>
                <button
                  onClick={() => setAnnPick(null)}
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--line2)',
                    background: 'transparent',
                    color: 'var(--ink2)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Bỏ chọn
                </button>
                <span style={{ fontSize: '11px', color: 'var(--ink3)' }}>
                  Đổi nhãn trong danh sách để sửa loại cho mẫu này
                </span>
              </div>
            )}

            {/* Bottom Save Action Bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '10px' }}>
              <button
                onClick={handleSaveSamples}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '7px',
                  fontSize: '12.5px',
                  fontWeight: 600,
                  padding: '10px 18px',
                  borderRadius: '10px',
                  border: 'none',
                  background: pendingCount > 0 ? 'var(--ok)' : 'var(--line2)',
                  color: '#fff',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                Lưu {pendingCount} mẫu đã gắn
              </button>
              {savedMsg && (
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ok)' }}>
                  {savedMsg}
                </span>
              )}
              <span style={{ fontSize: '11px', color: 'var(--ink3)', flex: 1 }}>
                Khoanh khung quanh đối tượng theo nhãn đang chọn, có thể gắn nhiều mẫu trên một khung hình rồi bấm lưu.
              </span>
            </div>

            {/* Post-Save Actions Banner */}
            {savedMsg && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  marginTop: '10px',
                  background: 'var(--okq)',
                  border: '1px solid var(--ok)',
                  borderRadius: '10px',
                  padding: '10px 14px',
                  flexWrap: 'wrap',
                }}
              >
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ok)' }}>
                  Đã lưu xong — gắn nhãn tiếp:
                </span>
                <button
                  onClick={handleImportImage}
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    padding: '6px 13px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--acc)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  + Import hình mới
                </button>
                <button
                  onClick={handleImportVideo}
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    padding: '6px 13px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'var(--acc)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  + Import video mới
                </button>
                {currentAnnSource.kind === 'video' && (
                  <button
                    onClick={() => {
                      const nextFrame = Math.min(
                        vidFrame + 1,
                        Math.max(0, (annFrameMeta?.totalFrames ?? 301) - 1),
                      );
                      setVidFrame(nextFrame);
                      setAnnFrameDraft(nextFrame);
                      setAnnDraft(null);
                      setSavedMsg('');
                      setAnnPick(null);
                    }}
                    style={{
                      fontSize: '11.5px',
                      fontWeight: 600,
                      padding: '6px 13px',
                      borderRadius: '8px',
                      border: '1px solid var(--line2)',
                      background: 'var(--card)',
                      color: 'var(--ink)',
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    Khung hình tiếp theo →
                  </button>
                )}
                <button
                  onClick={() => setSavedMsg('')}
                  style={{
                    fontSize: '11.5px',
                    fontWeight: 600,
                    padding: '6px 13px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--ink3)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Đóng
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Master Label List & New Label Form */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {/* Master Label Selection List */}
            <div
              style={{
                background: 'var(--card)',
                border: '1px solid var(--line)',
                borderRadius: '14px',
                overflow: 'hidden',
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                minHeight: 0,
              }}
            >
              <div style={{ padding: '12px 15px', borderBottom: '1px solid var(--line)' }}>
                <div style={{ fontSize: '13px', fontWeight: 600 }}>Chọn nhãn để gắn mẫu</div>
                <div style={{ fontSize: '11px', color: 'var(--ink3)', marginTop: '2px' }}>
                  {activeLabelObj ? `Đang gắn mẫu cho: ${activeLabelObj.name}` : 'Bấm một nhãn để bắt đầu gắn mẫu'}
                </div>
              </div>
              <div style={{ flex: 1, overflow: 'auto', maxHeight: '330px' }}>
                {objLabels.map((o) => {
                  const isSelected = annSel === o.id;
                  const sampleCount =
                    o.samples + annSamples.filter((s) => s.labelId === o.id && s.session).length;
                  const iconSvgPath = iconsSvg[o.kind] || iconsSvg.xe;
                  const kindLabel = o.kind === 'nguoi' ? 'Người' : 'Xe';
                  const kindBg = o.kind === 'nguoi' ? 'var(--accq)' : 'var(--okq)';
                  const kindFg = o.kind === 'nguoi' ? 'var(--acc)' : 'var(--ok)';

                  return (
                    <div
                      key={o.id}
                      onClick={() => setAnnSel(o.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        padding: '9px 15px',
                        borderBottom: '1px solid var(--line)',
                        cursor: 'pointer',
                        background: isSelected ? 'var(--accq)' : 'transparent',
                      }}
                    >
                      <div
                        style={{
                          width: '38px',
                          height: '28px',
                          flex: 'none',
                          borderRadius: '6px',
                          background: `linear-gradient(150deg, ${o.tint || '#1a2129'}, #11161c)`,
                          border: `1px solid ${isSelected ? 'var(--acc)' : 'var(--line2)'}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#cfd6dd" strokeWidth="1.8">
                          <path d={iconSvgPath} />
                        </svg>
                      </div>
                      <input
                        value={o.name}
                        onChange={(e) => renameObjLabel(o.id, e.target.value)}
                        onClick={(e) => e.stopPropagation()}
                        style={{
                          flex: 1,
                          minWidth: 0,
                          border: 'none',
                          background: 'transparent',
                          color: 'var(--ink)',
                          fontSize: '12.5px',
                          fontWeight: 600,
                          fontFamily: 'inherit',
                          outline: 'none',
                        }}
                      />
                      <span
                        style={{
                          fontSize: '10.5px',
                          fontWeight: 600,
                          padding: '2px 8px',
                          borderRadius: '20px',
                          background: kindBg,
                          color: kindFg,
                          flex: 'none',
                        }}
                      >
                        {kindLabel}
                      </span>
                      <span
                        style={{
                          fontSize: '10.5px',
                          color: 'var(--ink3)',
                          fontFamily: "'IBM Plex Mono', monospace",
                          flex: 'none',
                          width: '48px',
                          textAlign: 'right',
                        }}
                      >
                        {sampleCount} mẫu
                      </span>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteObjLabel(o.id);
                          if (annSel === o.id) setAnnSel(null);
                        }}
                        style={{
                          fontSize: '10.5px',
                          fontWeight: 600,
                          padding: '3px 8px',
                          borderRadius: '6px',
                          border: '1px solid var(--p0)',
                          background: 'transparent',
                          color: 'var(--p0)',
                          cursor: 'pointer',
                          fontFamily: 'inherit',
                          flex: 'none',
                        }}
                      >
                        Xóa
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Add New Label Form Card */}
            <div
              style={{
                background: 'var(--card)',
                border: '1px solid var(--acc)',
                borderRadius: '14px',
                padding: '16px',
                alignSelf: 'start',
              }}
            >
              <div style={{ fontSize: '13.5px', fontWeight: 600, marginBottom: '4px' }}>Thêm nhãn mới</div>
              <div style={{ fontSize: '11.5px', color: 'var(--ink3)', lineHeight: '1.5', marginBottom: '14px' }}>
                Đặt tên nhãn (vd: Xe nâng reach stacker, Người mặc áo phản quang…) rồi lưu để dùng trong các zone.
              </div>

              <label style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--ink2)', display: 'block', marginBottom: '6px' }}>
                Tên nhãn
              </label>
              <input
                value={nlName}
                onChange={(e) => setNlName(e.target.value)}
                placeholder="vd: Người mặc áo phản quang"
                style={{
                  width: '100%',
                  border: '1px solid var(--line2)',
                  borderRadius: '9px',
                  padding: '10px 12px',
                  background: 'var(--bg)',
                  color: 'var(--ink)',
                  fontSize: '13px',
                  fontFamily: 'inherit',
                  outline: 'none',
                  marginBottom: '13px',
                  boxSizing: 'border-box',
                }}
              />

              <label style={{ fontSize: '11.5px', fontWeight: 600, color: 'var(--ink2)', display: 'block', marginBottom: '8px' }}>
                Loại đối tượng
              </label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
                <button
                  onClick={() => setNlKind('nguoi')}
                  style={{
                    flex: 1,
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '8px',
                    borderRadius: '9px',
                    border: `1px solid ${nlKind === 'nguoi' ? 'var(--acc)' : 'var(--line2)'}`,
                    background: nlKind === 'nguoi' ? 'var(--acc)' : 'transparent',
                    color: nlKind === 'nguoi' ? '#fff' : 'var(--ink2)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Người
                </button>
                <button
                  onClick={() => setNlKind('xe')}
                  style={{
                    flex: 1,
                    fontSize: '12px',
                    fontWeight: 600,
                    padding: '8px',
                    borderRadius: '9px',
                    border: `1px solid ${nlKind === 'xe' ? 'var(--acc)' : 'var(--line2)'}`,
                    background: nlKind === 'xe' ? 'var(--acc)' : 'transparent',
                    color: nlKind === 'xe' ? '#fff' : 'var(--ink2)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  Hình dáng xe
                </button>
              </div>

              <button
                onClick={handleSaveNewLabel}
                style={{
                  width: '100%',
                  padding: '11px',
                  borderRadius: '10px',
                  border: 'none',
                  background: 'var(--acc)',
                  color: '#fff',
                  fontSize: '13px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                Lưu nhãn
              </button>
              <div style={{ fontSize: '10.5px', color: 'var(--ink3)', textAlign: 'center', marginTop: '10px' }}>
                Nhãn mới sẽ xuất hiện trong danh sách chọn loại của mọi zone
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
