// 'use client';

// import { UserInfo, ChatSession } from '@/lib/types';
// import UserAvatar from './UserAvatar';
// import { LogOut, Plus, MessageSquare, Folder } from 'lucide-react';

// interface Props {
//   user: UserInfo;
//   sessions: ChatSession[];
//   currentSessionId: string;
//   onSelectSession: (id: string) => void;
//   onNewSession: () => void;
//   onLogout: () => void;
// }

// export default function Sidebar({
//   user,
//   sessions,
//   currentSessionId,
//   onSelectSession,
//   onNewSession,
//   onLogout,
// }: Props) {
//   return (
//     <aside className="w-64 shrink-0 h-full flex flex-col bg-[#0d1018] border-r border-[#1e2535]">
//       {/* Logo */}
//       <div className="p-5 border-b border-[#1e2535]">
//         <div className="flex items-center gap-2.5">
//           <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-[#e8532a] to-[#ff6b42] flex items-center justify-center">
//             <Folder size={15} className="text-white" />
//           </div>
//           <div>
//             <p className="text-sm font-bold text-white leading-none">Zoho Projects</p>
//             <p className="text-[10px] text-slate-500 mt-0.5">AI Assistant</p>
//           </div>
//         </div>
//       </div>

//       {/* New chat button */}
//       <div className="p-3">
//         <button
//           onClick={onNewSession}
//           className="w-full flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium
//             bg-[#1e2535] hover:bg-[#252d3d] border border-[#252d3d] text-slate-300
//             transition-all duration-150 group"
//         >
//           <Plus size={15} className="text-slate-400 group-hover:text-slate-200 transition-colors" />
//           New conversation
//         </button>
//       </div>

//       {/* Sessions list */}
//       <div className="flex-1 overflow-y-auto px-2 pb-2">
//         {sessions.length === 0 ? (
//           <p className="text-xs text-slate-600 text-center mt-4 px-4">No conversations yet</p>
//         ) : (
//           <div className="space-y-0.5">
//             {sessions.map(s => (
//               <button
//                 key={s.id}
//                 onClick={() => onSelectSession(s.id)}
//                 className={`w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-left
//                   transition-all duration-150 group
//                   ${currentSessionId === s.id
//                     ? 'bg-[#1e2d4a] border border-[#2a3f6a] text-slate-200'
//                     : 'hover:bg-[#161b27] text-slate-400 hover:text-slate-300'
//                   }`}
//               >
//                 <MessageSquare size={13} className="shrink-0 opacity-60" />
//                 <span className="text-xs truncate flex-1">{s.label}</span>
//               </button>
//             ))}
//           </div>
//         )}
//       </div>

//       {/* User footer */}
//       <div className="p-3 border-t border-[#1e2535]">
//         <div className="flex items-center gap-2.5 p-2">
//           <UserAvatar name={user.display_name} size="sm" />
//           <div className="flex-1 min-w-0">
//             <p className="text-xs font-semibold text-slate-200 truncate">{user.display_name}</p>
//             <p className="text-[10px] text-slate-500 truncate">{user.email}</p>
//           </div>
//           <button
//             onClick={onLogout}
//             title="Logout"
//             className="p-1.5 rounded-lg hover:bg-[#1e2535] text-slate-500 hover:text-slate-300 transition-all"
//           >
//             <LogOut size={13} />
//           </button>
//         </div>
//       </div>
//     </aside>
//   );
// }

'use client';

import { UserInfo, ChatSession } from '@/lib/types';
import { LogOut, Plus, MessageSquare, Folder } from 'lucide-react';

interface Props {
  user: UserInfo;
  sessions: ChatSession[];
  currentSessionId: string;
  onSelectSession: (id: string) => void;
  onNewSession: () => void;
  onLogout: () => void;
}

export default function Sidebar({ user, sessions, currentSessionId, onSelectSession, onNewSession, onLogout }: Props) {
  const initials = user.display_name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);

  return (
    <aside style={{
      width: 260,
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: '#010409',
      borderRight: '1px solid #21262d',
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid #21262d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: 8,
            background: 'linear-gradient(135deg, #e05c30, #ff7f5c)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Folder size={16} color="#fff" />
          </div>
          <div>
            <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: '#e6edf3', lineHeight: 1.2 }}>
              Zoho Projects
            </p>
            <p style={{ margin: 0, fontSize: 11, color: '#6e7681', marginTop: 2 }}>
              AI Assistant
            </p>
          </div>
        </div>
      </div>

      {/* New chat */}
      <div style={{ padding: '12px 12px 8px' }}>
        <button
          onClick={onNewSession}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 12px', borderRadius: 8, border: '1px solid #30363d',
            background: '#161b22', color: '#e6edf3', fontSize: 13, fontWeight: 500,
            cursor: 'pointer', transition: 'all 0.15s',
          }}
          onMouseEnter={e => (e.currentTarget.style.background = '#1c2128')}
          onMouseLeave={e => (e.currentTarget.style.background = '#161b22')}
        >
          <Plus size={14} color="#8b949e" />
          New conversation
        </button>
      </div>

      {/* Sessions */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 8px' }}>
        {sessions.length === 0 ? (
          <p style={{ fontSize: 12, color: '#484f58', textAlign: 'center', marginTop: 16, padding: '0 12px' }}>
            No conversations yet
          </p>
        ) : (
          sessions.map(s => {
            const active = currentSessionId === s.id;
            return (
              <button
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px', borderRadius: 6, border: 'none',
                  background: active ? '#1c2d4a' : 'transparent',
                  color: active ? '#58a6ff' : '#8b949e',
                  fontSize: 12, cursor: 'pointer', textAlign: 'left',
                  transition: 'all 0.15s', marginBottom: 1,
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = '#161b22'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              >
                <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.7 }} />
                <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1 }}>
                  {s.label}
                </span>
              </button>
            );
          })
        )}
      </div>

      {/* User footer */}
      <div style={{ padding: '12px', borderTop: '1px solid #21262d' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 30, height: 30, borderRadius: '50%',
            background: 'linear-gradient(135deg, #1f6feb, #388bfd)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 11, fontWeight: 600, color: '#fff', flexShrink: 0,
          }}>
            {initials}
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <p style={{ margin: 0, fontSize: 12, fontWeight: 500, color: '#e6edf3', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.display_name}
            </p>
            <p style={{ margin: 0, fontSize: 11, color: '#6e7681', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {user.email}
            </p>
          </div>
          <button
            onClick={onLogout}
            title="Logout"
            style={{
              padding: 6, borderRadius: 6, border: 'none',
              background: 'transparent', color: '#6e7681',
              cursor: 'pointer', display: 'flex', alignItems: 'center',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = '#e6edf3'; e.currentTarget.style.background = '#21262d'; }}
            onMouseLeave={e => { e.currentTarget.style.color = '#6e7681'; e.currentTarget.style.background = 'transparent'; }}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}