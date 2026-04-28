export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  requiresConfirmation?: boolean;
  pendingAction?: PendingAction | null;
}

export interface PendingAction {
  action: string;
  summary: string;
  details: Record<string, unknown>;
  requires_confirmation: boolean;
}

export interface ChatResponse {
  response: string;
  requires_confirmation: boolean;
  pending_action: PendingAction | null;
  session_id: string;
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
}

export interface ChatSession {
  id: string;
  label: string;
  createdAt: Date;
}