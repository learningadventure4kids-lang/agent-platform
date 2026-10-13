/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // Styles are injected into a Shadow DOM root at runtime (see src/index.tsx),
  // which already fully isolates them from the host page in both directions,
  // so no class-name prefix is needed here.
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: "#15141F", soft: "#201F2E", border: "#2C2A3D" },
        parchment: { DEFAULT: "#F6F1E6" },
        brass: { DEFAULT: "#C08A3E", light: "#DDA85F" },
        dust: { DEFAULT: "#9B98AE", light: "#C7C4D6" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
