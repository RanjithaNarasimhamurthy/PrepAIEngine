"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp, Building2, Briefcase, Star } from "lucide-react";
import clsx from "clsx";
import type { Interview, OfferStatus } from "@/types";

// ─── Status badge ─────────────────────────────────────────────────────────────

const STATUS_STYLES: Record<OfferStatus, string> = {
  offered:  "badge-offered",
  rejected: "badge-rejected",
  pending:  "badge-pending",
  no_offer: "badge-no_offer",
  unknown:  "badge-unknown",
};

const STATUS_LABELS: Record<OfferStatus, string> = {
  offered:  "Offered",
  rejected: "Rejected",
  pending:  "Pending",
  no_offer: "No Offer",
  unknown:  "Unknown",
};

function StatusBadge({ status }: { status: OfferStatus }) {
  return (
    <span className={clsx("badge", STATUS_STYLES[status] ?? "badge-unknown")}>
      {STATUS_LABELS[status] ?? status}
    </span>
  );
}

// ─── Card ─────────────────────────────────────────────────────────────────────

interface Props {
  interview: Interview;
}

export default function InterviewCard({ interview }: Props) {
  const [expanded, setExpanded] = useState(false);

  const {
    company, role, offer_status, topics, questions,
    rounds, prep_insights, score, similarity_score,
  } = interview;

  return (
    <div className="card hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">
              <Building2 className="w-4 h-4 inline mr-1 text-blue-500" />
              {company || "Unknown Company"}
            </span>
            <StatusBadge status={(offer_status as OfferStatus) ?? "unknown"} />
            {similarity_score !== undefined && (
              <span className="badge bg-purple-50 text-purple-700 border border-purple-100">
                {Math.round(similarity_score * 100)}% match
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 mt-0.5">
            <Briefcase className="w-3.5 h-3.5 inline mr-1" />
            {role || "Unknown Role"}
          </p>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {score > 0 && (
            <div className="flex items-center gap-1 text-xs text-amber-600">
              <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
              {score}
            </div>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-gray-400 hover:text-gray-600 transition-colors"
            aria-label={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Topics */}
      {topics && topics.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {topics.map((t) => (
            <span key={t} className="topic-chip">{t}</span>
          ))}
        </div>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 space-y-4 border-t border-gray-100 pt-4">
          {/* Rounds */}
          {rounds && rounds.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Interview Rounds
              </h4>
              <div className="space-y-2">
                {rounds.map((rnd) => (
                  <div key={rnd.round_number} className="flex gap-3 text-sm">
                    <span className="shrink-0 font-medium text-gray-700 w-20">
                      Round {rnd.round_number}
                    </span>
                    <span className="shrink-0 text-blue-600 font-medium w-32">
                      {rnd.round_type}
                    </span>
                    <span className="text-gray-600">
                      {rnd.questions && rnd.questions.length > 0
                        ? rnd.questions.join(" • ")
                        : "—"}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Questions */}
          {questions && questions.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Questions Asked
              </h4>
              <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
                {questions.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Prep Insights */}
          {prep_insights && prep_insights.weak_areas && prep_insights.weak_areas.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">
                Weak Areas Reported
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {prep_insights.weak_areas.map((w) => (
                  <span key={w} className="badge bg-red-50 text-red-700">{w}</span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
