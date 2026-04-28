'use client';

import { useState, useCallback, useRef } from 'react';
import { Message, PendingAction } from '@/lib/types';
import { sendMessage } from '@/lib/api';

// Simple ID generator
function makeId() {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function useChat(sessionId: string) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [pendingAction, setPendingAction] = useState<PendingAction | null>(null);
  const [error, setError] = useState<string | null>(null);

  const pendingRef = useRef<PendingAction | null>(null);

  const addMessage = useCallback(
    (role: 'user' | 'assistant', content: string, extra?: Partial<Message>) => {
      const msg: Message = {
        id: makeId(),
        role,
        content,
        timestamp: new Date(),
        ...extra,
      };
      setMessages(prev => [...prev, msg]);
      return msg;
    },
    []
  );

  const send = useCallback(
    async (text: string, confirmation?: boolean) => {
      if (!text.trim() && confirmation === undefined) return;

      setError(null);

      if (text.trim()) {
        addMessage('user', text);
      }

      setIsLoading(true);

      try {
        const currentPending = pendingRef.current;

        const result = await sendMessage(
          text || (confirmation ? 'yes' : 'no'),
          sessionId,
          confirmation,
          currentPending as unknown as Record<string, unknown>
        );

        const assistantMsg: Partial<Message> = {
          requiresConfirmation: result.requires_confirmation,
          pendingAction: result.pending_action as unknown as PendingAction | null,
        };

        addMessage('assistant', result.response, assistantMsg);

        if (result.requires_confirmation && result.pending_action) {
          const action = result.pending_action as unknown as PendingAction;
          pendingRef.current = action;
          setPendingAction(action);
        } else {
          pendingRef.current = null;
          setPendingAction(null);
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Something went wrong';
        setError(msg);
        addMessage('assistant', `❌ ${msg}`);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId, addMessage]
  );

  const confirm = useCallback(async () => {
    const action = pendingRef.current;

    setPendingAction(null);
    pendingRef.current = null;
    setIsLoading(true);
    setError(null);

    addMessage('user', 'Yes, confirm.');

    try {
      const result = await sendMessage(
        'yes',
        sessionId,
        true,
        action as unknown as Record<string, unknown>
      );

      addMessage('assistant', result.response);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Action failed';
      setError(msg);
      addMessage('assistant', `❌ ${msg}`);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage]);

  const cancel = useCallback(async () => {
    const action = pendingRef.current;

    setPendingAction(null);
    pendingRef.current = null;
    setIsLoading(true);

    addMessage('user', 'No, cancel.');

    try {
      const result = await sendMessage(
        'no',
        sessionId,
        false,
        action as unknown as Record<string, unknown> | undefined
      );

      addMessage('assistant', result.response);
    } catch {
      addMessage('assistant', '❌ Action cancelled.');
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, addMessage]);

  const clearSession = useCallback(() => {
    setMessages([]);
    setPendingAction(null);
    pendingRef.current = null;
    setError(null);
  }, []);

  return {
    messages,
    isLoading,
    pendingAction,
    error,
    send,
    confirm,
    cancel,
    clearSession,
  };
}