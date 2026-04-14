"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { AlertCircle, Inbox } from "lucide-react";
import SearchBar, { type SearchFilters } from "@/components/SearchBar";
import InterviewCard from "@/components/InterviewCard";
import { searchInterviews, getStoredSessionId } from "@/lib/api";
import type { Interview } from "@/types";

const PAGE_SIZE = 20;

export default function SearchPage() {
  const searchParams = useSearchParams();
  const router       = useRouter();

  const [results,  setResults]  = useState<Interview[]>([]);
  const [total,    setTotal]    = useState(0);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [offset,   setOffset]   = useState(0);

  const initialFilters: SearchFilters = {
    q:       searchParams.get("q")       ?? undefined,
    company: searchParams.get("company") ?? undefined,
    role:    searchParams.get("role")    ?? undefined,
    topic:   searchParams.get("topic")   ?? undefined,
  };

  const doSearch = useCallback(async (filters: SearchFilters, newOffset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const session_id = getStoredSessionId() ?? undefined;
      const data = await searchInterviews({
        ...filters,
        session_id,
        limit:  PAGE_SIZE,
        offset: newOffset,
      });
      if (newOffset === 0) {
        setResults(data.results);
      } else {
        setResults((prev) => [...prev, ...data.results]);
      }
      setTotal(data.total);
      setOffset(newOffset);
    } catch (err: unknown) {
      setError("Failed to fetch results. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }, []);

  // Run search on mount from URL params
  useEffect(() => {
    const hasParams = initialFilters.q || initialFilters.company ||
                      initialFilters.role || initialFilters.topic;
    if (hasParams) {
      doSearch(initialFilters, 0);
    } else {
      doSearch({}, 0);  // default: latest interviews
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (filters: SearchFilters) => {
    // Update URL params
    const params = new URLSearchParams();
    if (filters.q)       params.set("q",       filters.q);
    if (filters.company) params.set("company", filters.company);
    if (filters.role)    params.set("role",    filters.role);
    if (filters.topic)   params.set("topic",   filters.topic);
    router.replace(`/search?${params.toString()}`);
    doSearch(filters, 0);
  };

  const loadMore = () => {
    doSearch(initialFilters, offset + PAGE_SIZE);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 mb-1">Search Interviews</h1>
        <p className="text-sm text-gray-500">
          Semantic search across interview experiences. Combine free-text with filters.
        </p>
      </div>

      <SearchBar
        initialFilters={initialFilters}
        onSearch={handleSearch}
        loading={loading}
        showFilters
      />

      {/* Result count */}
      {!loading && (results.length > 0 || total > 0) && (
        <p className="text-sm text-gray-500">
          Showing <span className="font-medium text-gray-800">{results.length}</span> of{" "}
          <span className="font-medium text-gray-800">{total}</span> results
        </p>
      )}

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Loading skeleton */}
      {loading && results.length === 0 && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="card animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
              <div className="h-3 bg-gray-100 rounded w-1/4 mb-3" />
              <div className="flex gap-2">
                {[...Array(3)].map((_, j) => (
                  <div key={j} className="h-5 bg-gray-100 rounded-full w-16" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty state */}
      {!loading && results.length === 0 && !error && (
        <div className="text-center py-16 text-gray-400">
          <Inbox className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p className="font-medium">No interviews found</p>
          <p className="text-sm mt-1">Try different keywords or run the pipeline to load data.</p>
        </div>
      )}

      {/* Results */}
      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((interview) => (
            <InterviewCard key={interview.id} interview={interview} />
          ))}
        </div>
      )}

      {/* Load more */}
      {results.length < total && results.length > 0 && (
        <div className="text-center pt-2">
          <button
            onClick={loadMore}
            disabled={loading}
            className="btn-secondary"
          >
            {loading ? "Loading…" : `Load more (${total - results.length} remaining)`}
          </button>
        </div>
      )}
    </div>
  );
}
