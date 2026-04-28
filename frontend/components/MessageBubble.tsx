// 'use client';

// import ReactMarkdown from 'react-markdown';
// import { Message } from '@/lib/types';
// import UserAvatar from './UserAvatar';

// interface Props {
//   message: Message;
//   userName: string;
// }

// export default function MessageBubble({ message, userName }: Props) {
//   const isUser = message.role === 'user';

//   return (
//     <div
//       className={`flex gap-3 animate-slide-up ${isUser ? 'flex-row-reverse' : 'flex-row'}`}
//     >
//       {/* Avatar */}
//       {isUser ? (
//         <UserAvatar name={userName} size="sm" />
//       ) : (
//         <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#e8532a] to-[#ff6b42] flex items-center justify-center shrink-0 text-xs font-bold text-white">
//           Z
//         </div>
//       )}

//       {/* Bubble */}
//       <div
//         className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed
//           ${isUser
//             ? 'bg-[#1e3a6e] border border-[#2a4a8a] text-slate-100 rounded-tr-sm'
//             : 'bg-[#161b27] border border-[#1e2535] text-slate-200 rounded-tl-sm'
//           }`}
//       >
//         {isUser ? (
//           <p className="whitespace-pre-wrap">{message.content}</p>
//         ) : (
//           <div className="prose-chat">
//             <ReactMarkdown>{message.content}</ReactMarkdown>
//           </div>
//         )}

//         <div className={`text-[10px] mt-1.5 opacity-40 ${isUser ? 'text-right' : 'text-left'}`}>
//           {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
//         </div>
//       </div>
//     </div>
//   );
// }

'use client';

import ReactMarkdown from 'react-markdown';
import { Message } from '@/lib/types';

interface Props {
  message: Message;
  userName: string;
}

function formatTime(date: Date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function UserInitials({ name }: { name: string }) {
  const initials = name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
  return (
    <div style={{
      width: 32, height: 32, borderRadius: '50%',
      background: 'linear-gradient(135deg, #238636, #2ea043)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, fontWeight: 600, color: '#fff',
      flexShrink: 0, userSelect: 'none'
    }}>
      {initials}
    </div>
  );
}

function BotAvatar() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: '50%',
      background: 'linear-gradient(135deg, #e05c30, #ff7f5c)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 13, fontWeight: 700, color: '#fff',
      flexShrink: 0
    }}>
      Z
    </div>
  );
}

export default function MessageBubble({ message, userName }: Props) {
  const isUser = message.role === 'user';

  return (
    <div style={{
      display: 'flex',
      flexDirection: isUser ? 'row-reverse' : 'row',
      gap: 10,
      alignItems: 'flex-start',
      animation: 'slideUp 0.25s ease forwards',
    }}>
      {isUser ? <UserInitials name={userName} /> : <BotAvatar />}

      <div style={{
        maxWidth: '72%',
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        alignItems: isUser ? 'flex-end' : 'flex-start',
      }}>
        <div style={{
          background: isUser ? '#1c3a5e' : '#161b22',
          border: `1px solid ${isUser ? '#2d5a9e' : '#30363d'}`,
          borderRadius: isUser ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
          padding: '10px 14px',
          fontSize: 14,
          lineHeight: 1.6,
          color: '#e6edf3',
          wordBreak: 'break-word',
        }}>
          {isUser ? (
            <p style={{ margin: 0, color: '#e6edf3', fontSize: 14, lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
              {message.content}
            </p>
          ) : (
            <div className="prose-chat">
              <ReactMarkdown>{message.content}</ReactMarkdown>
            </div>
          )}
        </div>
        <span style={{ fontSize: 11, color: '#484f58', padding: '0 4px' }}>
          {formatTime(message.timestamp)}
        </span>
      </div>
    </div>
  );
}