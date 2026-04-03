import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        dark: {
          primary:           "#f97316",  // amber — playhead, active pads
          "primary-focus":   "#ea580c",
          "primary-content": "#0a0a0a",
          secondary:         "#a855f7",  // violet — lock indicators
          accent:            "#22d3ee",  // cyan — misc highlights
          neutral:           "#1a1a1a",
          "neutral-content": "#737373",
          "base-100":        "#0a0a0a",  // near-black background
          "base-200":        "#111111",
          "base-300":        "#1a1a1a",
          "base-content":    "#e5e5e5",
          info:              "#0ea5e9",
          success:           "#22c55e",
          warning:           "#f97316",
          error:             "#ef4444",
        },
        light: {
          primary:           "#ea580c",
          "primary-focus":   "#c2410c",
          "primary-content": "#ffffff",
          secondary:         "#7c3aed",
          accent:            "#0891b2",
          neutral:           "#f5f5f5",
          "neutral-content": "#525252",
          "base-100":        "#ffffff",
          "base-200":        "#f5f5f5",
          "base-300":        "#e5e5e5",
          "base-content":    "#0a0a0a",
          info:              "#0369a1",
          success:           "#15803d",
          warning:           "#c2410c",
          error:             "#dc2626",
        },
      },
    ],
    darkTheme: "dark",
    base: true,
    styled: true,
    utils: true,
    logs: false,
  },
};

export default config;
