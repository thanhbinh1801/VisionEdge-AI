import React, { useState } from 'react';
import { Bot, Send, User, Play, Sparkles } from 'lucide-react';
import { useApp } from '../context/AppContext';

interface ChatMessage {
  id: string;
  sender: 'user' | 'bot';
  text: string;
  sqlQuery?: string;
  clipUrl?: string;
}

export const AIChatbotAssistant: React.FC = () => {
  const { setSelectedVideoClipUrl } = useApp();
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: '1',
      sender: 'bot',
      text: 'Xin chào! Tôi là Trợ lý AI SentriAI (Text-to-SQL). Bạn có thể hỏi tôi các câu hỏi như: "Hôm nay có bao nhiêu xe công ty vào cổng?" hoặc "Cho xem clip xe vi phạm bãi kiểm lúc 9h".',
    },
  ]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      sender: 'user',
      text: input,
    };

    setMessages((prev) => [...prev, userMsg]);
    const currentQuery = input;
    setInput('');

    // Simulated LLM Text-to-SQL Fallback Engine response
    setTimeout(() => {
      let responseText = 'Theo dữ liệu ghi nhận từ hệ thống SQLite:';
      let sql = "SELECT COUNT(*) FROM events WHERE event_type = 'LPR';";

      if (currentQuery.toLowerCase().includes('vi phạm')) {
        responseText = 'Đã tìm thấy 1 trường hợp xe xâm nhập vùng cấm bãi kiểm lúc 09:15:30.';
        sql = "SELECT * FROM events WHERE severity = 3 ORDER BY timestamp DESC LIMIT 1;";
      }

      const botMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        sender: 'bot',
        text: responseText,
        sqlQuery: sql,
        clipUrl: 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
      };

      setMessages((prev) => [...prev, botMsg]);
    }, 800);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
            <span>Tab 4: AI Chatbot Assistant</span>
            <Sparkles className="w-5 h-5 text-indigo-400" />
          </h2>
          <p className="text-xs text-slate-400">Hỏi Đáp Ngôn Ngữ Tự Nhiên (Text-to-SQL + Ring Buffer Clips)</p>
        </div>
      </div>

      <div className="bg-[#0f172a] border border-slate-800 rounded-xl flex flex-col h-[520px] shadow-lg">
        <div className="p-4 border-b border-slate-800 flex items-center space-x-3 bg-slate-900/60">
          <div className="p-2 bg-indigo-600 rounded-lg">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-200">LLM Q&A Agent (ADR-004)</h3>
            <p className="text-[11px] text-slate-400">Rule-based Fallback Matcher + SQL Query Engine</p>
          </div>
        </div>

        <div className="flex-1 p-4 overflow-y-auto space-y-4">
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex items-start space-x-3 ${
                m.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div
                className={`p-2 rounded-lg shrink-0 ${
                  m.sender === 'user' ? 'bg-indigo-600 text-white' : 'bg-slate-800 text-indigo-400'
                }`}
              >
                {m.sender === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              <div
                className={`max-w-xl p-3.5 rounded-xl text-xs space-y-2 ${
                  m.sender === 'user'
                    ? 'bg-indigo-600/20 border border-indigo-500/40 text-slate-100'
                    : 'bg-slate-900 border border-slate-800 text-slate-200'
                }`}
              >
                <div>{m.text}</div>

                {m.sqlQuery && (
                  <div className="p-2 bg-slate-950 rounded border border-slate-800 font-mono text-[11px] text-indigo-300">
                    <span className="text-slate-500 select-none">SQL: </span>
                    {m.sqlQuery}
                  </div>
                )}

                {m.clipUrl && (
                  <button
                    onClick={() => setSelectedVideoClipUrl(m.clipUrl || null)}
                    className="flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-950 text-indigo-300 hover:bg-indigo-900 rounded border border-indigo-800 font-medium"
                  >
                    <Play className="w-3.5 h-3.5" />
                    <span>Xem Evidence Video Clip 10s</span>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handleSend} className="p-3 border-t border-slate-800 bg-slate-900/60 flex items-center space-x-2">
          <input
            type="text"
            placeholder="Hỏi về sự kiện, số lượng xe, clip vi phạm..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="flex-1 px-4 py-2 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="p-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
