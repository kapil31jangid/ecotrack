import React, { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { Milestone, Trophy, Info } from "lucide-react";

export default function Benchmark({ result }) {
  if (!result) return null;

  const { co2e_monthly, co2e_annual } = result;

  // Real-world equivalency calculations
  const carKm = Math.round(co2e_monthly / 0.21);
  const treeOffset = Math.round(co2e_monthly / 1.67); // roughly 1.67 kg per tree per month (20kg/year)

  // Recharts dual monthly/annual comparisons
  const data = [
    {
      name: "Monthly Emissions (kg CO2e)",
      User: co2e_monthly,
      "India Avg": 150.0,
      "Global Avg": 333.0,
    },
    {
      name: "Annual Emissions (kg CO2e)",
      User: co2e_annual,
      "India Avg": 150.0 * 12,
      "Global Avg": 333.0 * 12,
    },
  ];

  // Tailored encouragement copywriting
  const message = useMemo(() => {
    if (co2e_monthly < 150.0) {
      return {
        title: "Eco Champion! 🏆",
        text: "Incredible! Your carbon footprint is below the India national average. You're paving the way for a highly sustainable future.",
        style: "bg-green-50 border-green-500/10 text-green-800",
      };
    } else if (co2e_monthly < 333.0) {
      return {
        title: "Sustainably Minded! 💚",
        text: "Well done! Your emissions are lower than the global average. You're in a great position to challenge yourself and align with India's national baseline.",
        style: "bg-amber-50/50 border-amber-500/10 text-amber-800",
      };
    } else {
      return {
        title: "Starting the Journey! 🌱",
        text: "Your carbon footprint is currently above global averages. Don't worry—small, consistent lifestyle changes will stack up over time! Try starting with easy local public transport habits.",
        style: "bg-red-50/50 border-red-500/10 text-red-800",
      };
    }
  }, [co2e_monthly]);

  return (
    <div className="bg-white p-8 rounded-3xl border border-green-500/10 shadow-xl glow-card space-y-8 animate-fade-in">
      <div>
        <h3 className="text-lg font-bold text-primary-dark">Global & Regional Benchmarking</h3>
        <p className="text-xs text-gray-500">Compare your ratings to regional baselines</p>
      </div>

      {/* Recharts comparison bar graph */}
      <div className="w-full h-[280px]" role="region" aria-label="Carbon footprint comparisons against India and global averages">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 5 }}>
            <XAxis dataKey="name" stroke="#052e16" fontSize={11} tickLine={false} />
            <YAxis stroke="#052e16" fontSize={11} tickLine={false} />
            <Tooltip
              contentStyle={{ borderRadius: "12px", border: "1px solid rgba(22, 163, 74, 0.12)" }}
            />
            <Legend verticalAlign="top" height={36} iconType="circle" wrapperStyle={{ fontSize: "11px" }} />
            <Bar dataKey="User" fill="#16a34a" radius={[6, 6, 0, 0]} />
            <Bar dataKey="India Avg" fill="#86efac" radius={[6, 6, 0, 0]} />
            <Bar dataKey="Global Avg" fill="#94a3b8" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Motivation Banner */}
      <div className={`p-5 border rounded-2xl flex items-start space-x-3.5 ${message.style}`}>
        <Trophy className="h-5 w-5 mt-0.5 flex-shrink-0" />
        <div>
          <h4 className="text-sm font-bold">{message.title}</h4>
          <p className="text-xs mt-1 leading-relaxed">{message.text}</p>
        </div>
      </div>

      {/* Real-world equivalents grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        
        {/* Equivalent Car Drive */}
        <div className="border border-green-500/10 p-5 rounded-2xl flex items-center space-x-4 bg-surface/30">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-xl">
            <Milestone className="h-6 w-6" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400">Equivalent Car Trip</span>
            <div className="text-lg font-extrabold text-primary-dark">≈ {carKm} km</div>
            <p className="text-[10px] text-gray-500 mt-0.5">driving in a standard petrol passenger car</p>
          </div>
        </div>

        {/* Equivalent Forest Absorption */}
        <div className="border border-green-500/10 p-5 rounded-2xl flex items-center space-x-4 bg-surface/30">
          <div className="p-3 bg-green-100 text-green-600 rounded-xl">
            <Info className="h-6 w-6" />
          </div>
          <div>
            <span className="text-[10px] uppercase font-bold text-gray-400">Forest Impact</span>
            <div className="text-lg font-extrabold text-primary-dark">≈ {treeOffset} trees</div>
            <p className="text-[10px] text-gray-500 mt-0.5">needed to offset your monthly emissions</p>
          </div>
        </div>
      </div>
    </div>
  );
}
