import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: "#4D3A4D",
          darker: "#362636",
          darkest: "#241824",
          accent: "#BE5CA9",
          accentHover: "#AA4995",
          muted: "#D59CC5",
          light: "#EADADA",
          surface: "#FBF9FB",
        },
        semantic: {
          verified: "#16A34A",
          verifiedBg: "#ECFDF5",
          verifiedBorder: "#A7F3D0",
          inferred: "#D97706",
          inferredBg: "#FFFBEB",
          inferredBorder: "#FDE68A",
          conflicted: "#DC2626",
          conflictedBg: "#FEF2F2",
          conflictedBorder: "#FECACA",
          unknown: "#6B7280",
          unknownBg: "#F3F4F6",
          unknownBorder: "#E5E7EB",
          unsupported: "#9333EA",
          unsupportedBg: "#FAF5FF",
          unsupportedBorder: "#E9D5FF",
        },
      },
      fontFamily: {
        sans: ["var(--font-ibm-plex-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-ibm-plex-mono)", "monospace"],
      },
      boxShadow: {
        subtle: "0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)",
        card: "0 4px 12px rgba(77, 58, 77, 0.06), 0 1px 3px rgba(0, 0, 0, 0.04)",
        elevation: "0 10px 25px -5px rgba(77, 58, 77, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.04)",
      },
    },
  },
  plugins: [],
};

export default config;
