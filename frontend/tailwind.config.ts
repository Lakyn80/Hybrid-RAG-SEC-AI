import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./hooks/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "rgb(var(--color-ink) / <alpha-value>)",
        canvas: "rgb(var(--color-canvas) / <alpha-value>)",
        paper: "rgb(var(--color-paper) / <alpha-value>)",
        line: "rgb(var(--color-line) / <alpha-value>)",
        brand: {
          DEFAULT: "rgb(var(--color-brand) / <alpha-value>)",
          soft: "rgb(var(--color-brand-soft) / <alpha-value>)",
        },
        signal: {
          blue: "rgb(var(--color-signal-blue) / <alpha-value>)",
          green: "rgb(var(--color-signal-green) / <alpha-value>)",
          amber: "rgb(var(--color-signal-amber) / <alpha-value>)",
          red: "rgb(var(--color-signal-red) / <alpha-value>)",
        },
      },
      fontFamily: {
        sans: ["var(--font-space-grotesk)"],
        mono: ["var(--font-ibm-plex-mono)"],
      },
      boxShadow: {
        panel: "0 22px 50px rgba(0, 0, 0, 0.48)",
        focus: "0 0 0 2px rgba(248, 250, 252, 0.18)",
      },
      backgroundImage: {
        "hero-grid":
          "linear-gradient(to right, rgba(71, 85, 105, 0.22) 1px, transparent 1px), linear-gradient(to bottom, rgba(71, 85, 105, 0.22) 1px, transparent 1px)",
      },
      animation: {
        pulseGlow: "pulseGlow 1.8s ease-in-out infinite",
        slideFade: "slideFade 0.45s ease-out both",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { boxShadow: "0 0 0 0 rgba(248, 250, 252, 0.22)" },
          "50%": { boxShadow: "0 0 0 10px rgba(248, 250, 252, 0)" },
        },
        slideFade: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
