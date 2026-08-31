import React, { useState, useRef, useEffect } from 'react';
import { useApp } from '../context/AppContext';
import { VideoModal } from '../components/common/VideoModal';

/** Prompt chips gợi ý — bấm là gửi thẳng câu hỏi tới trợ lý. */
const SUGGESTIONS = [
  'Hôm nay có bao nhiêu xe lạ vào?',
  'Đưa tôi 3 clip vi phạm gần nhất',
  'Loại xe nào vi phạm nhiều nhất tuần này?',
  'Xe nâng hoạt động thế nào tuần này?',
];

/** ISO timestamp của clip -> "17:38 27/08". Giá trị lạ thì trả về nguyên văn. */
const formatClipTime = (iso: string): string => {
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleString('vi-VN', {
    hour: '2-digit',
    minute: '2-digit',
    day: '2-digit',
    month: '2-digit',
  });
};

export const AIChatbotAssistant: React.FC = () => {
  const { chatMessages, sendChatMessage } = useApp();
  const [draft, setDraft] = useState<string>('');
  const [activeClipUrl, setActiveClipUrl] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  // Đang chờ backend: khoá ô nhập và các chip để không xếp chồng nhiều truy vấn.
  const isPending = chatMessages.some((m) => m.status === 'pending');

  // Cuộn xuống tin nhắn mới nhất sau mỗi lần log thay đổi.
  useEffect(() => {
    const node = logRef.current;
    if (node) node.scrollTop = node.scrollHeight;
  }, [chatMessages]);

  const submit = (text: string) => {
    if (isPending) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    void sendChatMessage(trimmed);
  };

  const handleSend = () => {
    submit(draft);
    setDraft('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleSend();
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
      {/* Chat Messages Log */}
      <div
        ref={logRef}
        role="log"
        aria-live="polite"
        aria-label="Hội thoại với trợ lý sự kiện"
        aria-busy={isPending}
        style={{
          flex: 1,
          overflow: 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
          padding: '6px 2px',
        }}
      >
        {chatMessages.map((m) => {
          if (m.role === 'user') {
            return (
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
            );
          }

          const isError = m.status === 'error';
          const isLoading = m.status === 'pending';

          return (
            <div key={m.id} style={{ alignSelf: 'flex-start', maxWidth: '86%', animation: 'msgIn .25s ease' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '7px', marginBottom: '6px' }}>
                <span
                  style={{
                    width: '22px',
                    height: '22px',
                    borderRadius: '7px',
                    background: 'linear-gradient(145deg,#2f9bff,#1361c9)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" aria-hidden="true">
                    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
                  </svg>
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink3)' }}>Trợ lý sự kiện</span>
              </div>

              <div
                {...(isError ? { role: 'alert' as const } : {})}
                style={{
                  background: 'var(--card)',
                  border: `1px solid ${isError ? 'rgba(255,69,58,.45)' : 'var(--line)'}`,
                  fontSize: '13.5px',
                  lineHeight: 1.6,
                  padding: '13px 16px',
                  borderRadius: '4px 15px 15px 15px',
                  color: isError ? 'var(--p0)' : 'var(--ink)',
                  opacity: isLoading ? 0.7 : 1,
                  fontStyle: isLoading ? 'italic' : 'normal',
                  // Câu trả lời dạng liệt kê/thống kê xuống dòng bằng '\n'; không
                  // giữ khoảng trắng thì mọi gạch đầu dòng dồn thành một khối chữ.
                  whiteSpace: 'pre-wrap',
                }}
              >
                {m.text}
              </div>

              {/* Câu SQL backend đã sinh — để người dùng kiểm chứng câu trả lời. */}
              {m.sqlQuery && (
                <details style={{ marginTop: '8px', maxWidth: '430px' }}>
                  <summary
                    style={{
                      fontSize: '11px',
                      color: 'var(--ink3)',
                      cursor: 'pointer',
                      userSelect: 'none',
                    }}
                  >
                    Xem truy vấn SQL
                  </summary>
                  <pre
                    style={{
                      margin: '6px 0 0',
                      padding: '9px 11px',
                      background: 'var(--raise)',
                      border: '1px solid var(--line)',
                      borderRadius: '8px',
                      fontSize: '10.5px',
                      lineHeight: 1.5,
                      color: 'var(--ink2)',
                      fontFamily: "'IBM Plex Mono', monospace",
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                    }}
                  >
                    {m.sqlQuery}
                  </pre>
                </details>
              )}

              {/* Clip 10s bằng chứng của đúng những sự kiện có trong câu trả lời. */}
              {m.clips && m.clips.length > 0 && (
                <div
                  role="list"
                  aria-label={`${m.clips.length} clip bằng chứng`}
                  style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '7px' }}
                >
                  {m.clips.map((clip, idx) => (
                    <div
                      key={clip.event_id || `${clip.url}-${idx}`}
                      role="listitem"
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        background: 'var(--panel)',
                        border: '1px solid var(--line2)',
                        borderRadius: '13px',
                        padding: '10px 13px',
                        maxWidth: '470px',
                      }}
                    >
                      <span
                        style={{
                          fontSize: '9px',
                          fontWeight: 700,
                          background: 'var(--p0)',
                          color: '#fff',
                          padding: '2px 7px',
                          borderRadius: '5px',
                          flex: 'none',
                        }}
                      >
                        CLIP 10s
                      </span>
                      <span
                        title={clip.label || undefined}
                        style={{
                          fontSize: '11px',
                          color: 'var(--ink2)',
                          flex: 1,
                          minWidth: 0,
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {clip.label || 'Video bằng chứng của sự kiện'}
                        {clip.timestamp ? ` · ${formatClipTime(clip.timestamp)}` : ''}
                      </span>
                      <button
                        onClick={() => setActiveClipUrl(clip.url)}
                        aria-label={`Xem clip 10 giây bằng chứng${clip.label ? `: ${clip.label}` : ''}`}
                        style={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          fontSize: '11px',
                          fontWeight: 600,
                          padding: '5px 11px',
                          borderRadius: '8px',
                          border: '1px solid var(--line2)',
                          background: 'transparent',
                          color: 'var(--ink)',
                          cursor: 'pointer',
                          fontFamily: 'inherit',
                          flex: 'none',
                        }}
                      >
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                        Xem clip
                      </button>
                      <a
                        href={clip.url}
                        download
                        style={{
                          fontSize: '11px',
                          fontWeight: 600,
                          color: 'var(--ink3)',
                          textDecoration: 'none',
                          flex: 'none',
                        }}
                      >
                        Tải
                      </a>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Input Footer & Suggestions */}
      <div style={{ flex: 'none', paddingTop: '14px' }}>
        <div
          role="group"
          aria-label="Câu hỏi gợi ý"
          style={{ display: 'flex', gap: '7px', flexWrap: 'wrap', marginBottom: '10px' }}
        >
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => submit(s)}
              disabled={isPending}
              style={{
                fontSize: '11.5px',
                fontWeight: 500,
                padding: '6px 13px',
                borderRadius: '20px',
                border: '1px solid var(--line2)',
                background: 'var(--card)',
                color: 'var(--ink2)',
                cursor: isPending ? 'not-allowed' : 'pointer',
                opacity: isPending ? 0.5 : 1,
                fontFamily: 'inherit',
              }}
            >
              {s}
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
            disabled={isPending}
            aria-label="Câu hỏi gửi tới trợ lý sự kiện"
            placeholder="Hỏi về sự kiện đã ghi nhận… vd: hôm nay có bao nhiêu xe lạ vào?"
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
            onClick={handleSend}
            disabled={isPending || !draft.trim()}
            aria-label="Gửi câu hỏi"
            style={{
              width: '38px',
              height: '38px',
              flex: 'none',
              borderRadius: '10px',
              border: 'none',
              background: 'var(--acc)',
              color: '#fff',
              cursor: isPending || !draft.trim() ? 'not-allowed' : 'pointer',
              opacity: isPending || !draft.trim() ? 0.5 : 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" aria-hidden="true">
              <path d="m22 2-7 20-4-9-9-4z" />
            </svg>
          </button>
        </div>

        <div style={{ fontSize: '10.5px', color: 'var(--ink3)', textAlign: 'center', marginTop: '8px' }}>
          Trả lời dựa trên chỉ mục sự kiện đã lưu · kèm đoạn video 10s làm bằng chứng khi có
        </div>
      </div>

      <VideoModal videoUrl={activeClipUrl} onClose={() => setActiveClipUrl(null)} />
    </div>
  );
};
