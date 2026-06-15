import React, { useState, useEffect } from "react";
import Layout from "./components/Layout";
import Calculator from "./components/Calculator";
import Dashboard from "./components/Dashboard";
import Benchmark from "./components/Benchmark";
import ProgressTracker from "./components/ProgressTracker";
import BadgeSystem from "./components/BadgeSystem";
import AiChat from "./components/AiChat";
import { useFootprint } from "./hooks/useFootprint";
import { AlertTriangle, Award } from "lucide-react";

export default function App() {
  const {
    sessionId,
    footprintResult,
    history,
    chatMessages,
    doneTips,
    badges,
    toasts,
    isCalculating,
    isChatLoading,
    error,
    calculate,
    sendChat,
    markTipDone,
    clearError,
    removeToast,
  } = useFootprint();

  const [activeTab, setActiveTab] = useState("calculate");

  // Automatically direct user to dashboard after calculation
  const handleCalculate = async (formData) => {
    try {
      await calculate(formData);
      setActiveTab("dashboard");
    } catch (err) {
      console.error(err);
    }
  };

  const showDashboardLink = history.length >= 1;
  const showAiChat = history.length >= 1;

  // Protect tabs navigation if no history exists yet
  useEffect(() => {
    if (activeTab === "dashboard" && !showDashboardLink) {
      setActiveTab("calculate");
    }
  }, [activeTab, showDashboardLink]);

  return (
    <Layout
      activeTab={activeTab}
      setActiveTab={setActiveTab}
      showDashboardLink={showDashboardLink}
    >
      {/* 1. Global error banner */}
      {error && (
        <div className="mb-6 p-4 bg-danger/10 border border-danger/25 text-danger rounded-2xl flex items-center justify-between text-xs font-semibold glow-card">
          <div className="flex items-center space-x-2">
            <AlertTriangle className="h-4.5 w-4.5 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={clearError}
            className="underline uppercase tracking-wider text-[10px] font-bold focus:outline-none"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* 2. Tab Routing views */}
      <div className="space-y-8">
        {activeTab === "calculate" && (
          <Calculator
            onCalculate={handleCalculate}
            isCalculating={isCalculating}
            error={error}
            clearError={clearError}
          />
        )}

        {activeTab === "dashboard" && footprintResult && (
          <div className="space-y-8">
            <Dashboard
              result={footprintResult}
              doneTips={doneTips}
              onMarkTipDone={markTipDone}
            />
            <Benchmark result={footprintResult} />
          </div>
        )}

        {activeTab === "progress" && (
          <ProgressTracker
            history={history}
            onNavigateToCalculate={() => setActiveTab("calculate")}
          />
        )}

        {activeTab === "badges" && (
          <BadgeSystem badges={badges} />
        )}
      </div>

      {/* 3. Floating AI Chat Widget */}
      {showAiChat && (
        <AiChat
          chatMessages={chatMessages}
          onSendMessage={sendChat}
          isChatLoading={isChatLoading}
          error={error}
          clearError={clearError}
        />
      )}

      {/* 4. Sliding Badge Unlocks Toast Notifier (Bottom Left) */}
      <div className="fixed bottom-6 left-6 z-50 flex flex-col space-y-3 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className="bg-primary text-white border border-primary-light/25 px-5 py-4 rounded-3xl shadow-2xl flex items-center space-x-3.5 pointer-events-auto transform translate-y-0 transition-transform duration-300 animate-slide-up"
            style={{
              animation: "slideUpToast 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards",
            }}
          >
            <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-xl">
              {toast.icon}
            </div>
            <div>
              <div className="text-[9px] uppercase font-bold tracking-widest text-primary-light/90">
                Milestone Reached!
              </div>
              <div className="text-xs font-extrabold mt-0.5">{toast.name}</div>
            </div>
          </div>
        ))}
      </div>

      {/* Slide up animation styles */}
      <style>{`
        @keyframes slideUpToast {
          0% { transform: translateY(40px); opacity: 0; }
          100% { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </Layout>
  );
}
