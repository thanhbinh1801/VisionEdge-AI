import React, { useEffect, useRef, useState } from 'react';
import { AlertTriangle, Car, Download, Loader2, Send, ShieldAlert, Truck, Video } from 'lucide-react';
import { VideoModal } from '../components/common/VideoModal';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

/** Hình dạng phản hồi của POST /api/v1/assistant/query (TASK-011). */
interface AssistantAnswer {
  answer: string;
  sql_query?: string | null;
  event_id?: string | null;
  clip_url?: string | null;
}

interface ChatMessage {
  id: string;
  role: 'user' | 'ai';
  text: string;
  sqlQuery?: string | null;
  eventId?: string | null;
  clipUrl?: string | null;
  /** Đánh dấu bong bóng lỗi để tô khác màu và gắn role="alert". */
  failed?: boolean;
}

const GREETING: ChatMessage = {
  id: 'm-init',
  role: 'ai',
  text:
    'Xin chào! Tôi trả lời các câu hỏi về sự kiện đã ghi nhận trong cơ sở dữ liệu. ' +
    'Câu trả lời về một sự kiện cụ thể sẽ kèm đoạn video 10 giây làm bằng chứng.',
};

const PROMPT_CHIPS = [
  { icon: ShieldAlert, label: 'Hôm nay có bao nhiêu vi phạm?' },
  { icon: Car, label: 'Có xe máy nào vào khu vực cấm không?' },
  { icon: Truck, label: 'Xe nâng hoạt động thế nào ở bãi kiểm?' },
];

export const AIChatbotAssistant: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState(false);
  const [clipUrl, setClipUrl] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Cuộn xuống tin nhắn mới nhất. Đặt trong useEffect vì đụng tới DOM thật.
  useEffect(() => {
    const log = logRef.current;
    if (log) log.scrollTop = log.scrollHeight;
  }, [messages, pending]);

  const ask = async (question: string) => {
    const text = question.trim();
    if (!text || pending) return;

    setMessages((prev) => [...prev, { id: `user-${Date.now()}`, role: 'user', text }]);
    setDraft('');
    setPending(true);

    try {
      const res = await fetch(`${API_BASE_URL}/assistant/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: text }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: AssistantAnswer = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          role: 'ai',
          text: data.answer,
          sqlQuery: data.sql_query,
          eventId: data.event_id,
          clipUrl: data.clip_url,
        },
      ]);
    } catch (error) {
      // Không nuốt lỗi thành câu trả lời trông bình thường: người dùng phải phân
      // biệt được "không có sự kiện nào" với "không gọi được backend".
      setMessages((prev) => [
        ...prev,
        {
          id: `err-${Date.now()}`,
          role: 'ai',
          failed: true,
          text:
            'Không kết nối được dịch vụ hỏi đáp. ' +
            (error instanceof Error ? error.message : 'Lỗi không xác định.'),
        },
      ]);
    } finally {
      setPending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      ask(draft);
    }
  };

  return (
    <div
      style={{
        maxWidth: '860px',
        margin: '0 auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 63px)',
        boxSizing: 'border-box',
      }}
    >
      <div
        ref={logRef}
        role="log"
        aria-live="polite"
        aria-label="Lịch sử hỏi đáp"
        style={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          padding: '6px 2px',
        }}
      >
        {messages.map((m) =>
          m.role === 'user' ? (
            <div
              key={m.id}
              style={{
                alignSelf: 'flex-end',
                maxWidth: '70%',
                background: 'var(--acc)',
                color: '#fff',
                fontSize: '13.5px',
                lineHeight: 1.5,
                padding: '11px 15px',
                borderRadius: '15px 15px 4px 15px',
                animation: 'msgIn .25s ease',
              }}
            >
              {m.text}
            </div>
          ) : (
            <div
              key={m.id}
              role={m.failed ? 'alert' : undefined}
              style={{ alignSelf: 'flex-start', maxWidth: '86%', animation: 'msgIn .25s ease' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '6px' }}>
                <span
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '7px',
                    background: m.failed
                      ? 'linear-gradient(145deg,#ff6b6b,#c92a2a)'
                      : 'linear-gradient(145deg,#2f9bff,#1361c9)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#fff',
                    flex: 'none',
                  }}
                >
                  {m.failed ? <AlertTriangle size={13} /> : <ShieldAlert size={13} />}
                </span>
                <span style={{ fontSize: '11.5px', color: 'var(--ink3)', fontWeight: 600 }}>
                  {m.failed ? 'Lỗi kết nối' : 'Trợ lý SentriAI'}
                </span>
              </div>

              <div
                style={{
                  background: 'var(--card)',
                  border: `1px solid ${m.failed ? 'var(--p0)' : 'var(--line2)'}`,
                  color: m.failed ? 'var(--p0)' : 'var(--ink)',
                  fontSize: '13.5px',
                  lineHeight: 1.55,
                  padding: '11px 15px',
                  borderRadius: '4px 15px 15px 15px',
                  whiteSpace: 'pre-line',
                }}
              >
                {m.text}
              </div>

              {m.sqlQuery && (
                <details style={{ marginTop: '6px' }}>
                  <summary style={{ fontSize: '10.5px', color: 'var(--ink3)', cursor: 'pointer' }}>
                    Truy vấn đã dùng
                  </summary>
                  <code
                    style={{
                      display: 'block',
                      marginTop: '4px',
                      padding: '8px 10px',
                      background: 'var(--panel)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      fontSize: '11px',
                      color: 'var(--ink2)',
                      overflowX: 'auto',
                    }}
                  >
                    {m.sqlQuery}
                  </code>
                </details>
              )}

              {/* Chứng cứ chỉ hiện khi backend thực sự trả về clip. Không có thì
                  không dựng thẻ video rỗng để câu trả lời trông đầy đủ hơn. */}
              {m.clipUrl && (
                <div
                  style={{
                    marginTop: '10px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    flexWrap: 'wrap',
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setClipUrl(m.clipUrl ?? null)}
                    aria-label={`Xem clip 10 giây của sự kiện ${m.eventId ?? ''}`.trim()}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '12px',
                      padding: '7px 13px',
                      borderRadius: '20px',
                      border: '1px solid var(--line2)',
                      background: 'var(--card)',
                      color: 'var(--ink)',
                      cursor: 'pointer',
                      fontFamily: 'inherit',
                    }}
                  >
                    <Video size={13} /> Xem clip 10s
                  </button>

                  <a
                    href={m.clipUrl}
                    download
                    aria-label={`Tải clip 10 giây của sự kiện ${m.eventId ?? ''}`.trim()}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '6px',
                      fontSize: '12px',
                      padding: '7px 13px',
                      borderRadius: '20px',
                      border: '1px solid var(--line2)',
                      background: 'var(--card)',
                      color: 'var(--ink2)',
                      textDecoration: 'none',
                      fontFamily: 'inherit',
                    }}
                  >
                    <Download size={13} /> Tải clip
                  </a>

                  {m.eventId && (
                    <span style={{ fontSize: '10.5px', color: 'var(--ink3)' }}>
                      Sự kiện {m.eventId}
                    </span>
                  )}
                </div>
              )}
            </div>
          ),
        )}

        {pending && (
          <div
            style={{
              alignSelf: 'flex-start',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '12px',
              color: 'var(--ink3)',
            }}
          >
            <Loader2 size={13} className="animate-spin" /> Đang tra cứu sự kiện…
          </div>
        )}
      </div>

      <div style={{ paddingTop: '12px' }}>
        <div
          role="group"
          aria-label="Câu hỏi gợi ý"
          style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '10px' }}
        >
          {PROMPT_CHIPS.map(({ icon: Icon, label }) => (
            <button
              key={label}
              type="button"
              onClick={() => ask(label)}
              disabled={pending}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '11.5px',
                padding: '6px 13px',
                borderRadius: '20px',
                border: '1px solid var(--line2)',
                background: 'var(--card)',
                color: 'var(--ink2)',
                cursor: pending ? 'not-allowed' : 'pointer',
                opacity: pending ? 0.55 : 1,
                fontFamily: 'inherit',
              }}
            >
              <Icon size={12} /> {label}
            </button>
          ))}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            background: 'var(--card)',
            border: '1px solid var(--line2)',
            borderRadius: '13px',
            padding: '5px 6px 5px 16px',
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={pending}
            aria-label="Câu hỏi gửi tới trợ lý"
            placeholder="Hỏi về sự kiện đã ghi nhận… vd: hôm nay có bao nhiêu vi phạm?"
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              background: 'transparent',
              color: 'var(--ink)',
              fontSize: '13.5px',
              fontFamily: 'inherit',
              padding: '10px 0',
            }}
          />
          <button
            type="button"
            onClick={() => ask(draft)}
            disabled={pending || !draft.trim()}
            aria-label="Gửi câu hỏi"
            style={{
              width: '38px',
              height: '38px',
              flex: 'none',
              borderRadius: '10px',
              border: 'none',
              background: 'var(--acc)',
              color: '#fff',
              cursor: pending || !draft.trim() ? 'not-allowed' : 'pointer',
              opacity: pending || !draft.trim() ? 0.55 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {pending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>

        <div style={{ fontSize: '10.5px', color: 'var(--ink3)', textAlign: 'center', marginTop: '8px' }}>
          Trả lời dựa trên chỉ mục sự kiện đã lưu · sự kiện có clip sẽ kèm đoạn video 10s làm bằng chứng
        </div>
      </div>

      <VideoModal videoUrl={clipUrl} onClose={() => setClipUrl(null)} />
    </div>
  );
};
