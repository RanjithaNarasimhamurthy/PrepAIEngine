// ─── Interview Data ───────────────────────────────────────────────────────────

export interface Round {
  round_number: number;
  round_type:   "Behavioral" | "DSA" | "OOD" | "System Design" | "Technical Screen" | "HR" | "Bar Raiser" | "Unknown";
  questions:    string[];
}

export interface OA {
  question_type: string | null;
  difficulty:    "Easy" | "Medium" | "Hard" | "Mixed" | null;
}

export interface PrepInsights {
  questions_solved: number | null;
  weak_areas:       string[];
}

export type OfferStatus = "offered" | "rejected" | "no_offer" | "pending" | "unknown";

export interface Interview {
  id:            number;
  reddit_id?:    string;
  company:       string;
  role:          string;
  offer_status:  OfferStatus;
  rounds:        Round[];
  oa:            OA;
  topics:        string[];
  questions:     string[];
  prep_insights: PrepInsights;
  score:         number;
  created_at:    string;
  similarity_score?: number;
}

// ─── Search ───────────────────────────────────────────────────────────────────

export interface SearchParams {
  q?:          string;
  company?:    string;
  role?:       string;
  topic?:      string;
  limit?:      number;
  offset?:     number;
  session_id?: string;
}

export interface SearchResponse {
  results:  Interview[];
  total:    number;
  has_more: boolean;
}

// ─── Analytics ───────────────────────────────────────────────────────────────

export interface DistEntry {
  name:  string;
  count: number;
}

export interface AnalyticsData {
  total_interviews:     number;
  companies:            DistEntry[];
  offer_status:         DistEntry[];
  topics:               DistEntry[];
  roles:                DistEntry[];
  round_type_distribution: DistEntry[];
  filtered_company?:    string;
}

// ─── RAG / Ask ────────────────────────────────────────────────────────────────

export interface AskSource {
  company:      string;
  role:         string;
  offer_status: OfferStatus;
  topics:       string[];
}

export interface AskResponse {
  answer:  string;
  sources: AskSource[];
  cached:  boolean;
}

// ─── Roadmap ─────────────────────────────────────────────────────────────────

export interface WeekPlan {
  week:   number;
  topics: string[];
  focus:  string;
}

export interface RoadmapResponse {
  company:           string;
  role:              string;
  experience_level:  string;
  weeks:             number;
  week_plan:         WeekPlan[];
  top_questions:     string[];
  top_topics:        string[];
  llm_advice:        string | null;
  data_source_count: number;
}

// ─── Session ──────────────────────────────────────────────────────────────────

export interface ChatMessage {
  role:    "user" | "assistant";
  content: string;
  ts:      string;
}

export interface Session {
  session_id:      string;
  chat_history:    ChatMessage[];
  preferences:     Record<string, string>;
  recent_searches: string[];
  created_at:      string;
  last_active:     string;
}
