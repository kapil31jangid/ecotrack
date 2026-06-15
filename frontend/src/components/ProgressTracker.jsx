import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import { Leaf, TrendingDown, TrendingUp, Calendar, RefreshCw } from "lucide-react";

export default function ProgressTracker({ history, onNavigateToCalculate }) {
  // 1. Log today check
  const loggedToday = useMemo(() => {
    const today = new Date().toDateString();
    return history.some((h) => {
      if (!h.timestamp) return false;
      return new Date(h.timestamp).toDateString() === today;
    });
  }, [history]);

  // 2. Trend indicators
  const trend = useMemo(() => {
    if (history.length < 2) return null;
    const first = history[0].co2e_monthly;
    const last = history[history.length - 1].co2e_monthly;
    const pctDiff = ((last - first) / first) * 100;
    return {
      percent: Math.abs(round(pctDiff, 1)),
      direction: pctDiff > 0 ? "increased" : pctDiff < 0 ? "decreased" : "stable",
      isPositive: pctDiff <= 0, // decrease or stable is good
    };
  }, [history]);

  function round(num, decimals) {
    const t = Math.pow(10, decimals);
    return Math.round(num * t) / t;
  }

  // 3. Format history logs for Recharts
  const chartData = useMemo(() => {
    return history.map((h, index) => {
      const dateLabel = h.timestamp
        ? new Date(h.timestamp).toLocaleDateString(undefined, {
            month: "short",
            day: "numeric",
          })
        : `Log ${index + 1}`;
      return {
        index: index + 1,
        date: dateLabel,
        Emissions: h.co2e_monthly,
      };
    });
  }, [history]);

  // 4. Empty State template
  if (history.length === 0) {
    return (
      <div className="bg-white p-12 rounded-3xl border border-green-500/10 shadow-xl glow-card text-center max-w-lg mx-auto flex flex-col items-center justify-center space-y-6 animate-fade-in">
        <div className="bg-surface p-6 rounded-full text-primary shadow-sm border border-green-100">
          <Leaf className="h-12 w-12 animate-pulse" />
        </div>
        <div>
          <h3 className="text-xl font-bold text-primary-dark">No Footprint Logs Yet</h3>
          <p className="text-sm text-gray-500 mt-2 max-w-sm leading-relaxed">
            Record your emissions today to start tracking carbon savings, progress histories, and unlock sustainable achievement badges.
          </p>
        </div>
        <button
          onClick={onNavigateToCalculate}
          className="bg-primary hover:bg-primary-dark text-white px-6 py-3 rounded-xl font-semibold shadow-sm hover:shadow-md transition-all duration-200 text-sm focus:outline-none"
        >
          Calculate Footprint
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white p-8 rounded-3xl border border-green-500/10 shadow-xl glow-card space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">
        <div>
          <h3 className="text-lg font-bold text-primary-dark">Progress History</h3>
          <p className="text-xs text-gray-500">Track carbon savings over multiple calculations</p>
        </div>
        <button
          onClick={onNavigateToCalculate}
          disabled={loggedToday}
          className="flex items-center space-x-2 text-xs font-semibold px-4 py-2.5 bg-primary text-white hover:bg-primary-dark rounded-xl shadow-sm hover:shadow transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none"
        >
          <Calendar className="h-3.5 w-3.5" />
          <span>{loggedToday ? "Logged Today" : "Log Today"}</span>
        </button>
      </div>

      {/* Trend Summary Notification */}
      {trend && (
        <div
          className={`p-4 border rounded-2xl flex items-center space-x-3.5 ${
            trend.isPositive
              ? "bg-green-50/70 border-green-500/10 text-green-800"
              : "bg-red-50/70 border-red-500/10 text-red-800"
          }`}
        >
          {trend.isPositive ? (
            <TrendingDown className="h-5 w-5 flex-shrink-0" />
          ) : (
            <TrendingUp className="h-5 w-5 flex-shrink-0" />
          )}
          <span className="text-xs font-semibold">
            {trend.direction === "stable"
              ? `Your footprint remained stable over ${history.length} audits.`
              : `Your footprint ${trend.direction} by ${trend.percent}% over the last ${history.length} calculations.`}{" "}
            {trend.isPositive
              ? "Awesome progress! Keep implementing the action checklist."
              : "Analyze your shopping or diet levels to search for additional reductions."}
          </span>
        </div>
      )}

      {/* Recharts line graph */}
      <div className="w-full h-[260px] pr-2" role="region" aria-label="Line chart showing carbon footprint progress over time">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 10, right: 10, left: -10, bottom: 5 }}>
            <XAxis dataKey="date" stroke="#052e16" fontSize={11} tickLine={false} />
            <YAxis stroke="#052e16" fontSize={11} tickLine={false} />
            <Tooltip
              formatter={(value) => [`${value} kg`, "Emissions"]}
              contentStyle={{ borderRadius: "12px", border: "1px solid rgba(22, 163, 74, 0.12)" }}
            />
            {/* National/global benchmarks comparison references */}
            <ReferenceLine
              y={150}
              stroke="#16a34a"
              strokeDasharray="4 4"
              label={{
                value: "India Avg (150)",
                fill: "#16a34a",
                fontSize: 9,
                position: "insideBottomRight",
                dy: -2,
              }}
            />
            <ReferenceLine
              y={333}
              stroke="#94a3b8"
              strokeDasharray="4 4"
              label={{
                value: "Global Avg (333)",
                fill: "#64748b",
                fontSize: 9,
                position: "insideTopRight",
                dy: 2,
              }}
            />
            <Line
              type="monotone"
              dataKey="Emissions"
              stroke="#16a34a"
              strokeWidth={3.5}
              dot={{ stroke: "#16a34a", strokeWidth: 2, r: 4, fill: "#fff" }}
              activeDot={{ r: 7, stroke: "#14532d", strokeWidth: 1.5 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
