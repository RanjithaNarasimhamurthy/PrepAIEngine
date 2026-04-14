"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  BrainCircuit, Search, BarChart2, MessageSquare,
  Map, TrendingUp, Clock, Zap,
} from "lucide-react";
import SearchBar, { type SearchFilters } from "@/components/SearchBar";
import { getOrCreateSession } from "@/lib/api";
import type { Session } from "@/types";

const FEATURE_CARDS = [
  {
    icon: Search,
    title: "Semantic Search",
    description: "Find interview experiences using natural language. Powered by FAISS vector search + PostgreSQL.",
    href: "/search",
    color: "bg-blue-50 text-blue-600",
  },
  {
    icon: BarChart2,
    title: "Analytics Dashboard",
    description: "Topic frequency heatmaps, company offer rates, round-type breakdowns across hundreds of interviews.",
    href: "/analytics",
    color: "bg-green-50 text-green-600",
  },
  {
    icon: MessageSquare,
    title: "AI Assistant",
    description: "Ask any interview prep question. Grounded answers backed by real data via RAG + LLaMA 3.",
    href: "/assistant",
    color: "bg-purple-50 text-purple-600",
  },
  {
    icon: Map,
    title: "Roadmap Generator",
    description: "Get a personalised week-by-week study plan tailored to your target company, role, and experience.",
    href: "/roadmap",
    color: "bg-orange-50 text-orange-600",
  },
];

const STATS = [
  { icon: TrendingUp, label: "Interview reports analysed",   value: "500+" },
  { icon: Zap,        label: "Companies covered",             value: "50+"  },
  { icon: Clock,      label: "Avg. extraction time per post", value: "<10s" },
];

export default function HomePage() {
  const router  = useRouter();
  const [session, setSession] = useState<Session | null>(null);

  useEffect(() => {
    getOrCreateSession().then(setSession).catch(() => null);
  }, []);

  const handleSearch = (filters: SearchFilters) => {
    const params = new URLSearchParams();
    if (filters.q)       params.set("q",       filters.q);
    if (filters.company) params.set("company", filters.company);
    if (filters.role)    params.set("role",    filters.role);
    if (filters.topic)   params.set("topic",   filters.topic);
    if (session)         params.set("sid",     session.session_id);
    router.push(`/search?${params.toString()}`);
  };

  return (
    <div className="space-y-12">
      {/* Hero */}
      <section className="text-center space-y-6 py-12">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-50 border border-blue-100 text-blue-700 text-sm font-medium">
          <BrainCircuit className="w-4 h-4" />
          AI-Powered Interview Intelligence
        </div>
        <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 tracking-tight">
          Know exactly what to{" "}
          <span className="text-blue-600">prepare</span>
        </h1>
        <p className="text-lg text-gray-500 max-w-2xl mx-auto">
          PrepAI extracts structured insights from thousands of Reddit interview
          reports — so you can search smarter, study strategically, and walk in confident.
        </p>

        {/* Search box */}
        <div className="max-w-2xl mx-auto">
          <SearchBar
            onSearch={handleSearch}
            placeholder="Search: Google SWE system design experience…"
            showFilters={false}
          />
        </div>
      </section>

      {/* Stats */}
      <section className="grid grid-cols-3 gap-4 max-w-lg mx-auto">
        {STATS.map(({ icon: Icon, label, value }) => (
          <div key={label} className="text-center">
            <Icon className="w-5 h-5 mx-auto text-blue-500 mb-1" />
            <div className="text-2xl font-bold text-gray-900">{value}</div>
            <div className="text-xs text-gray-500 mt-0.5">{label}</div>
          </div>
        ))}
      </section>

      {/* Feature cards */}
      <section>
        <h2 className="text-xl font-semibold text-gray-900 mb-5">Explore PrepAI</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {FEATURE_CARDS.map(({ icon: Icon, title, description, href, color }) => (
            <a
              key={href}
              href={href}
              className="card group hover:border-blue-300 hover:shadow-md transition-all cursor-pointer"
            >
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center mb-3 ${color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <h3 className="font-semibold text-gray-900 group-hover:text-blue-600 transition-colors">
                {title}
              </h3>
              <p className="text-sm text-gray-500 mt-1">{description}</p>
            </a>
          ))}
        </div>
      </section>

      {/* Recent searches */}
      {session && session.recent_searches && session.recent_searches.length > 0 && (
        <section>
          <h2 className="text-sm font-medium text-gray-500 mb-3 flex items-center gap-2">
            <Clock className="w-4 h-4" /> Recent searches
          </h2>
          <div className="flex flex-wrap gap-2">
            {session.recent_searches.map((q) => (
              <button
                key={q}
                onClick={() => handleSearch({ q })}
                className="px-3 py-1.5 bg-white border border-gray-200 rounded-lg text-sm text-gray-600
                           hover:border-blue-300 hover:text-blue-600 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
