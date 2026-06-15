import { useState, useEffect, useMemo } from "react";
import { v4 as uuidv4 } from "uuid";
import { calculateFootprint, sendChat, getHistory } from "../api/client";

export function useFootprint() {
  // 1. Session ID hydration
  const [sessionId] = useState(() => {
    let sid = localStorage.getItem("ecotrack_session_id");
    if (!sid) {
      sid = uuidv4();
      localStorage.setItem("ecotrack_session_id", sid);
    }
    return sid;
  });

  // 2. Core states
  const [history, setHistory] = useState(() => {
    try {
      const stored = localStorage.getItem("ecotrack_history");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [doneTips, setDoneTips] = useState(() => {
    try {
      const stored = localStorage.getItem("ecotrack_tips_done");
      return stored ? new Set(JSON.parse(stored)) : new Set();
    } catch {
      return new Set();
    }
  });

  const [chatMessages, setChatMessages] = useState(() => {
    try {
      const stored = localStorage.getItem("ecotrack_chat");
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });

  const [toasts, setToasts] = useState([]);
  const [isCalculating, setIsCalculating] = useState(false);
  const [isChatLoading, setIsChatLoading] = useState(false);
  const [error, setError] = useState(null);

  // Latest calculated result
  const footprintResult = useMemo(() => {
    if (history.length === 0) return null;
    // Return the latest log
    return history[history.length - 1];
  }, [history]);

  // Sync state changes with localStorage
  useEffect(() => {
    localStorage.setItem("ecotrack_history", JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    localStorage.setItem("ecotrack_tips_done", JSON.stringify(Array.from(doneTips)));
  }, [doneTips]);

  useEffect(() => {
    localStorage.setItem("ecotrack_chat", JSON.stringify(chatMessages));
  }, [chatMessages]);

  // Proactive DB sync on mount
  useEffect(() => {
    let active = true;
    async function syncHistory() {
      try {
        const remoteHistory = await getHistory(sessionId);
        if (active && remoteHistory && remoteHistory.length > 0) {
          // Map to match structure of calculated logs
          const normalized = remoteHistory.map(h => ({
            co2e_monthly: h.co2e_monthly,
            co2e_annual: h.co2e_annual,
            category_breakdown: h.category_breakdown,
            tips: h.tips,
            vs_global: h.vs_global,
            vs_india: h.vs_india,
            timestamp: h.timestamp,
            session_id: h.session_id
          }));
          setHistory(normalized);
        }
      } catch (err) {
        console.error("Failed to sync footprint history with Firestore:", err);
      }
    }
    syncHistory();
    return () => {
      active = false;
    };
  }, [sessionId]);

  // 3. Computed badge milestones
  const badges = useMemo(() => {
    return [
      {
        id: "first_step",
        name: "First Step",
        earned: history.length >= 1,
        hint: "Log your carbon footprint for the first time",
        icon: "🌱",
      },
      {
        id: "action_taker",
        name: "Action Taker",
        earned: doneTips.size >= 3,
        hint: "Commit to at least 3 carbon reduction tips",
        icon: "✅",
      },
      {
        id: "consistent",
        name: "Consistent",
        earned: history.length >= 3,
        hint: "Record your emissions logs at least 3 times",
        icon: "📅",
      },
      {
        id: "green_starter",
        name: "Green Starter",
        earned: history.some((h) => h.co2e_monthly < 200),
        hint: "Reach a monthly footprint rating below 200 kg CO2e",
        icon: "💚",
      },
      {
        id: "eco_warrior",
        name: "Eco Warrior",
        earned: history.some((h) => h.co2e_monthly < 100),
        hint: "Lower your monthly emissions below 100 kg CO2e",
        icon: "🏆",
      },
      {
        id: "india_champ",
        name: "India Champion",
        earned: history.some((h) => h.co2e_monthly < 150),
        hint: "Keep your emissions below the India national average (150 kg)",
        icon: "🇮🇳",
      },
    ];
  }, [history, doneTips]);

  // Toast notifier for new badge unlocking
  useEffect(() => {
    let earnedBadges = [];
    try {
      const stored = localStorage.getItem("ecotrack_earned_badges");
      earnedBadges = stored ? JSON.parse(stored) : [];
    } catch {
      earnedBadges = [];
    }

    const currentEarned = badges.filter((b) => b.earned).map((b) => b.id);
    const newlyEarned = currentEarned.filter((id) => !earnedBadges.includes(id));

    if (newlyEarned.length > 0) {
      newlyEarned.forEach((badgeId) => {
        const badgeObj = badges.find((b) => b.id === badgeId);
        if (badgeObj) {
          const toastId = uuidv4();
          setToasts((t) => [...t, { id: toastId, name: badgeObj.name, icon: badgeObj.icon }]);
          // Auto dismiss toast after 3 seconds
          setTimeout(() => {
            setToasts((t) => t.filter((toast) => toast.id !== toastId));
          }, 3000);
        }
      });
      localStorage.setItem("ecotrack_earned_badges", JSON.stringify(currentEarned));
    }
  }, [badges]);

  // 4. API Operations
  const calculate = async (formData) => {
    setIsCalculating(true);
    setError(null);
    try {
      const payload = {
        session_id: sessionId,
        transport_mode: formData.transport_mode,
        transport_km_per_week: parseFloat(formData.transport_km_per_week),
        diet_type: formData.diet_type,
        energy_kwh_per_month: parseFloat(formData.energy_kwh_per_month),
        shopping_level: formData.shopping_level,
      };
      const result = await calculateFootprint(payload);
      
      // Append new log to history state
      setHistory((prev) => [...prev, result]);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setIsCalculating(false);
    }
  };

  const sendChatMessage = async (messageText) => {
    if (!messageText.trim()) return;
    
    // Add user message to display chat state
    const userMsg = {
      id: uuidv4(),
      role: "user",
      content: messageText,
      timestamp: new Date().toISOString(),
    };
    
    setChatMessages((prev) => [...prev, userMsg]);
    setIsChatLoading(true);
    setError(null);
    
    try {
      // Package active carbon context for Gemini personalization
      const context = footprintResult
        ? {
            co2e_monthly: footprintResult.co2e_monthly,
            category_breakdown: footprintResult.category_breakdown,
            vs_global: footprintResult.vs_global,
            vs_india: footprintResult.vs_india,
          }
        : null;

      const replyData = await sendChat({
        message: messageText,
        session_id: sessionId,
        footprint_context: context,
      });

      const aiMsg = {
        id: uuidv4(),
        role: "model",
        content: replyData.reply,
        model_used: replyData.model_used,
        timestamp: new Date().toISOString(),
      };

      setChatMessages((prev) => [...prev, aiMsg]);
    } catch (err) {
      setError(`Gemini chat error: ${err.message}`);
      // Return a special flag so components know it failed
      throw err;
    } finally {
      setIsChatLoading(false);
    }
  };

  const markTipDone = (actionTitle) => {
    setDoneTips((prev) => {
      const next = new Set(prev);
      if (next.has(actionTitle)) {
        next.delete(actionTitle);
      } else {
        next.add(actionTitle);
      }
      return next;
    });
  };

  const clearError = () => setError(null);

  const removeToast = (id) => {
    setToasts((t) => t.filter((toast) => toast.id !== id));
  };

  return {
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
    sendChat: sendChatMessage,
    markTipDone,
    clearError,
    removeToast,
  };
}
