/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      boxShadow: {
        cockpit: "0 24px 70px rgba(15, 23, 42, 0.12)",
        "cockpit-soft": "0 14px 38px rgba(15, 23, 42, 0.08)",
        "cockpit-button": "0 10px 24px rgba(37, 99, 235, 0.22)"
      },
      colors: {
        cockpit: {
          ink: "#0f172a",
          muted: "#64748b",
          bg: "#eef4f8",
          blue: "#2563eb",
          cyan: "#0f766e"
        }
      }
    }
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: false,
    logs: false
  }
};
