import React, { useState } from "react";
import { Copy, CheckSquare, Award, ArrowUpRight, CheckCircle2 } from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getFootprintLabel } from "../utils/emissions";

export default function Dashboard({ result, doneTips, onMarkTipDone }) {
  const [copySuccess, setCopySuccess] = useState(false);
  const [confettiActive, setConfettiActive] = useState(false);
  const [confettiCoords, setConfettiCoords] = useState({ x: 0, y: 0 });

  if (!result) return null;

  const {
    co2e_monthly,
    co2e_annual,
    category_breakdown: breakdown,
    tips,
    vs_global,
    vs_india,
  } = result;

  const labelData = getFootprintLabel(co2e_monthly);

  // SVG Gauge computation
  const MAX_GAUGE_CO2 = 600;
  const pct = Math.min(co2e_monthly / MAX_GAUGE_CO2, 1);
  const needleAngle = 180 + pct * 180; // maps 0-100% to 180-360 deg (top half semi-circle)

  // Recharts horizontal BarChart data
  const chartData = [
    {
      name: "Transport",
      value: breakdown.transport,
      pct: Math.round((breakdown.transport / co2e_monthly) * 100) || 0,
      fill: "#3b82f6",
    },
    {
      name: "Diet",
      value: breakdown.diet,
      pct: Math.round((breakdown.diet / co2e_monthly) * 100) || 0,
      fill: "#16a34a",
    },
    {
      name: "Energy",
      value: breakdown.energy,
      pct: Math.round((breakdown.energy / co2e_monthly) * 100) || 0,
      fill: "#f59e0b",
    },
    {
      name: "Shopping",
      value: breakdown.shopping,
      pct: Math.round((breakdown.shopping / co2e_monthly) * 100) || 0,
      fill: "#a855f7",
    },
  ];

  const handleCopy = async () => {
    const textToCopy = `My Carbon Footprint: ${co2e_monthly} kg CO2e/month (${co2e_annual} kg/year). Rated: ${labelData.label}. Track yours on EcoTrack!`;
    try {
      await navigator.clipboard.writeText(textToCopy);
      setCopySuccess(true);
      setTimeout(() => setCopySuccess(false), 2000);
    } catch (err) {
      console.error("Failed to copy footprint results", err);
    }
  };

  const triggerConfetti = (e) => {
    const rect = e.target.getBoundingClientRect();
    setConfettiCoords({
      x: rect.left + rect.width / 2 + window.scrollX,
      y: rect.top + rect.height / 2 + window.scrollY,
    });
    setConfettiActive(true);
    setTimeout(() => setConfettiActive(false), 800);
  };

  const handleTipToggle = (e, action) => {
    const checked = e.target.checked;
    onMarkTipDone(action);
    if (checked) {
      triggerConfetti(e);
    }
  };

  return (
    <div className="space-y-8 animate-fade-in relative">
      {/* Visual Lightweight Confetti Effect */}
      {confettiActive && (
        <div
          className="pointer-events-none fixed z-50 flex items-center justify-center"
          style={{ left: `${confettiCoords.x}px`, top: `${confettiCoords.y}px` }}
        >
          {[...Array(16)].map((_, i) => {
            const angle = (i * 360) / 16;
            const distance = 40 + Math.random() * 40;
            const delay = Math.random() * 0.1;
            const color = ["#16a34a", "#86efac", "#f59e0b", "#3b82f6", "#a855f7"][i % 5];
            return (
              <div
                key={i}
                className="absolute w-2 h-2 rounded-full animate-ping"
                style={{
                  backgroundColor: color,
                  transform: `rotate(${angle}deg) translate(${distance}px)`,
                  transition: `all 0.6s ease-out ${delay}s`,
                  opacity: 0,
                  animation: `confettiPop 0.8s ease-out forwards`,
                }}
              />
            );
          })}
          <style>{`
            @keyframes confettiPop {
              0% { transform: scale(0) translate(0px, 0px); opacity: 1; }
              100% { opacity: 0; }
            }
          `}</style>
        </div>
      )}

      {/* Main Score Board */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* SVG Arc Gauge */}
        <div className="bg-white p-6 rounded-3xl border border-green-500/10 shadow-xl glow-card flex flex-col items-center justify-between text-center relative overflow-hidden">
          <h3 className="text-sm font-bold uppercase tracking-wider text-gray-500">Your Monthly Rating</h3>
          
          <div className="w-full max-w-[200px] h-[120px] relative mt-4">
            <svg viewBox="0 0 200 110" className="w-full h-full">
              <defs>
                <linearGradient id="gaugeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                  <stop offset="0%" stopColor="#16a34a" />
                  <stop offset="35%" stopColor="#f59e0b" />
                  <stop offset="70%" stopColor="#f97316" />
                  <stop offset="100%" stopColor="#ef4444" />
                </linearGradient>
              </defs>
              {/* Outer gauge track */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="#e2e8f0"
                strokeWidth="12"
                strokeLinecap="round"
              />
              {/* Highlight gauge track */}
              <path
                d="M 20 100 A 80 80 0 0 1 180 100"
                fill="none"
                stroke="url(#gaugeGradient)"
                strokeWidth="12"
                strokeLinecap="round"
                opacity="0.85"
              />
              {/* Needle Indicator */}
              <g transform={`rotate(${needleAngle} 100 100)`}>
                <line
                  x1="100"
                  y1="100"
                  x2="25"
                  y2="100"
                  stroke="#052e16"
                  strokeWidth="3.5"
                  strokeLinecap="round"
                  className="transition-transform duration-1000 ease-out"
                />
                <circle cx="100" cy="100" r="6" fill="#052e16" />
              </g>
            </svg>

            {/* Float values */}
            <div className="absolute inset-x-0 bottom-0 flex flex-col items-center justify-center">
              <span className="text-3xl font-display font-extrabold text-primary-dark">
                {co2e_monthly}
              </span>
              <span className="text-[10px] uppercase font-bold text-gray-400">kg CO2e/mo</span>
            </div>
          </div>

          <div className="mt-4">
            <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-extrabold tracking-wider uppercase bg-surface ${labelData.color}`}>
              {labelData.label}
            </span>
            <div className="text-xs text-gray-500 mt-2 space-y-1">
              <p>🌍 {vs_global}</p>
              <p>🇮🇳 {vs_india}</p>
            </div>
          </div>
        </div>

        {/* Categories Emissions Horizontal Bar Chart */}
        <div className="bg-white p-6 rounded-3xl border border-green-500/10 shadow-xl glow-card lg:col-span-2 flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <div>
              <h3 className="text-lg font-bold text-primary-dark">Emissions Breakdown</h3>
              <p className="text-xs text-gray-500">Monthly footprint categories in kg CO2e</p>
            </div>
            <button
              onClick={handleCopy}
              className="flex items-center space-x-2 text-xs font-semibold px-3 py-2 border border-gray-200 rounded-xl hover:bg-gray-50 text-gray-600 transition-colors focus:outline-none relative"
            >
              <Copy className="h-3.5 w-3.5" />
              <span>{copySuccess ? "Copied! ✓" : "Share Score"}</span>
            </button>
          </div>

          <div className="flex-grow w-full min-h-[180px]" role="region" aria-label="Monthly carbon footprint breakdown by category">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={chartData}
                layout="vertical"
                margin={{ top: 0, right: 10, left: -10, bottom: 0 }}
              >
                <XAxis type="number" hide />
                <YAxis dataKey="name" type="category" stroke="#052e16" fontSize={11} width={80} tickLine={false} axisLine={false} />
                <Tooltip
                  formatter={(value) => [`${value} kg CO2e`, "Emissions"]}
                  contentStyle={{ borderRadius: "12px", border: "1px solid rgba(22, 163, 74, 0.12)" }}
                />
                <Bar dataKey="value" barSize={14} radius={[0, 8, 8, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          <div className="grid grid-cols-4 gap-2 border-t border-gray-100 pt-4 text-center mt-2">
            {chartData.map((cat) => (
              <div key={cat.name} className="flex flex-col items-center">
                <span className="text-[10px] font-bold text-gray-500 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full inline-block" style={{ backgroundColor: cat.fill }} />
                  <span>{cat.name}</span>
                </span>
                <span className="text-xs font-extrabold text-primary-dark mt-0.5">{cat.value} kg</span>
                <span className="text-[9px] text-gray-400 font-medium">{cat.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Checklist / Action Center */}
      <div className="bg-white p-8 rounded-3xl border border-green-500/10 shadow-xl glow-card">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h3 className="text-lg font-bold text-primary-dark">Personalized Action Steps</h3>
            <p className="text-xs text-gray-500">
              Check off actions you commit to. These recommendations are tailored to your highest emission source.
            </p>
          </div>
          <span className="text-xs font-bold bg-primary-light/20 text-primary px-3 py-1 rounded-full border border-primary-light/40">
            {doneTips.size} / 5 Done
          </span>
        </div>

        <div className="space-y-4">
          {tips.map((tip) => {
            const isCompleted = doneTips.has(tip.action);
            const difficultyColors = {
              Easy: "bg-green-100 text-green-700",
              Medium: "bg-amber-100 text-amber-700",
              Hard: "bg-red-100 text-red-700",
            };

            return (
              <div
                key={tip.action}
                className={`p-4 border rounded-2xl flex items-start space-x-4 transition-all duration-300 ${
                  isCompleted
                    ? "bg-gray-50/70 border-gray-100 opacity-60 line-through"
                    : "bg-white border-green-500/10 hover:border-primary/20 shadow-sm"
                }`}
              >
                <input
                  type="checkbox"
                  id={`tip-${tip.action}`}
                  checked={isCompleted}
                  onChange={(e) => handleTipToggle(e, tip.action)}
                  className="w-5 h-5 mt-0.5 accent-primary border-gray-300 rounded focus:ring-primary cursor-pointer"
                  aria-label={`Mark tip as completed: ${tip.action}`}
                />
                
                <div className="flex-grow">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                    <label
                      htmlFor={`tip-${tip.action}`}
                      className="font-bold text-sm text-primary-dark cursor-pointer"
                    >
                      {tip.action}
                    </label>
                    
                    <div className="flex items-center space-x-2">
                      <span className={`text-[10px] font-extrabold px-2 py-0.5 rounded-full ${difficultyColors[tip.difficulty]}`}>
                        {tip.difficulty}
                      </span>
                      <span className="text-[10px] font-bold text-primary flex items-center space-x-0.5">
                        <ArrowUpRight className="h-3 w-3" />
                        <span>Save ~{tip.saving_kg} kg/mo</span>
                      </span>
                    </div>
                  </div>
                  <p className="text-[11px] text-gray-500 mt-1 capitalize">
                    Category: {tip.category}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
