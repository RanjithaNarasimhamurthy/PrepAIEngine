"use client";

import { useState } from "react";
import { Map, Loader2, AlertCircle, ChevronDown, ChevronUp, Lightbulb, Database } from "lucide-react";
import { generateRoadmap } from "@/lib/api";
import type { RoadmapResponse, WeekPlan } from "@/types";
import clsx from "clsx";

const EXPERIENCE_LEVELS = [
  { value: "beginner",     label: "Beginner",     desc: "0–1 year or new to DSA" },
  { value: "intermediate", label: "Intermediate", desc: "1–3 years, knows basics"   },
  { value: "advanced",     label: "Advanced",     desc: "3+ years, targeting senior" },
];

const COMPANIES = [
  "Google", "Amazon", "Meta", "Apple", "Microsoft", "Netflix",
  "Uber", "Airbnb", "Stripe", "Databricks", "Snowflake", "Other",
];

const ROLES = [
  "Software Engineer", "Senior Software Engineer", "Staff Software Engineer",
  "Machine Learning Engineer", "Data Scientist", "Site Reliability Engineer",
  "Backend Engineer", "Frontend Engineer", "Full Stack Engineer",
];

function WeekCard({ plan, index }: { plan: WeekPlan; index: number }) {
  const [open, setOpen] = useState(index < 2);   // first 2 weeks expanded by default

  const isFinal = plan.focus.toLowerCase().includes("mock");

  return (
    <div className={clsx("border rounded-xl overflow-hidden", isFinal ? "border-purple-200 bg-purple-50" : "border-gray-200 bg-white")}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4"
      >
        <div className="flex items-center gap-3">
          <div className={clsx(
            "w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0",
            isFinal ? "bg-purple-600 text-white" : "bg-blue-600 text-white"
          )}>
            {plan.week}
          </div>
          <div className="text-left">
            <p className="font-semibold text-gray-900">Week {plan.week} — {plan.focus}</p>
            <p className="text-xs text-gray-500 mt-0.5">{plan.topics.join(", ")}</p>
          </div>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </button>

      {open && (
        <div className="border-t border-gray-100 px-5 py-4 space-y-3">
          <div className="flex flex-wrap gap-2">
            {plan.topics.map((t) => (
              <span key={t} className="topic-chip">{t}</span>
            ))}
          </div>
          {isFinal && (
            <p className="text-sm text-purple-700">
              Dedicate this week to timed mock interviews and reviewing your weakest areas.
              Focus on explaining your thought process out loud.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

export default function RoadmapPage() {
  const [company,    setCompany]    = useState("");
  const [customCo,   setCustomCo]   = useState("");
  const [role,       setRole]       = useState("");
  const [weeks,      setWeeks]      = useState(6);
  const [expLevel,   setExpLevel]   = useState("intermediate");
  const [roadmap,    setRoadmap]    = useState<RoadmapResponse | null>(null);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    const finalCompany = company === "Other" ? customCo.trim() : company;
    if (!finalCompany || !role) return;

    setLoading(true);
    setError(null);
    setRoadmap(null);

    try {
      const result = await generateRoadmap({
        company:          finalCompany,
        role,
        time_available:   weeks,
        experience_level: expLevel,
      });
      setRoadmap(result);
      // Scroll to results
      setTimeout(() => {
        document.getElementById("roadmap-result")?.scrollIntoView({ behavior: "smooth" });
      }, 100);
    } catch {
      setError("Failed to generate roadmap. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <Map className="w-5 h-5 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Study Roadmap Generator</h1>
          <p className="text-sm text-gray-500">
            Personalised week-by-week plan backed by real interview data
          </p>
        </div>
      </div>

      {/* Form */}
      <form onSubmit={handleGenerate} className="card space-y-5 max-w-2xl">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Company */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Target Company</label>
            <select
              value={company}
              onChange={(e) => setCompany(e.target.value)}
              required
              className="input-field"
            >
              <option value="">Select company…</option>
              {COMPANIES.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
            {company === "Other" && (
              <input
                type="text"
                value={customCo}
                onChange={(e) => setCustomCo(e.target.value)}
                placeholder="Enter company name"
                className="input-field mt-2"
                required
              />
            )}
          </div>

          {/* Role */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Target Role</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              required
              className="input-field"
            >
              <option value="">Select role…</option>
              {ROLES.map((r) => (
                <option key={r} value={r}>{r}</option>
              ))}
            </select>
          </div>

          {/* Weeks */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">
              Time Available — <span className="text-blue-600">{weeks} weeks</span>
            </label>
            <input
              type="range"
              min={1}
              max={24}
              value={weeks}
              onChange={(e) => setWeeks(Number(e.target.value))}
              className="w-full accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-0.5">
              <span>1 week</span><span>12 weeks</span><span>24 weeks</span>
            </div>
          </div>

          {/* Experience */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1.5">Experience Level</label>
            <div className="space-y-2">
              {EXPERIENCE_LEVELS.map(({ value, label, desc }) => (
                <label
                  key={value}
                  className={clsx(
                    "flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors",
                    expLevel === value
                      ? "border-blue-400 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300"
                  )}
                >
                  <input
                    type="radio"
                    name="exp"
                    value={value}
                    checked={expLevel === value}
                    onChange={() => setExpLevel(value)}
                    className="mt-0.5 accent-blue-600"
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-800">{label}</p>
                    <p className="text-xs text-gray-500">{desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full justify-center py-3">
          {loading
            ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating your roadmap…</>
            : <><Map className="w-4 h-4" /> Generate Roadmap</>
          }
        </button>
      </form>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {error}
        </div>
      )}

      {/* Roadmap results */}
      {roadmap && (
        <div id="roadmap-result" className="space-y-6">
          {/* Summary */}
          <div className="card bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">
                  {roadmap.company} — {roadmap.role}
                </h2>
                <p className="text-sm text-gray-600 mt-1 capitalize">
                  {roadmap.experience_level} · {roadmap.weeks}-week plan
                </p>
              </div>
              {roadmap.data_source_count > 0 && (
                <div className="flex items-center gap-1.5 text-xs text-blue-700 bg-blue-100 px-3 py-1.5 rounded-full">
                  <Database className="w-3.5 h-3.5" />
                  Based on {roadmap.data_source_count} real interview reports
                </div>
              )}
            </div>

            {/* LLM advice */}
            {roadmap.llm_advice && (
              <div className="mt-4 flex gap-3 bg-white/70 rounded-xl p-4 border border-blue-100">
                <Lightbulb className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
                <p className="text-sm text-gray-700 italic">{roadmap.llm_advice}</p>
              </div>
            )}
          </div>

          {/* Top topics */}
          {roadmap.top_topics && roadmap.top_topics.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-3">
                Most Critical Topics for {roadmap.company}
              </h3>
              <div className="flex flex-wrap gap-2">
                {roadmap.top_topics.map((t, i) => (
                  <span
                    key={t}
                    className={clsx(
                      "inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium",
                      i === 0 ? "bg-blue-600 text-white" :
                      i <= 2  ? "bg-blue-100 text-blue-800" :
                                "bg-gray-100 text-gray-700"
                    )}
                  >
                    {i < 3 && <span className="text-xs">#{i + 1}</span>}
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Week-by-week plan */}
          <div>
            <h3 className="font-semibold text-gray-900 mb-4">
              Week-by-Week Study Plan
            </h3>
            <div className="space-y-3">
              {roadmap.week_plan.map((plan, idx) => (
                <WeekCard key={plan.week} plan={plan} index={idx} />
              ))}
            </div>
          </div>

          {/* Top questions */}
          {roadmap.top_questions && roadmap.top_questions.length > 0 && (
            <div className="card">
              <h3 className="font-semibold text-gray-900 mb-3">
                Most Asked Questions at {roadmap.company}
              </h3>
              <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {roadmap.top_questions.map((q) => (
                  <li key={q} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0" />
                    {q}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
