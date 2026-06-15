import { describe, it, expect } from "vitest"
import { estimateMonthlyFootprint } from "../utils/emissions"

describe("estimateMonthlyFootprint", () => {
  it("should yield only diet contribution when other transport, energy, and shopping factors are zeroed", () => {
    const result = estimateMonthlyFootprint({
      transport_mode: "car",
      transport_km_per_week: 0,
      diet_type: "vegan",
      energy_kwh_per_month: 0,
      shopping_level: "low",
    })
    // vegan (55) + shopping low (30) = 85
    expect(result.transport).toBe(0)
    expect(result.diet).toBe(55)
    expect(result.shopping).toBe(30)
    expect(result.energy).toBe(0)
    expect(result.total).toBe(85)
  })

  it("should calculate car 100km/week to be approximately 91 kg CO2 transport emissions", () => {
    const result = estimateMonthlyFootprint({
      transport_mode: "car",
      transport_km_per_week: 100,
      diet_type: "vegan",
      energy_kwh_per_month: 0,
      shopping_level: "low",
    })
    // 100 * 4.33 * 0.21 = 90.93
    expect(result.transport).toBeCloseTo(90.93, 1)
  })

  it("should ensure the total is exactly equal to the sum of transport, diet, energy, and shopping parts", () => {
    const result = estimateMonthlyFootprint({
      transport_mode: "flight",
      transport_km_per_week: 250,
      diet_type: "vegetarian",
      energy_kwh_per_month: 120,
      shopping_level: "medium",
    })
    const sum = result.transport + result.diet + result.energy + result.shopping
    expect(result.total).toBeCloseTo(sum, 2)
  })

  it("should calculate meat heavy footprint total to be strictly greater than vegan footprint total when other factors match", () => {
    const veganResult = estimateMonthlyFootprint({
      transport_mode: "bus",
      transport_km_per_week: 50,
      diet_type: "vegan",
      energy_kwh_per_month: 100,
      shopping_level: "medium",
    })
    const meatHeavyResult = estimateMonthlyFootprint({
      transport_mode: "bus",
      transport_km_per_week: 50,
      diet_type: "meat_heavy",
      energy_kwh_per_month: 100,
      shopping_level: "medium",
    })
    expect(meatHeavyResult.total).toBeGreaterThan(veganResult.total)
    expect(meatHeavyResult.diet).toBe(230)
    expect(veganResult.diet).toBe(55)
  })
})
