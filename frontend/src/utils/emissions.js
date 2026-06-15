export const TRANSPORT_FACTORS = { car: 0.21, bus: 0.089, flight: 0.255 };
export const DIET_FACTORS = { vegan: 55, vegetarian: 85, omnivore: 150, meat_heavy: 230 };
export const ENERGY_FACTOR = 0.82;
export const SHOPPING_FACTORS = { low: 30, medium: 70, high: 130 };
export const WEEKS_PER_MONTH = 4.33;

/**
 * Calculates live footprint previews on the client side using current inputs.
 */
export function estimateMonthlyFootprint({
  transport_mode,
  transport_km_per_week,
  diet_type,
  energy_kwh_per_month,
  shopping_level,
}) {
  const transport =
    (parseFloat(transport_km_per_week) || 0) *
    WEEKS_PER_MONTH *
    (TRANSPORT_FACTORS[transport_mode] || 0);
  const diet = DIET_FACTORS[diet_type] || 0;
  const energy = (parseFloat(energy_kwh_per_month) || 0) * ENERGY_FACTOR;
  const shopping = SHOPPING_FACTORS[shopping_level] || 0;

  return {
    transport: Math.round(transport * 100) / 100,
    diet: Math.round(diet * 100) / 100,
    energy: Math.round(energy * 100) / 100,
    shopping: Math.round(shopping * 100) / 100,
    total: Math.round((transport + diet + energy + shopping) * 100) / 100,
  };
}

/**
 * Maps footprint total to a grade and text color.
 */
export function getFootprintLabel(total) {
  if (total < 100) return { label: "Excellent", color: "text-primary" };
  if (total < 200) return { label: "Good", color: "text-green-500" };
  if (total < 350) return { label: "Average", color: "text-amber-500" };
  return { label: "High", color: "text-red-500" };
}
