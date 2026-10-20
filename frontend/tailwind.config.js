export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: { navy: { 950: "#050d1c", 900: "#08162b", 800: "#0d2240", 700: "#16345e" }, gold: { 300: "#f1d27a", 400: "#e3b94a", 500: "#c99a2e", 600: "#a47a1f" }, parchment: { 100: "#f6ecd2", 200: "#ead9ae", 300: "#d8c08a" }, ink: "#3a2a12" },
    fontFamily: { display: ["Palatino Linotype", "Palatino", "Book Antiqua", "Georgia", "serif"], body: ["Georgia", "Cambria", "serif"], mono: ["ui-monospace", "Menlo", "monospace"] },
  } },
  plugins: [],
};
