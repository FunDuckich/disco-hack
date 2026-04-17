/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'disco-dark': '#05050a',
        'disco-cyan': '#00ffff',
        'disco-magenta': '#ff00ff',
        'disco-purple': '#9d00ff',
      },
      boxShadow: {
        'glow-cyan': '0 0 20px rgba(0, 255, 255, 0.4)',
        'glow-magenta': '0 0 20px rgba(255, 0, 255, 0.4)',
      }
    },
  },
  plugins: [],
}