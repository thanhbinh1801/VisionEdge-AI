/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'monitoring-base': '#020617',
        'monitoring-card': '#0f172a',
        'monitoring-hover': '#1e293b',
        'monitoring-border': '#334155',
      },
    },
  },
  plugins: [],
}
