/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "Roboto", "sans-serif"],
      },
      colors: {
        sidebar: "#0a192f",
        "sidebar-hover": "#112240",
        accent: "#1a73e8",
        "accent-hover": "#1557b0",
        canvas: "#f0f2f5",
      },
    },
  },
  plugins: [],
};
