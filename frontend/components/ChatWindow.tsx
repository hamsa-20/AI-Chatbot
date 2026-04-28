// 'use client';

// import { useEffect, useRef, useState } from 'react';
// import { Send, Loader2, Zap } from 'lucide-react';
// import { Message, PendingAction, UserInfo } from '@/lib/types';
// import MessageBubble from './MessageBubble';
// import ConfirmationDialog from './ConfirmationDialog';

// interface Props {
//   messages: Message[];
//   isLoading: boolean;
//   pendingAction: PendingAction | null;
//   user: UserInfo;
//   onSend: (text: string) => void;
//   onConfirm: () => void;
//   onCancel: () => void;
// }

// const SUGGESTIONS = [
//   'List all my projects',
//   'Show tasks in my current project',
//   'What tasks are overdue?',
//   'Show task utilisation report',
// ];

// export default function ChatWindow({
//   messages,
//   isLoading,
//   pendingAction,
//   user,
//   onSend,
//   onConfirm,
//   onCancel,
// }: Props) {
//   const [input, setInput] = useState('');
//   const bottomRef = useRef<HTMLDivElement>(null);
//   const inputRef = useRef<HTMLTextAreaElement>(null);

//   useEffect(() => {
//     bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
//   }, [messages, isLoading]);

//   const handleSend = () => {
//     const text = input.trim();
//     if (!text || isLoading) return;
//     setInput('');
//     onSend(text);
//   };

//   const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
//     if (e.key === 'Enter' && !e.shiftKey) {
//       e.preventDefault();
//       handleSend();
//     }
//   };

//   const isEmpty = messages.length === 0;

//   return (
//     <div className="flex flex-col h-full">
//       {/* Messages area */}
//       <div className="flex-1 overflow-y-auto">
//         <div className="max-w-3xl mx-auto px-4 py-6">

//           {/* Empty state */}
//           {isEmpty && (
//             <div className="flex flex-col items-center justify-center min-h-[60vh] text-center animate-fade-in">
//               <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#e8532a] to-[#ff6b42] flex items-center justify-center mb-5 shadow-lg shadow-orange-900/30">
//                 <Zap size={22} className="text-white" />
//               </div>
//               <h2 className="text-xl font-bold text-slate-100 mb-2">
//                 Zoho Projects AI
//               </h2>
//               <p className="text-sm text-slate-500 max-w-xs mb-8 leading-relaxed">
//                 Ask me anything about your projects and tasks. I can list, create, update, or delete them.
//               </p>

//               {/* Suggestion chips */}
//               <div className="flex flex-wrap gap-2 justify-center max-w-sm">
//                 {SUGGESTIONS.map(s => (
//                   <button
//                     key={s}
//                     onClick={() => onSend(s)}
//                     className="px-3 py-2 text-xs rounded-xl border border-[#1e2535] bg-[#161b27]
//                       text-slate-400 hover:text-slate-200 hover:border-[#3b7eff]/50 hover:bg-[#1a2235]
//                       transition-all duration-200"
//                   >
//                     {s}
//                   </button>
//                 ))}
//               </div>
//             </div>
//           )}

//           {/* Message list */}
//           <div className="space-y-5">
//             {messages.map(msg => (
//               <MessageBubble key={msg.id} message={msg} userName={user.display_name} />
//             ))}

//             {/* Typing indicator */}
//             {isLoading && (
//               <div className="flex gap-3 animate-fade-in">
//                 <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#e8532a] to-[#ff6b42] flex items-center justify-center shrink-0 text-xs font-bold text-white">
//                   Z
//                 </div>
//                 <div className="bg-[#161b27] border border-[#1e2535] rounded-2xl rounded-tl-sm px-4 py-3">
//                   <div className="flex gap-1 items-center h-4">
//                     {[0, 1, 2].map(i => (
//                       <span
//                         key={i}
//                         className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse-dot"
//                         style={{ animationDelay: `${i * 0.2}s` }}
//                       />
//                     ))}
//                   </div>
//                 </div>
//               </div>
//             )}

//             {/* Confirmation dialog */}
//             {pendingAction && !isLoading && (
//               <ConfirmationDialog
//                 action={pendingAction}
//                 onConfirm={onConfirm}
//                 onCancel={onCancel}
//                 isLoading={isLoading}
//               />
//             )}

//             <div ref={bottomRef} />
//           </div>
//         </div>
//       </div>

//       {/* Input area */}
//       <div className="border-t border-[#1e2535] bg-[#0d1018]/80 backdrop-blur-sm p-4">
//         <div className="max-w-3xl mx-auto">
//           <div className="flex items-end gap-3 bg-[#161b27] border border-[#1e2535] rounded-2xl px-4 py-3
//             focus-within:border-[#3b7eff]/60 transition-colors duration-200">
//             <textarea
//               ref={inputRef}
//               value={input}
//               onChange={e => {
//                 setInput(e.target.value);
//                 // Auto-grow
//                 e.target.style.height = 'auto';
//                 e.target.style.height = Math.min(e.target.scrollHeight, 160) + 'px';
//               }}
//               onKeyDown={handleKey}
//               placeholder="Ask about your projects and tasks…"
//               disabled={isLoading || !!pendingAction}
//               rows={1}
//               className="flex-1 bg-transparent text-sm text-slate-200 placeholder:text-slate-600
//                 resize-none outline-none leading-relaxed max-h-40
//                 disabled:opacity-40 disabled:cursor-not-allowed"
//             />
//             <button
//               onClick={handleSend}
//               disabled={!input.trim() || isLoading || !!pendingAction}
//               className="w-8 h-8 rounded-xl flex items-center justify-center shrink-0
//                 bg-[#3b7eff] hover:bg-[#5590ff] text-white
//                 disabled:opacity-30 disabled:cursor-not-allowed disabled:hover:bg-[#3b7eff]
//                 transition-all duration-150"
//             >
//               {isLoading ? (
//                 <Loader2 size={14} className="animate-spin" />
//               ) : (
//                 <Send size={14} />
//               )}
//             </button>
//           </div>
//           <p className="text-[10px] text-slate-600 text-center mt-2">
//             Press Enter to send · Shift+Enter for new line
//           </p>
//         </div>
//       </div>
//     </div>
//   );
// }


'use client';

import { useEffect, useRef, useState } from 'react';
import { Send, Loader2, Zap } from 'lucide-react';
import { Message, PendingAction, UserInfo } from '@/lib/types';
import MessageBubble from './MessageBubble';
import ConfirmationDialog from './ConfirmationDialog';

interface Props {
  messages: Message[];
  isLoading: boolean;
  pendingAction: PendingAction | null;
  user: UserInfo;
  onSend: (text: string) => void;
  onConfirm: () => void;
  onCancel: () => void;
}

const SUGGESTIONS = [
  'List all my projects',
  'Show open tasks',
  'What tasks are overdue?',
  'Show task utilisation report',
];

export default function ChatWindow({ messages, isLoading, pendingAction, user, onSend, onConfirm, onCancel }: Props) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading || pendingAction) return;
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
    onSend(text);
  };

  const handleKey = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: '#0d1117' }}>
      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '24px 0' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', padding: '0 20px' }}>

          {isEmpty && (
            <div style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', minHeight: '55vh', textAlign: 'center',
            }}>
              <div style={{
                width: 52, height: 52, borderRadius: 14,
                background: 'linear-gradient(135deg, #e05c30, #ff7f5c)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                marginBottom: 20,
              }}>
                <Zap size={22} color="#fff" />
              </div>
              <h2 style={{ margin: '0 0 8px', fontSize: 22, fontWeight: 600, color: '#e6edf3' }}>
                Zoho Projects AI
              </h2>
              <p style={{ margin: '0 0 28px', fontSize: 14, color: '#8b949e', maxWidth: 300, lineHeight: 1.6 }}>
                Ask anything about your projects and tasks. I can list, create, update, and more.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, justifyContent: 'center', maxWidth: 420 }}>
                {SUGGESTIONS.map(s => (
                  <button
                    key={s}
                    onClick={() => onSend(s)}
                    style={{
                      padding: '8px 14px', borderRadius: 20,
                      border: '1px solid #30363d', background: '#161b22',
                      color: '#8b949e', fontSize: 13, cursor: 'pointer',
                      transition: 'all 0.15s',
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.color = '#e6edf3';
                      e.currentTarget.style.borderColor = '#58a6ff';
                      e.currentTarget.style.background = '#1c2128';
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.color = '#8b949e';
                      e.currentTarget.style.borderColor = '#30363d';
                      e.currentTarget.style.background = '#161b22';
                    }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {messages.map(msg => (
              <MessageBubble key={msg.id} message={msg} userName={user.display_name} />
            ))}

            {isLoading && (
              <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <div style={{
                  width: 32, height: 32, borderRadius: '50%',
                  background: 'linear-gradient(135deg, #e05c30, #ff7f5c)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 13, fontWeight: 700, color: '#fff', flexShrink: 0,
                }}>Z</div>
                <div style={{
                  background: '#161b22', border: '1px solid #30363d',
                  borderRadius: '4px 18px 18px 18px', padding: '12px 16px',
                }}>
                  <div style={{ display: 'flex', gap: 5, alignItems: 'center', height: 16 }}>
                    {[0, 1, 2].map(i => (
                      <span key={i} style={{
                        width: 7, height: 7, borderRadius: '50%',
                        background: '#484f58', display: 'block',
                        animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
                      }} />
                    ))}
                  </div>
                </div>
              </div>
            )}

            {pendingAction && !isLoading && (
              <ConfirmationDialog
                action={pendingAction}
                onConfirm={onConfirm}
                onCancel={onCancel}
                isLoading={isLoading}
              />
            )}

            <div ref={bottomRef} />
          </div>
        </div>
      </div>

      {/* Input */}
      <div style={{
        borderTop: '1px solid #21262d',
        background: '#010409',
        padding: '16px 20px',
      }}>
        <div style={{ maxWidth: 760, margin: '0 auto' }}>
          <div style={{
            display: 'flex', alignItems: 'flex-end', gap: 10,
            background: '#161b22', border: '1px solid #30363d',
            borderRadius: 12, padding: '10px 12px',
            transition: 'border-color 0.15s',
          }}
            onFocus={() => {}}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={e => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 150) + 'px';
              }}
              onKeyDown={handleKey}
              placeholder="Ask about your projects and tasks…"
              disabled={isLoading || !!pendingAction}
              rows={1}
              style={{
                flex: 1, background: 'transparent', border: 'none', outline: 'none',
                resize: 'none', color: '#e6edf3', fontSize: 14, lineHeight: 1.6,
                fontFamily: 'inherit', maxHeight: 150,
                caretColor: '#58a6ff',
              }}
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading || !!pendingAction}
              style={{
                width: 34, height: 34, borderRadius: 8, border: 'none',
                background: input.trim() && !isLoading && !pendingAction ? '#1f6feb' : '#21262d',
                color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: input.trim() && !isLoading && !pendingAction ? 'pointer' : 'not-allowed',
                flexShrink: 0, transition: 'all 0.15s',
              }}
            >
              {isLoading ? <Loader2 size={15} style={{ animation: 'spin 1s linear infinite' }} /> : <Send size={15} />}
            </button>
          </div>
          <p style={{ margin: '6px 0 0', fontSize: 11, color: '#484f58', textAlign: 'center' }}>
            Enter to send · Shift+Enter for new line
          </p>
        </div>
      </div>

      <style>{`
        @keyframes bounce {
          0%, 80%, 100% { transform: scale(0.7); opacity: 0.4; }
          40% { transform: scale(1); opacity: 1; }
        }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}