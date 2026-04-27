"use client";
import { useState, useRef, useEffect, useCallback } from "react";
import { api, CopilotMessage, CopilotResponse } from "@/lib/api";
import Link from "next/link";
import { ArrowLeft, Send, Bot, User, Loader2, BookOpen, Zap, AlertTriangle } from "lucide-react";

interface Message {
  id:        string;
  role:      "user" | "assistant";
  content:   string;
  sources?:  string[];
  actions?:  string[];
  intent?:   string;
  loading?:  boolean;
}

const INTENT_BADGE: Record<string, { label: string; cls: string }> = {
  alert_query: { label: "Alert Analysis",  cls: "bg-red-900/40 text-red-400 border-red-800/50"    },
  sop_lookup:  { label: "SOP Lookup",      cls: "bg-blue-900/40 text-blue-400 border-blue-800/50" },
  general:     { label: "General Query",   cls: "bg-gray-800 text-gray-400 border-gray-700"       },
};

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1.5 py-2">
      {[0,1,2].map(i => (
        <span key={i} className="w-2 h-2 bg-indigo-500 rounded-full animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }} />
      ))}
    </div>
  );
}

export default function CopilotPage() {
  const [messages, setMessages]     = useState<Message[]>([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [statusReady, setStatusReady] = useState<boolean | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef  = useRef<HTMLInputElement>(null);
  const sessionId = useRef(`session-${Date.now()}`);

  // Scroll to bottom on new message
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  // Load initial suggestions and status
  useEffect(() => {
    api.suggestedPrompts().then(r => setSuggestions(r.prompts)).catch(() => {});
    api.copilotStatus().then(s => setStatusReady(s.ready)).catch(() => setStatusReady(false));
  }, []);

  const sendMessage = useCallback(async (text: string) => {
    if (!text.trim() || loading) return;
    setInput("");

    const userMsg: Message = { id: crypto.randomUUID(), role: "user", content: text };
    const thinkingMsg: Message = { id: crypto.randomUUID(), role: "assistant", content: "", loading: true };

    setMessages(prev => [...prev, userMsg, thinkingMsg]);
    setLoading(true);

    const history: CopilotMessage[] = messages
      .filter(m => !m.loading)
      .map(m => ({ role: m.role, content: m.content }));

    try {
      const res: CopilotResponse = await api.copilotChat({
        message:    text,
        history,
        session_id: sessionId.current,
      });

      const assistantMsg: Message = {
        id:      crypto.randomUUID(),
        role:    "assistant",
        content: res.response,
        sources: res.sources,
        actions: res.suggested_actions,
        intent:  res.intent,
      };
      setMessages(prev => [...prev.slice(0, -1), assistantMsg]);
    } catch {
      const errMsg: Message = {
        id:      crypto.randomUUID(),
        role:    "assistant",
        content: "⚠️ Unable to reach the AI copilot. Make sure the backend is running and the FAISS index is built.",
      };
      setMessages(prev => [...prev.slice(0, -1), errMsg]);
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [loading, messages]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); }
  };

  return (
    <main className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* ── Nav ── */}
      <nav className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50 px-6 py-3 flex-shrink-0">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm">
              <ArrowLeft className="w-4 h-4" /> Command Center
            </Link>
            <span className="text-gray-600">/</span>
            <span className="flex items-center gap-1.5 text-gray-300 text-sm">
              <Bot className="w-4 h-4 text-indigo-400" /> AI Copilot
            </span>
          </div>
          {/* Status indicator */}
          <div className={`text-[10px] px-2 py-1 rounded-full border font-medium flex items-center gap-1.5 ${
            statusReady === null ? "bg-gray-800 text-gray-500 border-gray-700" :
            statusReady ? "bg-green-900/40 text-green-400 border-green-800/50" :
                          "bg-amber-900/40 text-amber-400 border-amber-800/50"
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${statusReady ? "bg-green-400" : "bg-amber-400"} animate-pulse`} />
            {statusReady === null ? "Checking…" : statusReady ? "Gemini + FAISS Ready" : "Build FAISS index first"}
          </div>
        </div>
      </nav>

      {/* ── Chat thread ── */}
      <div className="flex-1 overflow-y-auto max-w-4xl w-full mx-auto px-4 py-6 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-16 space-y-6">
            <div className="w-16 h-16 mx-auto bg-indigo-900/40 border border-indigo-800/50 rounded-2xl flex items-center justify-center">
              <Bot className="w-8 h-8 text-indigo-400" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">CyberBattery AI Copilot</h1>
              <p className="text-sm text-gray-500 mt-2">
                Ask about any asset, alert, or operational procedure.<br />
                Powered by Gemini 1.5 Flash + FAISS knowledge retrieval.
              </p>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-w-2xl mx-auto">
              {suggestions.map((s, i) => (
                <button key={i} onClick={() => sendMessage(s)}
                        className="text-left text-sm bg-gray-900 border border-gray-800 rounded-xl px-4 py-3
                                   text-gray-300 hover:border-indigo-700 hover:text-white transition-all duration-150">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "assistant" && (
              <div className="w-8 h-8 rounded-full bg-indigo-900/50 border border-indigo-800/50
                              flex items-center justify-center flex-shrink-0 mt-0.5">
                <Bot className="w-4 h-4 text-indigo-400" />
              </div>
            )}

            <div className={`max-w-[80%] space-y-2 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
              {/* Bubble */}
              <div className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-indigo-600 text-white rounded-tr-sm"
                  : "bg-gray-900 border border-gray-800 text-gray-200 rounded-tl-sm"
              }`}>
                {msg.loading ? <TypingIndicator /> : msg.content}
              </div>

              {/* Intent badge */}
              {msg.intent && INTENT_BADGE[msg.intent] && (
                <span className={`text-[9px] font-bold tracking-widest px-2 py-0.5 rounded-full border ${INTENT_BADGE[msg.intent].cls}`}>
                  {INTENT_BADGE[msg.intent].label}
                </span>
              )}

              {/* Sources */}
              {msg.sources && msg.sources.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {msg.sources.map((s) => (
                    <span key={s} className="flex items-center gap-1 text-[10px] text-gray-500
                                             bg-gray-900 border border-gray-800 px-2 py-0.5 rounded-full">
                      <BookOpen className="w-2.5 h-2.5" /> {s}
                    </span>
                  ))}
                </div>
              )}

              {/* Suggested actions */}
              {msg.actions && msg.actions.length > 0 && (
                <div className="space-y-1 w-full">
                  <p className="text-[10px] text-gray-600 uppercase tracking-widest">Suggested actions</p>
                  {msg.actions.map((a, i) => (
                    <div key={i} className="flex items-start gap-1.5 text-xs text-gray-400">
                      <Zap className="w-3 h-3 text-yellow-500 flex-shrink-0 mt-0.5" /> {a}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {msg.role === "user" && (
              <div className="w-8 h-8 rounded-full bg-gray-800 border border-gray-700
                              flex items-center justify-center flex-shrink-0 mt-0.5">
                <User className="w-4 h-4 text-gray-400" />
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* ── Input bar ── */}
      <div className="flex-shrink-0 border-t border-gray-800 bg-gray-900/80 backdrop-blur-sm px-4 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <input
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={loading ? "Thinking…" : "Ask about an asset, alert, or SOP…"}
            disabled={loading}
            className="flex-1 bg-gray-950 border border-gray-700 rounded-xl px-4 py-3 text-sm
                       text-white placeholder-gray-600 focus:outline-none focus:border-indigo-600
                       transition-colors disabled:opacity-50"
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="w-11 h-11 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40
                       flex items-center justify-center transition-colors flex-shrink-0"
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Send className="w-4 h-4" />
            }
          </button>
        </div>
        <p className="text-center text-[10px] text-gray-700 mt-2">
          Powered by Gemini 1.5 Flash · Grounded by FAISS knowledge index · Rate limited: 10 req/min
        </p>
      </div>
    </main>
  );
}
