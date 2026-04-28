const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function sendMessage(
  message: string,
  sessionId: string,
  confirmation?: boolean,
  pendingAction?: Record<string, unknown> | null
): Promise<{ response: string; requires_confirmation: boolean; pending_action: Record<string, unknown> | null; session_id: string }> {
  const res = await fetch(`${API}/chat`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      ...(confirmation !== undefined && { confirmation }),
      ...(pendingAction && { pending_action: pendingAction }),
    }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Request failed');
  }

  return res.json();
}

export async function fetchUser(): Promise<{
  id: string;
  email: string;
  display_name: string;
} | null> {
  try {
    const res = await fetch(`${API}/auth/me`, {
      credentials: 'include',
    });
    if (!res.ok) return null;
    return res.json();
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  await fetch(`${API}/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  });
}

export async function getChatHistory(sessionId: string): Promise<Array<{ role: string; content: string }>> {
  try {
    const res = await fetch(`${API}/chat/history/${sessionId}`, {
      credentials: 'include',
    });
    if (!res.ok) return [];
    const data = await res.json();
    return data.history || [];
  } catch {
    return [];
  }
}