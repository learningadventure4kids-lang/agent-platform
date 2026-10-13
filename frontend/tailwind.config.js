/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#15141F", soft: "#201F2E", border: "#2C2A3D" },
        parchment: { DEFAULT: "#F6F1E6", dim: "#EDE6D6" },
        brass: { DEFAULT: "#C08A3E", light: "#DDA85F", dark: "#96692A" },
        dust: { DEFAULT: "#9B98AE", light: "#C7C4D6" },
        plum: { DEFAULT: "#4B4470" },
      },
      fontFamily: {
        display: ["'Fraunces'", "ui-serif", "Georgia", "serif"],
        sans: ["'Inter'", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
