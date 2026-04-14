"use client";

import { useState, FormEvent } from "react";
import { Search, X, SlidersHorizontal } from "lucide-react";
import clsx from "clsx";

export interface SearchFilters {
  q?:       string;
  company?: string;
  role?:    string;
  topic?:   string;
}

interface Props {
  initialFilters?: SearchFilters;
  onSearch:        (filters: SearchFilters) => void;
  loading?:        boolean;
  placeholder?:    string;
  showFilters?:    boolean;
}

const POPULAR_TOPICS = [
  "Dynamic Programming", "Graph", "Tree", "System Design",
  "Arrays", "Two Pointers", "Binary Search", "Behavioral",
];

export default function SearchBar({
  initialFilters = {},
  onSearch,
  loading = false,
  placeholder = "Search interviews by question, company, or topic…",
  showFilters = true,
}: Props) {
  const [q,       setQ]       = useState(initialFilters.q       ?? "");
  const [company, setCompany] = useState(initialFilters.company ?? "");
  const [role,    setRole]    = useState(initialFilters.role    ?? "");
  const [topic,   setTopic]   = useState(initialFilters.topic   ?? "");
  const [showAdv, setShowAdv] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearch({ q: q.trim() || undefined, company: company.trim() || undefined,
               role: role.trim() || undefined, topic: topic || undefined });
  };

  const handleClear = () => {
    setQ(""); setCompany(""); setRole(""); setTopic("");
    onSearch({});
  };

  const hasFilters = q || company || role || topic;

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      {/* Main search row */}
      <div className="relative flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder={placeholder}
            className="input-field pl-9 pr-10"
          />
          {q && (
            <button
              type="button"
              onClick={() => setQ("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {showFilters && (
          <button
            type="button"
            onClick={() => setShowAdv((v) => !v)}
            className={clsx(
              "btn-secondary shrink-0",
              showAdv && "bg-blue-50 border-blue-300 text-blue-700"
            )}
          >
            <SlidersHorizontal className="w-4 h-4" />
            <span className="hidden sm:inline">Filters</span>
          </button>
        )}

        <button type="submit" disabled={loading} className="btn-primary shrink-0">
          {loading ? (
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <Search className="w-4 h-4" />
          )}
          <span className="hidden sm:inline">Search</span>
        </button>

        {hasFilters && (
          <button
            type="button"
            onClick={handleClear}
            className="btn-secondary shrink-0 text-red-600 border-red-200 hover:bg-red-50"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Advanced filters */}
      {showFilters && showAdv && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 bg-white border border-gray-200 rounded-xl p-4">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Company</label>
            <input
              type="text"
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              placeholder="e.g. Google, Amazon"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Role</label>
            <input
              type="text"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Software Engineer"
              className="input-field"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Topic</label>
            <select
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              className="input-field"
            >
              <option value="">All topics</option>
              {POPULAR_TOPICS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Topic quick-select chips */}
      <div className="flex flex-wrap gap-1.5">
        {POPULAR_TOPICS.map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => { setTopic(t); onSearch({ q: q || undefined, company: company || undefined, role: role || undefined, topic: t }); }}
            className={clsx(
              "topic-chip cursor-pointer transition-colors",
              topic === t && "bg-blue-600 text-white border-blue-600"
            )}
          >
            {t}
          </button>
        ))}
      </div>
    </form>
  );
}
