'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { fetchUser } from '@/lib/api';
import { Folder, ArrowRight, Loader2, Check } from 'lucide-react';

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const FEATURES = [
  'List & search projects and tasks',
  'Create and assign tasks via chat',
  'Update task status and priority',
  'Workload utilisation reports',
  'Human-in-the-loop confirmation',
  'Persistent conversation memory',
];

export default function LandingPage() {
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [loggingIn, setLoggingIn] = useState(false);

  useEffect(() => {
    fetchUser().then(user => {
      if (user) router.replace('/chat');
      else setChecking(false);
    });
  }, [router]);

  if (checking) {
    return (
      <div className="h-full flex items-center justify-center">
        <Loader2 className="animate-spin text-slate-500" size={22} />
      </div>
    );
  }

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-16 bg-[#0f1117]">
      {/* Glow background */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 w-[600px] h-[400px]
          bg-gradient-radial from-[#e8532a]/8 to-transparent rounded-full blur-3xl" />
      </div>

      <div className="relative z-10 flex flex-col items-center text-center max-w-lg animate-fade-in">
        {/* Icon */}
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#e8532a] to-[#ff8c6b]
          flex items-center justify-center mb-6 shadow-xl shadow-orange-900/40">
          <Folder size={26} className="text-white" />
        </div>

        {/* Headline */}
        <h1 className="text-3xl font-bold text-white mb-3 tracking-tight">
          Zoho Projects AI
        </h1>
        <p className="text-slate-400 text-base leading-relaxed mb-10 max-w-xs">
          A conversational assistant that reads and manages your Zoho Projects with natural language.
        </p>

        {/* Features */}
        <div className="w-full bg-[#161b27] border border-[#1e2535] rounded-2xl p-5 mb-8 text-left">
          <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-4">What you can do</p>
          <ul className="space-y-2.5">
            {FEATURES.map(f => (
              <li key={f} className="flex items-center gap-2.5 text-sm text-slate-300">
                <span className="w-4 h-4 rounded-full bg-[#1e3a6e] border border-[#3b7eff]/40 flex items-center justify-center shrink-0">
                  <Check size={10} className="text-[#3b7eff]" />
                </span>
                {f}
              </li>
            ))}
          </ul>
        </div>

        {/* CTA */}
        <a
          href={`${API}/auth/login`}
          onClick={() => setLoggingIn(true)}
          className="w-full flex items-center justify-center gap-2.5 py-3.5 px-6 rounded-2xl
            bg-gradient-to-r from-[#e8532a] to-[#ff6b42] text-white font-semibold text-sm
            hover:from-[#ff6035] hover:to-[#ff7a55] transition-all duration-200
            shadow-lg shadow-orange-900/30 hover:shadow-orange-900/50"
        >
          {loggingIn ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <>
              Connect with Zoho
              <ArrowRight size={16} />
            </>
          )}
        </a>

        <p className="text-[11px] text-slate-600 mt-4">
          Your credentials are handled entirely by Zoho OAuth. We never store your password.
        </p>
      </div>
    </div>
  );
}