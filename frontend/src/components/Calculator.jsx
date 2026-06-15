import React, { useState, useMemo } from "react";
import { Car, Bus, Plane, HelpCircle, Loader2 } from "lucide-react";
import { estimateMonthlyFootprint } from "../utils/emissions";

export default function Calculator({ onCalculate, isCalculating, error, clearError }) {
  const [activeStep, setActiveStep] = useState(1);
  const [formData, setFormData] = useState({
    transport_mode: "car",
    transport_km_per_week: 100,
    diet_type: "vegetarian",
    energy_kwh_per_month: 200,
    shopping_level: "medium",
  });

  const [validationErrors, setValidationErrors] = useState({});

  // Compute live preview estimates client-side
  const livePreview = useMemo(() => {
    return estimateMonthlyFootprint(formData);
  }, [formData]);

  const updateField = (name, value) => {
    setFormData((prev) => ({ ...prev, [name]: value }));
    // Clear validation error when field is updated
    if (validationErrors[name]) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[name];
        return next;
      });
    }
    if (error) clearError();
  };

  const validateStep = (step) => {
    const errors = {};
    if (step === 1) {
      const km = parseFloat(formData.transport_km_per_week);
      if (isNaN(km) || km < 0 || km > 5000) {
        errors.transport_km_per_week = "Weekly travel distance must be between 0 and 5,000 km.";
      }
    } else if (step === 2) {
      const energy = parseFloat(formData.energy_kwh_per_month);
      if (isNaN(energy) || energy < 0 || energy > 10000) {
        errors.energy_kwh_per_month = "Monthly energy usage must be between 0 and 10,000 kWh.";
      }
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleNext = () => {
    if (validateStep(activeStep)) {
      setActiveStep((prev) => prev + 1);
    }
  };

  const handleBack = () => {
    setActiveStep((prev) => prev - 1);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep(3)) return;
    try {
      await onCalculate(formData);
    } catch (err) {
      console.error("Footprint calculation failed", err);
    }
  };

  return (
    <div className="max-w-2xl mx-auto bg-white rounded-3xl border border-green-500/10 shadow-xl glow-card overflow-hidden">
      {/* Form Progress Header */}
      <div className="bg-gradient-to-r from-primary-dark to-primary px-8 py-6 text-white">
        <h2 className="font-display font-bold text-2xl">Emissions Calculator</h2>
        <p className="text-white/80 text-sm mt-1">Estimate your footprint in 3 simple steps</p>
        
        {/* Progress Bar */}
        <div className="mt-6 flex items-center space-x-2" aria-label="Step progress">
          {[1, 2, 3].map((step) => (
            <React.Fragment key={step}>
              <div
                className={`h-8 w-8 rounded-full flex items-center justify-center font-bold text-xs border transition-all duration-300 ${
                  activeStep >= step
                    ? "bg-white text-primary border-white"
                    : "bg-primary-dark/40 text-white/50 border-white/20"
                }`}
              >
                {step}
              </div>
              {step < 3 && (
                <div
                  className={`flex-grow h-1 rounded transition-all duration-300 ${
                    activeStep > step ? "bg-white" : "bg-primary-dark/40"
                  }`}
                />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-8">
        {error && (
          <div
            className="mb-6 p-4 bg-danger/10 border border-danger/20 rounded-2xl text-danger text-sm flex items-center"
            role="alert"
          >
            {error}
          </div>
        )}

        {/* STEP 1: TRANSPORT */}
        {activeStep === 1 && (
          <div className="space-y-6">
            <h3 className="text-lg font-bold text-primary-dark">Step 1: Transport & Mobility</h3>
            
            {/* Mode Selectors */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { id: "car", label: "Car 🚗", icon: Car },
                { id: "bus", label: "Bus/Metro 🚌", icon: Bus },
                { id: "flight", label: "Flight ✈️", icon: Plane },
              ].map((mode) => {
                const Icon = mode.icon;
                const isSelected = formData.transport_mode === mode.id;
                return (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => updateField("transport_mode", mode.id)}
                    className={`flex flex-col items-center justify-center p-5 rounded-2xl border transition-all duration-200 ${
                      isSelected
                        ? "bg-primary/5 border-primary text-primary shadow-sm ring-1 ring-primary"
                        : "border-gray-200 hover:border-primary/50 text-gray-600"
                    }`}
                  >
                    <Icon className="h-6 w-6 mb-2" />
                    <span className="text-xs font-semibold">{mode.label}</span>
                  </button>
                );
              })}
            </div>

            {/* Range Slider and Synced Input */}
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label
                  htmlFor="transport_km"
                  className="block text-sm font-semibold text-gray-700"
                >
                  Weekly travel distance
                </label>
                <div className="flex items-center space-x-1">
                  <input
                    id="transport_km_number"
                    type="number"
                    value={formData.transport_km_per_week}
                    onChange={(e) => updateField("transport_km_per_week", e.target.value)}
                    className="w-20 px-2 py-1 text-right border border-gray-300 rounded-lg text-sm focus:outline-none"
                    min="0"
                    max="5000"
                    aria-describedby="transport_km_error"
                  />
                  <span className="text-xs text-gray-500 font-medium">km</span>
                </div>
              </div>

              <input
                id="transport_km"
                type="range"
                min="0"
                max="5000"
                step="10"
                value={formData.transport_km_per_week}
                onChange={(e) => updateField("transport_km_per_week", e.target.value)}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary"
              />

              {validationErrors.transport_km_per_week && (
                <p id="transport_km_error" className="text-danger text-xs mt-1" role="alert">
                  {validationErrors.transport_km_per_week}
                </p>
              )}
            </div>

            {/* Live Preview Metric */}
            <div className="bg-surface border border-green-500/10 rounded-2xl p-4 flex justify-between items-center">
              <span className="text-xs text-primary-dark/80 font-medium">Live Transport Estimate:</span>
              <span className="font-bold text-primary">{livePreview.transport} kg CO2e/mo</span>
            </div>
          </div>
        )}

        {/* STEP 2: LIFESTYLE & CONSUMPTION */}
        {activeStep === 2 && (
          <div className="space-y-6">
            <h3 className="text-lg font-bold text-primary-dark">Step 2: Lifestyle & Consumption</h3>

            {/* Diet Cards */}
            <div className="space-y-2">
              <span className="block text-sm font-semibold text-gray-700 mb-2">Diet type</span>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { id: "vegan", label: "Vegan 🥦", desc: "No animal products" },
                  { id: "vegetarian", label: "Vegetarian 🥗", desc: "No meat/fish" },
                  { id: "omnivore", label: "Omnivore 🍽️", desc: "Balanced meat & plants" },
                  { id: "meat_heavy", label: "Meat-Heavy 🥩", desc: "Regular daily meat" },
                ].map((diet) => {
                  const isSelected = formData.diet_type === diet.id;
                  return (
                    <button
                      key={diet.id}
                      type="button"
                      onClick={() => updateField("diet_type", diet.id)}
                      className={`flex flex-col items-start p-4 rounded-xl border text-left transition-all duration-200 ${
                        isSelected
                          ? "bg-primary/5 border-primary shadow-sm ring-1 ring-primary"
                          : "border-gray-200 hover:border-primary/50"
                      }`}
                    >
                      <span className="text-sm font-bold text-primary-dark">{diet.label}</span>
                      <span className="text-[10px] text-gray-500 mt-1">{diet.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Energy Input with Help Tooltip */}
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <label
                  htmlFor="energy_kwh"
                  className="block text-sm font-semibold text-gray-700"
                >
                  Monthly Electricity Usage
                </label>
                <div className="relative group">
                  <HelpCircle className="h-4 w-4 text-gray-400 cursor-pointer" />
                  <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 hidden group-hover:block w-48 bg-gray-900 text-white text-[10px] rounded-lg p-2 shadow-lg z-20 leading-snug">
                    Refer to your utility bill. Average Indian household uses ~150-250 kWh/month.
                  </div>
                </div>
              </div>

              <div className="relative">
                <input
                  id="energy_kwh"
                  type="number"
                  min="0"
                  max="10000"
                  value={formData.energy_kwh_per_month}
                  onChange={(e) => updateField("energy_kwh_per_month", e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:border-primary text-sm"
                  aria-describedby="energy_kwh_error"
                />
                <span className="absolute right-4 top-1/2 -translate-y-1/2 text-xs text-gray-500 font-medium">
                  kWh/mo
                </span>
              </div>
              {validationErrors.energy_kwh_per_month && (
                <p id="energy_kwh_error" className="text-danger text-xs mt-1" role="alert">
                  {validationErrors.energy_kwh_per_month}
                </p>
              )}
            </div>

            {/* Shopping Habits */}
            <div className="space-y-2">
              <span className="block text-sm font-semibold text-gray-700 mb-2">
                Shopping & consumption levels
              </span>
              <div className="grid grid-cols-3 gap-3">
                {[
                  { id: "low", label: "Low", desc: "Minimalist buying" },
                  { id: "medium", label: "Medium", desc: "Average buyer" },
                  { id: "high", label: "High", desc: "Frequent purchases" },
                ].map((level) => {
                  const isSelected = formData.shopping_level === level.id;
                  return (
                    <button
                      key={level.id}
                      type="button"
                      onClick={() => updateField("shopping_level", level.id)}
                      className={`flex flex-col items-center p-3 rounded-xl border text-center transition-all duration-200 ${
                        isSelected
                          ? "bg-primary/5 border-primary shadow-sm ring-1 ring-primary"
                          : "border-gray-200 hover:border-primary/50"
                      }`}
                    >
                      <span className="text-xs font-bold text-primary-dark">{level.label}</span>
                      <span className="text-[9px] text-gray-500 mt-1">{level.desc}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* STEP 3: REVIEW & SUBMIT */}
        {activeStep === 3 && (
          <div className="space-y-6">
            <h3 className="text-lg font-bold text-primary-dark">Step 3: Review Estimates</h3>
            
            <div className="border border-green-500/10 rounded-2xl overflow-hidden shadow-sm">
              <table className="min-w-full divide-y divide-gray-100 text-sm">
                <thead className="bg-surface">
                  <tr>
                    <th className="px-4 py-3 text-left font-semibold text-primary-dark text-xs">Category</th>
                    <th className="px-4 py-3 text-left font-semibold text-primary-dark text-xs">Selection</th>
                    <th className="px-4 py-3 text-right font-semibold text-primary-dark text-xs">Estimated Monthly CO2e</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 bg-white">
                  <tr>
                    <td className="px-4 py-3 font-medium text-gray-900">Transport</td>
                    <td className="px-4 py-3 text-gray-500 capitalize">{formData.transport_mode} ({formData.transport_km_per_week} km/wk)</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">{livePreview.transport} kg</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-gray-900">Diet</td>
                    <td className="px-4 py-3 text-gray-500 capitalize">{formData.diet_type}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">{livePreview.diet} kg</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-gray-900">Energy</td>
                    <td className="px-4 py-3 text-gray-500">{formData.energy_kwh_per_month} kWh/mo</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">{livePreview.energy} kg</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 font-medium text-gray-900">Shopping</td>
                    <td className="px-4 py-3 text-gray-500 capitalize">{formData.shopping_level}</td>
                    <td className="px-4 py-3 text-right font-semibold text-gray-900">{livePreview.shopping} kg</td>
                  </tr>
                  <tr className="bg-primary/5">
                    <td className="px-4 py-3 font-bold text-primary-dark" colSpan="2">Estimated Monthly Total</td>
                    <td className="px-4 py-3 text-right font-bold text-primary">{livePreview.total} kg CO2e</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div className="bg-surface p-4 rounded-xl border border-green-500/10 text-xs text-primary-dark/80 leading-relaxed">
              🌍 This calculation is an estimate. Final personalized carbon audits and reduction goals will be calibrated via Google Vertex AI Gemini.
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="mt-8 pt-6 border-t border-gray-100 flex justify-between">
          {activeStep > 1 ? (
            <button
              type="button"
              onClick={handleBack}
              disabled={isCalculating}
              className="px-6 py-3 border border-gray-200 text-gray-600 rounded-xl font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors text-sm"
            >
              Back
            </button>
          ) : (
            <div />
          )}

          {activeStep < 3 ? (
            <button
              type="button"
              onClick={handleNext}
              className="px-6 py-3 bg-primary text-white rounded-xl font-medium hover:bg-primary-dark shadow-sm hover:shadow transition-all duration-200 text-sm"
            >
              Next Step
            </button>
          ) : (
            <button
              type="submit"
              disabled={isCalculating}
              className="px-6 py-3 bg-primary hover:bg-primary-dark text-white font-semibold rounded-xl flex items-center justify-center space-x-2 shadow-sm hover:shadow-md disabled:opacity-50 transition-all duration-200 text-sm"
            >
              {isCalculating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Calculating with Google AI...</span>
                </>
              ) : (
                <span>Calculate My Footprint</span>
              )}
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
