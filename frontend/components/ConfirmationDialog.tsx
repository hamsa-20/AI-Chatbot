'use client';

import { PendingAction } from '@/lib/types';
import { AlertTriangle, Check, X } from 'lucide-react';

interface Props {
  action: PendingAction;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

export default function ConfirmationDialog({ action, onConfirm, onCancel, isLoading }: Props) {
  const isDestructive = action.action === 'delete_task';

  return (
    <div className="animate-slide-up mx-auto max-w-md w-full">
      <div
        className={`rounded-2xl border p-4 ${
          isDestructive
            ? 'bg-red-950/30 border-red-900/50'
            : 'bg-[#1a2235] border-[#253450]'
        }`}
      >
        <div className="flex items-start gap-3 mb-4">
          <div
            className={`mt-0.5 w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
              isDestructive ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
            }`}
          >
            <AlertTriangle size={15} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">
              Confirmation Required
            </p>
            <p className="text-sm text-slate-200 leading-snug">
              {action.summary}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={onConfirm}
            disabled={isLoading}
            className={`flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-sm font-semibold transition-all
              disabled:opacity-50 disabled:cursor-not-allowed
              ${isDestructive
                ? 'bg-red-600 hover:bg-red-500 text-white'
                : 'bg-[#3b7eff] hover:bg-[#5590ff] text-white'
              }`}
          >
            <Check size={14} />
            Confirm
          </button>
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="flex-1 flex items-center justify-center gap-2 py-2 px-4 rounded-xl text-sm font-semibold
              bg-[#1e2535] hover:bg-[#252d3d] border border-[#252d3d] text-slate-300
              transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X size={14} />
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}