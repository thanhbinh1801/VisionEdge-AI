import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  batchCreateDatasetSamples,
  createDatasetLabel,
  deleteDatasetLabel,
  deleteDatasetSample,
  fetchDatasetFrame,
  fetchDatasetLabels,
  fetchDatasetSamples,
  fetchDatasetSources,
  fetchZonesStrict,
  restoreDatasetLabel,
  syncDatasetZones,
  updateDatasetLabel,
  updateDatasetSample,
  updateZoneApi,
  uploadDatasetSource,
  VideoFrameMetadata,
} from '../../services/api';
import {
  BBoxPercent,
  BBoxSample,
  CreateBBoxSampleItem,
  DatasetSource,
  ObjectLabel,
  ZoneSyncResult,
} from '../../contracts/api/dataset.schema';

type PendingSample = CreateBBoxSampleItem & { id: string; error?: string };
type LabelCategoryInput = 'person' | 'vehicle_shape';

const formatTimestamp = (seconds: number) => {
  const safeSeconds = Math.max(0, Math.round(seconds));
  const minutes = Math.floor(safeSeconds / 60);
  const remainder = safeSeconds % 60;
  return `${String(minutes).padStart(2, '0')}:${String(remainder).padStart(2, '0')}`;
};

const labelColor = (labelId: string) => {
  const palette = ['#39e0d0', '#30d158', '#ff9f0a', '#bf5af2', '#5fb3ff', '#ff453a', '#a1a1ab', '#2f9bff'];
  let hash = 0;
  for (const char of labelId) hash = (hash + char.charCodeAt(0)) % palette.length;
  return palette[hash];
};

const categoryLabel = (category: ObjectLabel['category']) => {
  if (category === 'person') return 'Người';
  if (category === 'vehicle_shape') return 'Hình dáng xe';
  return 'Custom';
};

const getErrorMessage = (error: unknown) => (error instanceof Error ? error.message : 'Thao tác không thành công.');

const validateBBox = (bbox: BBoxPercent) => {
  if (bbox.x < 0 || bbox.y < 0 || bbox.w <= 0 || bbox.h <= 0) return 'BBox phải có kích thước dương.';
  if (bbox.x + bbox.w > 100 || bbox.y + bbox.h > 100) return 'BBox phải nằm trong khung ảnh.';
  if (bbox.w < 2 || bbox.h < 2) return 'BBox quá nhỏ để lưu.';
  return '';
};

export const ObjectLabelingTab: React.FC = () => {
  const [labels, setLabels] = useState<ObjectLabel[]>([]);
  const [sources, setSources] = useState<DatasetSource[]>([]);
  const [samples, setSamples] = useState<BBoxSample[]>([]);
  const [pendingSamples, setPendingSamples] = useState<PendingSample[]>([]);
  const [selectedLabelId, setSelectedLabelId] = useState('');
  const [selectedSourceId, setSelectedSourceId] = useState('');
  const [selectedSampleId, setSelectedSampleId] = useState('');
  const [frameIndex, setFrameIndex] = useState(0);
  const [frameDraft, setFrameDraft] = useState(0);
  const [frameSrc, setFrameSrc] = useState('');
  const [frameMeta, setFrameMeta] = useState<VideoFrameMetadata | null>(null);
  const [showDeleted, setShowDeleted] = useState(false);
  const [newLabelName, setNewLabelName] = useState('');
  const [newLabelCategory, setNewLabelCategory] = useState<LabelCategoryInput>('vehicle_shape');
  const [editingLabelId, setEditingLabelId] = useState('');
  const [editingLabelName, setEditingLabelName] = useState('');
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [frameStatus, setFrameStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('idle');
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [syncResult, setSyncResult] = useState<ZoneSyncResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragRef = useRef<{ x0: number; y0: number } | null>(null);
  const [draftBox, setDraftBox] = useState<BBoxPercent | null>(null);

  const selectedSource = sources.find((source) => source.id === selectedSourceId) || null;
  const selectedLabel = labels.find((label) => label.id === selectedLabelId) || null;
  const activeLabels = labels.filter((label) => label.is_active);
  const visibleLabels = labels.filter((label) => (showDeleted ? !label.is_active : label.is_active));
  const selectedSample =
    samples.find((sample) => sample.id === selectedSampleId) ||
    pendingSamples.find((sample) => sample.id === selectedSampleId) ||
    null;

  const frameSamples = useMemo(() => {
    if (!selectedSource) return [];
    const saved = samples.filter((sample) => {
      if (sample.source_id !== selectedSource.id) return false;
      if (selectedSource.kind === 'video') return sample.frame_index === frameIndex;
      return sample.frame_index === 0 || sample.frame_index === null;
    });
    const pending = pendingSamples.filter((sample) => {
      if (sample.source_id !== selectedSource.id) return false;
      if (selectedSource.kind === 'video') return sample.frame_index === frameIndex;
      return sample.frame_index === 0 || sample.frame_index === null || sample.frame_index === undefined;
    });
    return [...saved, ...pending];
  }, [frameIndex, pendingSamples, samples, selectedSource]);

  const refreshLabels = async (includeDeleted = showDeleted) => {
    const nextLabels = await fetchDatasetLabels(includeDeleted);
    setLabels(nextLabels);
    if (!selectedLabelId || !nextLabels.some((label) => label.id === selectedLabelId && label.is_active)) {
      setSelectedLabelId(nextLabels.find((label) => label.is_active)?.id || '');
    }
  };

  const refreshSources = async () => {
    const data = await fetchDatasetSources();
    setSources(data.items);
    if (!selectedSourceId || !data.items.some((source) => source.id === selectedSourceId)) {
      setSelectedSourceId(data.items[0]?.id || '');
    }
  };

  const refreshSamples = async () => {
    if (!selectedSourceId) {
      setSamples([]);
      return;
    }
    const nextSamples = await fetchDatasetSamples({ sourceId: selectedSourceId, frameIndex: selectedSource?.kind === 'video' ? frameIndex : 0 });
    setSamples(nextSamples);
  };

  const loadInitialData = async () => {
    setStatus('loading');
    setError('');
    try {
      const [nextLabels, sourcePage] = await Promise.all([fetchDatasetLabels(showDeleted), fetchDatasetSources()]);
      setLabels(nextLabels);
      setSources(sourcePage.items);
      setSelectedLabelId((current) => current || nextLabels.find((label) => label.is_active)?.id || '');
      setSelectedSourceId((current) => current || sourcePage.items[0]?.id || '');
      setStatus('ready');
    } catch (loadError) {
      setStatus('error');
      setError(getErrorMessage(loadError));
    }
  };

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    refreshLabels(showDeleted).catch((loadError) => setError(getErrorMessage(loadError)));
  }, [showDeleted]);

  useEffect(() => {
    refreshSamples().catch((loadError) => setError(getErrorMessage(loadError)));
  }, [selectedSourceId, frameIndex, selectedSource?.kind]);

  useEffect(() => {
    setFrameIndex(0);
    setFrameDraft(0);
    setPendingSamples([]);
    setSelectedSampleId('');
  }, [selectedSourceId]);

  useEffect(() => {
    if (!selectedSource) {
      setFrameSrc('');
      setFrameStatus('idle');
      return;
    }
    let active = true;
    let objectUrl = '';
    setFrameStatus('loading');
    fetchDatasetFrame(selectedSource.id, selectedSource.kind === 'video' ? { frameIndex } : {})
      .then(({ blob, metadata }) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setFrameSrc(objectUrl);
        setFrameMeta(metadata);
        setFrameStatus('ready');
      })
      .catch((frameError) => {
        if (!active) return;
        setFrameSrc(selectedSource.public_url || '');
        setFrameStatus(selectedSource.kind === 'img' && selectedSource.public_url ? 'ready' : 'error');
        setError(getErrorMessage(frameError));
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [selectedSource, frameIndex]);

  const getCanvasPoint = (event: React.MouseEvent) => {
    const element = event.currentTarget as HTMLElement;
    const rect = element.getBoundingClientRect();
    const clamp = (value: number) => Math.max(0, Math.min(100, value));
    return {
      x: clamp(((event.clientX - rect.left) / rect.width) * 100),
      y: clamp(((event.clientY - rect.top) / rect.height) * 100),
    };
  };

  const handleCanvasMouseDown = (event: React.MouseEvent) => {
    if (!selectedSource || !selectedLabel || frameStatus !== 'ready') return;
    const point = getCanvasPoint(event);
    dragRef.current = { x0: point.x, y0: point.y };
    setDraftBox({ x: point.x, y: point.y, w: 0, h: 0 });
  };

  const handleCanvasMouseMove = (event: React.MouseEvent) => {
    if (!dragRef.current) return;
    const point = getCanvasPoint(event);
    setDraftBox({
      x: Math.min(dragRef.current.x0, point.x),
      y: Math.min(dragRef.current.y0, point.y),
      w: Math.abs(point.x - dragRef.current.x0),
      h: Math.abs(point.y - dragRef.current.y0),
    });
  };

  const handleCanvasMouseUp = () => {
    const box = draftBox;
    dragRef.current = null;
    setDraftBox(null);
    if (!box || !selectedSource || !selectedLabelId) return;
    const validation = validateBBox(box);
    if (validation) {
      setError(validation);
      return;
    }
    const normalizedFrame = selectedSource.kind === 'video' ? frameIndex : 0;
    const sample: PendingSample = {
      id: `pending-${Date.now()}`,
      label_id: selectedLabelId,
      source_id: selectedSource.id,
      frame_index: normalizedFrame,
      frame_timestamp_seconds: selectedSource.kind === 'video' && selectedSource.fps ? normalizedFrame / selectedSource.fps : null,
      bbox: {
        x: Number(box.x.toFixed(1)),
        y: Number(box.y.toFixed(1)),
        w: Number(box.w.toFixed(1)),
        h: Number(box.h.toFixed(1)),
      },
    };
    setPendingSamples((current) => [...current, sample]);
    setSelectedSampleId(sample.id);
    setMessage('');
    setError('');
  };

  const handleUpload = async (file: File | null) => {
    if (!file) return;
    const allowed = ['image/jpeg', 'image/png', 'video/mp4', 'video/quicktime'];
    if (!allowed.includes(file.type)) {
      setError('Chỉ hỗ trợ JPEG, PNG, MP4 hoặc MOV.');
      return;
    }
    setUploading(true);
    setError('');
    try {
      const source = await uploadDatasetSource(file, file.name);
      await refreshSources();
      setSelectedSourceId(source.id);
      setMessage(`Đã import ${source.original_filename}.`);
    } catch (uploadError) {
      setError(getErrorMessage(uploadError));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleCreateLabel = async () => {
    const labelName = newLabelName.trim();
    if (!labelName) {
      setError('Tên nhãn không được rỗng.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await createDatasetLabel({ label_name: labelName, category: newLabelCategory });
      setNewLabelName('');
      setSelectedLabelId(result.label.id);
      if (result.sync) setSyncResult(result.sync);
      await refreshLabels();
      setMessage(`Đã tạo nhãn "${result.label.label_name}" và đồng bộ zone mặc định cấm.`);
    } catch (createError) {
      setError(getErrorMessage(createError));
    } finally {
      setSaving(false);
    }
  };

  const handleRenameLabel = async (label: ObjectLabel) => {
    const labelName = editingLabelName.trim();
    if (!labelName) {
      setError('Tên nhãn không được rỗng.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await updateDatasetLabel(label.id, { label_name: labelName, category: label.category === 'person' ? 'person' : 'vehicle_shape' });
      if (result.sync) setSyncResult(result.sync);
      setEditingLabelId('');
      setEditingLabelName('');
      await refreshLabels();
      await refreshSamples();
      setMessage(`Đã đổi tên nhãn thành "${result.label.label_name}".`);
    } catch (renameError) {
      setError(getErrorMessage(renameError));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLabel = async (label: ObjectLabel) => {
    if (label.label_type === 'system') return;
    const confirmed = window.confirm(`Xóa nhãn "${label.label_name}"? Mẫu đã lưu sẽ được giữ để có thể khôi phục.`);
    if (!confirmed) return;
    setSaving(true);
    setError('');
    try {
      const zones = await fetchZonesStrict();
      const referencedZones = zones.filter((zone) => (zone.allowed_classes || []).includes(label.label_key));
      if (referencedZones.length > 0) {
        setError(
          `Chưa thể xóa "${label.label_name}" vì nhãn vẫn đang được chọn trong ${referencedZones.length} zone. Hãy bỏ dấu ✓ trong tab Vẽ zone trước.`,
        );
        return;
      }

      const cleanupTargets = zones
        .map((zone) => {
          const forbidden = zone.forbidden_classes || [];
          const nextForbidden = forbidden.filter((key) => key !== label.label_key);
          return { zone, nextForbidden, changed: nextForbidden.length !== forbidden.length };
        })
        .filter((target) => target.changed);

      if (cleanupTargets.length > 0) {
        await Promise.all(
          cleanupTargets.map(({ zone, nextForbidden }) =>
            updateZoneApi(zone.id, {
              allowed_classes: zone.allowed_classes || [],
              forbidden_classes: nextForbidden,
            }),
          ),
        );
        await fetchZonesStrict();
      }

      await deleteDatasetLabel(label.id);
      await refreshLabels(true);
      if (selectedLabelId === label.id) setSelectedLabelId(activeLabels.find((item) => item.id !== label.id)?.id || '');
      setShowDeleted(false);
      setMessage(`Đã xóa nhãn "${label.label_name}".`);
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    } finally {
      setSaving(false);
    }
  };

  const handleRestoreLabel = async (label: ObjectLabel) => {
    setSaving(true);
    setError('');
    try {
      const result = await restoreDatasetLabel(label.id);
      if (result.sync) setSyncResult(result.sync);
      await refreshLabels(true);
      setSelectedLabelId(result.label.id);
      setShowDeleted(false);
      setMessage(`Đã restore "${result.label.label_name}" và đồng bộ zone mặc định cấm.`);
    } catch (restoreError) {
      setError(getErrorMessage(restoreError));
    } finally {
      setSaving(false);
    }
  };

  const handleSavePendingSamples = async () => {
    if (!pendingSamples.length) return;
    const checked = pendingSamples.map((sample) => ({ ...sample, error: validateBBox(sample.bbox) }));
    if (checked.some((sample) => sample.error)) {
      setPendingSamples(checked);
      setError('Batch chưa được lưu: sửa toàn bộ sample lỗi rồi thử lại.');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await batchCreateDatasetSamples(checked.map(({ id: _id, error: _error, ...sample }) => sample));
      setPendingSamples([]);
      setLabels(result.labels);
      await refreshSamples();
      setMessage(`Đã lưu atomic ${result.saved_count} mẫu BBox.`);
    } catch (saveError) {
      setPendingSamples(checked.map((sample) => ({ ...sample, error: getErrorMessage(saveError) })));
      setError(`Batch không được lưu: ${getErrorMessage(saveError)}`);
    } finally {
      setSaving(false);
    }
  };

  const handleUpdateSampleLabel = async (sampleId: string, labelId: string) => {
    const pending = pendingSamples.find((sample) => sample.id === sampleId);
    if (pending) {
      setPendingSamples((current) => current.map((sample) => (sample.id === sampleId ? { ...sample, label_id: labelId } : sample)));
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await updateDatasetSample(sampleId, { label_id: labelId });
      setLabels(result.labels);
      await refreshSamples();
      setMessage('Đã cập nhật nhãn cho sample.');
    } catch (updateError) {
      setError(getErrorMessage(updateError));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteSample = async (sampleId: string) => {
    if (sampleId.startsWith('pending-')) {
      setPendingSamples((current) => current.filter((sample) => sample.id !== sampleId));
      setSelectedSampleId('');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const result = await deleteDatasetSample(sampleId);
      setLabels(result.labels);
      await refreshSamples();
      setSelectedSampleId('');
      setMessage('Đã xóa sample đã lưu.');
    } catch (deleteError) {
      setError(getErrorMessage(deleteError));
    } finally {
      setSaving(false);
    }
  };

  const retryZoneSync = async () => {
    setSaving(true);
    setError('');
    try {
      const result = await syncDatasetZones();
      setSyncResult(result);
      setMessage('Đã đồng bộ lại zone rules cho nhãn custom.');
    } catch (syncError) {
      setError(getErrorMessage(syncError));
    } finally {
      setSaving(false);
    }
  };

  if (status === 'loading') {
    return <div role="status" style={{ padding: '28px', color: 'var(--ink2)' }}>Đang tải dữ liệu nhãn đối tượng...</div>;
  }

  if (status === 'error') {
    return (
      <div role="alert" style={{ padding: '18px', border: '1px solid var(--p0)', borderRadius: '10px', background: 'var(--p0q)' }}>
        <div style={{ fontWeight: 700, marginBottom: '8px' }}>Không tải được dữ liệu nhãn đối tượng</div>
        <div style={{ color: 'var(--ink2)', fontSize: '12px', marginBottom: '12px' }}>{error}</div>
        <button type="button" onClick={loadInitialData}>Thử lại</button>
      </div>
    );
  }

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.55fr) minmax(330px, .9fr)', gap: '16px', marginBottom: '16px' }}>
      <div>
        {(message || error || syncResult) && (
          <div
            role={error ? 'alert' : 'status'}
            aria-live={error ? 'assertive' : 'polite'}
            style={{
              marginBottom: '10px',
              padding: '10px 13px',
              borderRadius: '10px',
              border: `1px solid ${error ? 'var(--p0)' : 'var(--ok)'}`,
              background: error ? 'var(--p0q)' : 'var(--okq)',
              color: error ? 'var(--p0)' : 'var(--ok)',
              fontSize: '12px',
              fontWeight: 600,
            }}
          >
            {error || message}
            {syncResult && (
              <div style={{ color: 'var(--ink2)', fontWeight: 500, marginTop: '4px' }}>
                Sync: {syncResult.synced_labels.length} nhãn, {syncResult.affected_zones.length} zone, cache {syncResult.cache.map((cache) => `${cache.camera_id}:${cache.cache_status}`).join(', ') || 'không đổi'}.
                <button type="button" onClick={retryZoneSync} style={{ marginLeft: '10px' }}>Retry sync</button>
              </div>
            )}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '10px', flexWrap: 'wrap' }}>
          <strong style={{ fontSize: '12.5px' }}>Gắn mẫu từ hình / video</strong>
          <span style={{ fontSize: '11.5px', color: 'var(--ink3)' }}>
            {selectedLabel ? `Kéo khoanh khung quanh "${selectedLabel.label_name}" trên khung hình.` : 'Chọn một nhãn active trước khi vẽ.'}
          </span>
          <div style={{ flex: 1 }} />
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,video/mp4,video/quicktime"
            onChange={(event) => handleUpload(event.target.files?.[0] || null)}
            style={{ display: 'none' }}
          />
          <button type="button" onClick={() => fileInputRef.current?.click()} disabled={uploading} style={buttonStyle()}>
            {uploading ? 'Đang import...' : '+ Import media'}
          </button>
          <button type="button" onClick={loadInitialData} style={buttonStyle()}>
            Reload
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px', overflowX: 'auto', paddingBottom: '2px' }}>
          {sources.length === 0 && (
            <div style={{ width: '100%', padding: '22px', border: '1px dashed var(--line2)', borderRadius: '10px', color: 'var(--ink2)', textAlign: 'center' }}>
              Chưa có media source persisted. Import ảnh hoặc video để bắt đầu.
            </div>
          )}
          {sources.map((source) => (
            <button
              key={source.id}
              type="button"
              onClick={() => setSelectedSourceId(source.id)}
              style={{
                position: 'relative',
                flex: 'none',
                width: '132px',
                height: '76px',
                borderRadius: '8px',
                border: `2px solid ${source.id === selectedSourceId ? 'var(--acc)' : 'var(--line)'}`,
                background: '#0c0f13',
                color: 'var(--ink)',
                cursor: 'pointer',
                overflow: 'hidden',
                padding: '8px',
                textAlign: 'left',
              }}
            >
              <span style={{ fontSize: '10px', fontWeight: 700 }}>{source.kind === 'video' ? 'VIDEO' : 'IMAGE'}</span>
              <span style={{ position: 'absolute', left: '8px', right: '8px', bottom: '8px', fontSize: '10px', fontWeight: 600, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {source.name}
              </span>
            </button>
          ))}
        </div>

        <div
          role="application"
          aria-label="Canvas gắn BBox cho nhãn đối tượng"
          tabIndex={0}
          onKeyDown={(event) => {
            if (event.key === 'Delete' && selectedSampleId) handleDeleteSample(selectedSampleId);
            if (event.key === 'Escape') {
              setDraftBox(null);
              setSelectedSampleId('');
            }
          }}
          onMouseDown={handleCanvasMouseDown}
          onMouseMove={handleCanvasMouseMove}
          onMouseUp={handleCanvasMouseUp}
          onMouseLeave={handleCanvasMouseUp}
          style={{
            position: 'relative',
            width: '100%',
            aspectRatio: selectedSource?.width && selectedSource?.height ? `${selectedSource.width}/${selectedSource.height}` : '16/9',
            minHeight: '300px',
            background: '#0c0f13',
            border: '1px solid var(--line)',
            borderRadius: '8px',
            overflow: 'hidden',
            cursor: selectedSource && selectedLabel ? 'crosshair' : 'default',
            userSelect: 'none',
          }}
        >
          {selectedSource && frameSrc ? (
            <img src={frameSrc} alt={`Frame dataset ${selectedSource.name}`} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'contain', pointerEvents: 'none' }} />
          ) : (
            <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center', color: 'var(--ink2)', textAlign: 'center', padding: '20px' }}>
              Chọn hoặc import media source để hiển thị frame.
            </div>
          )}
          {selectedSource && frameStatus === 'loading' && (
            <div role="status" style={overlayStyle()}>Đang tải frame...</div>
          )}
          {selectedSource && frameStatus === 'error' && (
            <div role="alert" style={overlayStyle()}>Không tải được frame. Chọn source khác hoặc reload.</div>
          )}
          {selectedSource && (
            <div style={{ position: 'absolute', left: 10, top: 9, background: 'rgba(0,0,0,.62)', color: '#e3e7ea', fontSize: '10px', padding: '3px 7px', borderRadius: '5px', pointerEvents: 'none' }}>
              {selectedSource.name}
              {selectedSource.kind === 'video' ? ` · frame ${frameMeta?.frameIndex ?? frameIndex} · ${formatTimestamp(frameMeta?.timestampSeconds ?? 0)}` : ''}
            </div>
          )}
          {frameSamples.map((sample) => {
            const label = labels.find((item) => item.id === sample.label_id);
            const color = labelColor(sample.label_id);
            const isSelected = selectedSampleId === sample.id;
            return (
              <button
                key={sample.id}
                type="button"
                onMouseDown={(event) => event.stopPropagation()}
                onClick={(event) => {
                  event.stopPropagation();
                  setSelectedSampleId(sample.id);
                }}
                style={{
                  position: 'absolute',
                  left: `${sample.bbox.x}%`,
                  top: `${sample.bbox.y}%`,
                  width: `${sample.bbox.w}%`,
                  height: `${sample.bbox.h}%`,
                  border: `${isSelected ? '2.5px' : '1.5px'} solid ${color}`,
                  background: color + (isSelected ? '2e' : '14'),
                  padding: 0,
                  cursor: 'pointer',
                }}
                aria-label={`Chọn sample ${label?.label_name || sample.label_id}`}
              >
                <span style={{ position: 'absolute', left: -1, top: -18, background: color, color: '#06080a', fontSize: '9.5px', fontWeight: 700, padding: '1px 7px', borderRadius: '3px', whiteSpace: 'nowrap' }}>
                  {(label?.label_name || sample.label_id).toUpperCase()}
                </span>
              </button>
            );
          })}
          {draftBox && <div style={{ position: 'absolute', left: `${draftBox.x}%`, top: `${draftBox.y}%`, width: `${draftBox.w}%`, height: `${draftBox.h}%`, border: '1.5px dashed #fff', background: 'rgba(255,255,255,.12)', pointerEvents: 'none' }} />}
        </div>

        {selectedSource?.kind === 'video' && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '9px', background: 'var(--card)', border: '1px solid var(--line)', borderRadius: '8px', padding: '8px 13px', flexWrap: 'wrap' }}>
            <button type="button" onClick={() => setFrameIndex(Math.max(0, frameIndex - 1))} style={buttonStyle()}>-1</button>
            <input
              type="range"
              min={0}
              max={Math.max(0, (selectedSource.total_frames ?? frameMeta?.totalFrames ?? 1) - 1)}
              value={Math.min(frameDraft, Math.max(0, (selectedSource.total_frames ?? frameMeta?.totalFrames ?? 1) - 1))}
              onChange={(event) => setFrameDraft(Number(event.target.value))}
              onPointerUp={(event) => {
                setFrameIndex(Number(event.currentTarget.value));
                setSelectedSampleId('');
              }}
              aria-label="Chọn frame cho video dataset"
              style={{ flex: 1, minWidth: '180px' }}
            />
            <button type="button" onClick={() => setFrameIndex(Math.min(Math.max(0, (selectedSource.total_frames ?? 1) - 1), frameIndex + 1))} style={buttonStyle()}>+1</button>
            <label style={{ fontSize: '11px', color: 'var(--ink2)' }}>
              Frame
              <input
                type="number"
                min={0}
                max={Math.max(0, (selectedSource.total_frames ?? 1) - 1)}
                value={frameDraft}
                onChange={(event) => setFrameDraft(Number(event.target.value))}
                onBlur={() => setFrameIndex(Math.max(0, Math.min(frameDraft, Math.max(0, (selectedSource.total_frames ?? 1) - 1))))}
                style={{ width: '82px', marginLeft: '6px', background: 'var(--bg)', color: 'var(--ink)', border: '1px solid var(--line2)', borderRadius: '6px', padding: '5px 7px' }}
              />
            </label>
          </div>
        )}

        {selectedSample && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '10px', background: 'var(--card)', border: '1px solid var(--acc)', borderRadius: '8px', padding: '9px 13px', flexWrap: 'wrap' }}>
            <strong style={{ fontSize: '12px' }}>{selectedSampleId.startsWith('pending-') ? 'Sample pending' : 'Sample đã lưu'}</strong>
            <select value={selectedSample.label_id} onChange={(event) => handleUpdateSampleLabel(selectedSample.id, event.target.value)} style={selectStyle()} aria-label="Đổi nhãn cho sample">
              {activeLabels.map((label) => <option key={label.id} value={label.id}>{label.label_name}</option>)}
            </select>
            <span style={{ fontSize: '11px', color: 'var(--ink3)' }}>
              x {selectedSample.bbox.x.toFixed(1)} · y {selectedSample.bbox.y.toFixed(1)} · w {selectedSample.bbox.w.toFixed(1)} · h {selectedSample.bbox.h.toFixed(1)}
            </span>
            <button type="button" onClick={() => handleDeleteSample(selectedSample.id)} style={buttonStyle('danger')}>Xóa mẫu</button>
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginTop: '10px', flexWrap: 'wrap' }}>
          <button type="button" onClick={handleSavePendingSamples} disabled={saving || pendingSamples.length === 0} style={buttonStyle(pendingSamples.length ? 'ok' : 'muted')}>
            Lưu atomic {pendingSamples.length} mẫu
          </button>
          <button type="button" onClick={() => setPendingSamples([])} disabled={!pendingSamples.length} style={buttonStyle()}>
            Discard pending
          </button>
          <span style={{ fontSize: '11px', color: 'var(--ink3)' }}>Nếu một mẫu lỗi, toàn bộ batch vẫn ở pending để sửa và retry.</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ background: 'var(--card)', border: '1px solid var(--line)', borderRadius: '8px', overflow: 'hidden' }}>
          <div style={{ padding: '12px 15px', borderBottom: '1px solid var(--line)', display: 'flex', gap: '8px', alignItems: 'center' }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: 700 }}>Chọn nhãn để gắn mẫu</div>
              <div style={{ fontSize: '11px', color: 'var(--ink3)', marginTop: '2px' }}>
                Nhãn hệ thống bị khóa; nhãn custom đã xóa có thể xem lại và khôi phục khi cần.
              </div>
            </div>
            <label style={{ fontSize: '11px', color: 'var(--ink2)', display: 'inline-flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap' }}>
              <input type="checkbox" checked={showDeleted} onChange={(event) => setShowDeleted(event.target.checked)} />
              Hiện nhãn đã xóa
            </label>
          </div>
          <div style={{ maxHeight: '420px', overflow: 'auto' }}>
            {visibleLabels.map((label) => {
              const selected = selectedLabelId === label.id;
              const isEditing = editingLabelId === label.id;
              return (
                <div key={label.id} style={{ padding: '10px 12px', borderBottom: '1px solid var(--line)', background: selected ? 'var(--accq)' : 'transparent' }}>
                  <div style={{ width: '100%', color: 'var(--ink)', display: 'grid', gridTemplateColumns: '10px minmax(0, 1fr) 120px', gap: '10px', alignItems: 'start' }}>
                    <span style={{ width: 10, height: 10, borderRadius: 10, background: labelColor(label.id), flex: 'none' }} />
                    <div style={{ minWidth: 0 }}>
                      <button
                        type="button"
                        disabled={!label.is_active}
                        onClick={() => setSelectedLabelId(label.id)}
                        style={{
                          width: '100%',
                          border: 0,
                          background: 'transparent',
                          color: 'var(--ink)',
                          fontSize: '12.5px',
                          fontWeight: 700,
                          fontFamily: 'inherit',
                          padding: 0,
                          textAlign: 'left',
                          cursor: label.is_active ? 'pointer' : 'not-allowed',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {label.label_name}
                      </button>
                      <div style={{ marginTop: '8px', fontSize: '10.5px', color: 'var(--ink3)' }}>
                        {categoryLabel(label.category)}
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'stretch' }}>
                      <div style={{ display: 'grid', gridTemplateColumns: '56px 54px', gap: '10px', alignItems: 'center' }}>
                        <span style={{ fontSize: '10px', color: label.label_type === 'system' ? 'var(--p1)' : 'var(--ink2)' }}>{label.label_type === 'system' ? 'Khóa' : label.is_active ? 'Custom' : 'Đã xóa'}</span>
                        <span style={{ fontSize: '10px', color: 'var(--ink3)', textAlign: 'right' }}>{label.sample_count} mẫu</span>
                      </div>
                      {label.label_type === 'custom' && label.is_active && (
                        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', flexWrap: 'wrap' }}>
                          {isEditing ? (
                            <>
                              <input value={editingLabelName} onChange={(event) => setEditingLabelName(event.target.value)} aria-label="Tên nhãn mới" style={{ ...inputStyle(), width: '120px' }} />
                              <button type="button" onClick={() => handleRenameLabel(label)} style={buttonStyle('ok')}>Lưu</button>
                              <button type="button" onClick={() => setEditingLabelId('')} style={buttonStyle()}>Hủy</button>
                            </>
                          ) : (
                            <button type="button" onClick={() => { setEditingLabelId(label.id); setEditingLabelName(label.label_name); }} style={buttonStyle()}>Sửa</button>
                          )}
                          <button type="button" onClick={() => handleDeleteLabel(label)} style={buttonStyle('danger')}>Xóa</button>
                        </div>
                      )}
                      {label.label_type === 'custom' && !label.is_active && (
                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <button type="button" onClick={() => handleRestoreLabel(label)} style={buttonStyle('ok')}>Khôi phục</button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div style={{ background: 'var(--card)', border: '1px solid var(--acc)', borderRadius: '8px', padding: '16px' }}>
          <div style={{ fontSize: '13.5px', fontWeight: 700, marginBottom: '10px' }}>Thêm nhãn custom</div>
          <label style={labelStyle()} htmlFor="object-label-name">Tên nhãn</label>
          <input id="object-label-name" value={newLabelName} onChange={(event) => setNewLabelName(event.target.value)} placeholder="vd: Người mặc áo phản quang" style={{ ...inputStyle(), width: '100%', marginBottom: '12px' }} />
          <label style={labelStyle()} htmlFor="object-label-category">Loại đối tượng</label>
          <select id="object-label-category" value={newLabelCategory} onChange={(event) => setNewLabelCategory(event.target.value as LabelCategoryInput)} style={{ ...selectStyle(), width: '100%', marginBottom: '14px' }}>
            <option value="person">Người</option>
            <option value="vehicle_shape">Hình dáng xe</option>
          </select>
          <button type="button" onClick={handleCreateLabel} disabled={saving} style={{ ...buttonStyle('primary'), width: '100%', justifyContent: 'center' }}>
            Lưu nhãn
          </button>
          <div style={{ fontSize: '10.5px', color: 'var(--ink3)', textAlign: 'center', marginTop: '10px' }}>
            Nhãn mới được sync vào zone rules với mặc định cấm.
          </div>
        </div>
      </div>
    </div>
  );
};

const buttonStyle = (tone: 'primary' | 'ok' | 'danger' | 'muted' | undefined = undefined): React.CSSProperties => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  fontSize: '11.5px',
  fontWeight: 700,
  padding: '7px 12px',
  borderRadius: '8px',
  border: tone === 'primary' || tone === 'ok' ? 'none' : `1px solid ${tone === 'danger' ? 'var(--p0)' : 'var(--line2)'}`,
  background: tone === 'primary' ? 'var(--acc)' : tone === 'ok' ? 'var(--ok)' : tone === 'muted' ? 'var(--line2)' : 'var(--card)',
  color: tone === 'danger' ? 'var(--p0)' : tone === undefined ? 'var(--ink)' : '#fff',
  cursor: 'pointer',
  fontFamily: 'inherit',
});

const overlayStyle = (): React.CSSProperties => ({
  position: 'absolute',
  inset: 0,
  zIndex: 5,
  display: 'grid',
  placeItems: 'center',
  background: 'rgba(0,0,0,.72)',
  color: '#fff',
  textAlign: 'center',
  fontSize: '12px',
});

const inputStyle = (): React.CSSProperties => ({
  border: '1px solid var(--line2)',
  borderRadius: '8px',
  padding: '7px 9px',
  background: 'var(--bg)',
  color: 'var(--ink)',
  fontSize: '12px',
  fontFamily: 'inherit',
  outline: 'none',
});

const selectStyle = (): React.CSSProperties => ({
  ...inputStyle(),
  cursor: 'pointer',
});

const labelStyle = (): React.CSSProperties => ({
  fontSize: '11.5px',
  fontWeight: 700,
  color: 'var(--ink2)',
  display: 'block',
  marginBottom: '6px',
});
