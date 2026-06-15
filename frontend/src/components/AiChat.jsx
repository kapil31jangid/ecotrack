import React, { useState, useRef, useEffect } from "react";
import { MessageSquare, Send, X, Leaf, Sparkles, AlertCircle } from "lucide-react";

export default function AiChat({ chatMessages, onSendMessage, isChatLoading, error, clearError }) {
  const [isOpen, setIsOpen] = useState(false);
  const [inputMessage, setInputMessage] = useState("");
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom of chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [chatMessages, isOpen, isChatLoading]);

  const handleSend = async (e) => {
    if (e) e.preventDefault();
    if (!inputMessage.trim() || isChatLoading) return;
    
    const textToSend = inputMessage;
    setInputMessage(""); // Clear early for smooth UX
    
    try {
      await onSendMessage(textToSend);
    } catch (err) {
      // Restore input if message failed
      setInputMessage(textToSend);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Helper mapping response key values to tidy badge labels
  const formatModelBadge = (modelStr) => {
    if (modelStr === "gemini-1.5-flash") return "✦ Gemini 1.5 Flash";
    if (modelStr === "gemini-1.0-pro") return "✦ Gemini 1.0 Pro";
    return modelStr ? `✦ ${modelStr}` : "✦ Gemini AI";
  };

  return (
    <div className="fixed bottom-6 right-6 z-50 font-body">
      {/* 1. Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="bg-primary hover:bg-primary-dark text-white rounded-full p-4 flex items-center space-x-2 shadow-2xl glow-primary transition-all duration-300 hover:scale-105 group focus:outline-none"
          aria-label="Ask Gemini AI coach"
        >
          <MessageSquare className="h-6 w-6 group-hover:rotate-12 transition-transform duration-300" />
          <span className="text-sm font-semibold pr-1">Ask Gemini AI</span>
        </button>
      )}

      {/* 2. Chat Panel */}
      {isOpen && (
        <div className="bg-white rounded-3xl border border-green-500/10 shadow-2xl w-[380px] h-[520px] max-w-[calc(100vw-32px)] max-h-[calc(100vh-48px)] flex flex-col overflow-hidden animate-slide-up">
          
          {/* Header */}
          <div className="bg-gradient-to-r from-primary-dark to-primary p-4 text-white flex items-center justify-between shadow-sm">
            <div className="flex items-center space-x-2.5">
              <div className="bg-white/10 p-1.5 rounded-lg">
                <Leaf className="h-4 w-4" />
              </div>
              <div>
                <h4 className="font-display font-bold text-sm">EcoTrack AI</h4>
                <div className="text-[10px] text-white/70 font-semibold tracking-wide flex items-center space-x-1">
                  <Sparkles className="h-2.5 w-2.5" />
                  <span>Powered by Gemini</span>
                </div>
              </div>
            </div>
            
            <button
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white p-1 rounded-lg hover:bg-white/10 transition-colors focus:outline-none"
              aria-label="Close Chat"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Messages Area */}
          <div
            className="flex-grow p-4 overflow-y-auto space-y-4 bg-surface/20"
            aria-live="polite"
          >
            {/* Welcome message */}
            <div className="flex items-start space-x-2">
              <div className="bg-primary/10 text-primary p-1.5 rounded-lg text-xs mt-1">
                🌱
              </div>
              <div className="bg-white border border-green-500/5 rounded-2xl rounded-tl-none p-3 shadow-sm text-xs text-gray-700 leading-relaxed max-w-[85%]">
                Hi! I'm EcoTrack AI, powered by Google Gemini 🌱 I can answer any sustainability question and analyse your carbon data. What would you like to explore?
              </div>
            </div>

            {/* Suggestion chips — only show when chat is empty */}
            {chatMessages.length === 0 && !isChatLoading && (
              <div className="flex flex-wrap gap-1.5 px-1">
                {[
                  "How can I reduce my energy bill?",
                  "Is an EV worth it?",
                  "Best ways to reduce diet emissions?",
                  "What is a carbon offset?",
                  "How does solar energy work?",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => {
                      setInputMessage(suggestion);
                    }}
                    className="text-[10px] font-semibold px-2.5 py-1 bg-primary/8 border border-primary/20 text-primary rounded-full hover:bg-primary/15 transition-colors focus:outline-none"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            {/* Chat history logs */}
            {chatMessages.map((msg) => {
              const isUser = msg.role === "user";
              return (
                <div
                  key={msg.id}
                  className={`flex ${isUser ? "justify-end" : "justify-start"} items-start space-x-2`}
                >
                  {!isUser && (
                    <div className="bg-primary/10 text-primary p-1.5 rounded-lg text-xs mt-1">
                      ✦
                    </div>
                  )}
                  <div
                    className={`max-w-[85%] rounded-2xl p-3 shadow-sm text-xs leading-relaxed ${
                      isUser
                        ? "bg-primary text-white rounded-tr-none text-right font-medium"
                        : "bg-white border border-green-500/5 text-gray-700 rounded-tl-none text-left"
                    }`}
                  >
                    <div>{msg.content}</div>
                    
                    {/* Model Used Badge */}
                    {!isUser && msg.model_used && (
                      <div className="text-[9px] text-primary/70 font-semibold mt-1.5 tracking-wider uppercase">
                        {formatModelBadge(msg.model_used)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}

            {/* Chat typing bubbles loader */}
            {isChatLoading && (
              <div className="flex justify-start items-center space-x-2">
                <div className="bg-primary/10 text-primary p-1.5 rounded-lg text-xs mt-1">
                  ✦
                </div>
                <div className="bg-white border border-green-500/5 rounded-2xl rounded-tl-none p-3 shadow-sm flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                  <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                </div>
              </div>
            )}

            {/* Error notifications */}
            {error && (
              <div className="bg-danger/5 border border-danger/10 p-3 rounded-xl flex items-start space-x-2 text-danger">
                <AlertCircle className="h-4 w-4 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-[10px] font-bold">Couldn't reach Gemini AI. Please try again.</p>
                  <button
                    onClick={clearError}
                    className="text-[9px] font-extrabold uppercase mt-1 tracking-wider underline block focus:outline-none"
                  >
                    Dismiss
                  </button>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>

          {/* Message Input Footer Form */}
          <form onSubmit={handleSend} className="p-3 bg-white border-t border-gray-100 flex items-end space-x-2">
            <div className="flex-grow relative">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value.slice(0, 1000))}
                onKeyDown={handleKeyDown}
                placeholder="Ask advice on reducing footprint..."
                rows={1}
                className="w-full pl-3 pr-10 py-2.5 border border-gray-200 rounded-2xl focus:outline-none focus:border-primary text-xs resize-none"
                aria-label="Type sustainability message"
                maxLength={1000}
              />
              <span className="absolute right-2.5 bottom-2 text-[8px] font-bold text-gray-400">
                {inputMessage.length}/1000
              </span>
            </div>
            
            <button
              type="submit"
              disabled={!inputMessage.trim() || isChatLoading}
              className="bg-primary hover:bg-primary-dark text-white p-2.5 rounded-2xl shadow disabled:opacity-40 transition-colors focus:outline-none flex-shrink-0"
              aria-label="Send Message"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>

        </div>
      )}
    </div>
  );
}
