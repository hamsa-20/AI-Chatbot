'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { fetchUser, logout } from '@/lib/api';
import { useChat } from '@/hooks/useChat';
import ChatWindow from '@/components/ChatWindow';
import Sidebar from '@/components/Sidebar';
import { UserInfo, ChatSession } from '@/lib/types';
import { Loader2, Menu, X } from 'lucide-react';

function makeId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function makeSession(label = 'New conversation'): ChatSession {
  return { id: makeId(), label, createdAt: new Date() };
}

export default function ChatPage() {
  const router = useRouter();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSession, setCurrentSession] = useState<ChatSession>(() => makeSession());

  const { messages, isLoading, pendingAction, error, send, confirm, cancel, clearSession } =
    useChat(currentSession.id);

  // Auth check
  useEffect(() => {
    fetchUser().then(u => {
      if (!u) {
        router.replace('/');
      } else {
        setUser(u);
        setLoading(false);
      }
    });
  }, [router]);

  // Auto-label session based on first message
  useEffect(() => {
    if (messages.length === 1 && messages[0].role === 'user') {
      const label = messages[0].content.slice(0, 40) + (messages[0].content.length > 40 ? '…' : '');
      setTimeout(() => setSessions(prev => {
        const exists = prev.find(s => s.id === currentSession.id);
        const updated = { ...currentSession, label };
        if (exists) return prev.map(s => s.id === updated.id ? updated : s);
        return [updated, ...prev];
      }), 0);
    }
  }, [messages, currentSession]);

  const handleNewSession = useCallback(() => {
    const s = makeSession();
    setCurrentSession(s);
    clearSession();
    setSidebarOpen(false);
  }, [clearSession]);

  const handleSelectSession = useCallback((id: string) => {
    // For simplicity - in production you'd reload history from API
    const s = sessions.find(x => x.id === id);
    if (s) {
      setCurrentSession(s);
      clearSession();
      setSidebarOpen(false);
    }
  }, [sessions, clearSession]);

  const handleLogout = useCallback(async () => {
    await logout();
    router.replace('/');
  }, [router]);

  if (loading || !user) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#0f1117]">
        <Loader2 className="animate-spin text-slate-500" size={22} />
      </div>
    );
  }

  return (
    <div className="h-screen flex overflow-hidden bg-[#0f1117]">
      {/* Sidebar — mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/60 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar — desktop always visible, mobile slide-in */}
      <div
        className={`fixed lg:relative z-30 h-full transition-transform duration-300
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}
      >
        <Sidebar
          user={user}
          sessions={sessions}
          currentSessionId={currentSession.id}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          onLogout={handleLogout}
        />
      </div>

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar (mobile) */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-[#1e2535] lg:hidden shrink-0">
          <button
            onClick={() => setSidebarOpen(v => !v)}
            className="p-1.5 rounded-lg hover:bg-[#1e2535] text-slate-400 hover:text-slate-200 transition"
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
          <span className="text-sm font-semibold text-slate-300 truncate">{currentSession.label}</span>
        </div>

        {/* Error banner */}
        {error && (
          <div className="mx-4 mt-3 px-4 py-2 rounded-xl bg-red-950/40 border border-red-900/50 text-xs text-red-400 shrink-0">
            {error}
          </div>
        )}

        {/* Chat window */}
        <div className="flex-1 min-h-0">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            pendingAction={pendingAction}
            user={user}
            onSend={send}
            onConfirm={confirm}
            onCancel={cancel}
          />
        </div>
      </div>
    </div>
  );
}