import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  TabId,
  SubTabId,
  VehicleRecord,
  GateEvent,
  AreaEvent,
  ZoneConfig,
  ObjectLabel,
  AnnotationSource,
  AnnotationSample,
  AIChatMessage,
} from '../types';
import { fetchZones, createZoneApi, updateZoneApi, deleteZoneApi } from '../services/api';

const defaultVehicles: VehicleRecord[] = [
  { plate: '15R-158.45', type: 'Container', visits: 42, last: '16/08 08:42', tag: 'quen', tint: '#2a4a6b' },
  { plate: '16H-678.90', type: 'Xe tải', visits: 31, last: '16/08 07:15', tag: 'quen', tint: '#3d5a40' },
  { plate: '16L-998.21', type: 'Xe con', visits: 2, last: '16/08 09:18', tag: 'la', tint: '#5a4a3d' },
  { plate: '29H-887.12', type: 'Xe tải', visits: 1, last: '15/08 22:04', tag: 'la', tint: '#4a3d5a' },
  { plate: '15H-012.34', type: 'Container', visits: 27, last: '16/08 06:51', tag: 'quen', tint: '#2a4a6b' },
  { plate: '16K-345.67', type: 'Container', visits: 19, last: '16/08 05:33', tag: 'quen', tint: '#3d4a5a' },
];

const defaultGateEvents: GateEvent[] = [
  { id: '1', time: '09:41', plate: '15R-158.45', zone: 'Làn IN 2', conf: 97 },
  { id: '2', time: '09:18', plate: '16L-998.21', zone: 'Làn IN 1', conf: 95 },
  { id: '3', time: '08:56', plate: '15H-012.34', zone: 'Làn IN 1', conf: 98 },
  { id: '4', time: '08:42', plate: '15R-158.45', zone: 'Làn IN 2', conf: 96 },
  { id: '5', time: '08:11', plate: '—', zone: 'Làn IN 2', conf: null },
  { id: '6', time: '07:15', plate: '16H-678.90', zone: 'Làn IN 1', conf: 94 },
  { id: '7', time: '06:51', plate: '15H-012.34', zone: 'Làn IN 2', conf: 97 },
  { id: '8', time: '05:33', plate: '16K-345.67', zone: 'Làn IN 1', conf: 99 },
];

const defaultAreaEvents: AreaEvent[] = [
  { id: 'a1', time: '09:52', obj: 'Xe máy', zone: 'Zone cấm phương tiện cá nhân', st: 'Vi phạm', ok: false },
  { id: 'a2', time: '09:38', obj: 'Xe nâng FL-02', zone: 'Zone bãi kiểm', st: 'Được phép', ok: true },
  { id: 'a3', time: '09:12', obj: 'Xe container 15R-158.45', zone: 'Zone bãi kiểm', st: 'Được phép', ok: true },
  { id: 'a4', time: '08:47', obj: 'Xe hơi trắng', zone: 'Zone bãi kiểm', st: 'Vi phạm', ok: false },
  { id: 'a5', time: '08:20', obj: 'Xe nâng FL-01', zone: 'Zone bãi kiểm', st: 'Được phép', ok: true },
  { id: 'a6', time: '07:55', obj: 'Xe container 15H-012.34', zone: 'Zone bãi kiểm', st: 'Được phép', ok: true },
];

const defaultObjLabels: ObjectLabel[] = [
  { id: 'l1', name: 'Container', kind: 'xe', tint: '#2a4a6b', samples: 128 },
  { id: 'l2', name: 'Xe tải', kind: 'xe', tint: '#3d5a40', samples: 64 },
  { id: 'l3', name: 'Xe nâng', kind: 'xe', tint: '#5a5230', samples: 41 },
  { id: 'l4', name: 'Xe cẩu', kind: 'xe', tint: '#4a3d5a', samples: 12 },
  { id: 'l5', name: 'Xe con', kind: 'xe', tint: '#5a4a3d', samples: 23 },
  { id: 'l6', name: 'Xe máy', kind: 'xe', tint: '#5a3d3d', samples: 17 },
  { id: 'l7', name: 'Xe đạp', kind: 'xe', tint: '#3d4a5a', samples: 6 },
  { id: 'l8', name: 'Người', kind: 'nguoi', tint: '#3d5a55', samples: 87 },
];

const defaultZonesByCam: Record<string, ZoneConfig[]> = {
  'GATE-01': [
    { id: 'zA', name: 'Làn IN 1', color: '#30d158', points: [[36, 54], [50, 54], [42, 95], [10, 95]], types: { 'Container': 1, 'Xe tải': 1, 'Xe con': 0, 'Xe máy': 0 } },
    { id: 'zB', name: 'Làn IN 2', color: '#2f9bff', points: [[52, 54], [66, 54], [95, 95], [47, 95]], types: { 'Container': 1, 'Xe tải': 1, 'Xe con': 0, 'Xe máy': 0 } },
  ],
  'BAI-KIEM': [
    { id: 'zK1', name: 'Zone bãi kiểm', color: '#30d158', points: [[54, 52], [88, 58], [92, 90], [48, 92]], types: { 'Container': 1, 'Xe nâng': 1, 'Xe con': 0, 'Xe máy': 0 } },
    { id: 'zK2', name: 'Zone làn di chuyển', color: '#ff9f0a', points: [[38, 42], [52, 42], [46, 94], [8, 94]], types: { 'Container': 1, 'Xe nâng': 1, 'Xe con': 0, 'Xe máy': 0 } },
    { id: 'zK3', name: 'Zone cấm PT cá nhân', color: '#ff453a', points: [[6, 30], [34, 28], [36, 60], [4, 66]], types: { 'Container': 1, 'Xe nâng': 0, 'Xe con': 0, 'Xe máy': 0 } },
  ],
};

const defaultAnnSources: AnnotationSource[] = [
  { id: 'src1', name: 'baikiem-cam-01.jpg', kind: 'img', tint: '#2a3f55' },
  { id: 'src2', name: 'gate-lan-in-06-15.jpg', kind: 'img', tint: '#3d4a3a' },
  { id: 'src3', name: 'yard-ca-chieu.mp4', kind: 'video', tint: '#3d4a3a' },
];

const defaultAnnSamples: AnnotationSample[] = [
  { id: 's1', labelId: 'l3', srcId: 'src1', x: 22, y: 40, w: 22, h: 40 },
  { id: 's2', labelId: 'l8', srcId: 'src1', x: 46, y: 44, w: 4.5, h: 9 },
];

const qaKnowledgeBase = [
  {
    keys: ['bao nhiêu', 'xe lạ', 'lạ vào'],
    text: 'Hôm nay có 2 sự kiện xe lạ / vi phạm zone: 16L-998.21 (xe con, chưa gắn nhãn quen) bị chặn tại Làn IN 1 lúc 09:18, và 29H-887.12 (xe tải) vào Làn IN 2 lúc 08:11 — zone này chỉ cho phép container. Đoạn video sự kiện gần nhất bên dưới.',
    clip: { cam: 'GATE-01', from: '09:18:05', to: '09:18:15', title: '16L-998.21 · Xe lạ bị chặn tại Làn IN 1', boxColor: '#ff453a', boxLabel: '16L-998.21 · XE LẠ', tint: '#5a4a3d' }
  },
  {
    keys: ['container', 'loại xe'],
    text: 'Trong ngày có 5 lượt container vào zone hợp lệ (15R-158.45 ×2, 15H-012.34 ×2, 16K-345.67 ×1). Không có container nào vi phạm. Video lượt gần nhất lúc 09:41 bên dưới.',
    clip: { cam: 'GATE-01', from: '09:41:22', to: '09:41:32', title: '15R-158.45 · Container vào Làn IN 1', boxColor: '#30d158', boxLabel: '15R-158.45 · CHO PHÉP', tint: '#2a4a6b' }
  },
  {
    keys: ['sai loại', 'bãi chờ', 'vi phạm'],
    text: 'Có 1 sự kiện sai loại xe: 29H-887.12 (xe tải) đi vào Làn IN 2 lúc 08:11 — làn này cấu hình chỉ cho phép container. Hệ thống đã sinh cảnh báo và lưu video.',
    clip: { cam: 'GATE-01', from: '08:11:40', to: '08:11:50', title: '29H-887.12 · Sai loại xe tại Làn IN 2', boxColor: '#ff9f0a', boxLabel: '29H-887.12 · SAI LOẠI', tint: '#4a3d5a' }
  },
  {
    keys: ['xe máy', 'xe đạp', 'xe hơi', 'khu vực', 'cá nhân'],
    text: 'Trong khu vực bãi hôm nay có 2 vi phạm loại xe: 1 xe máy vào Zone cấm phương tiện cá nhân lúc 09:52 và 1 xe hơi trắng vào Zone bãi container lúc 08:47. Xe nâng và xe container hoạt động bình thường (4 lượt hợp lệ). Video vi phạm gần nhất bên dưới.',
    clip: { cam: 'YARD-01', from: '09:52:18', to: '09:52:28', title: 'Xe máy · Vi phạm Zone cấm phương tiện cá nhân', boxColor: '#ff453a', boxLabel: 'XE MÁY · VI PHẠM', tint: '#5a3d3d' }
  },
  {
    keys: ['xe nâng', 'forklift'],
    text: 'Xe nâng thuộc nhóm được phép trong Zone bãi container. Hôm nay ghi nhận 2 lượt hoạt động: FL-01 lúc 08:20 và FL-02 lúc 09:38 — đều hợp lệ, không có cảnh báo. Video lượt gần nhất bên dưới.',
    clip: { cam: 'YARD-01', from: '09:38:02', to: '09:38:12', title: 'Xe nâng FL-02 · Zone bãi container', boxColor: '#30d158', boxLabel: 'XE NÂNG · ĐƯỢC PHÉP', tint: '#5a5230' }
  },
  {
    keys: ['15r', '158'],
    text: 'Xe 15R-158.45 (container, nhãn: xe quen) vào cổng 2 lần hôm nay: 08:42 vào Làn IN 2 và 09:41 vào Làn IN 1 — cả hai lượt đều hợp lệ. Video lượt 09:41 bên dưới.',
    clip: { cam: 'GATE-01', from: '09:41:22', to: '09:41:32', title: '15R-158.45 · Lượt vào 09:41', boxColor: '#30d158', boxLabel: '15R-158.45 · CHO PHÉP', tint: '#2a4a6b' }
  }
];

const fallbackQA = {
  text: 'Tôi tìm thấy 8 sự kiện trong ngày: 6 lượt cho phép, 2 cảnh báo (1 xe lạ, 1 sai loại xe). Bạn có thể hỏi cụ thể hơn — ví dụ theo biển số, theo zone, hoặc theo loại vi phạm. Video sự kiện mới nhất bên dưới.',
  clip: { cam: 'GATE-01', from: '09:41:22', to: '09:41:32', title: 'Sự kiện mới nhất · 15R-158.45 vào Làn IN 1', boxColor: '#30d158', boxLabel: '15R-158.45 · CHO PHÉP', tint: '#2a4a6b' }
};

interface AppContextType {
  tab: TabId;
  setTab: (tab: TabId) => void;
  subTab: SubTabId;
  setSubTab: (sub: SubTabId) => void;
  clock: string;
  vehicles: VehicleRecord[];
  toggleVehicleTag: (plate: string) => void;
  gateEvents: GateEvent[];
  areaEvents: AreaEvent[];
  objLabels: ObjectLabel[];
  addObjLabel: (name: string, kind: 'nguoi' | 'xe') => void;
  renameObjLabel: (id: string, name: string) => void;
  deleteObjLabel: (id: string) => void;
  zonesByCam: Record<string, ZoneConfig[]>;
  updateZone: (camId: string, zoneId: string, patch: Partial<ZoneConfig>) => void;
  addZone: (camId: string, zone: ZoneConfig) => void;
  deleteZone: (camId: string, zoneId: string) => void;
  toggleZoneType: (camId: string, zoneId: string, typeName: string) => void;
  annSources: AnnotationSource[];
  annSamples: AnnotationSample[];
  addAnnSource: (source: AnnotationSource) => void;
  addAnnSample: (sample: Omit<AnnotationSample, 'id'>) => string;
  updateAnnSampleLabel: (sampleId: string, labelId: string) => void;
  deleteAnnSample: (sampleId: string) => void;
  saveAnnSamples: () => number;
  chatMessages: AIChatMessage[];
  sendChatMessage: (text: string) => void;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [tab, setTab] = useState<TabId>('mon');
  const [subTab, setSubTab] = useState<SubTabId>('label');
  const [now, setNow] = useState<Date>(new Date());
  const [vehicles, setVehicles] = useState<VehicleRecord[]>(defaultVehicles);
  const [gateEvents] = useState<GateEvent[]>(defaultGateEvents);
  const [areaEvents] = useState<AreaEvent[]>(defaultAreaEvents);
  const [objLabels, setObjLabels] = useState<ObjectLabel[]>(defaultObjLabels);
  const [zonesByCam, setZonesByCam] = useState<Record<string, ZoneConfig[]>>(defaultZonesByCam);
  const [annSources, setAnnSources] = useState<AnnotationSource[]>(defaultAnnSources);
  const [annSamples, setAnnSamples] = useState<AnnotationSample[]>(defaultAnnSamples);
  const [chatMessages, setChatMessages] = useState<AIChatMessage[]>([
    {
      id: 'm-init',
      role: 'ai',
      text: 'Xin chào! Tôi có thể trả lời các câu hỏi về sự kiện xe ra vào cổng đã ghi nhận. Mỗi câu trả lời kèm đoạn video 10 giây của sự kiện liên quan.',
    },
  ]);

  useEffect(() => {
    const interval = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchZones().then((fetchedZones) => {
      if (fetchedZones && fetchedZones.length > 0) {
        const grouped: Record<string, ZoneConfig[]> = {};
        fetchedZones.forEach((z) => {
          const cam = z.camera_id || 'BAI-KIEM';
          if (!grouped[cam]) grouped[cam] = [];
          grouped[cam].push(z);
        });
        setZonesByCam((prev) => ({ ...prev, ...grouped }));
      }
    });
  }, []);


  const pad = (n: number) => String(n).padStart(2, '0');
  const clock = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  const toggleVehicleTag = (plate: string) => {
    setVehicles((prev) =>
      prev.map((v) => (v.plate === plate ? { ...v, tag: v.tag === 'la' ? 'quen' : 'la' } : v))
    );
  };

  const addObjLabel = (name: string, kind: 'nguoi' | 'xe') => {
    const tints = ['#2a4a6b', '#3d5a40', '#5a5230', '#4a3d5a', '#3d5a55'];
    const newId = 'l' + Date.now();
    setObjLabels((prev) => [
      ...prev,
      { id: newId, name, kind, tint: tints[prev.length % tints.length], samples: 0 },
    ]);
  };

  const renameObjLabel = (id: string, name: string) => {
    setObjLabels((prev) => prev.map((o) => (o.id === id ? { ...o, name } : o)));
  };

  const deleteObjLabel = (id: string) => {
    setObjLabels((prev) => prev.filter((o) => o.id !== id));
    setAnnSamples((prev) => prev.filter((s) => s.labelId !== id));
  };

  const updateZone = (camId: string, zoneId: string, patch: Partial<ZoneConfig>) => {
    setZonesByCam((prev) => {
      const arr = (prev[camId] || []).map((z) => (z.id === zoneId ? { ...z, ...patch } : z));
      return { ...prev, [camId]: arr };
    });
    if (patch.points || patch.name || patch.color || patch.allowed_classes || patch.forbidden_classes) {
      updateZoneApi(zoneId, {
        name: patch.name,
        vertices: patch.points,
        allowed_classes: patch.allowed_classes,
        forbidden_classes: patch.forbidden_classes,
        color: patch.color,
      });
    }
  };

  const addZone = (camId: string, newZone: ZoneConfig) => {
    const tempId = newZone.id;
    setZonesByCam((prev) => ({
      ...prev,
      [camId]: [...(prev[camId] || []), newZone],
    }));
    createZoneApi({
      camera_id: camId,
      name: newZone.name,
      vertices: newZone.points,
      color: newZone.color,
      allowed_classes: newZone.allowed_classes || [],
      forbidden_classes: newZone.forbidden_classes || [],
    }).then((created) => {
      if (created && created.id) {
        setZonesByCam((prev) => {
          const list = (prev[camId] || []).map((z) => (z.id === tempId ? { ...z, id: created.id } : z));
          return { ...prev, [camId]: list };
        });
      }
    });
  };

  const deleteZone = (camId: string, zoneId: string) => {
    setZonesByCam((prev) => ({
      ...prev,
      [camId]: (prev[camId] || []).filter((z) => z.id !== zoneId),
    }));
    deleteZoneApi(zoneId);
  };

  const toggleZoneType = (camId: string, zoneId: string, typeName: string) => {
    const CLASS_MAP: Record<string, { key: string; aliases: string[] }> = {
      'container': { key: 'container', aliases: ['container', 'Container', 'Xe container'] },
      'Container': { key: 'container', aliases: ['container', 'Container', 'Xe container'] },
      'Xe container': { key: 'container', aliases: ['container', 'Container', 'Xe container'] },
      'truck': { key: 'truck', aliases: ['truck', 'Xe tải'] },
      'Xe tải': { key: 'truck', aliases: ['truck', 'Xe tải'] },
      'forklift': { key: 'forklift', aliases: ['forklift', 'Xe nâng'] },
      'Xe nâng': { key: 'forklift', aliases: ['forklift', 'Xe nâng'] },
      'crane': { key: 'crane', aliases: ['crane', 'Xe cẩu'] },
      'Xe cẩu': { key: 'crane', aliases: ['crane', 'Xe cẩu'] },
      'car': { key: 'car', aliases: ['car', 'Xe con'] },
      'Xe con': { key: 'car', aliases: ['car', 'Xe con'] },
      'motorbike': { key: 'motorbike', aliases: ['motorbike', 'Xe máy'] },
      'Xe máy': { key: 'motorbike', aliases: ['motorbike', 'Xe máy'] },
      'bicycle': { key: 'bicycle', aliases: ['bicycle', 'Xe đạp'] },
      'Xe đạp': { key: 'bicycle', aliases: ['bicycle', 'Xe đạp'] },
      'person': { key: 'person', aliases: ['person', 'Người'] },
      'Người': { key: 'person', aliases: ['person', 'Người'] },
    };

    setZonesByCam((prev) => {
      const arr = (prev[camId] || []).map((z) => {
        if (z.id !== zoneId) return z;
        
        const mapped = CLASS_MAP[typeName] || { key: typeName.toLowerCase(), aliases: [typeName] };
        const canonicalKey = mapped.key;

        const isAllowed = !!(
          z.types[typeName] ||
          z.types[canonicalKey] ||
          (z.allowed_classes && z.allowed_classes.includes(canonicalKey))
        );
        const newVal = isAllowed ? 0 : 1;

        const updatedTypes = { ...z.types };
        mapped.aliases.forEach((a) => {
          updatedTypes[a] = newVal;
        });

        const ALL_CANONICAL_KEYS = ['container', 'truck', 'forklift', 'crane', 'car', 'motorbike', 'bicycle', 'person'];
        
        // Build new allowed list
        let allowed = (z.allowed_classes || []).slice();
        if (newVal === 1) {
          if (!allowed.includes(canonicalKey)) allowed.push(canonicalKey);
        } else {
          allowed = allowed.filter((k) => k !== canonicalKey && k !== typeName);
        }

        const forbidden = ALL_CANONICAL_KEYS.filter((k) => !allowed.includes(k));

        updateZoneApi(zoneId, { allowed_classes: allowed, forbidden_classes: forbidden });

        return {
          ...z,
          types: updatedTypes,
          allowed_classes: allowed,
          forbidden_classes: forbidden,
        };
      });
      return { ...prev, [camId]: arr };
    });
  };


  const addAnnSource = (source: AnnotationSource) => {
    setAnnSources((prev) => [...prev, source]);
  };

  const addAnnSample = (sample: Omit<AnnotationSample, 'id'>) => {
    const nid = 's' + Date.now();
    setAnnSamples((prev) => [...prev, { ...sample, id: nid, session: 1 }]);
    return nid;
  };

  const updateAnnSampleLabel = (sampleId: string, labelId: string) => {
    setAnnSamples((prev) => prev.map((s) => (s.id === sampleId ? { ...s, labelId } : s)));
  };

  const deleteAnnSample = (sampleId: string) => {
    setAnnSamples((prev) => prev.filter((s) => s.id !== sampleId));
  };

  const saveAnnSamples = () => {
    const sessionSamples = annSamples.filter((s) => s.session);
    const count = sessionSamples.length;
    if (!count) return 0;

    const increments: Record<string, number> = {};
    sessionSamples.forEach((s) => {
      increments[s.labelId] = (increments[s.labelId] || 0) + 1;
    });

    setObjLabels((prev) =>
      prev.map((o) => (increments[o.id] ? { ...o, samples: o.samples + increments[o.id] } : o))
    );

    setAnnSamples((prev) => prev.map((s) => ({ ...s, session: 0 })));
    return count;
  };

  const sendChatMessage = (text: string) => {
    const userText = text.trim();
    if (!userText) return;

    const lower = userText.toLowerCase();
    const hit =
      qaKnowledgeBase.find((q) => q.keys.some((k) => lower.includes(k))) || fallbackQA;

    setChatMessages((prev) => [
      ...prev,
      { id: 'user-' + Date.now(), role: 'user', text: userText },
      { id: 'ai-' + Date.now(), role: 'ai', text: hit.text, clip: hit.clip },
    ]);
  };

  return (
    <AppContext.Provider
      value={{
        tab,
        setTab,
        subTab,
        setSubTab,
        clock,
        vehicles,
        toggleVehicleTag,
        gateEvents,
        areaEvents,
        objLabels,
        addObjLabel,
        renameObjLabel,
        deleteObjLabel,
        zonesByCam,
        updateZone,
        addZone,
        deleteZone,
        toggleZoneType,
        annSources,
        annSamples,
        addAnnSource,
        addAnnSample,
        updateAnnSampleLabel,
        deleteAnnSample,
        saveAnnSamples,
        chatMessages,
        sendChatMessage,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = (): AppContextType => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
};
