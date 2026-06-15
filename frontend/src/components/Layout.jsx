import React, { useState } from "react";
import { Leaf, Menu, X, Calculator, LayoutDashboard, TrendingUp, Award } from "lucide-react";

export default function Layout({ activeTab, setActiveTab, showDashboardLink, children }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems = [
    { id: "calculate", label: "Calculate", icon: Calculator },
    ...(showDashboardLink ? [{ id: "dashboard", label: "Dashboard", icon: LayoutDashboard }] : []),
    { id: "progress", label: "Progress", icon: TrendingUp },
    { id: "badges", label: "Badges", icon: Award },
  ];

  const handleNavClick = (tabId) => {
    setActiveTab(tabId);
    setMobileMenuOpen(false);
  };

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-b from-surface to-white text-dark">
      {/* Header */}
      <header className="sticky top-0 z-40 w-full glass-panel border-b border-green-100 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          {/* Logo & Branding */}
          <div className="flex items-center space-x-3">
            <div className="bg-primary/10 p-2 rounded-xl text-primary glow-card">
              <Leaf className="h-6 w-6" aria-hidden="true" />
            </div>
            <div>
              <span className="font-display font-bold text-xl tracking-tight text-primary-dark">
                EcoTrack
              </span>
              <div className="text-[10px] font-medium text-primary-dark/60 tracking-wider uppercase -mt-1 block">
                Carbon Tracker
              </div>
            </div>
            {/* Subtle "Powered by Google Gemini" Badge */}
            <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-primary-light/20 text-primary border border-primary-light/40">
              Powered by Google Gemini
            </span>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex space-x-1" aria-label="Main navigation">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-primary text-white shadow-sm glow-card"
                      : "text-primary-dark/80 hover:bg-primary/5 hover:text-primary"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>

          {/* Mobile Menu Toggle */}
          <div className="md:hidden">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-xl text-primary-dark/80 hover:bg-primary/5 hover:text-primary focus:outline-none"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
          </div>
        </div>

        {/* Mobile Navigation Panel */}
        {mobileMenuOpen && (
          <div className="md:hidden px-4 pt-2 pb-4 space-y-1 bg-white/95 border-b border-green-100 shadow-lg animate-fade-in">
            <div className="mb-2 px-3">
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-primary-light/20 text-primary border border-primary-light/40">
                Powered by Google Gemini
              </span>
            </div>
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => handleNavClick(item.id)}
                  className={`flex items-center space-x-3 w-full px-4 py-3 rounded-xl text-left text-base font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-primary text-white"
                      : "text-primary-dark/80 hover:bg-primary/5 hover:text-primary"
                  }`}
                  aria-current={isActive ? "page" : undefined}
                >
                  <Icon className="h-5 w-5" />
                  <span>{item.label}</span>
                </button>
              );
            })}
          </div>
        )}
      </header>

      {/* Main Container */}
      <main id="main-content" className="flex-grow max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 focus:outline-none">
        {children}
      </main>

      {/* Footer */}
      <footer className="w-full py-6 mt-auto border-t border-green-500/10 bg-white/50 text-center text-xs text-primary-dark/60">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between space-y-2 sm:space-y-0">
          <div>
            🌱 <span className="font-semibold text-primary">EcoTrack</span> · Powered by Google Gemini AI · Built for a sustainable future
          </div>
          <div className="flex space-x-4">
            <span className="hover:text-primary transition-colors cursor-pointer">Privacy</span>
            <span className="hover:text-primary transition-colors cursor-pointer">Terms</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
