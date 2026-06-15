import React from "react";
import { Lock, CheckCircle2 } from "lucide-react";

export default function BadgeSystem({ badges }) {
  return (
    <div className="bg-white p-8 rounded-3xl border border-green-500/10 shadow-xl glow-card space-y-8 animate-fade-in">
      <div>
        <h3 className="text-lg font-bold text-primary-dark">Sustainability Achievements</h3>
        <p className="text-xs text-gray-500">Milestones earned on your path to green living</p>
      </div>

      {/* Badges Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {badges.map((badge) => {
          const isEarned = badge.earned;

          return (
            <div
              key={badge.id}
              className={`p-6 border rounded-3xl flex flex-col items-center text-center relative overflow-hidden transition-all duration-300 ${
                isEarned
                  ? "bg-surface/50 border-primary-light/50 shadow-md glow-card"
                  : "bg-gray-50/50 border-gray-100 opacity-60"
              }`}
            >
              {/* Earned Checklist / Locked indicators */}
              {isEarned ? (
                <div className="absolute top-4 right-4 text-primary bg-primary-light/25 p-1 rounded-full border border-primary-light/45">
                  <CheckCircle2 className="h-4.5 w-4.5" />
                </div>
              ) : (
                <div className="absolute top-4 right-4 text-gray-300">
                  <Lock className="h-4.5 w-4.5" />
                </div>
              )}

              {/* Badge Icon Emblem */}
              <div
                className={`w-16 h-16 rounded-full flex items-center justify-center text-3xl mb-4 transition-all duration-300 ${
                  isEarned
                    ? "bg-white glow-primary text-glow scale-105"
                    : "bg-gray-100 grayscale"
                }`}
              >
                {badge.icon}
              </div>

              {/* Badge Text Details */}
              <h4 className={`text-sm font-bold ${isEarned ? "text-primary-dark" : "text-gray-500"}`}>
                {badge.name}
              </h4>
              <p className="text-[11px] text-gray-500 mt-2 max-w-[180px] leading-relaxed">
                {badge.hint}
              </p>

              {/* Status Message */}
              <div className="mt-4 pt-3 border-t border-dashed border-gray-200/60 w-full">
                {isEarned ? (
                  <span className="text-[9px] uppercase tracking-wider font-extrabold text-primary">
                    Achieved ✓
                  </span>
                ) : (
                  <span className="text-[9px] uppercase tracking-wider font-extrabold text-gray-400">
                    Locked
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
