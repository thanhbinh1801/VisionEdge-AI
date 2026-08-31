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
import { fetchZones, createZoneApi, updateZoneApi, deleteZoneApi, fetchVehicles, updateVehicleTagApi, askAssistant } from '../services/api';

const defaultVehicles: VehicleRecord[] = [];
const defaultGateEvents: GateEvent[] = [];
const defaultAreaEvents: AreaEvent[] = [];

const defaultObjLabels: ObjectLabel[] = [
  { id: 'l1', name: 'Container', kind: 'xe', tint: '#2a4a6b', samples: 0 },
  { id: 'l2', name: 'Xe tải', kind: 'xe', tint: '#3d5a40', samples: 0 },
  { id: 'l3', name: 'Xe nâng', kind: 'xe', tint: '#5a5230', samples: 0 },
  { id: 'l4', name: 'Xe cẩu', kind: 'xe', tint: '#4a3d5a', samples: 0 },
  { id: 'l5', name: 'Xe con', kind: 'xe', tint: '#5a4a3d', samples: 0 },
  { id: 'l6', name: 'Xe máy', kind: 'xe', tint: '#5a3d3d', samples: 0 },
  { id: 'l7', name: 'Xe đạp', kind: 'xe', tint: '#3d4a5a', samples: 0 },
  { id: 'l8', name: 'Người', kind: 'nguoi', tint: '#3d5a55', samples: 0 },
];

const defaultZonesByCam: Record<string, ZoneConfig[]> = {
  'GATE-01': [],
  'BAI-KIEM': [],
};

const defaultAnnSources: AnnotationSource[] = [];
const defaultAnnSamples: AnnotationSample[] = [];


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
  refreshZones: () => Promise<ZoneConfig[]>;
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
  sendChatMessage: (text: string) => Promise<void>;
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

  const applyFetchedZones = (fetchedZones: ZoneConfig[]) => {
    if (fetchedZones.length === 0) return;
    const grouped: Record<string, ZoneConfig[]> = {};
    fetchedZones.forEach((z) => {
      const cam = z.camera_id || 'BAI-KIEM';
      if (!grouped[cam]) grouped[cam] = [];
      grouped[cam].push(z);
    });
    setZonesByCam((prev) => ({ ...prev, ...grouped }));
  };

  const refreshZones = async () => {
    const fetchedZones = await fetchZones();
    applyFetchedZones(fetchedZones);
    return fetchedZones;
  };

  useEffect(() => {
    refreshZones();
  }, []);

  useEffect(() => {
    fetchVehicles().then((res) => {
      if (res && res.length > 0) {
        const mapped: VehicleRecord[] = res.map((v: any) => ({
          plate: v.plate || v.license_plate || '',
          type: v.vehicle_type || 'Container',
          visits: v.total_sightings || 1,
          last: v.last_seen_at || 'Mới nhất',
          tag: (v.tag_label === 'known' ? 'quen' : v.tag_label === 'blacklisted' ? 'blacklist' : 'la') as any,
          tint: '#2a4a6b',
        }));
        setVehicles(mapped);
      }
    });
  }, []);

  const pad = (n: number) => String(n).padStart(2, '0');
  const clock = `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`;

  const toggleVehicleTag = (plate: string) => {
    setVehicles((prev) =>
      prev.map((v) => {
        if (v.plate === plate) {
          const newTag = v.tag === 'la' ? 'quen' : 'la';
          updateVehicleTagApi(plate, newTag === 'quen' ? 'known' : 'unknown');
          return { ...v, tag: newTag };
        }
        return v;
      })
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

  const sendChatMessage = async (text: string) => {
    const userText = text.trim();
    if (!userText) return;

    // Một id duy nhất cho bong bóng trả lời, để thay tại chỗ khi backend phản hồi
    // thay vì nối thêm tin nhắn mới.
    const answerId = 'ai-' + Date.now();

    // Ngữ cảnh của lượt trước, lấy trước khi ghi thêm tin nhắn mới vào log. Nhờ nó
    // trợ lý hiểu được câu hỏi rút gọn kiểu "còn nữa không" hay "lọc xe nâng thôi".
    const history = chatMessages
      .filter((m) => m.status !== 'pending' && m.status !== 'error')
      .slice(-4)
      .map((m) => ({ role: m.role, text: m.text }));
    const previousSpec =
      [...chatMessages].reverse().find((m) => m.role === 'ai' && m.spec)?.spec ?? null;

    setChatMessages((prev) => [
      ...prev,
      { id: 'user-' + Date.now(), role: 'user', text: userText },
      { id: answerId, role: 'ai', text: 'Đang tra cứu sự kiện…', status: 'pending' },
    ]);

    try {
      const res = await askAssistant(userText, { history, previousSpec });
      setChatMessages((prev) =>
        prev.map((m) =>
          m.id === answerId
            ? {
                ...m,
                text: res.answer,
                sqlQuery: res.sql_query || undefined,
                clips: res.clips,
                spec: res.spec ?? null,
                status: undefined,
              }
            : m
        )
      );
    } catch (err) {
      const reason = err instanceof Error ? err.message : 'Lỗi không xác định';
      setChatMessages((prev) =>
        prev.map((m) =>
          m.id === answerId
            ? { ...m, text: `Không lấy được câu trả lời: ${reason}`, status: 'error' }
            : m
        )
      );
    }
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
        refreshZones,
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
