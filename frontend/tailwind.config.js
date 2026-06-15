/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#16a34a",
        "primary-dark": "#14532d",
        "primary-light": "#86efac",
        surface: "#f0fdf4",
        dark: "#052e16",
        accent: "#f59e0b",
        danger: "#ef4444",
      },
      fontFamily: {
        display: ["Plus Jakarta Sans", "sans-serif"],
        body: ["Inter", "sans-serif"],
      },
    },
  },
  plugins: [],
}
