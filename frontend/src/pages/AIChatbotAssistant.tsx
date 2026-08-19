import React, { useState } from 'react';
import { useApp } from '../context/AppContext';

export const AIChatbotAssistant: React.FC = () => {
  const { chatMessages, sendChatMessage } = useApp();
  const [draft, setDraft] = useState<string>('');

  const suggestions = [
    'Hôm nay có bao nhiêu xe lạ vào?',
    'Có xe máy hay xe hơi nào vào khu vực cấm không?',
    'Xe nâng hoạt động thế nào hôm nay?',
  ];

  const handleSend = () => {
    if (!draft.trim()) return;
    sendChatMessage(draft);
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
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2">
                    <path d="M12 3v4M12 17v4M3 12h4M17 12h4" />
                  </svg>
                </span>
                <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink3)' }}>Trợ lý sự kiện</span>
              </div>

              <div
                style={{
                  background: 'var(--card)',
                  border: '1px solid var(--line)',
                  fontSize: '13.5px',
                  lineHeight: 1.6,
                  padding: '13px 16px',
                  borderRadius: '4px 15px 15px 15px',
                  color: 'var(--ink)',
                }}
              >
                {m.text}
              </div>

              {/* Embedded 10s Video Evidence Clip Card */}
              {m.clip && (
                <div
                  style={{
                    marginTop: '10px',
                    background: 'var(--panel)',
                    border: '1px solid var(--line2)',
                    borderRadius: '13px',
                    overflow: 'hidden',
                    maxWidth: '430px',
                  }}
                >
                  <div
                    style={{
                      position: 'relative',
                      aspectRatio: '16/9',
                      background:
                        'radial-gradient(120% 90% at 50% 18%, #1a2129 0%, #0c0f13 60%, #07090b 100%)',
                    }}
                  >
                    <div
                      style={{
                        position: 'absolute',
                        left: 0,
                        right: 0,
                        bottom: 0,
                        height: '56%',
                        background: 'linear-gradient(#0c1014,#060809)',
                        backgroundImage:
                          'repeating-linear-gradient(90deg, rgba(255,255,255,.05) 0 1px, transparent 1px 13%)',
                      }}
                    />

                    <div
                      style={{
                        position: 'absolute',
                        left: '28%',
                        top: '38%',
                        width: '44%',
                        height: '44%',
                        background: `linear-gradient(160deg, ${m.clip.tint || '#2a4a6b'}, #11161c)`,
                        borderRadius: '5px',
                      }}
                    />

                    <div
                      style={{
                        position: 'absolute',
                        left: '27%',
                        top: '37%',
                        width: '46%',
                        height: '46%',
                        border: `1.5px solid ${m.clip.boxColor}`,
                      }}
                    >
                      <span
                        style={{
                          position: 'absolute',
                          left: '-1px',
                          top: '-18px',
                          background: m.clip.boxColor,
                          color: '#06080a',
                          fontSize: '9.5px',
                          fontWeight: 700,
                          padding: '1px 7px',
                          borderRadius: '3px',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {m.clip.boxLabel}
                      </span>
                    </div>

                    <div
                      style={{
                        position: 'absolute',
                        left: '50%',
                        top: '50%',
                        transform: 'translate(-50%,-50%)',
                        width: '44px',
                        height: '44px',
                        borderRadius: '50%',
                        background: 'rgba(0,0,0,.55)',
                        backdropFilter: 'blur(3px)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        cursor: 'pointer',
                        border: '1.5px solid rgba(255,255,255,.5)',
                      }}
                    >
                      <svg width="17" height="17" viewBox="0 0 24 24" fill="#fff">
                        <path d="M8 5v14l11-7z" />
                      </svg>
                    </div>

                    <div
                      style={{
                        position: 'absolute',
                        left: '9px',
                        top: '8px',
                        background: 'rgba(0,0,0,.5)',
                        color: '#e3e7ea',
                        fontSize: '9.5px',
                        padding: '2px 7px',
                        borderRadius: '5px',
                        fontFamily: "'IBM Plex Mono', monospace",
                      }}
                    >
                      {m.clip.cam}
                    </div>

                    <div
                      style={{
                        position: 'absolute',
                        right: '9px',
                        top: '8px',
                        background: 'var(--p0)',
                        color: '#fff',
                        fontSize: '9px',
                        fontWeight: 700,
                        padding: '2px 7px',
                        borderRadius: '5px',
                      }}
                    >
                      CLIP 10s
                    </div>
                  </div>

                  <div style={{ padding: '10px 13px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '9px', marginBottom: '8px' }}>
                      <span
                        style={{
                          fontSize: '10.5px',
                          fontFamily: "'IBM Plex Mono', monospace",
                          color: 'var(--ink3)',
                        }}
                      >
                        {m.clip.from}
                      </span>
                      <div
                        style={{
                          flex: 1,
                          height: '4px',
                          borderRadius: '3px',
                          background: 'var(--raise)',
                          position: 'relative',
                        }}
                      >
                        <div
                          style={{
                            position: 'absolute',
                            left: 0,
                            top: 0,
                            bottom: 0,
                            width: '32%',
                            background: 'var(--acc)',
                            borderRadius: '3px',
                          }}
                        />
                        <div
                          style={{
                            position: 'absolute',
                            left: '32%',
                            top: '50%',
                            width: '11px',
                            height: '11px',
                            borderRadius: '50%',
                            background: '#fff',
                            transform: 'translate(-50%,-50%)',
                          }}
                        />
                      </div>
                      <span
                        style={{
                          fontSize: '10.5px',
                          fontFamily: "'IBM Plex Mono', monospace",
                          color: 'var(--ink3)',
                        }}
                      >
                        {m.clip.to}
                      </span>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '11px', color: 'var(--ink2)', flex: 1 }}>{m.clip.title}</span>
                      <button
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
                        }}
                      >
                        Tải 10s
                      </button>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Input Footer & Suggestions */}
      <div style={{ flex: 'none', paddingTop: '14px' }}>
        <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap', marginBottom: '10px' }}>
          {suggestions.map((s, idx) => (
            <button
              key={idx}
              onClick={() => sendChatMessage(s)}
              style={{
                fontSize: '11.5px',
                fontWeight: 500,
                padding: '6px 13px',
                borderRadius: '20px',
                border: '1px solid var(--line2)',
                background: 'var(--card)',
                color: 'var(--ink2)',
                cursor: 'pointer',
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
            style={{
              width: '38px',
              height: '38px',
              flex: 'none',
              borderRadius: '10px',
              border: 'none',
              background: 'var(--acc)',
              color: '#fff',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
              <path d="m22 2-7 20-4-9-9-4z" />
            </svg>
          </button>
        </div>

        <div style={{ fontSize: '10.5px', color: 'var(--ink3)', textAlign: 'center', marginTop: '8px' }}>
          Trả lời dựa trên chỉ mục sự kiện đã lưu · luôn kèm đoạn video 10s làm bằng chứng
        </div>
      </div>
    </div>
  );
};
