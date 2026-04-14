"use client";

import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { getAnalytics } from "@/lib/api";
import type { AnalyticsData } from "@/types";
import { BarChart2, AlertCircle, Loader2 } from "lucide-react";

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#06b6d4", "#f97316", "#84cc16", "#ec4899", "#6366f1",
];

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="card text-center">
      <div className="text-3xl font-bold text-blue-600">{value}</div>
      <div className="text-sm text-gray-500 mt-1">{label}</div>
    </div>
  );
}

export default function AnalyticsPage() {
  const [data,    setData]    = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState<string | null>(null);

  useEffect(() => {
    getAnalytics()
      .then(setData)
      .catch(() => setError("Failed to load analytics. Is the backend running?"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-64 text-gray-400">
        <Loader2 className="w-6 h-6 animate-spin mr-2" />
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <AlertCircle className="w-5 h-5 shrink-0" />
        {error}
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-8">
      <div className="flex items-center gap-3">
        <BarChart2 className="w-6 h-6 text-blue-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="text-sm text-gray-500">Aggregated insights from interview data</p>
        </div>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatCard label="Total Interviews"   value={data.total_interviews} />
        <StatCard label="Companies"          value={data.companies?.length ?? 0} />
        <StatCard label="Topics Tracked"     value={data.topics?.length ?? 0} />
        <StatCard
          label="Offer Rate"
          value={
            (() => {
              const offered  = data.offer_status?.find((o) => o.name === "offered")?.count ?? 0;
              const total    = data.total_interviews || 1;
              return `${Math.round((offered / total) * 100)}%`;
            })()
          }
        />
      </div>

      {/* Top companies */}
      {data.companies && data.companies.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Top Companies by Interview Volume</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart
              data={data.companies.slice(0, 15)}
              layout="vertical"
              margin={{ left: 10, right: 20, top: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis
                dataKey="name"
                type="category"
                width={100}
                tick={{ fontSize: 12 }}
              />
              <Tooltip />
              <Bar dataKey="count" fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Offer status */}
        {data.offer_status && data.offer_status.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Offer Status Distribution</h2>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={data.offer_status}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                >
                  {data.offer_status.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend formatter={(v) => <span className="text-sm">{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Round type distribution */}
        {data.round_type_distribution && data.round_type_distribution.length > 0 && (
          <div className="card">
            <h2 className="font-semibold text-gray-900 mb-4">Interview Round Types</h2>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie
                  data={data.round_type_distribution}
                  dataKey="count"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={3}
                >
                  {data.round_type_distribution.map((_, idx) => (
                    <Cell key={idx} fill={COLORS[(idx + 4) % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend formatter={(v) => <span className="text-sm">{v}</span>} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Top topics */}
      {data.topics && data.topics.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Most Frequent Interview Topics</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={data.topics.slice(0, 20)}
              margin={{ left: 0, right: 10, top: 0, bottom: 60 }}
            >
              <XAxis
                dataKey="name"
                tick={{ fontSize: 11 }}
                interval={0}
                angle={-35}
                textAnchor="end"
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                {data.topics.slice(0, 20).map((_, idx) => (
                  <Cell key={idx} fill={COLORS[idx % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Top roles */}
      {data.roles && data.roles.length > 0 && (
        <div className="card">
          <h2 className="font-semibold text-gray-900 mb-4">Top Roles</h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={data.roles.slice(0, 12)}
              layout="vertical"
              margin={{ left: 10, right: 20, top: 0, bottom: 0 }}
            >
              <XAxis type="number" tick={{ fontSize: 12 }} />
              <YAxis dataKey="name" type="category" width={160} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="count" fill="#10b981" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
