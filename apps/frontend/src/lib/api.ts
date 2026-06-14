export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export let JWT_TOKEN = '';
export function setJwtToken(token: string) {
  JWT_TOKEN = token;
}

export let API_KEY = '';
export function setApiKey(key: string) {
  API_KEY = key;
}

function getHeaders(isFormData = false) {
  const headers: Record<string, string> = {};
  if (!isFormData) headers['Content-Type'] = 'application/json';
  
  if (JWT_TOKEN) {
    headers['Authorization'] = `Bearer ${JWT_TOKEN}`;
  } else if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  return headers;
}

export interface SearchRequest {
  query: string;
  domain?: string;
  doc_type?: string;
  limit?: number;
  method?: string;
  rerank?: boolean;
}

export interface SearchResponse {
  query: string;
  results: any[];
}

export interface AskRequest extends SearchRequest {
  stream?: boolean;
  session_id?: string;
}

export interface Citation {
  id: number;
  source: string;
  snippet: string;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  metadata?: any;
  session_id?: string;
  message_id?: string;
}

export interface SessionResponse {
  id: string;
  last_active: string;
  first_message: string;
}

export interface FeedbackResponse {
  id: string;
  message_id: string;
  session_id: string;
  rating: "up" | "down";
  comment?: string | null;
  created_at?: string;
}

export interface FeedbackRequest {
  session_id: string;
  rating: "up" | "down";
  comment?: string;
}

export interface MessageResponse {
  id: string;
  role: string;
  content: string;
  citations?: Citation[];
  created_at: string;
  feedback?: FeedbackResponse | null;
}

export async function search(req: SearchRequest): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE_URL}/search`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('Search request failed');
  return res.json();
}

export async function uploadDocument(file: File, domain: string, docType: string) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('domain', domain);
  formData.append('doc_type', docType);

  const res = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    headers: getHeaders(true),
    body: formData,
  });
  if (!res.ok) throw new Error('Upload request failed');
  return res.json();
}

export async function getJobStatus(jobId: string) {
  const res = await fetch(`${API_BASE_URL}/jobs/${jobId}`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Job status request failed');
  return res.json();
}

export async function askQuery(req: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${API_BASE_URL}/ask`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify({ ...req, stream: false }),
  });

  if (!res.ok) {
    const errBody = await res.json().catch(() => ({}));
    throw new Error(errBody.detail || 'Ask request failed');
  }

  return res.json();
}

export async function login(email: string, password: string): Promise<string> {
  const res = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Login failed');
  }
  const data = await res.json();
  return data.access_token;
}

export async function register(email: string, password: string): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Registration failed');
  }
}

export async function getSessions(): Promise<SessionResponse[]> {
  const res = await fetch(`${API_BASE_URL}/sessions`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch sessions');
  return res.json();
}

export async function getSessionMessages(sessionId: string): Promise<MessageResponse[]> {
  const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/messages`, {
    headers: getHeaders(),
  });
  if (!res.ok) throw new Error('Failed to fetch messages');
  return res.json();
}

export async function addFeedback(messageId: string, req: FeedbackRequest): Promise<FeedbackResponse> {
  const res = await fetch(`${API_BASE_URL}/messages/${messageId}/feedback`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error('Failed to submit feedback');
  return res.json();
}
