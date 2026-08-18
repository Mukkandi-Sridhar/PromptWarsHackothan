/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: '#0F2027',
        'ink-raise': '#16303A',
        bone: '#E9E6DF',
        'bone-dim': '#8FA3A8',
        signal: '#FFB020',
        probe: '#4FD1D9',
        reject: '#FF6B5A',
        grid: '#234049',
      },
      fontFamily: {
        display: ['Space Grotesk', 'sans-serif'],
        body: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
