"use client";

import { useEffect, useRef, useState } from "react";
import { Send, Loader2, MessageSquare, Lightbulb } from "lucide-react";
import ChatMessageComp from "@/components/ChatMessage";
import { askQuestion, getOrCreateSession } from "@/lib/api";
import type { ChatMessage, Session } from "@/types";

const SUGGESTED = [
  "What topics does Google ask for L5 engineers?",
  "How should I prepare for Meta system design?",
  "What are the most common DSA questions at Amazon?",
  "What's the difference between FAANG behavioral rounds?",
  "How many LeetCode problems do I need before applying?",
];

export default function AssistantPage() {
  const [session,  setSession]  = useState<Session | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input,    setInput]    = useState("");
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getOrCreateSession().then((s) => {
      setSession(s);
      if (s.chat_history && s.chat_history.length > 0) {
        setMessages(s.chat_history);
      }
    }).catch(() => null);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const send = async (text?: string) => {
    const question = (text ?? input).trim();
    if (!question || loading) return;

    setInput("");
    setError(null);

    const userMsg: ChatMessage = {
      role:    "user",
      content: question,
      ts:      new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);

    try {
      const response = await askQuestion(question, session?.session_id);
      const assistantMsg: ChatMessage = {
        role:    "assistant",
        content: response.answer,
        ts:      new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch {
      setError("Failed to get a response. Is the backend and Ollama running?");
      setMessages((prev) => prev.slice(0, -1));  // remove optimistic user msg
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-7rem)]">
      {/* Header */}
      <div className="flex items-center gap-3 pb-4 border-b border-gray-200">
        <MessageSquare className="w-5 h-5 text-blue-600" />
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Interview Assistant</h1>
          <p className="text-xs text-gray-500">
            Answers grounded in real interview data (RAG + LLaMA 3)
          </p>
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-4">
        {messages.length === 0 && !loading && (
          <div className="text-center py-10 space-y-4">
            <p className="text-gray-400 text-sm">No messages yet. Try one of these:</p>
            <div className="flex flex-col gap-2 max-w-md mx-auto">
              {SUGGESTED.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="text-left px-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm
                             text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors
                             flex items-center gap-2"
                >
                  <Lightbulb className="w-3.5 h-3.5 text-amber-500 shrink-0" />
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, idx) => (
          <ChatMessageComp key={idx} message={msg} />
        ))}

        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center">
              <Loader2 className="w-4 h-4 text-white animate-spin" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.3s]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce [animation-delay:-0.15s]" />
                <span className="w-2 h-2 bg-gray-300 rounded-full animate-bounce" />
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="text-center text-sm text-red-500 bg-red-50 rounded-xl px-4 py-3 border border-red-100">
            {error}
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="pt-3 border-t border-gray-200">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask anything about interview prep…"
            rows={2}
            className="flex-1 input-field resize-none"
            disabled={loading}
          />
          <button
            onClick={() => send()}
            disabled={loading || !input.trim()}
            className="btn-primary self-end"
          >
            {loading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <Send className="w-4 h-4" />
            }
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5">
          Press <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">Enter</kbd> to send,{" "}
          <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600 font-mono">Shift+Enter</kbd> for newline
        </p>
      </div>
    </div>
  );
}
