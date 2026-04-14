import axios from "axios";
import type {
  AnalyticsData,
  AskResponse,
  RoadmapResponse,
  SearchParams,
  SearchResponse,
  Session,
} from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const client = axios.create({
  baseURL: BASE_URL,
  timeout: 60_000,
  headers: { "Content-Type": "application/json" },
});

// ─── Search ───────────────────────────────────────────────────────────────────

export async function searchInterviews(params: SearchParams): Promise<SearchResponse> {
  const { data } = await client.get<SearchResponse>("/search", { params });
  return data;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export async function getAnalytics(company?: string): Promise<AnalyticsData> {
  const { data } = await client.get<AnalyticsData>("/analytics", {
    params: company ? { company } : {},
  });
  return data;
}

export async function getCompanyAnalytics(company: string): Promise<AnalyticsData> {
  const { data } = await client.get<AnalyticsData>(`/analytics/company/${encodeURIComponent(company)}`);
  return data;
}

// ─── RAG ─────────────────────────────────────────────────────────────────────

export async function askQuestion(
  question: string,
  sessionId?: string
): Promise<AskResponse> {
  const { data } = await client.post<AskResponse>("/ask", {
    question,
    session_id: sessionId ?? null,
  });
  return data;
}

// ─── Roadmap ─────────────────────────────────────────────────────────────────

export async function generateRoadmap(payload: {
  company:          string;
  role:             string;
  time_available:   number;
  experience_level: string;
}): Promise<RoadmapResponse> {
  const { data } = await client.post<RoadmapResponse>("/roadmap", payload);
  return data;
}

// ─── Sessions ────────────────────────────────────────────────────────────────

export async function createSession(): Promise<Session> {
  const { data } = await client.post<Session>("/session/create");
  return data;
}

export async function getSession(sessionId: string): Promise<Session> {
  const { data } = await client.get<Session>(`/session/${sessionId}`);
  return data;
}

// ─── Session persistence (browser) ───────────────────────────────────────────

const SESSION_KEY = "prepai_session_id";

export function getStoredSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_KEY);
}

export function storeSessionId(id: string): void {
  if (typeof window === "undefined") return;
  localStorage.setItem(SESSION_KEY, id);
}

export async function getOrCreateSession(): Promise<Session> {
  const stored = getStoredSessionId();
  if (stored) {
    try {
      const session = await getSession(stored);
      return session;
    } catch {
      // Session expired — create a new one
    }
  }
  const session = await createSession();
  storeSessionId(session.session_id);
  return session;
}
